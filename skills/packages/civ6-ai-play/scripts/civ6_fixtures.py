#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_fixtures.py - 文明6 Mod 运行时测试夹具库（已实测有效的配方）。

背景：Mod 运行时测试常用 WorldBuilder / 控制台造物，但部分 API 在
FireTuner 直连上下文里会静默失败（见 references/mod-runtime-testing.md §4.6）。
本模块把 2026-10 一次完整测试里验证有效的夹具固化为可复用函数与 CLI，
避免每个测试脚本重复踩坑。

依赖：仅 Python 标准库；需要游戏已启动且 FireTuner 可连（默认 4318）。
上下文约定：
- **Scripts（GP）状态**：Mod 的 *_Scripts Lua 状态，可访问 Mod 全局与
  UnitManager.InitUnit / GameEvents / 属性读写等；名字含 "Scripts" 的状态。
- **UI 状态**：InGame，可执行 UI.RequestPlayerOperation /
  UnitManager.RequestOperation(FOUND_CITY) / Players[id]:GetStats():GetTourism()。

用法（库）：
    from civ6_fixtures import connect, scripts_state, ui_state, spawn_unit, found_city
    client = connect()
    ss = scripts_state(client); us = ui_state(client)
    spawn_unit(client, ss, "UNIT_WARRIOR", 25, 10)
    found_city(client, ss, us, x=30, y=12)

用法（CLI，输出 JSON）：
    python civ6_fixtures.py states
    python civ6_fixtures.py find-plot --owned --city-id 65536
    python civ6_fixtures.py spawn-unit --unit UNIT_WARRIOR --x 25 --y 10
    python civ6_fixtures.py found-city --x 30 --y 12
    python civ6_fixtures.py governor-points --points 12
    python civ6_fixtures.py create-building --city-id 65536 --building BUILDING_GRANARY
    python civ6_fixtures.py create-wonder --city-id 65536 --wonder BUILDING_STONEHENGE --plot-index 123
    python civ6_fixtures.py simulate-combat --attacker 131073 --defender 196610
    python civ6_fixtures.py tourism
    python civ6_fixtures.py list-production --city-id 65536 --kind wonder
    python civ6_fixtures.py build-targets --city-id 65536 --kind district --item DISTRICT_CAMPUS
    python civ6_fixtures.py set-production --city-id 65536 --kind district --item DISTRICT_CAMPUS --plot-index 123
    python civ6_fixtures.py end-turn
    python civ6_fixtures.py run-turns --count 10
    python civ6_fixtures.py press-escape

安全：本模块只操作当前对局，不修改游戏文件、不写 Mods.sqlite。

UI 侧生产夹具（2026-10-30 实测）：unit/building/district（带坐标）可设置并读回验证；
wonder 经 RequestOperation 实测未生效（需改用 GP CreateIncompleteBuilding 或 UI 面板点击流程）。
MCP 已有 get_city_production / set_city_production / get_district_advisor / get_wonder_advisor，优先用 MCP。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Iterable

from civ6_tuner import DEFAULT_HOST, DEFAULT_PORT, TunerClient

# 与 civ6_ops.lua_act 相同的 @@ 输出约定；复用 parse_lines 解析。
EMIT_PREAMBLE = r'''
local function emit(k, v)
    local ok, s = pcall(function() return tostring(v) end)
    if not ok then s = "<tostring-failed>" end
    print("@@CIV6AI:" .. tostring(k) .. "=" .. s)
end
'''

DEFAULT_SCRIPT_HINT = "Scripts"
DEFAULT_UI_HINT = "InGame"


# ---------------------------------------------------------------------------
# 连接与状态
# ---------------------------------------------------------------------------
def connect(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
            timeout: float = 40.0) -> TunerClient:
    client = TunerClient(host=host, port=port, timeout=timeout)
    client.connect(timeout=timeout)
    return client


def states(client: TunerClient) -> dict[int, str]:
    return dict(client.refresh_states())


def _find_state(client: TunerClient, hint: str) -> int | None:
    """精确优先（避免 InGamePopup/InGameTopPanel 抢先命中 InGame），再前缀、再子串。"""
    current = states(client)
    low = hint.lower()
    for idx, name in sorted(current.items()):
        if name.lower() == low:
            return idx
    for idx, name in sorted(current.items()):
        if name.lower().startswith(low):
            return idx
    for idx, name in sorted(current.items()):
        if low in name.lower():
            return idx
    return None


def scripts_state(client: TunerClient, hint: str = DEFAULT_SCRIPT_HINT) -> int:
    idx = _find_state(client, hint)
    if idx is None:
        raise RuntimeError(f"未找到 Scripts 状态（hint={hint!r}）；先确认对局已加载")
    return idx


def ui_state(client: TunerClient, hint: str = DEFAULT_UI_HINT) -> int:
    idx = _find_state(client, hint)
    if idx is None:
        raise RuntimeError(f"未找到 UI 状态（hint={hint!r}）")
    return idx


# ---------------------------------------------------------------------------
# Lua 构建器（纯函数，便于单测）
# ---------------------------------------------------------------------------
def _q(value: str) -> str:
    """Lua 字符串字面量（JSON 引号与 Lua 兼容）。"""
    return json.dumps(value, ensure_ascii=False)


def lua_find_plot(owned: bool = True, city_id: int | None = None,
                  unowned_min_distance: int | None = None,
                  wonder_slot: bool = False) -> str:
    """查找地块：默认找玩家自有、可放奇观/改良的空地。"""
    owner_expr = "pt:GetOwner() == pid" if owned else "pt:GetOwner() < 0"
    city_expr = ""
    if city_id is not None:
        city_expr = f"""
        local pc = Cities.GetPlotPurchaseCity(pt:GetIndex())
        ok_city = pc and pc:GetID() == {int(city_id)}"""
    else:
        city_expr = "        ok_city = true"
    dist_expr = ""
    if unowned_min_distance is not None:
        dist_expr = f"""
        local cap = p:GetCities():GetCapitalCity()
        ok_dist = (not cap) or (Map.GetPlotDistance(pt:GetX(), pt:GetY(), cap:GetX(), cap:GetY()) >= {int(unowned_min_distance)})"""
    else:
        dist_expr = "        ok_dist = true"
    wonder_expr = ""
    if wonder_slot:
        wonder_expr = """
        ok_slot = (pt:GetDistrictType() == -1 and pt:GetWonderType() == -1
                   and pt:GetImprovementType() == -1 and pt:GetResourceType() == -1)"""
    else:
        wonder_expr = "        ok_slot = true"
    return f"""
local pid = Game.GetLocalPlayer()
local p = Players[pid]
local found = nil
for index = 0, Map.GetPlotCount() - 1 do
    local pt = Map.GetPlotByIndex(index)
    if pt and {owner_expr} and not pt:IsWater() and not pt:IsMountain()
       and not pt:IsNaturalWonder() and not pt:IsCity() then
        local ok_city = false
        local ok_dist = false
        local ok_slot = false
        {city_expr}
        {dist_expr}
        {wonder_expr}
        if ok_city and ok_dist and ok_slot then found = pt; break end
    end
end
if found then
    emit("plot.index", found:GetIndex())
    emit("plot.x", found:GetX())
    emit("plot.y", found:GetY())
else
    emit("plot", "none")
end
"""


def lua_spawn_unit(unit_type: str, x: int, y: int) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local u = UnitManager.InitUnit(pid, {_q(unit_type)}, {int(x)}, {int(y)})
if u then
    emit("unit.id", u:GetID())
    emit("unit.type", u:GetType())
    emit("unit.x", u:GetX())
    emit("unit.y", u:GetY())
else
    emit("unit", "none")
end
"""


def lua_found_city(unit_id: int) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local u = UnitManager.GetUnit(pid, {int(unit_id)})
if not u then emit("found", "unit-missing") else
    local ok, err = pcall(function() UnitManager.RequestOperation(u, UnitOperationTypes.FOUND_CITY) end)
    emit("found", ok)
    if not ok then emit("found.error", err) end
end
"""


def lua_governor_points(points: int) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local p = Players[pid]
local govs = p:GetGovernors()
govs:ChangeGovernorPoints({int(points)})
emit("governor.points", govs:GetGovernorPoints())
"""


def lua_governor_index(governor_type: str) -> str:
    return f"""
local gtype = nil
for row in GameInfo.Governors() do
    if row.GovernorType == {_q(governor_type)} then gtype = row.Index end
end
emit("governor.index", gtype)
"""


def lua_appoint_governor(governor_index: int) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local par = {{}}
par[PlayerOperations.PARAM_GOVERNOR_TYPE] = {int(governor_index)}
local ok, err = pcall(function()
    UI.RequestPlayerOperation(pid, PlayerOperations.APPOINT_GOVERNOR, par)
end)
emit("appoint", ok)
if not ok then emit("appoint.error", err) end
"""


def lua_assign_governor(governor_index: int, city_id: int) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local par = {{}}
par[PlayerOperations.PARAM_GOVERNOR_TYPE] = {int(governor_index)}
par[PlayerOperations.PARAM_CITY_DEST] = {int(city_id)}
local ok, err = pcall(function()
    UI.RequestPlayerOperation(pid, PlayerOperations.ASSIGN_GOVERNOR, par)
end)
emit("assign", ok)
if not ok then emit("assign.error", err) end
"""


def lua_create_building(city_id: int, building_type: str) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local city = CityManager.GetCity(pid, {int(city_id)})
local info = GameInfo.Buildings[{_q(building_type)}]
if not city or not info then
    emit("building", "missing-city-or-info")
else
    city:GetBuildQueue():CreateBuilding(info.Index)
    emit("building.has", city:GetBuildings():HasBuilding(info.Index))
end
"""


def lua_create_wonder(city_id: int, wonder_type: str, plot_index: int) -> str:
    # 关键：Wonder 只能用 CreateIncompleteBuilding；CreateBuilding 恒失败。
    return f"""
local pid = Game.GetLocalPlayer()
local city = CityManager.GetCity(pid, {int(city_id)})
local info = GameInfo.Buildings[{_q(wonder_type)}]
if not city or not info then
    emit("wonder", "missing-city-or-info")
else
    city:GetBuildQueue():CreateIncompleteBuilding(info.Index, {int(plot_index)}, 100)
    emit("wonder.has", city:GetBuildings():HasBuilding(info.Index))
end
"""


def lua_simulate_combat(attacker_component_id: int, defender_component_id: int) -> str:
    return f"""
local res = CombatManager.SimulateAttackVersus({int(attacker_component_id)}, {int(defender_component_id)})
if not res then
    emit("combat", "nil")
else
    local a = res[CombatResultParameters.ATTACKER]
    local d = res[CombatResultParameters.DEFENDER]
    emit("attacker.cs", a and a[CombatResultParameters.COMBAT_STRENGTH])
    emit("attacker.mod", a and a[CombatResultParameters.STRENGTH_MODIFIER])
    emit("defender.cs", d and d[CombatResultParameters.COMBAT_STRENGTH])
    emit("defender.mod", d and d[CombatResultParameters.STRENGTH_MODIFIER])
end
"""


def lua_tourism(player_id: int = 0) -> str:
    return f"""
local p = Players[{int(player_id)}]
local stats = p and p:GetStats()
if not stats then emit("tourism", "no-stats") else
    local ok, v = pcall(function() return stats:GetTourism() end)
    emit("tourism", ok and v or "unsupported")
end
"""


def lua_turn() -> str:
    return """
emit("turn", Game.GetCurrentGameTurn())
local p = Players[Game.GetLocalPlayer()]
emit("cities", p:GetCities():GetCount())
"""


def lua_city_list() -> str:
    return """
local p = Players[Game.GetLocalPlayer()]
for _, city in p:GetCities():Members() do
    emit("city." .. city:GetID(), city:GetX() .. "|" .. city:GetY() .. "|" .. city:GetName())
end
"""


# ---------------------------------------------------------------------------
# UI 侧生产夹具（建造/区域/奇观：必须满足建造条件与 3 环限制）
# ---------------------------------------------------------------------------
_ITEM_TABLE = {
    "unit": ("Units", "PARAM_UNIT_TYPE", "UnitType"),
    "building": ("Buildings", "PARAM_BUILDING_TYPE", "BuildingType"),
    "district": ("Districts", "PARAM_DISTRICT_TYPE", "DistrictType"),
    "project": ("Projects", "PARAM_PROJECT_TYPE", "ProjectType"),
}


def lua_production_list(city_id: int, kind: str = "all") -> str:
    """列出城市当前可生产的项目（CanProduce + CanStartOperation 过滤）。"""
    loops = []
    if kind in ("all", "unit"):
        loops.append('for row in GameInfo.Units() do probe("unit", row.Hash, row.UnitType, CityOperationTypes.PARAM_UNIT_TYPE) end')
    if kind in ("all", "building", "wonder"):
        wonder_only = 'if (row.IsWonder == true or row.IsWonder == 1) then' if kind == "wonder" else \
                      'if not (row.IsWonder == true or row.IsWonder == 1) then'
        loops.append(f'''for row in GameInfo.Buildings() do
    {wonder_only}
        probe("{'wonder' if kind == 'wonder' else 'building'}", row.Hash, row.BuildingType, CityOperationTypes.PARAM_BUILDING_TYPE)
    end
end''')
    if kind in ("all", "district"):
        loops.append('for row in GameInfo.Districts() do probe("district", row.Hash, row.DistrictType, CityOperationTypes.PARAM_DISTRICT_TYPE) end')
    if kind in ("all", "project"):
        loops.append('for row in GameInfo.Projects() do probe("project", row.Hash, row.ProjectType, CityOperationTypes.PARAM_PROJECT_TYPE) end')
    body = "\n".join(loops)
    return f"""
local pid = Game.GetLocalPlayer()
local city = CityManager.GetCity(pid, {int(city_id)})
if not city then
    emit("production", "no-city")
else
    local bq = city:GetBuildQueue()
    local function probe(kindName, hash, name, paramKey)
        if bq:CanProduce(hash, true) then
            local params = {{}}
            params[paramKey] = hash
            local can, res = CityManager.CanStartOperation(city, CityOperationTypes.BUILD, params, true)
            local reasons = ""
            if res then
                local fr = res[CityCommandResults.FAILURE_REASONS]
                if type(fr) == "table" and #fr > 0 then reasons = table.concat(fr, ",") end
            end
            emit(kindName .. "." .. name, tostring(can) .. "|" .. reasons)
        end
    end
    {body}
end
"""


def lua_build_targets(city_id: int, kind: str, item_name: str, limit: int = 20) -> str:
    """列出建筑/区域/奇观的合法地块（GetOperationTargets + 逐地块 CanStartOperation）。"""
    if kind not in ("building", "district"):
        raise ValueError(f"build_targets 只支持 building/district，收到 {kind!r}")
    table_name, param_key, _ = _ITEM_TABLE[kind]
    return f"""
local pid = Game.GetLocalPlayer()
local city = CityManager.GetCity(pid, {int(city_id)})
local info = GameInfo.{table_name}[{_q(item_name)}]
if not city or not info then
    emit("targets", "missing-city-or-item")
else
    local params = {{}}
    params[CityOperationTypes.{param_key}] = info.Hash
    local targets = CityManager.GetOperationTargets(city, CityOperationTypes.BUILD, params)
    local plots = {{}}
    if targets then
        for _, v in pairs(targets) do
            if type(v) == "table" then
                for _, idx in ipairs(v) do
                    if type(idx) == "number" then table.insert(plots, idx) end
                end
            end
        end
    end
    emit("targets.count", #plots)
    local max = math.min(#plots, {int(limit)})
    for i = 1, max do
        local idx = plots[i]
        local pt = Map.GetPlotByIndex(idx)
        if pt then
            local p2 = {{}}
            p2[CityOperationTypes.{param_key}] = info.Hash
            p2[CityOperationTypes.PARAM_X] = pt:GetX()
            p2[CityOperationTypes.PARAM_Y] = pt:GetY()
            local can, res = CityManager.CanStartOperation(city, CityOperationTypes.BUILD, p2, true)
            local reasons = ""
            if res then
                local sc = res[CityOperationResults.SUCCESS_CONDITIONS]
                if type(sc) == "table" and #sc > 0 then reasons = table.concat(sc, ",") end
                local fr = res[CityCommandResults.FAILURE_REASONS]
                if type(fr) == "table" and #fr > 0 then
                    if reasons ~= "" then reasons = reasons .. ";" end
                    reasons = reasons .. table.concat(fr, ",")
                end
            end
            emit("plot." .. i, idx .. "|" .. pt:GetX() .. "," .. pt:GetY() .. "|" .. tostring(can) .. "|" .. reasons)
        end
    end
end
"""


def lua_set_production(city_id: int, kind: str, item_name: str,
                       plot_index: int | None = None) -> str:
    """设置城市生产目标（VALUE_EXCLUSIVE：清空队列并替换当前生产）。

    建筑/区域/奇观需给 plot_index（先用 build_targets 找合法地块，限 3 环）。
    """
    if kind == "wonder":
        kind = "building"
    if kind not in _ITEM_TABLE:
        raise ValueError(f"不支持的 kind: {kind!r}")
    table_name, param_key, _ = _ITEM_TABLE[kind]
    plot_setup = ""
    xy_check = ""
    xy_params = ""
    if plot_index is not None:
        plot_setup = f"""
    local pt = Map.GetPlotByIndex({int(plot_index)})
    if not pt then emit("production", "bad-plot") return end
    local px, py = pt:GetX(), pt:GetY()"""
        xy_check = """
    check[CityOperationTypes.PARAM_X] = px
    check[CityOperationTypes.PARAM_Y] = py"""
        xy_params = """
        params[CityOperationTypes.PARAM_X] = px
        params[CityOperationTypes.PARAM_Y] = py"""
    return f"""
local pid = Game.GetLocalPlayer()
local city = CityManager.GetCity(pid, {int(city_id)})
local info = GameInfo.{table_name}[{_q(item_name)}]
if not city or not info then
    emit("production", "missing-city-or-item")
else{plot_setup}
    local check = {{}}
    check[CityOperationTypes.{param_key}] = info.Hash{xy_check}
    local can, res = CityManager.CanStartOperation(city, CityOperationTypes.BUILD, check, true)
    emit("production.can", can)
    if not can and res then
        local fr = res[CityCommandResults.FAILURE_REASONS]
        if type(fr) == "table" and #fr > 0 then emit("production.reasons", table.concat(fr, ",")) end
    end
    if can then
        local params = {{}}
        params[CityOperationTypes.{param_key}] = info.Hash{xy_params}
        params[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_EXCLUSIVE
        CityManager.RequestOperation(city, CityOperationTypes.BUILD, params)
    end
    local okc, cur = pcall(function() return city:GetBuildQueue():GetCurrentProductionTypeHash() end)
    emit("production.current_immediate", okc and cur or "nil")
    emit("production.expected", info.Hash)
end
"""


def lua_production_current(city_id: int) -> str:
    return f"""
local pid = Game.GetLocalPlayer()
local city = CityManager.GetCity(pid, {int(city_id)})
if not city then
    emit("production.current", "no-city")
else
    local bq = city:GetBuildQueue()
    emit("production.current", bq:GetCurrentProductionTypeHash())
    emit("production.turns", bq:GetTurnsLeft())
end
"""


# ---------------------------------------------------------------------------
# 执行封装
# ---------------------------------------------------------------------------
def eval_emit(client: TunerClient, state: int, body: str, wait: float = 12.0) -> dict:
    res = client.eval_collect(state, EMIT_PREAMBLE + body, wait=wait)
    from civ6_ops import parse_lines  # 延迟导入，避免无对局环境下额外依赖
    data = parse_lines(res.get("lines") or [])
    return {"ok": not res.get("error"), "error": res.get("error"), "data": data,
            "raw": res.get("raw")}


def run_scripts(client: TunerClient, body: str, hint: str = DEFAULT_SCRIPT_HINT,
                wait: float = 12.0) -> dict:
    return eval_emit(client, scripts_state(client, hint), body, wait=wait)


def run_ui(client: TunerClient, body: str, hint: str = DEFAULT_UI_HINT,
           wait: float = 12.0) -> dict:
    return eval_emit(client, ui_state(client, hint), body, wait=wait)


# ---------------------------------------------------------------------------
# 夹具函数
# ---------------------------------------------------------------------------
def find_plot(client: TunerClient, owned: bool = True, city_id: int | None = None,
              unowned_min_distance: int | None = None,
              wonder_slot: bool = False, hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_find_plot(owned, city_id, unowned_min_distance, wonder_slot), hint=hint)


def spawn_unit(client: TunerClient, unit_type: str, x: int, y: int,
               hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_spawn_unit(unit_type, x, y), hint=hint)


def found_city(client: TunerClient, x: int, y: int,
               hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    """两步夹具：Scripts 造 settler → UI 执行 FOUND_CITY。"""
    spawn = spawn_unit(client, "UNIT_SETTLER", x, y, hint=hint)
    unit_id = (spawn.get("data") or {}).get("unit.id")
    if not unit_id:
        return {"ok": False, "error": "settler spawn failed", "spawn": spawn}
    ui = run_ui(client, lua_found_city(int(unit_id)))
    return {"ok": ui.get("ok"), "spawn": spawn, "found": ui}


def governor_points(client: TunerClient, points: int,
                    hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_governor_points(points), hint=hint)


def governor_index(client: TunerClient, governor_type: str,
                   hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_governor_index(governor_type), hint=hint)


def appoint_governor(client: TunerClient, governor_type: str,
                     hint: str = DEFAULT_UI_HINT) -> dict:
    idx = (governor_index(client, governor_type, hint=DEFAULT_SCRIPT_HINT).get("data") or {}).get("governor.index")
    if idx is None:
        return {"ok": False, "error": "governor index not found"}
    return run_ui(client, lua_appoint_governor(int(idx)), hint=hint)


def assign_governor(client: TunerClient, governor_type: str, city_id: int,
                    hint: str = DEFAULT_UI_HINT) -> dict:
    idx = (governor_index(client, governor_type, hint=DEFAULT_SCRIPT_HINT).get("data") or {}).get("governor.index")
    if idx is None:
        return {"ok": False, "error": "governor index not found"}
    return run_ui(client, lua_assign_governor(int(idx), city_id), hint=hint)


def create_building(client: TunerClient, city_id: int, building_type: str,
                    hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_create_building(city_id, building_type), hint=hint)


def create_wonder(client: TunerClient, city_id: int, wonder_type: str, plot_index: int,
                  hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_create_wonder(city_id, wonder_type, plot_index), hint=hint)


def simulate_combat(client: TunerClient, attacker_component_id: int,
                    defender_component_id: int, hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_simulate_combat(attacker_component_id, defender_component_id), hint=hint)


def tourism(client: TunerClient, player_id: int = 0, hint: str = DEFAULT_UI_HINT) -> dict:
    return run_ui(client, lua_tourism(player_id), hint=hint)


def turn(client: TunerClient, hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_turn(), hint=hint)


def city_list(client: TunerClient, hint: str = DEFAULT_SCRIPT_HINT) -> dict:
    return run_scripts(client, lua_city_list(), hint=hint)


def list_production(client: TunerClient, city_id: int, kind: str = "all",
                    hint: str = DEFAULT_UI_HINT) -> dict:
    """列出可生产项目（unit/building/wonder/district/project/all）。"""
    return run_ui(client, lua_production_list(city_id, kind), hint=hint)


def build_targets(client: TunerClient, city_id: int, kind: str, item_name: str,
                  limit: int = 20, hint: str = DEFAULT_UI_HINT) -> dict:
    """列出建筑/区域/奇观的合法地块与逐地块建造条件。"""
    return run_ui(client, lua_build_targets(city_id, kind, item_name, limit), hint=hint)


def wonder_targets(client: TunerClient, city_id: int, wonder_name: str,
                   limit: int = 20, hint: str = DEFAULT_UI_HINT) -> dict:
    return build_targets(client, city_id, "building", wonder_name, limit=limit, hint=hint)


def district_targets(client: TunerClient, city_id: int, district_name: str,
                     limit: int = 20, hint: str = DEFAULT_UI_HINT) -> dict:
    return build_targets(client, city_id, "district", district_name, limit=limit, hint=hint)


def set_production(client: TunerClient, city_id: int, kind: str, item_name: str,
                   plot_index: int | None = None, verify_delay: float = 1.2,
                   hint: str = DEFAULT_UI_HINT) -> dict:
    """设置生产目标；建筑/区域/奇观需 plot_index（先用 build_targets 找合法地块）。

    RequestOperation 是异步的：立即读 GetCurrentProductionTypeHash 可能仍是 0，
    因此默认等待 verify_delay 后再读一次并给出 production.verified。
    """
    res = run_ui(client, lua_set_production(city_id, kind, item_name, plot_index), hint=hint)
    data = res.get("data") or {}
    expected = data.get("production.expected")
    if data.get("production.can") in ("true", True) and expected is not None:
        time.sleep(max(0.0, float(verify_delay)))
        check = run_ui(client, lua_production_current(city_id), hint=hint)
        cur = (check.get("data") or {}).get("production.current")
        data["production.current"] = cur
        data["production.verified"] = str(cur) == str(expected)
    res["data"] = data
    return res


# ---------------------------------------------------------------------------
# 回合与弹窗
# ---------------------------------------------------------------------------
def end_turn(client: TunerClient, hint: str = DEFAULT_UI_HINT) -> dict:
    from civ6_ops import lua_act, parse_lines
    res = client.eval_collect(ui_state(client, hint), lua_act("endturn"), wait=8.0)
    return {"ok": not res.get("error"), "error": res.get("error"),
            "data": parse_lines(res.get("lines") or []), "raw": res.get("raw")}


def _iter_windows():
    """枚举顶层窗口 (hwnd, title)；仅 Windows 可用。"""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    results: list[tuple[int, str]] = []
    proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            results.append((int(hwnd), buf.value))
        return True

    user32.EnumWindows(proc_type(_cb), 0)
    return results


def press_escape(times: int = 1, title_part: str = "Civilization VI") -> dict:
    """前台发送 Esc（清 Eureka/NaturalWonder/WonderBuilt 等弹窗）。"""
    if sys.platform != "win32":
        return {"ok": False, "error": "windows only"}
    import ctypes
    user32 = ctypes.windll.user32
    candidates = [(h, t) for h, t in _iter_windows() if title_part.lower() in t.lower()]
    if not candidates:
        return {"ok": False, "error": "game window not found"}
    hwnd = candidates[0][0]
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    for _ in range(max(1, int(times))):
        user32.keybd_event(0x1B, 0, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.2)
    return {"ok": True, "hwnd": hwnd, "title": candidates[0][1]}


def run_turns(client: TunerClient, count: int, esc_every: int = 3,
              hint: str = DEFAULT_UI_HINT, delay: float = 0.8) -> dict:
    """结束回合 count 次；每 esc_every 回合发一次 Esc，避免弹窗阻塞。"""
    results = []
    for i in range(1, max(1, int(count)) + 1):
        results.append(end_turn(client, hint=hint))
        time.sleep(delay)
        if esc_every and i % esc_every == 0:
            press_escape(1)
    return {"ok": True, "turns": len(results)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=40.0)
    parser.add_argument("--script-hint", default=DEFAULT_SCRIPT_HINT)
    parser.add_argument("--ui-hint", default=DEFAULT_UI_HINT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="文明6 Mod 运行时测试夹具")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("states", help="列出 Tuner Lua 状态")
    _add_common(p)

    p = sub.add_parser("turn", help="读当前回合/城市数")
    _add_common(p)

    p = sub.add_parser("cities", help="列出城市")
    _add_common(p)

    p = sub.add_parser("find-plot", help="查找空地（默认自有、可放奇观）")
    _add_common(p)
    p.add_argument("--owned", action="store_true", default=True)
    p.add_argument("--unowned", action="store_true", help="改找未占领地块")
    p.add_argument("--city-id", type=int)
    p.add_argument("--unowned-min-distance", type=int)
    p.add_argument("--wonder-slot", action="store_true")

    p = sub.add_parser("spawn-unit", help="在 (x,y) 造单位")
    _add_common(p)
    p.add_argument("--unit", required=True)
    p.add_argument("--x", type=int, required=True)
    p.add_argument("--y", type=int, required=True)

    p = sub.add_parser("found-city", help="造 settler 并在 (x,y) 建城")
    _add_common(p)
    p.add_argument("--x", type=int, required=True)
    p.add_argument("--y", type=int, required=True)

    p = sub.add_parser("governor-points", help="加总督点")
    _add_common(p)
    p.add_argument("--points", type=int, required=True)

    p = sub.add_parser("appoint-governor", help="任命总督（type 名）")
    _add_common(p)
    p.add_argument("--governor", required=True)

    p = sub.add_parser("assign-governor", help="指派总督到城市")
    _add_common(p)
    p.add_argument("--governor", required=True)
    p.add_argument("--city-id", type=int, required=True)

    p = sub.add_parser("create-building", help="落成普通建筑")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--building", required=True)

    p = sub.add_parser("create-wonder", help="落成奇观（CreateIncompleteBuilding）")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--wonder", required=True)
    p.add_argument("--plot-index", type=int, required=True)

    p = sub.add_parser("simulate-combat", help="模拟攻击并读战力修正")
    _add_common(p)
    p.add_argument("--attacker", type=int, required=True, help="attacker component id")
    p.add_argument("--defender", type=int, required=True, help="defender component id")

    p = sub.add_parser("tourism", help="读玩家旅游值（UI 上下文）")
    _add_common(p)
    p.add_argument("--player-id", type=int, default=0)

    p = sub.add_parser("end-turn", help="结束回合")
    _add_common(p)

    p = sub.add_parser("run-turns", help="连续结束回合（自动 Esc）")
    _add_common(p)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--esc-every", type=int, default=3)

    p = sub.add_parser("press-escape", help="前台发 Esc 清弹窗")
    _add_common(p)
    p.add_argument("--times", type=int, default=1)

    p = sub.add_parser("list-production", help="列出城市可生产项目")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--kind", default="all",
                   choices=["all", "unit", "building", "wonder", "district", "project"])

    p = sub.add_parser("build-targets", help="列出建筑/区域/奇观的合法地块")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--kind", required=True, choices=["building", "district"])
    p.add_argument("--item", required=True)
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("wonder-targets", help="列出奇观合法地块（build-targets 快捷方式）")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--wonder", required=True)
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("district-targets", help="列出区域合法地块")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--district", required=True)
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("set-production", help="设置生产目标（建筑/区域/奇观需 plot-index）")
    _add_common(p)
    p.add_argument("--city-id", type=int, required=True)
    p.add_argument("--kind", required=True,
                   choices=["unit", "building", "wonder", "district", "project"])
    p.add_argument("--item", required=True)
    p.add_argument("--plot-index", type=int)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "press-escape":
        print(json.dumps(press_escape(args.times), ensure_ascii=False))
        return 0
    client = connect(host=args.host, port=args.port, timeout=args.timeout)
    try:
        if args.command == "states":
            out = {str(k): v for k, v in states(client).items()}
        elif args.command == "turn":
            out = turn(client, hint=args.script_hint)
        elif args.command == "cities":
            out = city_list(client, hint=args.script_hint)
        elif args.command == "find-plot":
            out = find_plot(client, owned=not args.unowned, city_id=args.city_id,
                            unowned_min_distance=args.unowned_min_distance,
                            wonder_slot=args.wonder_slot, hint=args.script_hint)
        elif args.command == "spawn-unit":
            out = spawn_unit(client, args.unit, args.x, args.y, hint=args.script_hint)
        elif args.command == "found-city":
            out = found_city(client, args.x, args.y, hint=args.script_hint)
        elif args.command == "governor-points":
            out = governor_points(client, args.points, hint=args.script_hint)
        elif args.command == "appoint-governor":
            out = appoint_governor(client, args.governor, hint=args.ui_hint)
        elif args.command == "assign-governor":
            out = assign_governor(client, args.governor, args.city_id, hint=args.ui_hint)
        elif args.command == "create-building":
            out = create_building(client, args.city_id, args.building, hint=args.script_hint)
        elif args.command == "create-wonder":
            out = create_wonder(client, args.city_id, args.wonder, args.plot_index,
                                hint=args.script_hint)
        elif args.command == "simulate-combat":
            out = simulate_combat(client, args.attacker, args.defender, hint=args.script_hint)
        elif args.command == "tourism":
            out = tourism(client, args.player_id, hint=args.ui_hint)
        elif args.command == "end-turn":
            out = end_turn(client, hint=args.ui_hint)
        elif args.command == "run-turns":
            out = run_turns(client, args.count, esc_every=args.esc_every, hint=args.ui_hint)
        elif args.command == "list-production":
            out = list_production(client, args.city_id, args.kind, hint=args.ui_hint)
        elif args.command == "build-targets":
            out = build_targets(client, args.city_id, args.kind, args.item,
                                limit=args.limit, hint=args.ui_hint)
        elif args.command == "wonder-targets":
            out = wonder_targets(client, args.city_id, args.wonder,
                                 limit=args.limit, hint=args.ui_hint)
        elif args.command == "district-targets":
            out = district_targets(client, args.city_id, args.district,
                                   limit=args.limit, hint=args.ui_hint)
        elif args.command == "set-production":
            out = set_production(client, args.city_id, args.kind, args.item,
                                 plot_index=args.plot_index, hint=args.ui_hint)
        else:
            out = {"ok": False, "error": f"unknown command {args.command}"}
    finally:
        client.close()
    print(json.dumps(out, ensure_ascii=False, default=str))
    return 0 if (out.get("ok") if isinstance(out, dict) else True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
