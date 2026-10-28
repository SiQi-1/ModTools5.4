#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_game.py - 文明6 启动/窗口化/新建对局/对局内操作的共享逻辑。

职责：
- 定位游戏安装目录（默认自动探测 Steam 库，可用 CIV6_GAME_DIR/--game-dir 覆盖）、
  用户配置目录、日志目录；
- 备份并改写 AppOptions.txt / GraphicsOptions.txt，使游戏以低负载窗口模式运行；
- 直接启动 CivilizationVI(_DX12).exe（绕过启动器），等待 FireTuner 端口；
- 通过 FireTuner 在前端 Lua 状态里设置文明/领袖并 Network.HostGame 开新局；
- 等待 GameCore 就绪后读取状态、移动单位、建立城市、结束回合、退出游戏；
- 关闭游戏并还原被改写的配置。

依赖：civ6_tuner（同目录），标准库；截图主体在 civ6_win.py。
仅支持 Windows。所有改动前先备份，restore_options() 负责还原。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from civ6_tuner import TunerClient, TunerError

STEAM_APP_ID = "289070"
GAME_DIR_NAME = "Sid Meier's Civilization VI"
USER_DIR_NAME = "Sid Meier's Civilization VI"
EXE_DX11 = r"Base\Binaries\Win64Steam\CivilizationVI.exe"
EXE_DX12 = r"Base\Binaries\Win64Steam\CivilizationVI_DX12.exe"

STATE_DIR = Path(os.environ.get("CIV6_AI_PLAY_STATE", Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "civ6_ai_play"))
BACKUP_DIR = STATE_DIR / "backups"
STATE_JSON = STATE_DIR / "state.json"

# 测试默认用小窗口：窗口化 1280x720 可降低负载/温度，足够验证玩法（可用 --width/--height 覆盖）。
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720


# ---------------------------------------------------------------------------
# 路径探测
# ---------------------------------------------------------------------------
# 手动覆盖：--game-dir / set_game_dir_override() > CIV6_GAME_DIR 环境变量 > Steam 自动探测。
_GAME_DIR_OVERRIDE: Path | None = None


def set_game_dir_override(path: str | os.PathLike | None) -> None:
    """手动指定游戏根目录（--game-dir 或外部调用）；传 None 清除覆盖。"""
    global _GAME_DIR_OVERRIDE
    _GAME_DIR_OVERRIDE = (Path(os.path.expandvars(os.path.expanduser(str(path))))
                          if path else None)


def _env_game_dir() -> Path | None:
    raw = os.environ.get("CIV6_GAME_DIR", "").strip().strip('"')
    return Path(os.path.expandvars(os.path.expanduser(raw))) if raw else None


def _steam_roots() -> list[Path]:
    roots: list[Path] = []
    try:
        import winreg  # type: ignore
        for hive, key, value in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam", "SteamPath"),
        ]:
            try:
                with winreg.OpenKey(hive, key) as k:
                    p = winreg.QueryValueEx(k, value)[0]
                    if p:
                        roots.append(Path(p))
            except OSError:
                pass
    except ImportError:
        pass
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env)
        if base:
            roots.append(Path(base) / "Steam")
    for drive in "CDEFGH":
        roots.append(Path(drive + r":\Steam"))
        roots.append(Path(drive + r":\SteamLibrary"))
        roots.append(Path(drive + r":\Program Files (x86)\Steam"))
    uniq, seen = [], set()
    for r in roots:
        s = str(r).lower()
        if s not in seen:
            seen.add(s)
            uniq.append(r)
    return uniq


def _game_dir_ok(d: Path) -> bool:
    return (d / EXE_DX12).exists() or (d / EXE_DX11).exists()


def find_game_dir_detail() -> tuple[Path | None, str]:
    """返回 (游戏根目录, 来源说明)。

    优先级：--game-dir/set_game_dir_override() → CIV6_GAME_DIR → Steam 自动探测。
    显式覆盖无效时**不**回退自动探测，避免误用/误写到别的安装目录；调用方可用
    来源说明在错误信息里提示用户修正覆盖。
    """
    if _GAME_DIR_OVERRIDE is not None:
        if _game_dir_ok(_GAME_DIR_OVERRIDE):
            return _GAME_DIR_OVERRIDE, "cli:--game-dir"
        return None, "cli:--game-dir（无效：%s 下未找到 %s / %s）" % (
            _GAME_DIR_OVERRIDE, EXE_DX11, EXE_DX12)
    env_dir = _env_game_dir()
    if env_dir is not None:
        if _game_dir_ok(env_dir):
            return env_dir, "env:CIV6_GAME_DIR"
        return None, "env:CIV6_GAME_DIR（无效：%s 下未找到 %s / %s）" % (
            env_dir, EXE_DX11, EXE_DX12)
    for root in _steam_roots():
        libs = [root]
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            try:
                text = vdf.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(r'"path"\s*"([^"]+)"', text):
                    libs.append(Path(m.group(1).replace("\\\\", "\\")))
            except OSError:
                pass
        for lib in libs:
            cand = lib / "steamapps" / "common" / GAME_DIR_NAME
            if _game_dir_ok(cand):
                return cand, "auto:steam"
    return None, "none（未设置 CIV6_GAME_DIR，且 Steam 自动探测未命中）"


def find_game_dir() -> Path | None:
    return find_game_dir_detail()[0]


def game_dir_source() -> str:
    """当前游戏目录来源（用于 env 输出标注）。"""
    return find_game_dir_detail()[1]


def user_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "Firaxis Games" / USER_DIR_NAME


def logs_dir() -> Path:
    return user_dir() / "Logs"


def mods_db_path() -> Path:
    return user_dir() / "Mods.sqlite"


def app_options_path() -> Path:
    return user_dir() / "AppOptions.txt"


def graphics_options_path() -> Path:
    return user_dir() / "GraphicsOptions.txt"


# ---------------------------------------------------------------------------
# 进程 / 启动
# ---------------------------------------------------------------------------
def running_game_processes() -> list[dict]:
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    procs = []
    for line in out.stdout.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if not parts:
            continue
        name = parts[0].strip('"').lower()
        if name.startswith("civilizationvi"):
            pid = parts[1].strip('"') if len(parts) > 1 else ""
            procs.append({"name": name, "pid": pid})
    return procs


def game_running() -> bool:
    return bool(running_game_processes())


def _backup(path: Path, tag: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"{path.stem}-{tag}-{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    state = _load_state()
    state.setdefault("backups", {})[str(path)] = str(dest)
    _save_state(state)
    return dest


def _load_state() -> dict:
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _set_ini_value(lines: list[str], section: str, key: str, value: str) -> tuple[list[str], bool]:
    out = list(lines)
    in_section = False
    section_start = None
    for i, raw in enumerate(out):
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            if section_start is not None and not in_section:
                break
            in_section = line.lower() == f"[{section.lower()}]"
            if in_section:
                section_start = i
            continue
        if in_section:
            m = re.match(r"^(\s*)([A-Za-z_][\w]*)(\s+)(.*)$", raw)
            if m and m.group(2).lower() == key.lower():
                out[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{value}"
                return out, True
    if section_start is None:
        out.append(f"[{section}]")
        out.append(f"{key} {value}")
        return out, False
    insert_at = section_start + 1
    while insert_at < len(out) and not out[insert_at].strip().startswith("["):
        insert_at += 1
    out.insert(insert_at, f"{key} {value}")
    return out, False


def ensure_windowed(width: int = WINDOW_WIDTH, height: int = WINDOW_HEIGHT,
                    low_graphics: bool = True) -> dict:
    """备份并改写选项：窗口化 + 低画质。

    重要：重复调用时保留"最初一次"的备份（state.json 已记录的原始文件），
    否则连续多次 launch 会把已改写的配置当成原始配置备份，restore 就还原不到
    用户最初的状态。
    """
    if game_running():
        raise RuntimeError("游戏正在运行，拒绝改写配置；请先退出游戏。")
    state = _load_state()
    prev = state.get("options", {}) if isinstance(state.get("options"), dict) else {}

    def _original_backup(path: Path, key: str) -> Path:
        cur = prev.get(key)
        if cur and Path(cur).exists():
            return Path(cur)
        return _backup(path, "civ6ai")

    info: dict = {"app_options": str(app_options_path()), "graphics_options": None}
    ap = app_options_path()
    if ap.exists():
        backup = _original_backup(ap, "app_options_backup")
        lines = ap.read_text(encoding="utf-8", errors="replace").splitlines()
        lines, _ = _set_ini_value(lines, "Video", "FullScreen", "0")
        lines, _ = _set_ini_value(lines, "Video", "RenderWidth", str(width))
        lines, _ = _set_ini_value(lines, "Video", "RenderHeight", str(height))
        lines, _ = _set_ini_value(lines, "Debug", "EnableTuner", "1")
        ap.write_text("\n".join(lines) + "\n", encoding="utf-8")
        info["app_options_backup"] = str(backup)
    if low_graphics:
        gp = graphics_options_path()
        if gp.exists():
            backup = _original_backup(gp, "graphics_options_backup")
            lines = gp.read_text(encoding="utf-8", errors="replace").splitlines()
            for section, key, value in [
                ("Video", "PerformanceImpact", "-1"),
                ("Video", "MSAA", "0"),
                ("Video", "VSync", "0"),
                ("Video", "ShadowMapResolution", "1024"),
                ("Video", "AODepthResolution", "1024"),
                ("Video", "AORenderResolution", "1024"),
                ("Terrain", "TerrainQuality", "1"),
                ("General", "ClutterDetailLevel", "0"),
                ("General", "VFXDetailLevel", "0"),
                ("AO", "EnableAO", "0"),
                ("Bloom", "EnableBloom", "0"),
                ("Shadows", "EnableShadows", "0"),
                ("DynamicLighting", "EnableDynamicLighting", "0"),
                ("CloudShadows", "EnableCloudShadows", "0"),
                ("Leaders", "Quality", "1"),
            ]:
                lines, _ = _set_ini_value(lines, section, key, value)
            gp.write_text("\n".join(lines) + "\n", encoding="utf-8")
            info["graphics_options"] = str(gp)
            info["graphics_options_backup"] = str(backup)
    merged = dict(prev)
    merged.update({k: v for k, v in info.items() if v})
    _save_state({"options": merged, "updated": time.strftime("%Y-%m-%d %H:%M:%S")})
    return info


def restore_options() -> list[str]:
    state = _load_state()
    restored = []
    for key in ("app_options_backup", "graphics_options_backup"):
        src = state.get("options", {}).get(key)
        if not src:
            continue
        target = app_options_path() if key.startswith("app") else graphics_options_path()
        if Path(src).exists():
            shutil.copy2(src, target)
            restored.append(str(target))
    state.pop("options", None)
    _save_state(state)
    return restored


def launch(exe: str = "dx12", wait: bool = False, timeout: float = 120.0) -> subprocess.Popen:
    gd = find_game_dir()
    if gd is None:
        raise RuntimeError("未找到文明6安装目录（%s）；可用 --game-dir 或设置 CIV6_GAME_DIR "
                           "指向游戏根目录" % game_dir_source())
    rel = EXE_DX12 if exe.lower() == "dx12" else EXE_DX11
    exe_path = gd / rel
    if not exe_path.exists():
        hint = ""
        other = gd / (EXE_DX11 if exe.lower() == "dx12" else EXE_DX12)
        if other.exists():
            hint = "；该安装目录只有 %s，可用 --exe %s 启动" % (
                other.name, "dx11" if other.name == "CivilizationVI.exe" else "dx12")
        raise RuntimeError(f"找不到可执行文件: {exe_path}{hint}")
    if game_running():
        raise RuntimeError("已有文明6进程在运行，请先关闭")
    proc = subprocess.Popen([str(exe_path)], cwd=str(gd),
                            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                            close_fds=True)
    if wait:
        wait_for_tuner(timeout=timeout)
    return proc


def wait_for_tuner(timeout: float = 180.0, interval: float = 2.0) -> TunerClient:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        client = TunerClient()
        try:
            client.connect(timeout=3.0)
            return client
        except (ConnectionRefusedError, OSError, TunerError) as exc:
            last = exc
            client.close()
            time.sleep(interval)
    raise TimeoutError(f"等待 FireTuner 端口超时（{timeout}s）: {last}")


def wait_for_state(client: TunerClient, name_part: str, timeout: float = 180.0,
                   interval: float = 2.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        client.refresh_states()
        idx = client.find_state(name_part)
        if idx is not None:
            return idx
        time.sleep(interval)
    raise TimeoutError(f"等待 Lua 状态超时: {name_part}")


# ---------------------------------------------------------------------------
# Lua 片段
# ---------------------------------------------------------------------------
_EMIT = r'''
local function emit(k, v)
    local ok, s = pcall(function() return tostring(v) end)
    if not ok then s = "<tostring-failed>" end
    print("@@CIV6AI:" .. tostring(k) .. "=" .. s)
end
local function safe(k, fn)
    local ok, v = pcall(fn)
    if ok then emit(k, v) else emit(k, "<error:" .. tostring(v) .. ">") end
    return ok, v
end
'''


def lua_probe_frontend() -> str:
    return _EMIT + r'''
local ok, err = pcall(function()
    safe("inFrontend", function() return UI.IsInFrontEnd() end)
    safe("localPlayerID", function() return Network.GetLocalPlayerID() end)
    safe("gameState", function() return GameConfiguration.GetGameState() end)
    safe("ruleSet", function() return GameConfiguration.GetRuleSet() end)
    safe("mapSize", function() return MapConfiguration.GetMapSize() end)
    safe("mapScript", function() return MapConfiguration.GetScript() end)
    safe("gameSpeed", function() return GameConfiguration.GetGameSpeedType() end)
    safe("handicap", function() return GameConfiguration.GetHandicapType() end)
    local okIds, ids = pcall(function() return GameConfiguration.GetParticipatingPlayerIDs() end)
    if okIds and ids ~= nil then
        local count = 0
        for _, pid in ipairs(ids) do
            count = count + 1
            local okc, pc = pcall(function() return PlayerConfigurations[pid] end)
            if okc and pc ~= nil then
                local st = "<err>"
                local okS, vS = pcall(function() return pc:GetSlotStatus() end)
                if okS then st = tostring(vS) end
                local ldr = "<err>"
                local okL, vL = pcall(function() return pc:GetLeaderTypeName() end)
                if okL then ldr = tostring(vL) end
                local civ = "<err>"
                local okC, vC = pcall(function() return pc:GetCivilizationTypeName() end)
                if okC then civ = tostring(vC) end
                emit("player." .. tostring(pid), st .. "|" .. ldr .. "|" .. civ)
            else
                emit("player." .. tostring(pid), "<nil-or-error>")
            end
        end
        emit("participants", count)
    else
        emit("participants", "<error:" .. tostring(ids) .. ">")
    end
end)
emit("ok", tostring(ok))
if not ok then emit("err", tostring(err)) end
'''


def lua_setup_new_game(leader: str = "LEADER_QIN", civilization: str = "",
                       ruleset: str = "RULESET_EXPANSION_2", map_size: str = "MAPSIZE_TINY",
                       game_speed: str = "GAMESPEED_ONLINE", handicap: str = "HANDICAP_PRINCE",
                       game_name: str = "AI_CONTROL_TEST") -> str:
    def q(s: str) -> str:
        return json.dumps(s, ensure_ascii=False)

    return _EMIT + r'''
local LEADER = %s
local CIV = %s
local RULESET = %s
local MAPSIZE = %s
local SPEED = %s
local HANDICAP = %s
local GAMENAME = %s
local ok, err = pcall(function()
    safe("inFrontend", function() return UI.IsInFrontEnd() end)
    GameConfiguration.SetToDefaults()
    safe("ruleSet.set", function() GameConfiguration.SetRuleSet(RULESET) end)
    safe("mapSize.set", function() MapConfiguration.SetMapSize(MAPSIZE) end)
    safe("speed.set", function() GameConfiguration.SetGameSpeedType(SPEED) end)
    safe("handicap.set", function() GameConfiguration.SetHandicapType(HANDICAP) end)
    safe("name.set", function() GameConfiguration.SetValue("GAME_NAME", GAMENAME) end)
    local pid = Network.GetLocalPlayerID()
    -- 主菜单前端里 Network.GetLocalPlayerID() 实测为 -1；单机创建对局时本地玩家固定是 0 号槽。
    if type(pid) ~= "number" or pid < 0 then pid = 0 end
    emit("localPlayerID", pid)
    local pc = PlayerConfigurations[pid]
    if pc == nil then
        emit("playerConfig", "nil; scanning slots")
        for i = 0, 8 do
            local cand = PlayerConfigurations[i]
            if cand ~= nil then pid = i; pc = cand; break end
        end
        emit("localPlayerID.fallback", pid)
    end
    if pc == nil then error("no player configuration available") end
    pc:SetSlotStatus(SlotStatus.SS_TAKEN)
    safe("setMajor", function() pc:SetMajorCiv() end)
    safe("setLeader", function() pc:SetLeaderTypeName(LEADER) end)
    if CIV ~= "" then
        safe("setCiv", function() pc:SetCivilizationTypeName(CIV) end)
    end
    safe("broadcast", function() Network.BroadcastPlayerInfo(pid) end)
    safe("leaderNow", function() return pc:GetLeaderTypeName() end)
    safe("civNow", function() return pc:GetCivilizationTypeName() end)
    local okIds, ids = pcall(function() return GameConfiguration.GetParticipatingPlayerIDs() end)
    if okIds and ids ~= nil then
        local n = 0
        for _, id in ipairs(ids) do
            n = n + 1
            if id ~= pid then
                local opc = PlayerConfigurations[id]
                if opc ~= nil then
                    local okS, st = pcall(function() return opc:GetSlotStatus() end)
                    if okS and st == SlotStatus.SS_CLOSED then
                        pcall(function() opc:SetSlotStatus(SlotStatus.SS_COMPUTER) end)
                        pcall(function() opc:SetMajorCiv() end)
                    end
                end
            end
        end
        emit("participants", n)
    end
    safe("regenerateSeeds", function() GameConfiguration.RegenerateSeeds() end)
    safe("entryMethod", function() Events.SetGameEntryMethod("AI Control Test") end)
    safe("playSound", function() UI.PlaySound("Set_View_3D") end)
    local started = Network.HostGame(ServerType.SERVER_TYPE_NONE)
    emit("hostGame", started)
end)
emit("ok", tostring(ok))
if not ok then emit("err", tostring(err)) end
''' % (q(leader), q(civilization), q(ruleset), q(map_size), q(game_speed), q(handicap), q(game_name))


def lua_probe_game() -> str:
    return _EMIT + r'''
local ok, err = pcall(function()
    safe("turn", function() return Game.GetCurrentGameTurn() end)
    local pid = Game.GetLocalPlayer()
    emit("localPlayer", pid)
    if pid == PlayerTypes.NONE or pid == -1 then return end
    local p = Players[pid]
    safe("alive", function() return p:IsAlive() end)
    safe("cities", function() return p:GetCities():GetCount() end)
    safe("capital", function() local c = p:GetCities():GetCapitalCity(); if c then return c:GetName() end return nil end)
    local units = p:GetUnits()
    safe("units", function() return units:GetCount() end)
    local i = 0
    for idx, u in units:Members() do
        if not u:IsDead() then
            i = i + 1
            local parts = {}
            parts[#parts + 1] = tostring(u:GetID())
            parts[#parts + 1] = tostring(u:GetUnitType())
            parts[#parts + 1] = tostring(u:GetX())
            parts[#parts + 1] = tostring(u:GetY())
            local okm, mv = pcall(function() return u:GetMovesRemaining() end)
            parts[#parts + 1] = okm and tostring(mv) or "?"
            emit("unit." .. i, table.concat(parts, "|"))
        end
    end
end)
emit("ok", tostring(ok))
if not ok then emit("err", tostring(err)) end
'''


def lua_act(action: str = "probe", x: int | None = None, y: int | None = None,
            unit_type: str = "UNIT_SETTLER") -> str:
    prefix = _EMIT + r'''
local ACTION = %s
local X = %s
local Y = %s
local UNIT_TYPE = %s
''' % (json.dumps(action), "nil" if x is None else str(int(x)),
       "nil" if y is None else str(int(y)), json.dumps(unit_type))
    body = r'''
local ok, err = pcall(function()
    local pid = Game.GetLocalPlayer()
    local p = Players[pid]
    local function findUnit()
        local units = p:GetUnits()
        for idx, u in units:Members() do
            if not u:IsDead() then
                if UNIT_TYPE == "" or u:GetUnitType() == UNIT_TYPE then
                    return u
                end
            end
        end
        return nil
    end
    if ACTION == "probe" then
        safe("turn", function() return Game.GetCurrentGameTurn() end)
        safe("cities", function() return p:GetCities():GetCount() end)
        local i = 0
        for idx, u in p:GetUnits():Members() do
            if not u:IsDead() then
                i = i + 1
                emit("unit." .. i, tostring(u:GetID()) .. "|" .. tostring(u:GetUnitType())
                     .. "|" .. tostring(u:GetX()) .. "|" .. tostring(u:GetY()))
            end
        end
    elseif ACTION == "move" then
        local u = findUnit()
        if u == nil then emit("result", "no-unit") return end
        local params = {}
        params[UnitOperationTypes.PARAM_X] = X
        params[UnitOperationTypes.PARAM_Y] = Y
        safe("canMove", function() return UnitManager.CanStartOperation(u, UnitOperationTypes.MOVE_TO, nil, params, false, false) end)
        local okr, r = pcall(function() return UnitManager.RequestOperation(u, UnitOperationTypes.MOVE_TO, params) end)
        emit("requestMove", tostring(okr)); emit("requestMoveResult", tostring(r))
        emit("unitAt", tostring(u:GetX()) .. "," .. tostring(u:GetY()))
    elseif ACTION == "found" then
        local u = findUnit()
        if u == nil then emit("result", "no-unit") return end
        emit("foundUnit", tostring(u:GetUnitType()) .. "@" .. tostring(u:GetX()) .. "," .. tostring(u:GetY()))
        safe("canFound", function() return UnitManager.CanStartOperation(u, UnitOperationTypes.FOUND_CITY) end)
        local okr, r = pcall(function() return UnitManager.RequestOperation(u, UnitOperationTypes.FOUND_CITY) end)
        emit("requestFound", tostring(okr)); emit("requestFoundResult", tostring(r))
    elseif ACTION == "endturn" then
        local oka, r = pcall(function() return UI.RequestAction(ActionTypes.ACTION_ENDTURN) end)
        emit("endTurn", tostring(oka)); emit("endTurnResult", tostring(r))
    elseif ACTION == "quit" then
        local okq, r = pcall(function() return Events.UserConfirmedClose() end)
        emit("quit", tostring(okq)); emit("quitResult", tostring(r))
    end
end)
emit("ok", tostring(ok))
if not ok then emit("err", tostring(err)) end
'''
    return prefix + body


# ---------------------------------------------------------------------------
# 高层流程
# ---------------------------------------------------------------------------
@dataclass
class GameSession:
    client: object  # TunerClient 或 civ6_bridge.BridgeTunerClient
    frontend_state: int | None = None
    game_state: int | None = None

    def probe_frontend(self) -> dict:
        assert self.frontend_state is not None
        return self.client.eval_collect(self.frontend_state, lua_probe_frontend(), wait=4.0)

    def start_new_game(self, **kwargs) -> dict:
        assert self.frontend_state is not None
        return self.client.eval_collect(self.frontend_state, lua_setup_new_game(**kwargs), wait=6.0)

    def _ensure_game_state(self) -> int:
        # Lua 状态索引会随加载/重载变化，必须按名字重新解析
        self.client.refresh_states()
        for name in ("GameCore_Tuner", "GameCore"):
            idx = self.client.find_state(name)
            if idx is not None:
                self.game_state = idx
                return idx
        raise TunerError("对局 Lua 状态尚未出现（GameCore_Tuner）")

    def probe_game(self) -> dict:
        return self.client.eval_collect(self._ensure_game_state(), lua_probe_game(), wait=4.0)

    def act(self, action: str, **kwargs) -> dict:
        return self.client.eval_collect(self._ensure_game_state(), lua_act(action, **kwargs), wait=4.0)

    def act_ui(self, action: str, state_names=("InGame", "WorldInput", "ActionPanel"), **kwargs) -> dict:
        """在 UI Lua 上下文执行动作（如 UI.RequestAction 结束回合）。"""
        self.client.refresh_states()
        state = None
        for name in state_names:
            state = self.client.find_state(name)
            if state is not None:
                break
        if state is None:
            raise TunerError("找不到 UI Lua 状态（InGame/WorldInput/ActionPanel）")
        return self.client.eval_collect(state, lua_act(action, **kwargs), wait=4.0)


def bridge_health(url: str = "http://127.0.0.1:8770", timeout: float = 1.5) -> dict | None:
    """检查 civ6_bridge 是否在运行；返回 health dict 或 None。"""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None


def wait_for_bridge_connected(url: str = "http://127.0.0.1:8770",
                              timeout: float = 300.0, interval: float = 2.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        h = bridge_health(url)
        if h and h.get("connected"):
            return h
        last = h
        time.sleep(interval)
    raise TimeoutError(f"等待 civ6_bridge 连接 Tuner 超时: {last}")


def make_client(use_bridge: bool | None = None,
                bridge_url: str = "http://127.0.0.1:8770"):
    """返回可用客户端：默认自动优先使用 civ6_bridge，否则直连 Tuner。"""
    if use_bridge is not False:
        h = bridge_health(bridge_url)
        if h is not None:
            from civ6_bridge import BridgeTunerClient
            return BridgeTunerClient(bridge_url)
    return TunerClient()


def wait_for_game_window(timeout: float = 240.0, title_part: str = "civilization") -> dict:
    """等待游戏主窗口出现并可响应（不连接 Tuner）。"""
    import ctypes
    import ctypes.wintypes as wt
    user32 = ctypes.windll.user32

    def find_window():
        found = []

        def cb(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            title = buf.value
            if title_part in title.lower():
                found.append({"hwnd": hwnd, "title": title, "pid": pid.value})
                return False
            return True

        user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)(cb), 0)
        return found[0] if found else None

    deadline = time.time() + timeout
    while time.time() < deadline:
        w = find_window()
        if w:
            return w
        time.sleep(2.0)
    raise TimeoutError("等待游戏窗口超时")


def open_session(timeout: float = 180.0, use_bridge: bool | None = None,
                 require_frontend: bool = False) -> GameSession:
    """连接游戏。require_frontend=True 时等待主菜单 FrontEnd 状态（开局用）；
    否则允许直接连到对局中的 GameCore 状态（读取/操作用）。"""
    client = make_client(use_bridge)
    is_bridge = hasattr(client, "base_url")
    if is_bridge:
        wait_for_bridge_connected(client.base_url, timeout=timeout)
        client.connect()
    else:
        client = wait_for_tuner(timeout=timeout)
    idx = None
    try:
        idx = wait_for_state(client, "FrontEnd", timeout=120.0 if require_frontend else 8.0)
    except TimeoutError:
        idx = client.find_state("FrontEnd")
    gs = client.find_state("GameCore_Tuner") or client.find_state("GameCore")
    if idx is None and gs is None:
        raise TunerError("既不在主菜单（FrontEnd）也没有对局状态（GameCore）；游戏可能仍在加载")
    return GameSession(client=client, frontend_state=idx, game_state=gs)


def close_game(session: GameSession | None = None, wait: float = 30.0,
               stop_bridge: bool = False) -> None:
    bridge_base = None
    if session is not None:
        bridge_base = getattr(session.client, "base_url", None)
        try:
            session.client.eval_collect(session.game_state if session.game_state is not None else 0,
                                        lua_act("quit"), wait=3.0)
        except Exception:
            pass
        try:
            session.client.close()
        except Exception:
            pass
    deadline = time.time() + wait
    while time.time() < deadline:
        if not game_running():
            return
        time.sleep(1.0)
    for proc in running_game_processes():
        subprocess.run(["taskkill", "/PID", str(proc["pid"]), "/F"], capture_output=True)
    if stop_bridge and bridge_base:
        try:
            urllib.request.urlopen(bridge_base.rstrip("/") + "/shutdown",
                                   data=b"{}", timeout=3)
        except (OSError, urllib.error.URLError):
            pass


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="文明6 启动/新建对局/对局操作实验入口",
        epilog="游戏目录默认自动探测 Steam 库；也可用 --game-dir 或环境变量 CIV6_GAME_DIR "
               "指定游戏根目录（须含 Base\\Binaries\\Win64Steam）。")
    ap.add_argument("--game-dir", default=None,
                    help="游戏根目录（等价环境变量 CIV6_GAME_DIR；默认自动探测 Steam 库）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--game-dir", default=argparse.SUPPRESS,
                        help="游戏根目录（等价环境变量 CIV6_GAME_DIR）")

    def sp(name: str, **kwargs) -> argparse.ArgumentParser:
        """子命令解析器：额外接受 --game-dir（可写在子命令之后）。"""
        return sub.add_parser(name, parents=[common], **kwargs)

    sp("env")
    p = sp("windowed")
    p.add_argument("--width", type=int, default=WINDOW_WIDTH)
    p.add_argument("--height", type=int, default=WINDOW_HEIGHT)
    sp("restore")
    p = sp("launch")
    p.add_argument("--exe", default="dx12")
    p.add_argument("--no-wait", action="store_true")
    sp("states")
    sp("probe-frontend")
    p = sp("start-game")
    p.add_argument("--leader", default="LEADER_QIN")
    p.add_argument("--civ", default="")
    p.add_argument("--map-size", default="MAPSIZE_TINY")
    p.add_argument("--speed", default="GAMESPEED_ONLINE")
    p.add_argument("--handicap", default="HANDICAP_PRINCE")
    p = sp("wait-game")
    p.add_argument("--timeout", type=float, default=240.0)
    sp("probe-game")
    p = sp("act")
    p.add_argument("--action", default="probe", choices=["probe", "move", "found", "endturn", "quit"])
    p.add_argument("--x", type=int)
    p.add_argument("--y", type=int)
    p.add_argument("--unit-type", default="UNIT_SETTLER")
    sp("close")
    args = ap.parse_args()
    if getattr(args, "game_dir", None):
        set_game_dir_override(args.game_dir)

    if args.cmd == "env":
        print(json.dumps({
            "game_dir": str(find_game_dir()),
            "game_dir_source": game_dir_source(),
            "user_dir": str(user_dir()),
            "logs_dir": str(logs_dir()),
            "mods_db": str(mods_db_path()),
            "running": running_game_processes(),
            "state_dir": str(STATE_DIR),
        }, ensure_ascii=False, indent=2))
    elif args.cmd == "windowed":
        print(json.dumps(ensure_windowed(args.width, args.height), ensure_ascii=False, indent=2))
    elif args.cmd == "restore":
        print("restored:", restore_options())
    elif args.cmd == "launch":
        launch(exe=args.exe, wait=not args.no_wait)
        print("launched")
    elif args.cmd == "states":
        c = wait_for_tuner(timeout=30)
        try:
            for idx, name in sorted(c.states.items()):
                print(f"{idx:>3}  {name}")
        finally:
            c.close()
    else:
        session = open_session()
        try:
            if args.cmd == "probe-frontend":
                print(json.dumps(session.probe_frontend(), ensure_ascii=False, indent=2))
            elif args.cmd == "start-game":
                res = session.start_new_game(leader=args.leader, civilization=args.civ,
                                             map_size=args.map_size, game_speed=args.speed,
                                             handicap=args.handicap)
                print(json.dumps(res, ensure_ascii=False, indent=2))
            elif args.cmd == "wait-game":
                idx = wait_for_state(session.client, "GameCore", timeout=args.timeout)
                session.game_state = idx
                print("game state:", idx, session.client.states[idx])
            elif args.cmd == "probe-game":
                print(json.dumps(session.probe_game(), ensure_ascii=False, indent=2))
            elif args.cmd == "act":
                print(json.dumps(session.act(args.action, x=args.x, y=args.y,
                                             unit_type=args.unit_type), ensure_ascii=False, indent=2))
        finally:
            session.client.close()
