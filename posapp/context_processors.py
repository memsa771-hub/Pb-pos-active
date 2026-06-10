from .models import Setting, Order

def settings_processor(request):
    """Context processor to make settings available in all templates"""
    settings_dict = {}
    
    # Get core settings used in most pages
    core_settings = [
        'business_name',
        'currency_symbol',
        'currency_position',
        'tax_rate',
        'enable_tax',
        'theme_color',
    ]
    
    # Get settings from database
    for key in core_settings:
        settings_dict[key] = Setting.get_value(key, default='')
    
    # Process currency symbol and position for easier use in templates
    currency_symbol = Setting.get_currency_symbol()
    settings_dict['currency_symbol'] = currency_symbol
    currency_position = settings_dict.get('currency_position', 'before')
    
    # Add helper function for formatting currency
    def format_currency(amount):
        if currency_position == 'before':
            return f"{currency_symbol}{amount}"
        else:
            return f"{amount}{currency_symbol}"
    
    settings_dict['format_currency'] = format_currency
    
    return {
        'settings': settings_dict,
        'currency_symbol': currency_symbol,
    }

def pending_orders_processor(request):
    """Context processor to count pending orders for the current user"""
    user_pending_orders = 0
    
    if request.user.is_authenticated:
        # Skip for admin users
        is_admin = False
        try:
            is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role and request.user.profile.role.name == 'Admin')
        except:
            is_admin = request.user.is_superuser
        
        if not is_admin:
            user_pending_orders = Order.objects.filter(
                user=request.user,
                order_status='Pending'
            ).count()
    
    return {'user_pending_orders': user_pending_orders}

def user_permissions_processor(request):
    """Context processor to add user permissions to template context"""
    from .permissions import get_user_permissions, has_permission, get_base_role_name
    
    if request.user.is_authenticated:
        # Superusers automatically have all permissions
        if request.user.is_superuser:
            permissions = {
                'can_edit_orders': True,
                'can_cancel_orders': True,
                'can_apply_manual_discounts': True,
                'can_apply_discount_codes': True,
                'can_edit_orders_with_password': True,
            }
            
            def check_perm(permission):
                return True  # Superusers have all permissions
            
            user_role = 'Admin'
        else:
            permissions = get_user_permissions(request.user)
            
            # Add helper function to check permissions in templates
            def check_perm(permission):
                return has_permission(request.user, permission)
            
            user_role = get_base_role_name(request.user)
        
        return {
            'user_permissions': permissions,
            'has_perm': check_perm,
            'user_role': user_role
        }
    
    return {
        'user_permissions': {
            'can_edit_orders': False,
            'can_cancel_orders': False,
            'can_apply_manual_discounts': False,
            'can_apply_discount_codes': False,
            'can_edit_orders_with_password': False,
        },
        'has_perm': lambda x: False,
        'user_role': None
    } 