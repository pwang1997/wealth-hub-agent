import json


def cache_key(provider: str, tool_name: str, args: dict) -> str:
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return f"{provider}:{tool_name}:{normalized}"


def is_rate_limited(payload: dict) -> bool:
    note = payload.get("Note", "")
    return "frequency" in note.lower() or "rate" in note.lower()


class CacheConfig:
    LIST_COLLECTIONS_CACHE_TTL_SECONDS = 60
    RETRIEVE_REPORT_CACHE_TTL_SECONDS = 60 * 5
