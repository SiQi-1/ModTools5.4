"""Domain defaults shared by editors and standalone output builders.

Categories move here as their generators are extracted from the UI.
"""
from __future__ import annotations

from types import MappingProxyType


POLICY_FIELD_DEFAULTS = MappingProxyType({
    "Name": "",
    "Description": "",
    "PrereqCivic": "",
    "PrereqTech": "",
    "GovernmentSlotType": "SLOT_WILDCARD",
    "RequiresGovernmentUnlock": 0,
    "ExplicitUnlock": 0,
})
