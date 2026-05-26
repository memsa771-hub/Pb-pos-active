from django import template
from decimal import Decimal, InvalidOperation
from django.utils.dateformat import format
import pytz

register = template.Library()

PKT = pytz.timezone('Asia/Karachi')

def _to_pkt(value):
    """Convert any datetime to Asia/Karachi (PKT, UTC+5) regardless of server timezone."""
    if value is None:
        return None
    if hasattr(value, 'tzinfo') and value.tzinfo is not None:
        return value.astimezone(PKT)
    # Naive datetime — assume UTC
    return pytz.utc.localize(value).astimezone(PKT)

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return '' 

@register.filter
def dictsumattr(items, attr):
    """Sums up a specific attribute from a list of dictionaries"""
    try:
        total = sum(item[attr] for item in items)
        return total
    except (KeyError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply two values"""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, InvalidOperation):
        return 0

@register.filter
def pkt_time(value):
    """Format time in Pakistani Standard Time with 12-hour format"""
    if not value:
        return ''
    try:
        return format(_to_pkt(value), 'g:i A')
    except Exception:
        return str(value)

@register.filter
def pkt_date(value):
    """Format date in Pakistani Standard Time"""
    if not value:
        return ''
    try:
        return format(_to_pkt(value), 'd/m/Y')
    except Exception:
        return str(value)

@register.filter
def pkt_datetime(value):
    """Format datetime in Pakistani Standard Time with 12-hour format"""
    if not value:
        return ''
    try:
        return format(_to_pkt(value), 'd/m/Y g:i A')
    except Exception:
        return str(value)

@register.filter
def pkt_datetime_short(value):
    """Format datetime in Pakistani Standard Time with short format"""
    if not value:
        return ''
    try:
        return format(_to_pkt(value), 'd/m g:i A')
    except Exception:
        return str(value)