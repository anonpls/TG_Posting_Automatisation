from datetime import datetime, timedelta
import config

def tz_now():
    return datetime.utcnow() + timedelta(hours=config.TIMEZONE_OFFSET)
