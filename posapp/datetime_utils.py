from datetime import datetime
from urllib.parse import unquote_plus

from django.utils import timezone


def format_local_datetime_param(dt):
    """Format an aware datetime for URL/query params in the business timezone."""
    if dt is None:
        return ''
    return timezone.localtime(dt).strftime('%Y-%m-%d %H:%M:%S')


def parse_local_datetime_param(value, *, end_of_day_if_date_only=False):
    """
    Parse a datetime string from query params as local business time (Asia/Karachi).
    Accepts 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD', and '+' as space separators.
    """
    if not value:
        return None

    cleaned = unquote_plus(str(value).strip())
    parsed = None
    has_time = ':' in cleaned

    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        raise ValueError(f'Invalid datetime: {value}')

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    if end_of_day_if_date_only and not has_time:
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)

    return parsed
