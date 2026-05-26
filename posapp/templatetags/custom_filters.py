from django import template
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.utils.dateformat import format

register = template.Library()

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
        # Convert to PKT timezone
        pkt_time = timezone.localtime(value)
        # Format as 12-hour with AM/PM
        return format(pkt_time, 'g:i A')
    except:
        return str(value)

@register.filter
def pkt_date(value):
    """Format date in Pakistani Standard Time"""
    if not value:
        return ''
    try:
        # Convert to PKT timezone
        pkt_time = timezone.localtime(value)
        # Format as d/m/Y
        return format(pkt_time, 'd/m/Y')
    except:
        return str(value)

@register.filter
def pkt_datetime(value):
    """Format datetime in Pakistani Standard Time with 12-hour format"""
    if not value:
        return ''
    try:
        # Convert to PKT timezone
        pkt_time = timezone.localtime(value)
        # Format as d/m/Y g:i A
        return format(pkt_time, 'd/m/Y g:i A')
    except:
        return str(value)

@register.filter
def pkt_datetime_short(value):
    """Format datetime in Pakistani Standard Time with short format"""
    if not value:
        return ''
    try:
        # Convert to PKT timezone
        pkt_time = timezone.localtime(value)
        # Format as d/m g:i A (without year)
        return format(pkt_time, 'd/m g:i A')
    except:
        return str(value)