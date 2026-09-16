"""纯标准库 .civ6proj 工程文件生成器 —— 复刻 ModBuddy 新建工程向导的产物格式。

背景（对齐官方 SDK）：
- ModBuddy "新建工程" = 向导把模板里的 `{Name}.civ6proj`（MSBuild XML）与
  空白 `{Name}.Art.xml` 复制到 `文档\\Firaxis ModBuddy\\Civilization VI\\<Name>\\`，
  替换 `$Name$ / $guid1$ / $guid2$ / $Teaser$` 等占位符。**不生成 .modinfo**
  （.modinfo 是 Build 时由 Civ6.targets 的 GenerateModInfo 任务生成）。
- 本模块生成与向导产物同构的 XML：ModBuddy 之后仍可直接打开/构建；
  不含美术资源时也可直接手写/复制 modinfo 部署进游戏。

无 PyQt 依赖，GUI（基础信息页"新建 .civ6proj"按钮）、modgen CLI、
AI 控制接口（civ6proj_create 动作）共用同一实现。
"""
from __future__ import annotations

import html
import re
import uuid
from pathlib import Path

try:
    from ..db.paths import _resolve_data_path
except ImportError:  # 仓库布局被破坏时的兜底（与 mt_bridge 同思路）
    _resolve_data_path = lambda name: Path(__file__).resolve().parents[1] / "data" / name  # noqa: E731

DEFAULT_COMPATIBLE_VERSIONS = "1.2,2.0"
MSBUILD_NAMESPACE = "http://schemas.microsoft.com/developer/msbuild/2003"


def new_guid() -> str:
    """生成小写 GUID（与 ModBuddy 写入的 Guid/ProjectGuid 格式一致）。"""
    return str(uuid.uuid4())


def sanitize_file_name(raw_name: str) -> str:
    """清理文件名基名（去掉非法字符/空白），为空时回退 'MyMod'。"""
    text = re.sub(r"[\\/:*?\"<>|]+", "_", str(raw_name or ""))
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "MyMod"


def _xml_text(value: object, *, attribute: bool = False) -> str:
    return html.escape(str(value or ""), quote=attribute)


def build_action_data_xml(root_tag: str, entries: list[dict[str, object]]) -> str:
    """生成 FrontEndActions/InGameActions CDATA 内容（与 workspace_page 同格式）。"""
    lines = [f"<{root_tag}>"]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        action_type = str(entry.get("type") or "").strip() or "UpdateDatabase"
        action_id = str(entry.get("id") or "").strip() or action_type
        files = [
            str(item).strip()
            for item in (entry.get("files") if isinstance(entry.get("files"), list) else [])
            if str(item).strip()
        ]
        try:
            load_order = max(0, int(entry.get("load_order", 0)))
        except (TypeError, ValueError):
            load_order = 0

        lines.append(f'  <{action_type} id="{_xml_text(action_id, attribute=True)}">')
        needs_context = action_type == "AddUserInterfaces"
        if load_order > 0 or needs_context:
            lines.append("    <Properties>")
            if load_order > 0:
                lines.append(f"      <LoadOrder>{load_order}</LoadOrder>")
            if needs_context:
                lines.append("      <Context>InGame</Context>")
            lines.append("    </Properties>")
        for file_path in files:
            normalized_file = file_path
            if action_type == "UpdateIcons":
                normalized_lower = file_path.lower()
                if (
                    normalized_lower.endswith("icons.xml") or normalized_lower.endswith("_icons.xml")
                ) and not normalized_lower.startswith("icons/"):
                    normalized_file = f"Icons/{file_path.lstrip('/\\')}"
            lines.append(f"    <File>{_xml_text(normalized_file)}</File>")
        lines.append(f"  </{action_type}>")
    lines.append(f"</{root_tag}>")
    return "\n".join(lines)


def build_civ6proj_xml(
    *,
    mod_name: str,
    file_name: str,
    guid: str | None = None,
    project_guid: str | None = None,
    mod_version: str = "1",
    teaser: str = "",
    description: str = "",
    authors: str = "",
    special_thanks: str = "",
    affects_saved_games: bool = True,
    supports_single_player: bool = True,
    supports_multiplayer: bool = True,
    supports_hotseat: bool = True,
    compatible_versions: str = DEFAULT_COMPATIBLE_VERSIONS,
    localized_text_data: str = "",
    front_end_actions: list[dict[str, object]] | None = None,
    in_game_actions: list[dict[str, object]] | None = None,
    art_xml_name: str | None = None,
    content_files: list[str] | None = None,
    folder_paths: list[str] | None = None,
) -> str:
    """构造与 ModBuddy 向导同构的 .civ6proj（MSBuild XML）文本。

    必填：mod_name（Mod 显示名）、file_name（文件基名）。
    art_xml_name 缺省为 `{file_name}.Art.xml`（None Include 条目）；
    传 None 表示不写 Art.xml 条目。
    """
    name = str(mod_name or "").strip() or file_name
    teaser_text = str(teaser or "").strip() or name
    description_text = str(description or "").strip() or teaser_text
    project_guid_value = str(project_guid or "").strip() or new_guid()
    mod_guid = str(guid or "").strip() or new_guid()
    if art_xml_name is None:
        art_xml_name = f"{file_name}.Art.xml"

    def _bool(value: bool) -> str:
        return "true" if value else "false"

    lines: list[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<Project ToolsVersion="12.0" DefaultTargets="Default" xmlns="{MSBUILD_NAMESPACE}">',
        "  <PropertyGroup>",
        '    <Configuration Condition=" \'$(Configuration)\' == \'\' ">Default</Configuration>',
        f"    <Name>{_xml_text(name)}</Name>",
        f"    <Guid>{mod_guid}</Guid>",
        f"    <ProjectGuid>{project_guid_value}</ProjectGuid>",
        f"    <ModVersion>{int(mod_version) if str(mod_version).strip().isdigit() else 1}</ModVersion>",
        f"    <Teaser>{_xml_text(teaser_text)}</Teaser>",
        f"    <Description>{_xml_text(description_text)}</Description>",
        f"    <Authors>{_xml_text(authors)}</Authors>",
        f"    <SpecialThanks>{_xml_text(special_thanks)}</SpecialThanks>",
        f"    <AffectsSavedGames>{_bool(affects_saved_games)}</AffectsSavedGames>",
        f"    <SupportsSinglePlayer>{_bool(supports_single_player)}</SupportsSinglePlayer>",
        f"    <SupportsMultiplayer>{_bool(supports_multiplayer)}</SupportsMultiplayer>",
        f"    <SupportsHotSeat>{_bool(supports_hotseat)}</SupportsHotSeat>",
        f"    <CompatibleVersions>{_xml_text(compatible_versions or DEFAULT_COMPATIBLE_VERSIONS)}</CompatibleVersions>",
    ]
    if str(localized_text_data or "").strip():
        lines.append(f"    <LocalizedTextData><![CDATA[{localized_text_data}]]></LocalizedTextData>")
    front_entries = front_end_actions or []
    if front_entries:
        lines.append(f"    <FrontEndActionData><![CDATA[{build_action_data_xml('FrontEndActions', front_entries)}]]></FrontEndActionData>")
    in_game_entries = in_game_actions or []
    if in_game_entries:
        lines.append(f"    <InGameActionData><![CDATA[{build_action_data_xml('InGameActions', in_game_entries)}]]></InGameActionData>")
    lines.extend(
        [
            "  </PropertyGroup>",
            '  <PropertyGroup Condition=" \'$(Configuration)\' == \'Default\' ">',
            "    <OutputPath>.</OutputPath>",
            "  </PropertyGroup>",
            "  <ItemGroup>",
        ]
    )
    if art_xml_name:
        lines.append(f'    <None Include="{_xml_text(art_xml_name, attribute=True)}" />')
    for rel_path in content_files or []:
        include = str(rel_path).replace("/", "\\")
        lines.append(f'    <Content Include="{_xml_text(include, attribute=True)}">')
        lines.append("      <SubType>Content</SubType>")
        lines.append("    </Content>")
    for folder in folder_paths or []:
        include = str(folder).replace("/", "\\")
        if include and not include.endswith("\\"):
            include = f"{include}\\"
        lines.append(f'    <Folder Include="{_xml_text(include, attribute=True)}" />')
    lines.extend(
        [
            "  </ItemGroup>",
            '  <Import Project="$(MSBuildLocalExtensionPath)Civ6.targets" />',
            "</Project>",
            "",
        ]
    )
    return "\n".join(lines)


def blank_art_xml_source() -> Path:
    """内置空白 Art.xml 模板路径（ModTools_5_4/data/default_blank_art.xml）。"""
    return _resolve_data_path("default_blank_art.xml")


def default_modbuddy_project_dir(file_name: str) -> Path:
    """ModBuddy 新建工程的默认目录：文档\\Firaxis ModBuddy\\Civilization VI\\<file_name>\\。"""
    return Path.home() / "Documents" / "Firaxis ModBuddy" / "Civilization VI" / sanitize_file_name(file_name)


def generate_blank_art_xml_file(target: Path) -> Path:
    """把内置空白 Art.xml 模板写入 target，返回 target。"""
    source = blank_art_xml_source()
    if not source.exists():
        # 极端兜底：内置模板丢失时写最小合法骨架，保证 .civ6proj 引用不悬空
        target.write_text("<AssetObjects::ArtDefSet />\n", encoding="utf-8")
        return target
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def create_mod_project(
    *,
    directory: Path,
    file_name: str,
    mod_name: str,
    guid: str | None = None,
    project_guid: str | None = None,
    teaser: str = "",
    description: str = "",
    authors: str = "",
    special_thanks: str = "",
    affects_saved_games: bool = True,
    supports_single_player: bool = True,
    supports_multiplayer: bool = True,
    supports_hotseat: bool = True,
    compatible_versions: str = DEFAULT_COMPATIBLE_VERSIONS,
    write_art_xml: bool = True,
) -> dict[str, object]:
    """在 directory 下创建 `{file_name}.civ6proj`（+ 可选空白 `{file_name}.Art.xml`）。

    guid（=ModID，游戏唯一标识）/ project_guid 缺省时自动生成（UUID v4，不重复）；
    已存在 Mod 重建时必须传原 guid，保证 ModID 稳定。

    返回 {"civ6proj": Path, "art_xml": Path | None, "guid": str, "project_guid": str}。
    """
    safe_name = sanitize_file_name(file_name)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)

    mod_guid = str(guid or "").strip() or new_guid()
    project_guid_value = str(project_guid or "").strip() or new_guid()
    xml_text = build_civ6proj_xml(
        mod_name=mod_name,
        file_name=safe_name,
        guid=mod_guid,
        project_guid=project_guid_value,
        teaser=teaser,
        description=description,
        authors=authors,
        special_thanks=special_thanks,
        affects_saved_games=affects_saved_games,
        supports_single_player=supports_single_player,
        supports_multiplayer=supports_multiplayer,
        supports_hotseat=supports_hotseat,
        compatible_versions=compatible_versions,
    )
    proj_path = root / f"{safe_name}.civ6proj"
    proj_path.write_text(xml_text, encoding="utf-8")

    art_xml_path: Path | None = None
    if write_art_xml:
        art_xml_path = generate_blank_art_xml_file(root / f"{safe_name}.Art.xml")
    return {
        "civ6proj": proj_path,
        "art_xml": art_xml_path,
        "guid": mod_guid,
        "project_guid": project_guid_value,
    }
