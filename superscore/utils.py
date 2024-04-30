from datetime import datetime, timezone
from pathlib import Path

SUPERSCORE_SOURCE_PATH = Path(__file__).parent


def utcnow():
    return datetime.now(timezone.utc)
