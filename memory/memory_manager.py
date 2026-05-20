import json
from datetime import datetime
from threading import Lock
from pathlib import Path
import sys


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
MEMORY_PATH      = BASE_DIR / "memory" / "long_term.json"
_lock            = Lock()

# Per-value cap. Generous so detailed entries (thesis architecture, work areas,
# long preference descriptions) are NOT silently truncated.
MAX_VALUE_LENGTH = 5000

# Total memory size cap. Acts as a hard safety ceiling, not a routine trimmer.
# When raised this high, real profiles never hit it — only runaway growth would.
MEMORY_MAX_CHARS = 100_000

# When the cap IS exceeded, only trim from this category by default. Identity,
# family, relationships, preferences, etc. are never touched automatically.
TRIMMABLE_CATEGORIES = ("notes",)


def _empty_memory() -> dict:
    return {
        "identity":      {},
        "preferences":   {},
        "projects":      {},
        "relationships": {},
        "wishes":        {},
        "notes":         {},
    }


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return _empty_memory()
    with _lock:
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                # Preserve ANY extra top-level categories the user has added
                # (e.g. family, education, publications, technical_expertise,
                # strategic_perspective, character_traits, personal_life…).
                for key in base:
                    if key not in data:
                        data[key] = {}
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[Memory] ⚠️ Load error: {e}")
            return _empty_memory()


def _all_entries(memory: dict, only_categories: tuple | None = None) -> list[tuple]:
    """Return (category, key, entry) tuples, optionally filtered to a subset of categories."""
    entries = []
    for cat, items in memory.items():
        if only_categories is not None and cat not in only_categories:
            continue
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                entries.append((cat, key, entry))
    return entries


def _trim_to_limit(memory: dict) -> dict:
    """Only trim if memory exceeds the (very generous) ceiling, and only from
    explicitly trimmable categories. Never auto-deletes identity, family,
    preferences, projects, relationships, wishes, etc."""
    if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
        return memory

    print(f"[Memory] ⚠️ Size exceeds {MEMORY_MAX_CHARS} chars — trimming only from {TRIMMABLE_CATEGORIES}")
    entries = _all_entries(memory, only_categories=TRIMMABLE_CATEGORIES)
    entries.sort(key=lambda t: t[2].get("updated", "0000-00-00"))
    for cat, key, _ in entries:
        if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
            break
        del memory[cat][key]
        print(f"[Memory] 🗑️  Trimmed {cat}/{key} (oldest in trimmable category)")
    return memory


def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    memory = _trim_to_limit(memory)
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        MEMORY_PATH.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val


def _recursive_update(target: dict, updates: dict) -> bool:
    """Merge updates INTO target. Never deletes existing keys; only overwrites
    when the new value differs, and only adds keys that are present in updates.
    Existing keys not mentioned in updates are preserved."""
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, dict) and "value" not in value:
            # Nested category dict (e.g. {"identity": {"name": {...}}})
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            new_val  = _truncate_value(str(value["value"] if isinstance(value, dict) else value))
            entry    = {"value": new_val, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_val:
                target[key] = entry
                changed = True
    return changed


def update_memory(memory_update: dict) -> dict:
    """Merge new info into existing memory. Existing entries that aren't in
    `memory_update` are LEFT UNTOUCHED — this is purely additive/updating."""
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()
    memory = load_memory()
    if _recursive_update(memory, memory_update):
        save_memory(memory)
        print(f"[Memory] 💾 Updated: {list(memory_update.keys())}")
    return memory


def format_memory_for_prompt(memory: dict | None) -> str:
    if not memory:
        return ""

    lines = []

    identity  = memory.get("identity", {})
    id_fields = ["name", "full_name", "age", "birthday", "city", "location_city",
                 "country", "job", "language", "school", "nationality",
                 "assistant_name"]
    for field in id_fields:
        entry = identity.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.replace('_', ' ').title()}: {val}")
    for key, entry in identity.items():
        if key in id_fields:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")

    def _dump_section(cat_name: str, title: str, max_items: int = 20):
        section = memory.get(cat_name, {})
        if not section:
            return
        lines.append("")
        lines.append(f"{title}:")
        for key, entry in list(section.items())[:max_items]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    # Core categories — give them all room
    _dump_section("family",                "Family",                  max_items=10)
    _dump_section("education",             "Education",               max_items=10)
    _dump_section("preferences",           "Preferences",             max_items=20)
    _dump_section("projects",              "Active Projects / Work",  max_items=15)
    _dump_section("publications",          "Publications",            max_items=10)
    _dump_section("technical_expertise",   "Technical Expertise",     max_items=15)
    _dump_section("strategic_perspective", "Strategic Perspective",   max_items=10)
    _dump_section("character_traits",      "Character",               max_items=5)
    _dump_section("relationships",         "People in their life",    max_items=15)
    _dump_section("wishes",                "Goals / Wishes / Plans",  max_items=10)
    _dump_section("personal_life",         "Personal Life",           max_items=10)
    _dump_section("notes",                 "Other notes",             max_items=15)

    if not lines:
        return ""

    header = "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]\n"
    result = header + "\n".join(lines)

    # Prompt-side cap is separate from storage cap. Keep this if your LLM
    # context budget is tight; raise it if you want fuller context.
    MAX_PROMPT_CHARS = 6000
    if len(result) > MAX_PROMPT_CHARS:
        result = result[:MAX_PROMPT_CHARS - 3] + "…"

    return result + "\n"


def remember(key: str, value: str, category: str = "notes") -> str:
    # Accept any category the user wants — including the extended ones.
    update_memory({category: {key: {"value": value}}})
    return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    """Explicit removal only. The only way to actually delete a memory entry."""
    memory = load_memory()
    cat    = memory.get(category, {})
    if key in cat:
        del cat[key]
        memory[category] = cat
        save_memory(memory)
        return f"Forgotten: {category}/{key}"
    return f"Not found: {category}/{key}"


forget_memory = forget
