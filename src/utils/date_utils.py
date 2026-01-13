from datetime import datetime, timedelta


def since_last_week() -> str:
    # YYYYMMDDTHHMM
    return (datetime.now() - timedelta(days=7)).strftime("%Y%m%dT%H%M")
