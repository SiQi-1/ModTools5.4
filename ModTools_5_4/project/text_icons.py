"""Conservative description icon formatting; titles are never decorated."""
from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path

TERMS = {'科技值': 'Science', '生产力': 'Production', '食物': 'Food', '金币': 'Gold',
         '文化值': 'Culture', '文化': 'Culture', '信仰值': 'Faith', '信仰': 'Faith',
         '住房': 'Housing', '宜居度': 'Amenities', '旅游业绩': 'Tourism', '科技': 'Science'}
TOKENS = re.compile(r'\[[^\]]+\]|\{[^}]+\}|' + '|'.join(sorted(TERMS, key=len, reverse=True)))


def format_text(text, role='description'):
    if role in ('name', 'title'): return text
    if role != 'description': raise ValueError('role 必须为 description/name/title')
    def replace(match):
        term = match.group()
        if term not in TERMS: return term
        before = text[:match.start()]
        if re.search(r'\[ICON_[^\]]+\]\s*$', before): return term
        if term == '科技' and not re.search(r'(?:\d+|\{1_Amount\})\s*$', before): return term
        if term in ('文化', '信仰') and text[match.end():].startswith(('胜利', '遗产', '制度')): return term
        return '[ICON_' + TERMS[term] + ']' + term
    return TOKENS.sub(replace, text)


@lru_cache(maxsize=1)
def _registry():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/font_icons_registry.json').read_text(encoding='utf-8'))['icons']


def check_text(text, role='description'):
    registry = _registry()
    unknown = [t for t in re.findall(r'\[ICON_([^\]]+)\]', text) if t not in registry]
    candidate = format_text(text, role)
    return {'changed': candidate != text, 'text': candidate, 'unknown_icons': sorted(set(unknown)),
            'review_required': True}


def audit_project(payload):
    warnings = []; records = []
    fields = {'description', 'Description', 'trait_description', 'ability_description', 'description_zh'}
    def visit(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and key in fields and item and not item.startswith('LOC_'):
                    inspect(item, path + '.' + key)
                elif isinstance(item, (dict, list)): visit(item, path + '.' + key)
        elif isinstance(value, list):
            for i, item in enumerate(value): visit(item, f'{path}[{i}]')
    def inspect(text, path):
        result = check_text(text)
        if result['changed'] or result['unknown_icons']:
            records.append({'path': path, **result})
            if result['changed']: warnings.append(f'{path}: 效果描述缺少产出/属性图标，请按语义复核并补齐')
            if result['unknown_icons']: warnings.append(f'{path}: 图标未在随包注册表找到：{result["unknown_icons"]}；自定义图标须另核实')
    workspace = payload.get('workspace', {})
    # Project marketing metadata, diplomacy and names are not effect descriptions.
    for section, entries in workspace.items():
        if section not in ('基础信息', '美术', '文本'): visit(entries, section)
    for i, entry in enumerate(workspace.get('文本', {}).get('custom_entries', [])):
        if str(entry.get('tag', '')).endswith('_DESCRIPTION'):
            inspect(str(entry.get('text', '')), f'文本.custom_entries[{i}].text')
    return {'ok': not warnings, 'warnings': warnings, 'suggestions': records}
