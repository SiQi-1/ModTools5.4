"""modgen skill：本地技能库（仓库根 `skills/`）全文检索。

引擎在 `ModTools_5_4/skills_search.py`（GUI/AI 接口与 modgen 单一实现，防漂移），
本模块经 mt_bridge 委托，保持 modgen 纯标准库运行方式不变：

    python -m modgen.cli skill <关键词> [--file 相对路径] [--limit N] [--skills-dir 目录]
"""
from __future__ import annotations

from . import mt_bridge

_search = mt_bridge.skills_search

default_skills_root = _search.default_skills_root
search_skills = _search.search_skills
read_skill_file = _search.read_skill_file

reading_plan = _search.reading_plan
