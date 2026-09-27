"""Offline original adjacency lookup and replacement inheritance review."""
from __future__ import annotations
import json
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parents[1] / 'data/vanilla_adjacencies.json'
SOURCE_FIELDS = ('OtherDistrictAdjacent', 'AdjacentSeaResource', 'AdjacentTerrain', 'AdjacentFeature',
                 'AdjacentRiver', 'AdjacentWonder', 'AdjacentNaturalWonder', 'AdjacentImprovement',
                 'AdjacentDistrict', 'AdjacentResource', 'AdjacentResourceClass', 'Self')


def load_reference():
    return json.loads(SNAPSHOT.read_text(encoding='utf-8'))


def reference(entity, ruleset='expansion2'):
    snapshot = load_reference(); profile = snapshot['profiles'][ruleset]
    kind = 'improvements' if entity.startswith('IMPROVEMENT_') else 'districts'
    if entity in snapshot['optional_base_districts']:
        return {'entity': entity, 'ruleset': ruleset, **snapshot['optional_base_districts'][entity], 'rules': [], 'civ_rows': []}
    if entity not in profile[kind] and entity not in profile['base_districts']:
        raise ValueError(f'快照未收录 {entity}；不是没有相邻的证明，请查询目标环境')
    ids = profile[kind].get(entity, [])
    return {'entity': entity, 'ruleset': ruleset, 'scope': snapshot['scope'],
            'rules': [profile['definitions'][i] for i in ids],
            'civ_rows': [{'mode': 'existing', 'id': i} for i in ids]}


def effective_rows(entry, kind='district'):
    subkey, key = ('District_Adjacencies', 'adjacencies') if kind == 'district' else ('Improvement_Adjacencies', 'improvement_adjacencies')
    subtables = entry.get('subtables') or {}
    return subtables[subkey] if isinstance(subtables.get(subkey), list) else entry.get(key, [])


def _signature(row):
    fields = [(key, row[key]) for key in SOURCE_FIELDS if row.get(key) not in (None, '', 0, False, 'NO_RESOURCECLASS')]
    return (row.get('YieldType'), tuple(fields), *(row.get(k) for k in ('PrereqTech', 'PrereqCivic', 'ObsoleteTech', 'ObsoleteCivic')))


def _custom(row):
    source = row.get('source_type')
    result = {'YieldType': row.get('yield_type'), 'YieldChange': row.get('yield_change'),
              'TilesRequired': row.get('tiles_required', 1)}
    if source: result[source] = row.get('source_detail') or True
    for field in ('prereq_tech', 'prereq_civic', 'obsolete_tech', 'obsolete_civic'):
        result[''.join(s.title() for s in field.split('_'))] = row.get(field) or None
    return result


def infer_ruleset(payload):
    info = payload.get('workspace', {}).get('基础信息', {}).get('data', {}).get('project_info', {})
    association = str(info.get('association_data', '')).lower()
    if '4873eb62-8ccc-4574-b784-dda455e74e68' in association: return 'expansion2'
    if '1b28771a-c749-434b-9053-d1380c553de9' in association: return 'expansion1'
    return 'base'


def audit_project(payload, ruleset=None):
    ruleset = ruleset or infer_ruleset(payload)
    profile = load_reference()['profiles'][ruleset]
    reports = []; warnings = []
    for entry in payload.get('workspace', {}).get('区域', []):
        replaces = (entry.get('subtables') or {}).get('DistrictReplaces', entry.get('district_replaces')) or {}
        if isinstance(replaces, list): replaces = replaces[0] if replaces else {}
        base = replaces.get('ReplacesDistrictType')
        if not base: continue
        label = entry.get('type') or entry.get('name')
        if base not in profile['districts'] and base not in profile['base_districts']:
            warnings.append(f'{label}: 原区域 {base} 未收录于 {ruleset} 相邻快照，须另核实')
            continue
        rows = effective_rows(entry)
        existing = {r.get('id') for r in rows if r.get('mode') != 'custom'}
        custom = [(r, _custom(r)) for r in rows if r.get('mode') == 'custom']
        missing = []; changed = []; reusable = []
        for ident in profile['districts'].get(base, []):
            if ident in existing: continue
            original = profile['definitions'][ident]
            matches = [(r, rule) for r, rule in custom if _signature(rule) == _signature(original)]
            if not matches:
                missing.append(ident); continue
            changed.append({'original': ident, 'custom': [r['id'] for r, _ in matches]})
            for row, rule in matches:
                if (rule['YieldChange'], rule['TilesRequired']) == (original.get('YieldChange', 0), original.get('TilesRequired', 1)):
                    reusable.append({'custom': row['id'], 'original': ident})
        if missing: warnings.append(f'{label}: 相对 {base} 缺少原生相邻规则 {", ".join(missing)}；逐项确认继承/改写/移除意图')
        if reusable: warnings.append(f'{label}: 存在与原规则等价的 custom 相邻，可直接用 existing 复用：{reusable}')
        reports.append({'entity': label, 'base': base, 'missing': missing, 'overridden': changed,
                        'reused': sorted(existing.intersection(profile['districts'].get(base, []))), 'equivalent_custom': reusable})
    return {'ok': not warnings, 'ruleset': ruleset, 'districts': reports, 'warnings': warnings,
            'unverified': ['规则覆盖不等于玩法意图正确；overridden 仍需对照设计。可选模式及其他 Mod 的追加规则需目标环境核对。']}
