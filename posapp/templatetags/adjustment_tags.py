from django import template
from posapp.models import EndDay

register = template.Library()

@register.filter
def can_delete_adjustment(adjustment):
    """
    Check if an adjustment can be deleted.
    Returns False if the adjustment was created before the last end day operation.
    """
    last_end_day = EndDay.get_last_end_day()
    if last_end_day and adjustment.created_at < last_end_day.end_date:
        return False
    return True 