"""「UI图标」段：与游戏实体无关的自定义 UI 图标声明（纯标准库）。

用途：新闻分类图标、单位动作图标、追踪器图标等**不属于任何游戏实体**的图标，
原先只能借引擎自带的 ``ICON_YIELD_*`` 凑；本模块让 ``.CIV`` 可以直接声明它们，
并复用既有的「图标名 → IMG 缩放 → Textures DDS/TEX」链路输出纹理。

设计要点
--------
- **只加声明能力**：该段只影响 ``Icons.xml`` 与 IMG/Textures 产物，
  不参与 SQL / Players / PlayerItems / 文本生成；11 类实体内置图标的
  命名规则与产出顺序完全不变（回归面最小）。
- **单一事实来源**：GUI（``art_workspace``）、生成校验（``workspace_page``）与
  ``modgen validate`` 三处共用本模块，不再各写一套规则。
- **Qt 无关**：仅依赖标准库，可被 modgen（无 PyQt 环境）直接导入。

条目结构（``workspace["UI图标"]`` 列表元素）::

    {
        "icon_name": "ICON_SIQI_WUJIU_NEWS_CITY",  # 必填，须以 ICON_ 开头
        "name_zh": "城建图标",                      # 选填，仅 GUI 显示
        "sizes": [32, 50],                          # 选填，缺省用 DEFAULT_UI_ICON_SIZES
        "images": {"icon": {"path": "D:/.../news_city.png"}},  # 必填
        "alias": "",                                # 选填，非空则出 IconAliases 行
    }
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any, Callable, Iterable

#: ``.CIV`` workspace 里承载本段的键名
UI_ICON_SECTION = "UI图标"

#: 默认多尺寸（条目 ``sizes`` 为空时使用）
DEFAULT_UI_ICON_SIZES: tuple[int, ...] = (22, 32, 38, 50, 64, 80, 128, 256)

#: 图标名 / 图集名前缀
ICON_PREFIX = "ICON_"
ATLAS_PREFIX = "ATLAS_"

#: 条目 images 子键（与 11 类实体的 ``images.icon`` 约定一致）
IMAGE_VARIANT = "icon"

#: 源图搜索目录的缺省相对路径（条目只写文件名时按工程目录解析）
DEFAULT_SOURCE_SUBDIRS: tuple[str, ...] = ("IMG", "Images", "Art", "Art/Icons")

#: 缺省源图搜索子目录提供者：() -> 相对工程根目录的子目录列表
SourceDirProvider = Callable[[], Iterable[str]]


def normalize_icon_name(value: object) -> str:
    """规范化用户输入的图标名（去空白 + 大写）；不做 ``ICON_`` 前缀补全。

    前缀补全只在 GUI 编辑路径（保存时）执行，校验/构建路径保持原样，
    以便对「忘记写 ICON_」的条目报错而不是静默改写。
    """
    return str(value or "").strip().upper()


def entry_icon_name(entry: object) -> str:
    """条目的图标名（``icon_name``）。"""
    if not isinstance(entry, dict):
        return ""
    return normalize_icon_name(entry.get("icon_name"))


def entry_alias(entry: object) -> str:
    """条目的别名目标（``alias``）；非空表示用官方/其它图标别名代替自带图集。"""
    if not isinstance(entry, dict):
        return ""
    return normalize_icon_name(entry.get("alias"))


def entry_display_name(entry: object) -> str:
    """条目的 GUI 显示名（``name_zh`` 优先，回退图标名）。"""
    if isinstance(entry, dict):
        text = str(entry.get("name_zh") or entry.get("name") or "").strip()
        if text:
            return text
    return entry_icon_name(entry)


def entry_source_path(entry: object) -> str:
    """条目源 PNG 路径（``images.icon.path``）。"""
    if not isinstance(entry, dict):
        return ""
    images = entry.get("images")
    if not isinstance(images, dict):
        return ""
    payload = images.get(IMAGE_VARIANT)
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("path") or "").strip()


def set_entry_source_path(entry: dict[str, Any], path: object) -> None:
    """写回源 PNG 路径；路径为空时清空 ``images.icon``（不写 JSON 空串）。"""
    clean = str(path or "").strip()
    images = entry.get("images")
    if not isinstance(images, dict):
        images = {}
        entry["images"] = images
    if not clean:
        images.pop(IMAGE_VARIANT, None)
        return
    payload = images.get(IMAGE_VARIANT)
    if not isinstance(payload, dict):
        payload = {}
        images[IMAGE_VARIANT] = payload
    payload["path"] = clean


def parse_sizes_with_report(
    value: object, default: Iterable[int] = DEFAULT_UI_ICON_SIZES
) -> tuple[list[int], list[str], bool]:
    """解析尺寸输入，并回报被忽略的项。

    返回 ``(sizes, dropped, used_default)``：

    - ``dropped``：写了但非法的原始项（非数字 / <= 0），原样保留字符串以便报错；
    - ``used_default``：没有任何有效项、已回退 ``default``（此时 ``dropped`` 才值得告警）。
    """
    raw_items: list[object] = []
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    elif value is None or isinstance(value, bool):
        raw_items = []
    else:
        text = str(value).replace("，", ",").replace(";", ",").replace("；", ",")
        raw_items = text.replace("\n", ",").split(",")

    sizes: list[int] = []
    dropped: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            item = item.strip()
        if item in (None, ""):
            continue
        try:
            size = int(float(str(item).strip()))
        except (TypeError, ValueError):
            dropped.append(str(item))
            continue
        if size <= 0:
            dropped.append(str(item))
            continue
        if size not in sizes:
            sizes.append(size)

    used_default = not sizes
    if used_default:
        sizes = [int(item) for item in default if int(item) > 0]
    else:
        dropped = []
    return sorted(sizes), dropped, used_default


def parse_sizes(value: object, default: Iterable[int] = DEFAULT_UI_ICON_SIZES) -> list[int]:
    """解析尺寸输入：列表 / 逗号或空白分隔字符串 / 单值。

    非法（非数字、<= 0）项被忽略；结果去重并升序排列；
    全部为空时回退 ``default``。
    """
    sizes, _dropped, _used_default = parse_sizes_with_report(value, default)
    return sizes


def atlas_name_for(icon_name: str) -> str:
    """图标名 → 图集名：去掉 ``ICON_`` 前缀换成 ``ATLAS_``（与 11 类实体一致）。"""
    text = normalize_icon_name(icon_name)
    if text.startswith(ICON_PREFIX):
        return f"{ATLAS_PREFIX}{text[len(ICON_PREFIX):]}"
    return f"{ATLAS_PREFIX}{text}" if text else ""


def is_valid_icon_token(icon_name: str) -> bool:
    """图标名是否只含 ``[A-Za-z0-9_]``。"""
    text = normalize_icon_name(icon_name)
    if not text:
        return False
    return all(char.isalnum() and char.isascii() or char == "_" for char in text)


def iter_ui_icon_entries(section_value: object) -> list[dict[str, Any]]:
    """取「UI图标」段的条目列表（非列表/非字典元素一律忽略）。"""
    if not isinstance(section_value, list):
        return []
    return [entry for entry in section_value if isinstance(entry, dict)]


def read_png_size(path: object) -> tuple[int, int] | None:
    """只读 PNG 头部取 (宽, 高)；非 PNG / 读取失败返回 None（不依赖 Pillow）。"""
    clean = str(path or "").strip()
    if not clean:
        return None
    try:
        target = Path(clean)
        if not target.is_file():
            return None
        with target.open("rb") as handle:
            header = handle.read(24)
            if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                return None
            if header[12:16] != b"IHDR":
                return None
            width, height = struct.unpack(">II", header[16:24])
    except OSError:
        return None
    if width <= 0 or height <= 0:
        return None
    return int(width), int(height)


def resolve_source_path(
    raw_path: object,
    *,
    output_dir: Path | None = None,
    source_dir_provider: SourceDirProvider | None = None,
) -> Path | None:
    """把条目里的源图路径解析成实际路径。

    - 绝对路径 → 原样；
    - 形如 ``IMG/x.png`` → 按 ``output_dir``（工程根目录）解析；
    - 只有文件名 → 依次在 ``source_dir_provider()`` 给出的子目录（缺省
      :data:`DEFAULT_SOURCE_SUBDIRS`）与工程根目录下查找。
    找不到时返回最可能的候选路径（用于报错展示），完全无从下手返回 ``None``。
    """
    clean = str(raw_path or "").strip()
    if not clean:
        return None
    candidate = Path(clean)
    if candidate.is_absolute():
        return candidate
    if output_dir is None:
        return candidate

    normalized = clean.replace("\\", "/")
    if "/" in normalized:
        return output_dir / Path(normalized)

    subdirs: list[str] = []
    try:
        if source_dir_provider is not None:
            subdirs = [str(item) for item in source_dir_provider() if str(item).strip()]
    except Exception:
        subdirs = []
    if not subdirs:
        subdirs = list(DEFAULT_SOURCE_SUBDIRS)

    for subdir in subdirs:
        probe = output_dir / Path(subdir.replace("\\", "/")) / candidate.name
        if probe.is_file():
            return probe
    probe = output_dir / candidate.name
    if probe.is_file():
        return probe
    # 都找不到：按第一个搜索目录给出候选，报错信息里路径更贴近用户预期
    return output_dir / Path(subdirs[0].replace("\\", "/")) / candidate.name


def entity_icon_name_patterns(entity_icon_names: Iterable[str]) -> list[str]:
    """由真实实体图标名推导出「命名空间前缀」，用于重名判定。

    ``ICON_DISTRICT_SIQI_DEMO`` → ``ICON_DISTRICT_SIQI_DEMO``（本体）+
    ``ICON_DISTRICT``（去掉 ``_`` 后的首段）= 该实体类型名对应的命名空间。

    前者拦住与本工程实体的**完全同名**，后者拦住「换了个后缀也仍属于实体类型」
    的名字（``ICON_DISTRICT_NEWS`` 依然会和 ``DISTRICT_NEWS`` 撞车）。
    """
    patterns: set[str] = set()
    for raw in entity_icon_names:
        name = normalize_icon_name(raw)
        if not name:
            continue
        patterns.add(name)
        if not name.startswith(ICON_PREFIX):
            continue
        body = name[len(ICON_PREFIX):]
        if "_" in body:
            head = body.split("_", 1)[0]
            if head:
                patterns.add(f"{ICON_PREFIX}{head}")
    return sorted(patterns)


def _hits_entity_namespace(icon_name: str, entity_names: set[str]) -> bool:
    """图标名是否落在某个实体内置图标名下（完全同名或其后接 ``_`` 的派生名）。

    modgen 侧只提供 ``ICON_<实体头>`` 这样的模式（如 ``ICON_UNIT``），
    此时 ``ICON_UNIT_SIQI_X`` 会命中；GUI 侧提供真实图标名，判定同样精确。
    """
    if not entity_names:
        return False
    if icon_name in entity_names:
        return True
    return any(icon_name.startswith(f"{name}_") for name in entity_names)


def _entry_issue(kind: str, message: str, *, index: int, icon_name: str = "", path: str = "") -> dict[str, object]:
    return {
        "kind": kind,
        "message": message,
        "index": index,
        "icon_name": icon_name,
        "path": path,
    }


def build_ui_icons_xml_rows(
    entries: Iterable[object],
    *,
    entity_icon_names: Iterable[str] = (),
    default_sizes: Iterable[int] = DEFAULT_UI_ICON_SIZES,
) -> dict[str, object]:
    """按条目生成 ``Icons.xml`` 行（纯字符串，不参与 I/O）。

    返回值（字典）：

    ``atlas_rows``
        ``<IconTextureAtlases><Row .../></IconTextureAtlases>`` 内的行；
    ``def_rows``
        ``<IconDefinitions><Row .../></IconDefinitions>`` 内的行；
    ``alias_rows``
        ``<IconAliases><Row .../></IconAliases>`` 内的行；
    ``icon_names``
        实际产出（atlas + 定义行）的图标名列表；
    ``errors`` / ``warnings``
        逐条问题清单（``{"kind", "message", "index", "icon_name", "path"}``）；
        有 ``errors`` 的条目被跳过，但有问题的**其它条目照常产出**。

    ``entity_icon_names`` 用于「不得与 11 类实体图标重名」的硬校验：
    既拦完全同名，也拦**落在实体图标命名空间内**的名字（``ICON_<实体名>_*``）——
    后者即使本工程暂时没有该实体，也会在别的 Mod 里撞名。
    """
    entity_names = {normalize_icon_name(name) for name in entity_icon_names if str(name or "").strip()}

    atlas_rows: list[str] = []
    def_rows: list[str] = []
    alias_rows: list[str] = []
    icon_names: list[str] = []
    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(_entry_issue("entry_not_object", f"UI图标[{index}] 不是对象", index=index))
            continue

        icon_name = entry_icon_name(entry)
        alias = entry_alias(entry)

        if not icon_name:
            errors.append(_entry_issue("icon_name_missing", f"UI图标[{index}] 缺少 icon_name", index=index))
            continue
        if not icon_name.startswith(ICON_PREFIX):
            errors.append(
                _entry_issue(
                    "icon_name_prefix",
                    f"UI图标[{index}] 的 icon_name 必须以 {ICON_PREFIX} 开头（实际 {icon_name}）",
                    index=index,
                    icon_name=icon_name,
                )
            )
            continue
        if not is_valid_icon_token(icon_name):
            errors.append(
                _entry_issue(
                    "icon_name_token",
                    f"UI图标[{index}] 的 icon_name 含非法字符（只允许字母/数字/下划线）：{icon_name}",
                    index=index,
                    icon_name=icon_name,
                )
            )
            continue
        if icon_name in seen:
            errors.append(
                _entry_issue(
                    "icon_name_duplicate",
                    f"icon_name 在「UI图标」段内重复：{icon_name}",
                    index=index,
                    icon_name=icon_name,
                )
            )
            continue
        seen.add(icon_name)
        if _hits_entity_namespace(icon_name, entity_names):
            errors.append(
                _entry_issue(
                    "icon_name_entity_conflict",
                    f"icon_name 落在实体内置图标的命名空间：{icon_name}"
                    "（实体图标名为 ICON_<实体类型>，请换一个不会与实体类型冲突的名字；"
                    "若想复用某个已有图标，请把该图标名填到「别名」列）",
                    index=index,
                    icon_name=icon_name,
                )
            )
            continue

        sizes, dropped_sizes, used_default = parse_sizes_with_report(entry.get("sizes"), default_sizes)
        if used_default and dropped_sizes:
            warnings.append(
                _entry_issue(
                    "sizes_invalid",
                    f"{icon_name} 的 sizes 无有效项（{', '.join(dropped_sizes)}），"
                    f"已回退默认尺寸 {','.join(str(s) for s in sizes)}",
                    index=index,
                    icon_name=icon_name,
                )
            )

        if alias:
            alias_rows.append(f'    <Row Name="{icon_name}" OtherName="{alias}"/>')
            continue

        source_path = entry_source_path(entry)
        if not source_path:
            warnings.append(
                _entry_issue(
                    "source_missing",
                    f"{icon_name} 未设置源 PNG，已跳过图集输出（该条目不会出现在 Icons.xml）",
                    index=index,
                    icon_name=icon_name,
                )
            )
            continue

        atlas = atlas_name_for(icon_name)
        for size in sizes:
            atlas_rows.append(f'    <Row Name="{atlas}" IconSize="{size}" Filename="{icon_name}_{size}"/>')
        def_rows.append(f'    <Row Name="{icon_name}" Atlas="{atlas}" Index="0"/>')
        icon_names.append(icon_name)

    return {
        "atlas_rows": atlas_rows,
        "def_rows": def_rows,
        "alias_rows": alias_rows,
        "icon_names": icon_names,
        "errors": errors,
        "warnings": warnings,
    }


def validate_ui_icons(
    section_value: object,
    *,
    entity_icon_names: Iterable[str] = (),
    output_dir: Path | None = None,
    source_dir_provider: SourceDirProvider | None = None,
    check_source_files: bool = True,
) -> dict[str, object]:
    """校验「UI图标」段。

    返回 ``{"errors": [...], "warnings": [...], "icon_names": [...],
    "count": 段内条目数, "valid_count": 可产出条数}``。

    ERROR（阻断生成）：图标名缺失/前缀错误/非法字符/段内重复/落在实体图标命名空间、
    源 PNG 不存在；
    WARNING（不阻断）：未设置源 PNG（该条被跳过）、
    源图最小边小于 ``max(sizes)``（缩放会失真/模糊）、尺寸字段非法项。

    ``check_source_files=False``：调用方无法定位工程目录时跳过源图存在性判定
    （避免把「无法判定」误报成「文件不存在」）。
    """
    entries = iter_ui_icon_entries(section_value)
    built = build_ui_icons_xml_rows(entries, entity_icon_names=entity_icon_names)
    errors: list[dict[str, object]] = list(built["errors"])
    warnings: list[dict[str, object]] = list(built["warnings"])
    icon_names = list(built["icon_names"])
    produced = set(icon_names)

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        icon_name = entry_icon_name(entry)
        if not icon_name or icon_name not in produced:
            continue  # 已有 ERROR / 已按 alias 产出，无需再查源图

        sizes = parse_sizes(entry.get("sizes"))

        raw_path = entry_source_path(entry)
        resolved = resolve_source_path(
            raw_path, output_dir=output_dir, source_dir_provider=source_dir_provider
        )
        exists = bool(resolved is not None and resolved.is_file())
        if not exists:
            if not check_source_files:
                # 调用方没有可判定的基准目录：不做存在性判定
                continue
            errors.append(
                _entry_issue(
                    "source_not_found",
                    f"{icon_name} 的源 PNG 不存在：{resolved if resolved is not None else raw_path}",
                    index=index,
                    icon_name=icon_name,
                    path=str(resolved) if resolved is not None else raw_path,
                )
            )
            continue

        size = read_png_size(resolved)
        if size is None:
            warnings.append(
                _entry_issue(
                    "source_unreadable",
                    f"{icon_name} 的源 PNG 无法读取尺寸（文件损坏或非 PNG）：{resolved}",
                    index=index,
                    icon_name=icon_name,
                    path=str(resolved),
                )
            )
            continue

        required = max(sizes) if sizes else 0
        shortest = min(size)
        if required and shortest < required:
            warnings.append(
                _entry_issue(
                    "source_too_small",
                    f"{icon_name} 的源图最小边 {shortest}px 小于最大输出尺寸 {required}px"
                    f"（{resolved}），放大会模糊——建议源图至少 {required}×{required}",
                    index=index,
                    icon_name=icon_name,
                    path=str(resolved),
                )
            )

    return {
        "errors": errors,
        "warnings": warnings,
        "icon_names": icon_names,
        "count": len(entries),
        "valid_count": len(icon_names),
    }


def build_source_state_map(section_value: object) -> dict[str, dict[str, object]]:
    """``{icon_name: {"path": ...}}``（供 ``_collect_icon_source_states`` 合并）。

    未设置源 PNG 的条目不入表——与 11 类实体「无图则不产出 IMG/DDS」一致。
    """
    output: dict[str, dict[str, object]] = {}
    for entry in iter_ui_icon_entries(section_value):
        icon_name = entry_icon_name(entry)
        if not icon_name or entry_alias(entry):
            # 有 alias 的条目不出自带图集，无需源图
            continue
        path = entry_source_path(entry)
        if not path:
            continue
        output[icon_name] = {"path": path}
    return output


def build_preview_rows(section_value: object) -> list[dict[str, object]]:
    """GUI 表格数据：每条一行（含别名/未设源图等不可产出条目的说明）。"""
    rows: list[dict[str, object]] = []
    for entry in iter_ui_icon_entries(section_value):
        rows.append(
            {
                "icon_name": entry_icon_name(entry),
                "name_zh": str(entry.get("name_zh") or entry.get("name") or "").strip(),
                "sizes": parse_sizes(entry.get("sizes")),
                "source_path": entry_source_path(entry),
                "alias": entry_alias(entry),
            }
        )
    return rows
