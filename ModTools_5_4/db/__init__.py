"""Database helpers for ModTools 5.4."""

from .paths import DEFAULT_GAME_DB, DEFAULT_TEXT_SOURCE_DB
from .text_database import (
    import_dlc_texts,
    import_folder_texts,
    import_modinfo_texts,
    import_text_files,
    query_text_by_tag,
    create_local_text_database_from_source,
)

__all__ = [
    "DEFAULT_GAME_DB",
    "DEFAULT_TEXT_SOURCE_DB",
    "import_dlc_texts",
    "import_folder_texts",
    "import_modinfo_texts",
    "import_text_files",
    "query_text_by_tag",
    "create_local_text_database_from_source",
]
