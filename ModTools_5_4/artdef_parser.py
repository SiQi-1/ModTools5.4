from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional
import xml.etree.ElementTree as ET


def _module_root() -> Path:
    return Path(__file__).resolve().parent


def _workspace_root() -> Path:
    return _module_root().parent


def _from_roots() -> list[Path]:
    roots: list[Path] = []
    preferred = _module_root() / "From"
    fallback = _workspace_root() / "From"
    if preferred.exists():
        roots.append(preferred)
    if fallback.exists() and fallback != preferred:
        roots.append(fallback)
    return roots


def _find_artdef_files(file_names: set[str]) -> list[Path]:
    hits: list[Path] = []
    seen: set[Path] = set()
    lower_names = {name.lower() for name in file_names}
    for root in _from_roots():
        for path in root.rglob("*.artdef"):
            if path.name.lower() not in lower_names:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            hits.append(path)
    return hits


def _candidate_civilization_files() -> list[Path]:
    return _find_artdef_files({"Civilizations.artdef", "Civilizations_Shared.artdef"})


def _candidate_district_files() -> list[Path]:
    return _find_artdef_files({"Districts.artdef", "Districts_Shared.artdef"})


def _candidate_building_files() -> list[Path]:
    return _find_artdef_files({"Buildings.artdef", "Buildings_Shared.artdef"})


def _candidate_improvement_files() -> list[Path]:
    return _find_artdef_files({"Improvements.artdef", "Improvements_Shared.artdef"})


def _candidate_unit_files() -> list[Path]:
    return _find_artdef_files({"Units.artdef", "Units_Shared.artdef"})


def _list_names_from_files(paths: Iterable[Path], prefix: str) -> list[str]:
    names: set[str] = set()
    for path in paths:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except Exception:
            continue
        for node in root.iter("m_Name"):
            text = str(node.attrib.get("text") or "").strip()
            if text.startswith(prefix):
                names.add(text)
    return sorted(names)


def _find_entries(root: ET.Element, collection_name: str) -> list[ET.Element]:
    output: list[ET.Element] = []
    rc = root.find("m_RootCollections")
    if rc is None:
        return output
    for container in rc.findall("Element"):
        cname = container.find("m_CollectionName")
        if cname is None or str(cname.attrib.get("text") or "") != collection_name:
            continue
        for child in container.findall("Element"):
            if child.find("m_Name") is not None:
                output.append(child)
    return output


def _find_entry_from_files(paths: Iterable[Path], collection_name: str, target_name: str) -> Optional[ET.Element]:
    for path in paths:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except Exception:
            continue
        for entry in _find_entries(root, collection_name):
            m_name = entry.find("m_Name")
            if m_name is None:
                continue
            if str(m_name.attrib.get("text") or "").strip() != target_name:
                continue
            try:
                return ET.fromstring(ET.tostring(entry, encoding="utf-8"))
            except Exception:
                return None
    return None


@lru_cache(maxsize=1)
def list_civilization_artdef_names() -> list[str]:
    return _list_names_from_files(_candidate_civilization_files(), "CIVILIZATION_")


@lru_cache(maxsize=1)
def list_district_artdef_names() -> list[str]:
    return _list_names_from_files(_candidate_district_files(), "DISTRICT_")


@lru_cache(maxsize=1)
def list_building_artdef_names() -> list[str]:
    return _list_names_from_files(_candidate_building_files(), "BUILDING_")


@lru_cache(maxsize=1)
def list_improvement_artdef_names() -> list[str]:
    return _list_names_from_files(_candidate_improvement_files(), "IMPROVEMENT_")


@lru_cache(maxsize=1)
def list_unit_artdef_names() -> list[str]:
    return _list_names_from_files(_candidate_unit_files(), "UNIT_")


def get_civilization_entry_element(civ_type: str) -> Optional[ET.Element]:
    return _find_entry_from_files(_candidate_civilization_files(), "Civilization", civ_type)


def get_district_entry_element(district_type: str) -> Optional[ET.Element]:
    return _find_entry_from_files(_candidate_district_files(), "District", district_type)


def get_building_entry_element(building_type: str) -> Optional[ET.Element]:
    return _find_entry_from_files(_candidate_building_files(), "Building", building_type)


def get_improvement_entry_element(improvement_type: str) -> Optional[ET.Element]:
    return _find_entry_from_files(_candidate_improvement_files(), "Improvement", improvement_type)


def get_unit_entry_element(unit_type: str) -> Optional[ET.Element]:
    return _find_entry_from_files(_candidate_unit_files(), "Units", unit_type)


def invalidate_cache() -> None:
    list_civilization_artdef_names.cache_clear()
    list_district_artdef_names.cache_clear()
    list_building_artdef_names.cache_clear()
    list_improvement_artdef_names.cache_clear()
    list_unit_artdef_names.cache_clear()
