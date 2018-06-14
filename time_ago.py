from datetime import datetime
import time
import dateparser


def time_ago(timestamp=False):
    if type(timestamp) is str:
        dt = dateparser.parse(timestamp)
        timestamp = int(time.mktime(dt.timetuple()))
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc

    Modified from: http://stackoverflow.com/a/1551394/141084
    """
    now = datetime.utcnow()
    if type(timestamp) is int:
        diff = now - datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, datetime):
        diff = now - timestamp
    elif not timestamp:
        diff = now - now
    else:
        raise ValueError('invalid date %s of type %s' % (timestamp, type(timestamp)))
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(round(second_diff, 2)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(round((second_diff / 60), 2)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(round((second_diff / 3600), 2)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(round(day_diff, 2)) + " days ago"
    if day_diff < 31:
        return str(round((day_diff/7), 2)) + " weeks ago"
    if day_diff < 365:
        return str(round((day_diff/30), 2)) + " months ago"
    return str(round((day_diff/365), 2)) + " years ago"
