"""Conservative SQL inspection, never executing mod data against a game database."""
from __future__ import annotations

import re
from contextlib import closing
import sqlite3
import xml.etree.ElementTree as ET

# Minimum offline keys used by the generated core tables. Custom CREATE TABLE
# declarations supply schema information, including composite keys.
CORE_KEYS = {
    "types": ("Type",), "units": ("UnitType",), "buildings": ("BuildingType",),
    "districts": ("DistrictType",), "civilizations": ("CivilizationType",),
    "leaders": ("LeaderType",), "traits": ("TraitType",),
    "modifiers": ("ModifierId",), "dynamicmodifiers": ("ModifierType",),
    "requirements": ("RequirementId",), "requirementsets": ("RequirementSetId",),
    "modifierarguments": ("ModifierId", "Name"),
    "requirementarguments": ("RequirementId", "Name"),
    "requirementsetrequirements": ("RequirementSetId", "RequirementId"),
    "buildingmodifiers": ("BuildingType", "ModifierId"),
    "unitabilitymodifiers": ("UnitAbilityType", "ModifierId"),
    "traitmodifiers": ("TraitType", "ModifierId"),
    "districtyieldchanges": ("DistrictType", "YieldType"),
    "buildingyieldchanges": ("BuildingType", "YieldType"),
}

_LEX = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9]*|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[^\s]", re.M)


def statements(text: str) -> list[list[str]]:
    out, current = [], []
    for token in _LEX.findall(text):
        if token.startswith(("--", "/*")):
            continue
        if token == ";":
            if current and not sqlite3.complete_statement(" ".join(current) + ";"):
                current.append(token)  # Keep CREATE TRIGGER ... BEGIN ... END together.
                continue
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    if current:
        out.append(current)
    return out


def identifier(token: str) -> str:
    return token.strip('"`[]').replace('""', '"')


def literal(tokens: list[str]):
    if len(tokens) == 1 and tokens[0].startswith("'"):
        return tokens[0][1:-1].replace("''", "'")
    raw = "".join(tokens)
    if re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", raw):
        return int(raw) if re.fullmatch(r"[-+]?\d+", raw) else float(raw)
    return None  # NULL, expressions and SELECT cannot provide a proven static key.


def insert_rows(text: str) -> tuple[list[tuple[str, list[str], list]], set[str]]:
    rows, unsupported = [], set()
    for stmt in statements(text):
        upper = [token.upper() for token in stmt]
        if upper and (upper[0] == "WITH" or (upper[0] == "CREATE" and "TRIGGER" in upper[:4])):
            unsupported.add("CTE/trigger")
            continue
        if not upper or upper[0] != "INSERT" or "INTO" not in upper[:5]:
            continue
        start = upper.index("INTO") + 1
        if start >= len(stmt):
            continue
        table = identifier(stmt[start])
        i = start + 1
        columns = []
        if i < len(stmt) and stmt[i] == "(":
            i += 1
            while i < len(stmt) and stmt[i] != ")":
                if stmt[i] != ",":
                    columns.append(identifier(stmt[i]))
                i += 1
            i += 1
        if i >= len(stmt) or upper[i] != "VALUES":
            unsupported.add(table)
            continue
        i += 1
        while i < len(stmt) and stmt[i] == "(":
            i += 1
            depth, values, value = 0, [], []
            while i < len(stmt):
                token = stmt[i]
                if token == ")" and depth == 0:
                    values.append(literal(value))
                    break
                if token == "," and depth == 0:
                    values.append(literal(value))
                    value = []
                else:
                    value.append(token)
                    depth += (token == "(") - (token == ")")
                i += 1
            if i >= len(stmt):
                unsupported.add(table)
                break
            rows.append((table, columns, values))
            i += 1
            if i < len(stmt) and stmt[i] == ",":
                i += 1
            else:
                break
    return rows, unsupported


def xml_rows(text: str) -> list[tuple[str, list[str], list]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    rows = []
    for table in root:
        for row in table.findall("Row"):
            values = dict(row.attrib)
            values.update({child.tag: child.text for child in row})
            rows.append((table.tag, list(values), list(values.values())))
    return rows


def updated_tables(text: str) -> set[str]:
    tables = set()
    for stmt in statements(text):
        upper = [token.upper() for token in stmt]
        if len(stmt) > 1 and upper[0] == "UPDATE":
            index = 3 if upper[1] == "OR" else 1
            if index < len(stmt):
                tables.add(identifier(stmt[index]))
        if len(stmt) > 2 and upper[:2] == ["DELETE", "FROM"]:
            tables.add(identifier(stmt[2]))
    return tables


def schema_keys(sql_files: dict[str, str]) -> tuple[dict, dict]:
    keys, columns = dict(CORE_KEYS), {}
    # Only CREATE TABLE statements are applied to an isolated memory database.
    with closing(sqlite3.connect(":memory:")) as db:
        for text in sql_files.values():
            for stmt in statements(text):
                if [t.upper() for t in stmt[:2]] != ["CREATE", "TABLE"]:
                    continue
                # CREATE TABLE AS SELECT would execute data expressions. Schema
                # inspection only accepts a declared column/constraint list.
                if any(t.upper() == "SELECT" for t in stmt):
                    continue
                try:
                    db.execute(" ".join(stmt))
                except sqlite3.Error:
                    continue
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            info = db.execute('PRAGMA table_info("' + table.replace('"', '""') + '")').fetchall()
            keys[table.casefold()] = tuple(row[1] for row in sorted(info, key=lambda r: r[5]) if row[5])
            columns[table.casefold()] = [row[1] for row in info]
    return keys, columns


def row_key(table: str, cols: list[str], values: list, keys: dict, column_order: dict):
    pk = keys.get(table.casefold())
    if not pk:
        return None
    columns = cols or column_order.get(table.casefold(), [])
    mapping = dict(zip((c.casefold() for c in columns), values))
    values = tuple(mapping.get(name.casefold()) for name in pk)
    if any(v is None for v in values):
        return None
    return table.casefold(), values
