from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns current UTC datetime as a naive datetime compatible with standard SQL DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
