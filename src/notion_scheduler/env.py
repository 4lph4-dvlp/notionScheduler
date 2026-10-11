"""Environment and configuration resolution for Notion Scheduler."""

from pathlib import Path
import os


def default_env_paths() -> tuple[Path, ...]:
    """Return standard candidate paths for Notion Scheduler environment files in order of discovery."""
    candidates: list[Path] = []
    custom = os.getenv("NOTION_SCHEDULER_ENV")
    if custom:
        candidates.append(Path(custom))
    home = Path.home()
    candidates.extend([
        home / ".notionScheduler" / ".env",
        home / ".notionScheduler.env",
        home / ".config" / "notionScheduler" / ".env",
        home / ".config" / "notion-scheduler" / ".env",
        Path.cwd() / ".env",
    ])
    return tuple(candidates)


def load_default_env(override: bool = False) -> Path | None:
    """Find and load the first existing default environment file if token is not already set."""
    from dotenv import load_dotenv

    for path in default_env_paths():
        if path.is_file():
            load_dotenv(path, override=override)
            if os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY"):
                return path
    return None
