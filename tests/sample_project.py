"""Shared demo project fixture used by both unit tests and screenshot tooling.

Builds a CivProject containing one minimal-but-valid entry per content
section, so every SQL/XML preview builder has real data to chew on.
"""
from __future__ import annotations

from ModTools_5_4.project.civ_project import create_empty_project


def build_sample_project() -> object:
    project = create_empty_project("示例工程")

    project.sections["基础信息"] = {
        "prefix": "DEMO",
        "infix": 0,
        "mod_name": "示例工程",
    }

    # ---------------- 文明 ----------------
    project.sections["文明"].append({
        "name": "示例文明",
        "abbr": "DEMO",
        "type": "CIVILIZATION_SIQI_DEMO",
        "civilization_name": "示例文明",
        "civilization_description": "一个用于演示的工具生成的示例文明。",
        "civilization_adjective": "示例的",
        "description_suffix": "文明",
        "loc_name": "LOC_CIVILIZATION_SIQI_DEMO_NAME",
        "loc_description": "LOC_CIVILIZATION_SIQI_DEMO_DESCRIPTION",
        "loc_adjective": "LOC_CIVILIZATION_SIQI_DEMO_ADJECTIVE",
        "level": "CIVILIZATION_LEVEL_FULL_CIV",
        "ethnicity": "ETHNICITY_ASIAN",
        "city_name_depth": 10,
        "trait_name": "示例特性",
        "trait_description": "区域提供额外相邻加成，城市生产力提升。",
        "trait_bindings": [],
        "icon_image_name": "ICON_CIVILIZATION_SIQI_DEMO",
        "images": {},
        "city_info": {"mode_index": 1, "existing_selection": [], "existing_entries": [], "custom_count": 0,
                      "custom_entries": [], "custom_expanded": [], "random_count": 4,
                      "random_entries": ["示例城一", "示例城二", "示例城三", "示例城四"]},
        "citizen_info": {"mode_index": 1, "existing_selection": [], "existing_entries": [], "custom_count": 0,
                         "custom_entries": [], "custom_expanded": [], "random_count": 3,
                         "random_entries": ["示例市民一", "示例市民二", "示例市民三"]},
        "start_bias": {"terrains": [], "features": [], "resources": [], "river_enabled": False, "river_tier": 0},
    })

    # ---------------- 领袖（含 2 套球衣颜色） ----------------
    project.sections["领袖"].append({
        "name": "示例领袖",
        "abbr": "DEMO",
        "type": "LEADER_SIQI_DEMO",
        "leader_name": "示例领袖",
        "sex": "Female",
        "capital_name": "示例首都",
        "civilization_type": "CIVILIZATION_SIQI_DEMO",
        "civilization_name": "示例文明",
        "leader_text": "一位用于演示的示例领袖。",
        "leader_quote": "示例名言，来自示例领袖。",
        "ability_name": "示例能力",
        "ability_description": "城市人口为区域提供标准相邻加成。",
        "select_sort_index": 0,
        "add_diplo_background_curtain": False,
        "icon_image_name": "ICON_LEADER_SIQI_DEMO",
        "foreground_image_name": "LEADER_SIQI_DEMO_NEUTRAL",
        "background_image_name": "LEADER_SIQI_DEMO_BACKGROUND",
        "diplo_foreground_image_name": "FALLBACK_NEUTRAL_SIQI_DEMO",
        "diplo_background_image_name": "SIQI_DEMO_1",
        "select_foreground_image_name": "PORTRAIT_LEADER_SIQI_DEMO.png",
        "select_background_image_name": "PORTRAIT_BACKGROUND_LEADER_SIQI_DEMO.png",
        "colors": {
            "j1_primary": "#003E6B", "j1_secondary": "#F1C40F",
            "j2_primary": "#7B241C", "j2_secondary": "#FDFEFE",
            "j3_primary": "", "j3_secondary": "",
            "j4_primary": "", "j4_secondary": "",
        },
        "images": {},
        "bindings": [],
        "diplomacy": [],
    })

    # ---------------- 区域 ----------------
    project.sections["区域"].append({
        "name": "示例区域",
        "abbr": "DEMO",
        "type": "DISTRICT_SIQI_DEMO",
        "DistrictType": "DISTRICT_SIQI_DEMO",
        "table_name": "Districts",
        "table_data": {
            "Name": "示例区域",
            "Description": "示例区域描述。",
            "PrereqTech": "",
            "PrereqCivic": "CIVIC_DRAMA_POETRY",
            "TraitType": "TRAIT_DISTRICT_SIQI_DEMO",
            "AdvisorType": "ADVISOR_CULTURE",
            "Cost": 54,
            "Housing": 2,
            "Entertainment": 1,
            "MilitaryDomain": "NO_DOMAIN",
        },
        "Name": "示例区域",
        "Description": "示例区域描述。",
        "icon_image_name": "ICON_DISTRICT_SIQI_DEMO",
        "images": {},
        "districts_xp2": {},
        "district_great_person_points": [],
        "district_citizen_yield_changes": [],
        "district_required_features": [],
        "district_trade_route_yields": [],
        "district_valid_terrains": [],
        "district_replaces": {},
        "adjacencies": [],
        "subtables": {},
    })

    # ---------------- 建筑 ----------------
    project.sections["建筑"].append({
        "name": "示例建筑",
        "abbr": "DEMO",
        "type": "BUILDING_SIQI_DEMO",
        "BuildingType": "BUILDING_SIQI_DEMO",
        "table_name": "Buildings",
        "table_data": {
            "Name": "示例建筑",
            "Description": "示例建筑描述。",
            "PrereqTech": "",
            "PrereqCivic": "",
            "PrereqDistrict": "DISTRICT_CITY_CENTER",
            "TraitType": "TRAIT_BUILDING_SIQI_DEMO",
            "Cost": 120,
            "Housing": 1,
            "Maintenance": 2,
            "AdvisorType": "ADVISOR_CONQUEST",
        },
        "Name": "示例建筑",
        "Description": "示例建筑描述。",
        "icon_image_name": "ICON_BUILDING_SIQI_DEMO",
        "images": {},
        "buildings_xp2": {},
        "building_replaces": {"CivUniqueBuildingType": "BUILDING_SIQI_DEMO", "ReplacesBuildingType": ""},
        "building_prereqs": [],
        "building_citizen_yield_changes": [],
        "building_great_person_points": [],
        "building_required_features": [],
        "building_valid_features": [],
        "building_valid_terrains": [],
        "building_yield_changes": [],
        "building_greatworks": [],
        "subtables": {},
    })

    # ---------------- 单位 ----------------
    project.sections["单位"].append({
        "name": "示例单位",
        "abbr": "DEMO",
        "type": "UNIT_SIQI_DEMO",
        "UnitType": "UNIT_SIQI_DEMO",
        "table_name": "Units",
        "table_data": {
            "Name": "示例单位",
            "Description": "示例单位描述。",
            "BaseMoves": 2,
            "BaseSightRange": 2,
            "Combat": 20,
            "Cost": 120,
            "Domain": "DOMAIN_LAND",
            "FormationClass": "FORMATION_CLASS_LAND_COMBAT",
            "AdvisorType": "ADVISOR_CONQUEST",
        },
        "Name": "示例单位",
        "Description": "示例单位描述。",
        "icon_image_name": "ICON_UNIT_SIQI_DEMO",
        "images": {},
        "unit_replaces": {},
        "unit_upgrades": {},
        "unit_ai_infos": [],
        "unit_abilities": [],
        "unit_promotions": [],
        "unit_tags": [],
        "subtables": {},
    })

    # ---------------- 单位晋升（树形，2 节点带前置） ----------------
    project.sections["单位晋升"].append({
        "name": "示例晋升树",
        "type": "PROMOTION_CLASS_SIQI_DEMO",
        "mode": "tree",
        "nodes": [
            {"abbr": "DEMO_A", "name_cn": "示例晋升一", "desc_cn": "第一个示例晋升。",
             "level": 1, "column": 1, "prereq_indices": []},
            {"abbr": "DEMO_B", "name_cn": "示例晋升二", "desc_cn": "第二个示例晋升。",
             "level": 2, "column": 1, "prereq_indices": [0]},
        ],
    })

    # ---------------- 改良设施 ----------------
    project.sections["改良设施"].append({
        "name": "示例改良",
        "abbr": "DEMO",
        "type": "IMPROVEMENT_SIQI_DEMO",
        "ImprovementType": "IMPROVEMENT_SIQI_DEMO",
        "table_name": "Improvements",
        "table_data": {
            "Name": "示例改良",
            "Description": "示例改良描述。",
            "TraitType": "TRAIT_IMPROVEMENT_SIQI_DEMO",
            "BuildTime": 8,
            "Cost": 60,
        },
        "Name": "示例改良",
        "Description": "示例改良描述。",
        "icon_image_name": "ICON_IMPROVEMENT_SIQI_DEMO",
        "images": {},
        "improvement_bonus_resource_types": [],
        "improvement_buildable_resources": [],
        "improvement_terrains": [],
        "improvement_features": [],
        "improvement_valid_terrains": [],
        "improvement_valid_features": [],
        "subtables": {},
    })

    # ---------------- 总督 ----------------
    project.sections["总督"].append({
        "name": "示例总督",
        "code": "DEMO",
        "GovernorType": "GOVERNOR_SIQI_DEMO",
        "Name": "示例总督",
        "Description": "示例总督描述。",
        "Title": "示例头衔",
        "ShortTitle": "示例头衔",
        "IdentityPressure": 12,
        "TransitionStrength": 150,
        "AssignCityState": 0,
        "TraitType": "TRAIT_GOVERNOR_SIQI_DEMO",
        "new_trait_type": True,
        "assign_to_major": False,
        "cannot_assign": False,
        "Image": "GOVERNOR_SIQI_DEMO_NORMAL",
        "PortraitImage": "GOVERNOR_SIQI_DEMO_NORMAL",
        "PortraitImageSelected": "GOVERNOR_SIQI_DEMO_SELECTED",
        "icon_image_name": "ICON_GOVERNOR_SIQI_DEMO",
        "icon_fill_image_name": "ICON_GOVERNOR_SIQI_DEMO_FILL",
        "icon_slot_image_name": "ICON_GOVERNOR_SIQI_DEMO_SLOT",
        "images": {},
        "promotions": [],
    })

    # ---------------- 伟人（激活类个体 + 巨作类个体） ----------------
    project.sections["伟人"].append({
        "type": "GREAT_PERSON_CLASS_SIQI_DEMO",
        "name": "示例伟人",
        "class_data": {
            "GreatPersonClassType": "GREAT_PERSON_CLASS_SIQI_DEMO",
            "UnitType": "UNIT_SIQI_DEMO_GREAT",
            "Name": "示例伟人",
            "DistrictType": "",
            "IconString": "ICON_UNIT_GREAT_GENERAL",
            "ActionIcon": "ICON_UNITACTION_RETIRE",
            "AvailableInTimeline": True,
            "GenerateDuplicateIndividuals": False,
        },
        "unit_data": {},
        "import_locked": False,
        "individuals": [
            {
                "mode": "activation",
                "abbr": "DEMO_GENERAL",
                "GreatPersonIndividualType": "GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_GENERAL",
                "Name": "示例伟人个体",
                "EraType": "ERA_ANCIENT",
                "ActionCharges": 1,
                "Gender": "F",
                "ActionNameTextOverride": "LOC_GREATPERSON_ACTION_NAME_RETIRE",
                "ActionEffectTextOverride": "示例效果文本。",
            },
            {
                "mode": "greatwork",
                "abbr": "DEMO_WRITER",
                "GreatPersonIndividualType": "GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_WRITER",
                "Name": "示例作家",
                "EraType": "ERA_MEDIEVAL",
                "great_works": [
                    {
                        "GreatWorkType": "GREATWORK_SIQI_DEMO_BOOK",
                        "GreatWorkObjectType": "GREATWORKOBJECT_LITERATURE",
                        "Name": "示例巨作",
                        "Quote": "示例引言。",
                        "Tourism": 2,
                        "EraType": "ERA_MEDIEVAL",
                        "Audio": "",
                        "Image": "",
                        "yield_changes": [
                            {"YieldType": "YIELD_CULTURE", "YieldChange": 3},
                        ],
                    }
                ],
            },
        ],
    })

    # ---------------- 政策卡 ----------------
    project.sections["政策卡"].append({
        "name": "示例政策卡",
        "abbr": "DEMO",
        "type": "POLICY_SIQI_DEMO",
        "table_name": "Policies",
        "table_data": {
            "Name": "示例政策卡",
            "Description": "示例政策卡描述。",
            "GovernmentSlotType": "SLOT_ECONOMIC",
            "PrereqCivic": "CIVIC_STATE_WORKFORCE",
        },
        "Name": "示例政策卡",
        "Description": "示例政策卡描述。",
        "icon_image_name": "ICON_POLICY_SIQI_DEMO",
        "images": {},
        "policy_replaces": {},
        "policy_yield_changes": [],
        "policy_bonuses": [],
        "subtables": {},
    })

    # ---------------- 项目 ----------------
    project.sections["项目"].append({
        "name": "示例项目",
        "abbr": "DEMO",
        "type": "PROJECT_SIQI_DEMO",
        "table_name": "Projects",
        "table_data": {
            "Name": "示例项目",
            "Description": "示例项目描述。",
            "PrereqTech": "",
            "PrereqCivic": "CIVIC_DRAMA_POETRY",
            "Cost": 200,
            "AdvisorType": "ADVISOR_CULTURE",
        },
        "Name": "示例项目",
        "Description": "示例项目描述。",
        "icon_image_name": "ICON_PROJECT_SIQI_DEMO",
        "images": {},
        "project_yield_changes": [],
        "subtables": {},
    })

    # ---------------- 信仰 ----------------
    project.sections["信仰"].append({
        "name": "示例信仰",
        "abbr": "DEMO",
        "type": "BELIEF_SIQI_DEMO",
        "table_name": "Beliefs",
        "table_data": {
            "Name": "示例信仰",
            "Description": "示例信仰描述。",
            "BeliefClassType": "BELIEF_CLASS_PANTHEON",
        },
        "Name": "示例信仰",
        "Description": "示例信仰描述。",
        "icon_image_name": "ICON_BELIEF_SIQI_DEMO",
        "images": {},
        "use_official_icon": True,
        "belief_bonuses": [],
        "subtables": {},
    })

    # ---------------- 议程 ----------------
    project.sections["议程"].append({
        "name": "示例议程",
        "type": "AGENDA_SIQI_DEMO",
        "table_data": {
            "Name": "示例议程",
            "Description": "示例议程描述。",
        },
        "historical_agendas": {
            "LeaderType": "LEADER_SIQI_DEMO",
            "ExitKudoStatementKey": "LOC_DIPLO_KUDO_LEADER_SIQI_DEMO_REASON_ANY",
            "ExitKudoText": "示例嘉奖台词。",
            "ExitWarningStatementKey": "LOC_DIPLO_WARNING_LEADER_SIQI_DEMO_REASON_ANY",
            "ExitWarnText": "示例警告台词。",
        },
        "subtables": {
            "ExclusiveAgendas": [{"AgendaTwo": "AGENDA_EXPANSIONIST"}],
            "AiLists": [{"ListType": "AI_LIST_SIQI_DEMO", "System": "Bias", "LeaderType": "LEADER_SIQI_DEMO"}],
            "AgendaModifiers": [],
        },
    })

    # ---------------- 文本 ----------------
    project.sections["文本"] = {
        "LOC_CIVILIZATION_SIQI_DEMO_NAME": "示例文明",
        "LOC_CIVILIZATION_SIQI_DEMO_DESCRIPTION": "一个用于演示的工具生成的示例文明。",
        "LOC_LEADER_SIQI_DEMO_NAME": "示例领袖",
        "LOC_DISTRICT_SIQI_DEMO_NAME": "示例区域",
        "LOC_BUILDING_SIQI_DEMO_NAME": "示例建筑",
        "LOC_UNIT_SIQI_DEMO_NAME": "示例单位",
    }

    return project
