from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
import logging

logger = logging.getLogger('posapp')

def parse_date(date_str, default=None):
    """
    Parse date string with consistent format handling
    
    Args:
        date_str: The date string to parse
        default: The default value to return if parsing fails
        
    Returns:
        A timezone-aware datetime object or the default value
    """
    if not date_str:
        return default
    
    formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return timezone.make_aware(date_obj) if timezone.is_naive(date_obj) else date_obj
        except ValueError:
            continue
    
    # If all parsing attempts fail, return default
    logger.warning(f"Failed to parse date string: {date_str}, using default")
    return default

def get_today_range():
    """
    Get the start and end of today in the current timezone
    
    Returns:
        A tuple of (start_of_day, end_of_day) as timezone-aware datetime objects
    """
    today = timezone.localtime(timezone.now()).date()
    start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    return start_of_day, end_of_day

def decimal_to_str(value, decimal_places=2):
    """
    Convert a Decimal to a string with proper rounding
    
    Args:
        value: The Decimal value to convert
        decimal_places: Number of decimal places to round to
        
    Returns:
        A string representation of the Decimal value
    """
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except (ValueError, TypeError):
            logger.error(f"Failed to convert {value} to Decimal")
            return "0.00"
    
    # Round to specified decimal places
    return str(value.quantize(Decimal('0.' + '0' * decimal_places), rounding=ROUND_HALF_UP))

def ensure_decimal(value, default="0.00"):
    """
    Ensure a value is a Decimal
    
    Args:
        value: The value to convert
        default: The default value to use if conversion fails
        
    Returns:
        A Decimal object
    """
    if isinstance(value, Decimal):
        return value
    
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        logger.error(f"Failed to convert {value} to Decimal, using default {default}")
        return Decimal(default)

def ensure_defaults(order_data):
    """
    Ensure all required fields have proper default values
    
    Args:
        order_data: Dictionary containing order data
        
    Returns:
        Dictionary with default values for missing fields
    """
    defaults = {
        'discount_amount': Decimal('0.00'),
        'tax_amount': Decimal('0.00'),
        'service_charge_percent': Decimal('0.00'),
        'service_charge_amount': Decimal('0.00'),
        'delivery_charges': Decimal('0.00'),
        'payment_status': 'Pending',
        'order_status': 'Pending',
    }
    
    # Create a new dictionary to avoid modifying the original
    result = order_data.copy()
    
    for key, default_value in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default_value
    
    return result 

def has_permission(user, permission):
    from .permissions import has_permission as check_permission
    return check_permission(user, permission)


def get_user_permissions(user):
    from .permissions import get_user_permissions as get_permissions
    return get_permissions(user)

def require_permission(permission):
    """
    Decorator to require specific permission for view access
    Usage: @require_permission('can_create_orders')
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not has_permission(request.user, permission):
                from django.contrib import messages
                from django.shortcuts import redirect
                
                messages.error(request, f'You do not have permission to access this feature.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def check_multiple_permissions(user, permissions, require_all=True):
    """
    Check multiple permissions for a user
    Args:
        user: Django User object
        permissions: List of permission names
        require_all: If True, user must have ALL permissions. If False, user needs ANY permission
    Returns:
        Boolean indicating if user meets the permission requirements
    """
    if user.is_superuser:
        return True
        
    user_permissions = [has_permission(user, perm) for perm in permissions]
    
    if require_all:
        return all(user_permissions)
    else:
        return any(user_permissions) 