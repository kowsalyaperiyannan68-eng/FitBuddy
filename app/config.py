"""Central configuration read from environment variables (.env)."""

import os


def _clean(value: str | None) -> str:
    return (value or "").strip()


GEMINI_API_KEY = _clean(os.environ.get("GEMINI_API_KEY"))
DATABASE_URL = _clean(os.environ.get("DATABASE_URL")) or "sqlite:///./fitbuddy.db"
WORKOUT_MODEL = _clean(os.environ.get("WORKOUT_MODEL")) or "gemini-1.5-flash"
NUTRITION_MODEL = _clean(os.environ.get("NUTRITION_MODEL")) or "gemini-1.5-flash"
DEMO_MODE = _clean(os.environ.get("DEMO_MODE")).lower() in {"1", "true", "yes", "on"}
ADMIN_ENABLED = _clean(os.environ.get("ADMIN_ENABLED")).lower() in {"1", "true", "yes", "on"}


def ai_available() -> bool:
    """True only when a real-looking Gemini key is configured and demo mode is off.

    The shipped ``.env`` contains a placeholder key, so this returns False by
    default and the app generates plans locally (offline demo mode).
    """
    if DEMO_MODE:
        return False
    key = GEMINI_API_KEY
    if not key or key.startswith("YOUR_") or "YOUR_GEMINI_API_KEY" in key:
        return False
    return True
