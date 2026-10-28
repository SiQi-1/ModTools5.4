#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_ops.py - 文明6 对局内的 Lua 操作与开新局编排（实测可用版）。

相对 civ6_game.py 的改进（2026-10-26 真机验证）：
- 单位类型用 UnitManager.GetTypeName 获取（GetUnitType 在部分上下文返回 hash 数字）。
- 单位操作（MOVE_TO / FOUND_CITY）在 InGame UI 上下文执行；GameCore 上下文只有部分数据。
- 开局后 Tuner 连接会随应用切换失效；实测等地图加载完成、用 Esc 跳过领袖介绍后，
  游戏会重新监听 127.0.0.1:4318，可以新建连接。因此提供带重试的 connect_ingame。
- start_game_flow() 串起：前端选文明/领袖 -> HostGame -> 等加载 -> Esc 跳过介绍 ->
  重连 -> 返回可直接操作的 GameSession。

依赖：civ6_tuner、civ6_game（同目录）。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import time
from dataclasses import dataclass, field

from civ6_tuner import TunerClient, TunerError
import civ6_game as G

TUNER_PORT = 4318
LOAD_MARKER = "OnLoadGameViewStateDone"


# ---------------------------------------------------------------------------
# Lua 片段（输出统一为 @@CIV6AI 前缀；eval_collect 已会剥掉 @@）
# ---------------------------------------------------------------------------
_EMIT = r'''
local function emit(k, v)
    local ok, s = pcall(function() return tostring(v) end)
    if not ok then s = "<tostring-failed>" end
    print("@@CIV6AI:" .. tostring(k) .. "=" .. s)
end
local function safe(k, fn)
    local ok, v = pcall(fn)
    if ok then emit(k, v) else emit(k .. ".error", v) end
    return ok, v
end
'''


def lua_probe_game() -> str:
    return _EMIT + r'''
local ok, err = pcall(function()
    safe("turn", function() return Game.GetCurrentGameTurn() end)
    local pid = Game.GetLocalPlayer()
    emit("localPlayer", pid)
    if pid == nil or pid == PlayerTypes.NONE or pid == -1 then return end
    local p = Players[pid]
    safe("alive", function() return p:IsAlive() end)
    safe("cities", function() return p:GetCities():GetCount() end)
    safe("capital", function()
        local c = p:GetCities():GetCapitalCity()
        if c then return c:GetName() end
        return nil
    end)
    local units = p:GetUnits()
    safe("units", function() return units:GetCount() end)
    local i = 0
    for idx, u in units:Members() do
        local dead = false
        pcall(function() dead = u:IsDead() end)
        if not dead then
            i = i + 1
            local name = "?"
            local okn, n = pcall(function() return UnitManager.GetTypeName(u) end)
            if okn then name = tostring(n) end
            local parts = {}
            parts[#parts + 1] = tostring(u:GetID())
            parts[#parts + 1] = name
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


def lua_act(action: str, x: int | None = None, y: int | None = None,
            unit_type: str = "UNIT_SETTLER") -> str:
    head = _EMIT + r'''
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
    local function typeName(u)
        local okn, n = pcall(function() return UnitManager.GetTypeName(u) end)
        if okn then return tostring(n) end
        return "?"
    end
    local function findUnit()
        for idx, u in p:GetUnits():Members() do
            local dead = false
            pcall(function() dead = u:IsDead() end)
            if not dead and (UNIT_TYPE == "" or typeName(u) == UNIT_TYPE) then
                return u
            end
        end
        return nil
    end
    if ACTION == "probe" then
        emit("turn", Game.GetCurrentGameTurn())
        emit("cities", p:GetCities():GetCount())
        local i = 0
        for idx, u in p:GetUnits():Members() do
            local dead = false
            pcall(function() dead = u:IsDead() end)
            if not dead then
                i = i + 1
                emit("unit." .. i, tostring(u:GetID()) .. "|" .. typeName(u)
                     .. "|" .. tostring(u:GetX()) .. "|" .. tostring(u:GetY()))
            end
        end
    elseif ACTION == "move" then
        local u = findUnit()
        if u == nil then emit("result", "no-unit") return end
        emit("moveUnit", typeName(u) .. "@" .. tostring(u:GetX()) .. "," .. tostring(u:GetY()))
        local params = {}
        params[UnitOperationTypes.PARAM_X] = X
        params[UnitOperationTypes.PARAM_Y] = Y
        local okCan, can = pcall(function()
            return UnitManager.CanStartOperation(u, UnitOperationTypes.MOVE_TO, nil, params, false, false)
        end)
        emit("canMove", okCan and can or false)
        if not okCan or not can then emit("result", "cannot-move") return end
        local okr, r = pcall(function() return UnitManager.RequestOperation(u, UnitOperationTypes.MOVE_TO, params) end)
        emit("requestMove", okr)
        if not okr then emit("error", tostring(r)) end
    elseif ACTION == "found" then
        local u = findUnit()
        if u == nil then emit("result", "no-unit") return end
        emit("foundUnit", typeName(u) .. "@" .. tostring(u:GetX()) .. "," .. tostring(u:GetY()))
        local before = p:GetCities():GetCount()
        local okCan, can = pcall(function() return UnitManager.CanStartOperation(u, UnitOperationTypes.FOUND_CITY) end)
        emit("canFound", okCan and can or false)
        if not okCan or not can then emit("result", "cannot-found") return end
        local okr, r = pcall(function() return UnitManager.RequestOperation(u, UnitOperationTypes.FOUND_CITY) end)
        emit("requestFound", okr)
        if not okr then emit("error", tostring(r)) end
        emit("citiesBefore", before)
        emit("citiesAfter", p:GetCities():GetCount())
    elseif ACTION == "endturn" then
        local oka, r = pcall(function() return UI.RequestAction(ActionTypes.ACTION_ENDTURN) end)
        emit("endTurn", oka)
        if not oka then emit("error", tostring(r)) end
    elseif ACTION == "quit" then
        local okq, r = pcall(function() return Events.UserConfirmedClose() end)
        emit("quit", okq)
        if not okq then emit("error", tostring(r)) end
    end
end)
emit("ok", tostring(ok))
if not ok then emit("err", tostring(err)) end
'''
    return head + body


# ---------------------------------------------------------------------------
# 解析 @@ 行
# ---------------------------------------------------------------------------
def parse_lines(lines) -> dict:
    out = {}
    for raw in lines or []:
        text = raw
        if text.startswith("CIV6AI:"):
            text = text[len("CIV6AI:"):]
        if "=" not in text:
            continue
        k, v = text.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------------------
# 日志 / 加载等待 / 跳过介绍
# ---------------------------------------------------------------------------
def lua_log_path():
    return G.logs_dir() / "Lua.log"


def lua_log_offset() -> int:
    try:
        return lua_log_path().stat().st_size
    except OSError:
        return 0


def wait_for_log_marker(offset: int, marker: str = LOAD_MARKER,
                        timeout: float = 300.0, interval: float = 2.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(lua_log_path(), "r", encoding="utf-8", errors="replace") as f:
                f.seek(max(0, offset))
                if marker in f.read():
                    return True
        except OSError:
            pass
        time.sleep(interval)
    return False


def dismiss_intro(esc_times: int = 1, wait: float = 1.2) -> dict:
    """聚焦游戏窗口并按 Esc，跳过领袖介绍/开始界面。"""
    info = None
    try:
        import civ6_win
        info = civ6_win.game_window(timeout=20)
        civ6_win.focus_window(info.hwnd)
    except Exception:  # noqa: BLE001
        pass
    user32 = ctypes.windll.user32
    for _ in range(max(1, esc_times)):
        user32.keybd_event(0x1B, 0, 0, 0)
        time.sleep(0.06)
        user32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    time.sleep(wait)
    return {"dismissed": True, "window": getattr(info, "hwnd", None)}


# ---------------------------------------------------------------------------
# 连接（含重试）
# ---------------------------------------------------------------------------
def connect_tuner_retry(timeout: float = 120.0, interval: float = 2.0,
                        require_state: str | None = None):
    """反复尝试直连 127.0.0.1:4318，直到成功（可按状态名要求）。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        client = TunerClient(port=TUNER_PORT)
        try:
            client.connect(timeout=4.0, handshake_timeout=8.0)
            if client.states:
                if require_state is None or client.find_state(require_state) is not None:
                    return client
            last = f"states={len(client.states)}"
        except (OSError, TunerError) as exc:
            last = repr(exc)
        finally:
            if 'client' in dir() and client.sock is not None and (client.states and
                    (require_state is None or client.find_state(require_state) is not None)):
                pass
        client.close()
        time.sleep(interval)
    raise TimeoutError(f"连接 Tuner 超时（{timeout}s）：{last}")


# ---------------------------------------------------------------------------
# 会话
# ---------------------------------------------------------------------------
@dataclass
class Session:
    client: object
    frontend_state: int | None = None
    game_state: int | None = None
    ui_state: int | None = None
    notes: dict = field(default_factory=dict)

    def _refresh(self):
        self.client.refresh_states()
        gs = self.client.find_state("GameCore_Tuner") or self.client.find_state("GameCore")
        ui = self.client.find_state("InGame") or self.client.find_state("WorldInput")
        self.game_state = gs
        self.ui_state = ui
        return gs, ui

    def eval_in_game(self, code: str, wait: float = 6.0) -> dict:
        self._refresh()
        state = self.ui_state if self.ui_state is not None else self.game_state
        if state is None:
            raise TunerError("当前没有可用的对局 Lua 状态（InGame/GameCore_Tuner）")
        return self.client.eval_collect(state, code, wait=wait)

    def probe(self) -> dict:
        res = self.eval_in_game(lua_probe_game())
        return {"raw": res, "data": parse_lines(res.get("lines"))}

    def act(self, action: str, **kwargs) -> dict:
        # 不同动作的默认单位类型：移动默认勇士（最早可用于测试的作战单位），建城默认开拓者
        if "unit_type" not in kwargs:
            kwargs["unit_type"] = "UNIT_WARRIOR" if action == "move" else "UNIT_SETTLER"
        res = self.eval_in_game(lua_act(action, **kwargs))
        return {"raw": res, "data": parse_lines(res.get("lines"))}

    def quit(self) -> dict:
        try:
            return self.act("quit")
        except Exception as exc:  # noqa: BLE001
            return {"error": repr(exc)}

    def close(self):
        try:
            self.client.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# 开新局编排
# ---------------------------------------------------------------------------
def start_game_flow(leader: str = "LEADER_QIN", civilization: str = "CIVILIZATION_CHINA",
                    ruleset: str = "RULESET_EXPANSION_2", map_size: str = "MAPSIZE_TINY",
                    game_speed: str = "GAMESPEED_ONLINE", handicap: str = "HANDICAP_PRINCE",
                    game_name: str = "AI_CONTROL_TEST", frontend_timeout: float = 180.0,
                    load_timeout: float = 300.0, ingame_timeout: float = 300.0,
                    log_cb=None) -> Session:
    """在游戏已启动（主菜单）的前提下，完成：配置 -> HostGame -> 等加载 -> 跳过介绍 -> 重连。"""
    def log(msg):
        if log_cb:
            log_cb(msg)

    offset = lua_log_offset()
    log("connect tuner (frontend)")
    client = connect_tuner_retry(frontend_timeout, require_state=None)
    try:
        fe = None
        deadline = time.time() + frontend_timeout
        while time.time() < deadline:
            fe = client.find_state("FrontEnd")
            if fe is not None:
                break
            client.refresh_states()
            time.sleep(2.0)
        if fe is None:
            raise TimeoutError("未找到 FrontEnd 状态（游戏在主菜单吗？）")
        log(f"FrontEnd state={fe}")
        res = client.eval_collect(fe, G.lua_setup_new_game(
            leader=leader, civilization=civilization, ruleset=ruleset,
            map_size=map_size, game_speed=game_speed, handicap=handicap,
            game_name=game_name), wait=12.0)
        data = parse_lines(res.get("lines"))
        log("host result: " + json.dumps(data, ensure_ascii=False))
        if not data.get("hostGame") or data.get("hostGame") == "nil":
            raise RuntimeError("Network.HostGame 未成功：" + json.dumps(data, ensure_ascii=False))
    finally:
        client.close()

    log("wait for load marker")
    loaded = wait_for_log_marker(offset, LOAD_MARKER, timeout=load_timeout)
    log(f"load marker={loaded}")
    if not loaded:
        raise TimeoutError("等待地图加载完成超时（Lua.log 未出现 OnLoadGameViewStateDone）")
    time.sleep(2.0)
    log("dismiss leader intro (Esc)")
    dismiss_intro()
    log("reconnect tuner (in-game)")
    client2 = connect_tuner_retry(ingame_timeout, require_state="InGame")
    session = Session(client=client2)
    session._refresh()
    session.notes = {"leader": leader, "civilization": civilization,
                     "loaded": loaded}
    log(f"in-game states: GameCore={session.game_state} InGame={session.ui_state}")
    return session


def open_ingame_session(timeout: float = 120.0) -> Session:
    """已在对局中时直接连入。"""
    client = connect_tuner_retry(timeout, require_state="InGame")
    session = Session(client=client)
    session._refresh()
    return session
