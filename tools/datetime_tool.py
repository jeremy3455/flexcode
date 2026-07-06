from datetime import datetime


def get_current_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    return datetime.now().strftime(format)
