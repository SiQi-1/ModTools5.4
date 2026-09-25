"""Leader fallback declarations, shared by editor, exporter and CLI.

State vocabulary informed by 飞花白's LeaderFallbacks template (S6).
Independent implementation; see THIRD_PARTY_NOTICES.md. State spelling follows
that template; game activation still requires target SDK / in-game validation.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re

FALLBACK_STATES = {
    "DEFAULT": "默认", "DECLARE_WAR_FROM_AI": "AI 宣战",
    "DECLAR_WAR_FROM_HUMAN": "受到宣战", "DEFEAT": "败北",
    "ENRAGED": "愤怒", "FIRST_MEET": "初见", "HAPPY": "开心",
    "HAPPY_IDLE": "友好待机", "HAPPY_NEGATIVE": "友好拒绝",
    "HAPPY_POSITIVE": "友好接受", "KUDOS": "符合议程",
    "NEUTRAL": "中立", "NEUTRAL_GREETING": "中立会见",
    "NEUTRAL_NEGATIVE": "中立拒绝", "NEUTRAL_POSITIVE": "中立接受",
    "NEUTRAL_TO_HAPPY": "转为友好", "NEUTRAL_TO_UNHAPPY": "转为敌对",
    "UNHAPPY": "敌对", "UNHAPPY_IDLE": "敌对待机",
    "UNHAPPY_NEGATIVE": "敌对拒绝", "UNHAPPY_POSITIVE": "敌对接受",
    "UNHAPPY_TO_NEUTRAL": "转为中立", "WARNING": "违背议程",
}


def _explicit_image(image: dict) -> dict:
    value = deepcopy(image)
    if not any(key in value for key in ("scale", "offset_x", "offset_y", "canvas_width", "canvas_height")):
        value.setdefault("fit_mode", "contain")
    return value


def default_image(entry: dict) -> dict:
    explicit = entry.get("fallback_images")
    if isinstance(explicit, dict) and isinstance(explicit.get("DEFAULT"), dict):
        if explicit["DEFAULT"].get("path"):
            return _explicit_image(explicit["DEFAULT"])
    images = entry.get("images")
    image = images.get("diplo_foreground") if isinstance(images, dict) else None
    return deepcopy(image) if isinstance(image, dict) else {}


def fallback_rows(entry: dict) -> list[dict]:
    """Declared animations only; DEFAULT handles unassigned game states."""
    leader = str(entry.get("type") or "").strip()
    if not re.fullmatch(r"LEADER_[A-Za-z0-9_]+", leader):
        return []
    suffix = leader[7:]
    explicit = entry.get("fallback_images")
    explicit = explicit if isinstance(explicit, dict) else {}
    rows = []
    for state in FALLBACK_STATES:
        image = default_image(entry) if state == "DEFAULT" else explicit.get(state)
        if not isinstance(image, dict) or not str(image.get("path") or "").strip():
            continue
        if state != "DEFAULT":
            image = _explicit_image(image)
        name = (f"FALLBACK_NEUTRAL_{suffix}" if state == "DEFAULT"
                else f"FALLBACK_STATE_{state}__LEADER_{suffix}")
        rows.append({"state": state, "name": name, "source_state": deepcopy(image),
                     "source_path": str(image["path"]).strip(),
                     "target_width": 960, "target_height": 960,
                     "category": "leader_fallback"})
    return rows


def validate_fallbacks(entry: dict, *, check_files: bool = True,
                       check_images: bool = False) -> list[str]:
    """No Pillow import unless decoding is requested by the GUI exporter."""
    mapping = entry.get("fallback_images")
    if mapping is None:
        return []  # Preserve legacy projects' validation behavior.
    if not isinstance(mapping, dict):
        return ["fallback_images 必须为对象或 null"]
    if not mapping:
        return []
    errors = []
    for state, image in mapping.items():
        if state not in FALLBACK_STATES:
            errors.append(f"fallback_images 未知状态：{state}")
        if image is None:
            continue
        if not isinstance(image, dict):
            errors.append(f"fallback_images.{state} 必须为图片对象或 null")
            continue
        path = image.get("path")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"fallback_images.{state}.path 必须是非空图片路径")
    rows = fallback_rows(entry)
    if any(image is not None for image in mapping.values()) and not any(
            row["state"] == "DEFAULT" for row in rows):
        errors.append("领袖差分需要 DEFAULT 或原 images.diplo_foreground 默认图")
    if mapping and not re.fullmatch(r"LEADER_[A-Za-z0-9_]+", str(entry.get("type") or "")):
        errors.append("领袖差分需要合法的 LEADER_ type")
    if check_files:
        for row in rows:
            path = Path(row["source_path"])
            if not path.is_file():
                errors.append(f"领袖差分 {row['state']} 图片不存在：{path}")
            elif check_images:
                try:
                    from PIL import Image
                    with Image.open(path) as image:
                        image.verify()
                except (OSError, ValueError, SyntaxError) as exc:
                    errors.append(f"领袖差分 {row['state']} 图片不可读取：{exc}")
    return errors
