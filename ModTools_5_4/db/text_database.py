"""Text database creation/import/query helpers."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
import xml.etree.ElementTree as ET


SIMPLIFIED_LANGUAGE = "zh_Hans_CN"
SIMPLIFIED_LANGUAGE_NORMALIZED = SIMPLIFIED_LANGUAGE.lower()
LOC_REF_PATTERN = re.compile(r"\{(LOC_[A-Z0-9_]+)\}")


@dataclass(slots=True)
class ImportRecord:
    source_file: Path
    tag: str
    text: str


@dataclass(slots=True)
class ImportResult:
    inserted_count: int
    updated_count: int
    ignored_conflict_count: int
    parsed_file_count: int


@dataclass(slots=True)
class ConflictInfo:
    tag: str
    source_files: list[Path]


@dataclass(slots=True)
class ParsedImportBundle:
    records: list[ImportRecord]
    conflict_infos: list[ConflictInfo]


def _normalize_language(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def _is_chinese_language(value: str | None) -> bool:
    language = _normalize_language(value)
    return language == SIMPLIFIED_LANGUAGE_NORMALIZED


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\r", "").replace("\n", "").strip()


def _element_local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def create_local_text_database_from_source(source_db_path: Path, target_db_path: Path) -> int:
    """Create a local sqlite text DB by copying Chinese rows from source localization DB."""
    if not source_db_path.exists():
        raise FileNotFoundError(f"基础文本数据库不存在: {source_db_path}")

    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    if target_db_path.exists():
        target_db_path.unlink()

    source_conn = sqlite3.connect(str(source_db_path))
    source_conn.row_factory = sqlite3.Row
    target_conn = sqlite3.connect(str(target_db_path))
    copied = 0
    try:
        target_conn.execute(
            """
            CREATE TABLE LocalizedText (
                Tag TEXT PRIMARY KEY,
                Language TEXT NOT NULL,
                Text TEXT NOT NULL
            )
            """
        )
        target_conn.execute("CREATE INDEX idx_localized_language ON LocalizedText(Language)")

        rows = source_conn.execute(
            "SELECT Tag, Language, Text FROM LocalizedText WHERE lower(Language) = ?",
            (SIMPLIFIED_LANGUAGE_NORMALIZED,),
        ).fetchall()

        for row in rows:
            tag = str(row["Tag"] or "").strip()
            language = str(row["Language"] or "").strip()
            text = _clean_text(str(row["Text"] or ""))
            if not tag or not _is_chinese_language(language):
                continue
            target_conn.execute(
                "INSERT OR REPLACE INTO LocalizedText(Tag, Language, Text) VALUES (?, ?, ?)",
                (tag, SIMPLIFIED_LANGUAGE, text),
            )
            copied += 1

        target_conn.commit()
        return copied
    finally:
        source_conn.close()
        target_conn.close()


def import_dlc_texts(text_db_path: Path, dlc_root_path: Path, selected_conflict_files: set[Path] | None = None) -> ImportResult:
    """Import texts from all files under folders named Text within a DLC root."""
    text_files: list[Path] = []
    for candidate in dlc_root_path.rglob("*"):
        if not candidate.is_file():
            continue
        if not any(part.lower() == "text" for part in candidate.parts):
            continue
        if candidate.suffix.lower() not in {".xml", ".sql"}:
            continue
        text_files.append(candidate)
    return import_text_files(text_db_path, text_files, selected_conflict_files)


def import_folder_texts(text_db_path: Path, folder_path: Path, selected_conflict_files: set[Path] | None = None) -> ImportResult:
    """Import XML/SQL files recursively from a folder."""
    text_files = [
        path
        for path in folder_path.rglob("*")
        if path.is_file() and path.suffix.lower() in {".xml", ".sql"}
    ]
    return import_text_files(text_db_path, text_files, selected_conflict_files)


def import_modinfo_texts(text_db_path: Path, modinfo_path: Path, selected_conflict_files: set[Path] | None = None) -> ImportResult:
    """Import files referenced by <UpdateText><File> in .modinfo."""
    resolved_files = resolve_modinfo_text_files(modinfo_path)
    return import_text_files(text_db_path, resolved_files, selected_conflict_files)


def resolve_modinfo_text_files(modinfo_path: Path) -> list[Path]:
    """Resolve all text file paths declared in a .modinfo UpdateText section."""
    file_refs = _extract_modinfo_file_refs(modinfo_path)
    resolved_files: list[Path] = []
    root_dir = modinfo_path.parent
    for relative in file_refs:
        target = (root_dir / relative).resolve()
        if target.exists() and target.suffix.lower() in {".xml", ".sql"}:
            resolved_files.append(target)
    return resolved_files


def parse_import_files(files: list[Path], loc_tag_only: bool = False) -> ParsedImportBundle:
    records: list[ImportRecord] = []
    tag_sources: dict[str, set[Path]] = defaultdict(set)

    for file_path in files:
        file_records = _parse_one_file(file_path, loc_tag_only=loc_tag_only)
        records.extend(file_records)
        for record in file_records:
            tag_sources[record.tag].add(record.source_file)

    conflict_infos = [
        ConflictInfo(tag=tag, source_files=sorted(source_files, key=lambda p: str(p)))
        for tag, source_files in tag_sources.items()
        if len(source_files) > 1
    ]
    return ParsedImportBundle(records=records, conflict_infos=conflict_infos)


def import_text_files(
    text_db_path: Path,
    files: list[Path],
    selected_conflict_files: set[Path] | None = None,
    loc_tag_only: bool = False,
) -> ImportResult:
    """Import XML/SQL text files into current text DB (Chinese only)."""
    bundle = parse_import_files(files, loc_tag_only=loc_tag_only)
    return import_parsed_bundle(text_db_path, bundle, selected_conflict_files)


def import_parsed_bundle(
    text_db_path: Path,
    bundle: ParsedImportBundle,
    selected_conflict_files: set[Path] | None = None,
) -> ImportResult:
    """Import already parsed records into current text DB (Chinese only)."""
    records = bundle.records
    if not records:
        return ImportResult(0, 0, 0, 0)

    conn = sqlite3.connect(str(text_db_path))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_text_schema(conn)
        existing_tags = _fetch_existing_tags(conn, {record.tag for record in records})
        incoming_sources: dict[str, set[Path]] = defaultdict(set)
        for record in records:
            incoming_sources[record.tag].add(record.source_file)
        incoming_conflict_tags = {tag for tag, sources in incoming_sources.items() if len(sources) > 1}

        inserted_count = 0
        updated_count = 0
        ignored_conflict_count = 0

        for record in records:
            is_conflict = record.tag in existing_tags or record.tag in incoming_conflict_tags
            if is_conflict and selected_conflict_files is not None and record.source_file not in selected_conflict_files:
                ignored_conflict_count += 1
                continue

            if record.tag in existing_tags:
                conn.execute(
                    "UPDATE LocalizedText SET Text = ?, Language = ? WHERE Tag = ?",
                    (record.text, SIMPLIFIED_LANGUAGE, record.tag),
                )
                updated_count += 1
            else:
                conn.execute(
                    "INSERT INTO LocalizedText(Tag, Language, Text) VALUES (?, ?, ?)",
                    (record.tag, SIMPLIFIED_LANGUAGE, record.text),
                )
                existing_tags.add(record.tag)
                inserted_count += 1

        conn.commit()
        parsed_file_count = len({record.source_file for record in records})
        return ImportResult(inserted_count, updated_count, ignored_conflict_count, parsed_file_count)
    finally:
        conn.close()


def load_conflicts_against_db(text_db_path: Path, records: list[ImportRecord]) -> list[ConflictInfo]:
    """Build conflict list by checking incoming tags against existing DB tags."""
    if not records:
        return []

    conn = sqlite3.connect(str(text_db_path))
    try:
        _ensure_text_schema(conn)
        existing = _fetch_existing_tags(conn, {record.tag for record in records})
    finally:
        conn.close()

    by_tag: dict[str, set[Path]] = defaultdict(set)
    for record in records:
        if record.tag in existing:
            by_tag[record.tag].add(record.source_file)

    return [
        ConflictInfo(tag=tag, source_files=sorted(files, key=lambda p: str(p)))
        for tag, files in sorted(by_tag.items(), key=lambda item: item[0])
    ]


def query_text_by_tag(text_db_path: Path, tag: str, resolve_nested: bool = True) -> str:
    """Query text by tag, and optionally resolve nested {LOC_XXX} references."""
    normalized_tag = tag.strip()
    if not normalized_tag:
        return ""

    conn = sqlite3.connect(str(text_db_path))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_text_schema(conn)

        def fetch_one(one_tag: str) -> str | None:
            row = conn.execute(
                "SELECT Text FROM LocalizedText WHERE Tag = ? AND lower(Language) = ? LIMIT 1",
                (one_tag, SIMPLIFIED_LANGUAGE_NORMALIZED),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT Text FROM LocalizedText WHERE Tag = ? LIMIT 1",
                    (one_tag,),
                ).fetchone()
                if row is None:
                    return None
            return str(row[0])

        value = fetch_one(normalized_tag)
        if value is None:
            return normalized_tag

        if not resolve_nested:
            return value

        return _resolve_nested_loc_refs(value, fetch_one)
    finally:
        conn.close()


def _resolve_nested_loc_refs(text: str, getter) -> str:
    result = text
    visited: set[str] = set()

    for _ in range(10):
        matches = LOC_REF_PATTERN.findall(result)
        if not matches:
            return result

        changed = False
        for loc_tag in matches:
            if loc_tag in visited:
                continue
            visited.add(loc_tag)
            mapped = getter(loc_tag)
            replacement = mapped if mapped is not None else loc_tag
            if "\n" in replacement:
                replacement = replacement.replace("\n", "")
            previous = result
            result = result.replace("{" + loc_tag + "}", replacement)
            changed = changed or (previous != result)

        if not changed:
            return result

    return result


def _ensure_text_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS LocalizedText (
            Tag TEXT PRIMARY KEY,
            Language TEXT NOT NULL,
            Text TEXT NOT NULL
        )
        """
    )


def _fetch_existing_tags(conn: sqlite3.Connection, tags: set[str]) -> set[str]:
    if not tags:
        return set()

    max_bindings = 900
    tag_list = list(tags)
    existing: set[str] = set()

    for start in range(0, len(tag_list), max_bindings):
        batch = tag_list[start:start + max_bindings]
        placeholders = ",".join("?" for _ in batch)
        rows = conn.execute(
            f"SELECT Tag FROM LocalizedText WHERE Tag IN ({placeholders})",
            tuple(batch),
        ).fetchall()
        existing.update(str(row[0]) for row in rows)

    return existing


def _parse_one_file(file_path: Path, loc_tag_only: bool = False) -> list[ImportRecord]:
    suffix = file_path.suffix.lower()
    if suffix in {".xml", ".modinfo"}:
        return _parse_xml_file(file_path, loc_tag_only=loc_tag_only)
    if suffix == ".sql":
        return _parse_sql_file(file_path, loc_tag_only=loc_tag_only)
    return []


def _parse_xml_file(file_path: Path, loc_tag_only: bool = False) -> list[ImportRecord]:
    try:
        tree = ET.parse(file_path)
    except ET.ParseError:
        return []

    records: list[ImportRecord] = []
    root = tree.getroot()
    for element in root.iter():
        attrs = {k.lower(): v for k, v in element.attrib.items()}

        tag = attrs.get("tag")
        language = attrs.get("language")
        text_value = attrs.get("text")

        for child in list(element):
            child_name = _element_local_name(child.tag).lower()
            if child_name == "tag" and not tag:
                tag = (child.text or "").strip()
            elif child_name == "language" and not language:
                language = (child.text or "").strip()
            elif child_name == "text" and not text_value:
                text_value = "".join(child.itertext())

        if not tag:
            continue
        normalized_tag = str(tag).strip()
        if loc_tag_only and not normalized_tag.upper().startswith("LOC_"):
            continue
        if not _is_chinese_language(language):
            continue

        cleaned = _clean_text(text_value)
        if not cleaned:
            continue
        records.append(ImportRecord(source_file=file_path, tag=normalized_tag, text=cleaned))

    return records


def _parse_sql_file(file_path: Path, loc_tag_only: bool = False) -> list[ImportRecord]:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    statements = _split_sql_statements(content)
    records: list[ImportRecord] = []

    for statement in statements:
        lowered = statement.lower()
        if "update " in lowered:
            continue
        if "localizedtext" not in lowered:
            continue
        if "insert" not in lowered and "replace" not in lowered:
            continue

        parsed = _parse_insert_like_statement(statement)
        for row in parsed:
            tag = row.get("tag", "").strip()
            if loc_tag_only and not tag.upper().startswith("LOC_"):
                continue
            language = row.get("language", "").strip()
            text_value = _clean_text(row.get("text", ""))
            if not tag or not _is_chinese_language(language):
                continue
            records.append(ImportRecord(source_file=file_path, tag=tag, text=text_value))

    return records


def _split_sql_statements(content: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False

    for char in content:
        if char == "'":
            in_single_quote = not in_single_quote
        if char == ";" and not in_single_quote:
            buffer.append(char)
            text = "".join(buffer).strip()
            if text:
                statements.append(text)
            buffer = []
            continue
        buffer.append(char)

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def _parse_insert_like_statement(statement: str) -> list[dict[str, str]]:
    compact = re.sub(r"\s+", " ", statement).strip()
    pattern = re.compile(
        r"(?:insert(?:\s+or\s+replace)?|replace)\s+into\s+[^\(]+\(([^\)]*)\)\s+values\s*(.*)\s*;?$",
        re.IGNORECASE,
    )
    match = pattern.search(compact)
    if not match:
        return []

    columns_raw = match.group(1)
    values_raw = match.group(2)
    columns = [col.strip().strip("`\"[]") for col in columns_raw.split(",")]
    tuples = _parse_value_tuples(values_raw)

    rows: list[dict[str, str]] = []
    for value_items in tuples:
        if len(value_items) != len(columns):
            continue
        row = {columns[index].lower(): value_items[index] for index in range(len(columns))}
        rows.append(row)
    return rows


def _parse_value_tuples(values_raw: str) -> list[list[str]]:
    tuples: list[list[str]] = []
    current: list[str] = []
    token: list[str] = []
    in_quote = False
    depth = 0

    i = 0
    while i < len(values_raw):
        ch = values_raw[i]

        if ch == "'":
            if in_quote and i + 1 < len(values_raw) and values_raw[i + 1] == "'":
                token.append("'")
                i += 2
                continue
            in_quote = not in_quote
            i += 1
            continue

        if not in_quote and ch == "(":
            depth += 1
            if depth == 1:
                current = []
                token = []
                i += 1
                continue

        if not in_quote and ch == ")":
            depth -= 1
            if depth == 0:
                current.append("".join(token).strip())
                tuples.append(current)
                token = []
                i += 1
                continue

        if not in_quote and depth == 1 and ch == ",":
            current.append("".join(token).strip())
            token = []
            i += 1
            continue

        token.append(ch)
        i += 1

    return tuples


def _extract_modinfo_file_refs(modinfo_path: Path) -> list[str]:
    try:
        tree = ET.parse(modinfo_path)
    except ET.ParseError:
        return []

    refs: list[str] = []
    for update_text in tree.getroot().iter():
        if _element_local_name(update_text.tag).lower() != "updatetext":
            continue
        for child in update_text:
            if _element_local_name(child.tag).lower() != "file":
                continue
            value = (child.text or "").strip()
            if value:
                refs.append(value)
    return refs
