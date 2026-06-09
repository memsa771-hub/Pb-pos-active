from django.core.cache import cache
from .models import Setting, Order


def settings_processor(request):
    """Context processor to make settings available in all templates"""
    settings_dict = cache.get('ctx_core_settings')
    if settings_dict is None:
        settings_dict = {}
        core_settings = [
            'business_name',
            'currency_symbol',
            'currency_position',
            'tax_rate',
            'enable_tax',
            'theme_color',
        ]
        for key in core_settings:
            settings_dict[key] = Setting.get_value(key, default='')
        cache.set('ctx_core_settings', settings_dict, 300)

    currency_symbol = settings_dict.get('currency_symbol', '$')
    currency_position = settings_dict.get('currency_position', 'before')

    def format_currency(amount):
        if currency_position == 'before':
            return f"{currency_symbol}{amount}"
        return f"{amount}{currency_symbol}"

    settings_dict = dict(settings_dict)
    settings_dict['format_currency'] = format_currency

    return {'settings': settings_dict}


def pending_orders_processor(request):
    """Context processor to count pending orders for the current user"""
    user_pending_orders = 0

    if request.user.is_authenticated:
        is_admin = False
        try:
            is_admin = (
                request.user.is_superuser
                or (
                    hasattr(request.user, 'profile')
                    and request.user.profile
                    and request.user.profile.role
                    and request.user.profile.role.name == 'Admin'
                )
            )
        except Exception:
            is_admin = request.user.is_superuser

        if not is_admin:
            cache_key = f'ctx_pending_orders_{request.user.id}'
            user_pending_orders = cache.get(cache_key)
            if user_pending_orders is None:
                user_pending_orders = Order.objects.filter(
                    user=request.user,
                    order_status='Pending'
                ).count()
                cache.set(cache_key, user_pending_orders, 20)

    return {'user_pending_orders': user_pending_orders}


def user_permissions_processor(request):
    """Context processor to add user permissions to template context"""
    from .permissions import get_user_permissions, has_permission, get_base_role_name

    if request.user.is_authenticated:
        if request.user.is_superuser:
            permissions = {
                'can_edit_orders': True,
                'can_cancel_orders': True,
                'can_apply_manual_discounts': True,
                'can_apply_discount_codes': True,
                'can_edit_orders_with_password': True,
            }

            def check_perm(permission):
                return True

            user_role = 'Admin'
        else:
            cache_key = f'ctx_permissions_{request.user.id}'
            cached = cache.get(cache_key)
            if cached is None:
                permissions = get_user_permissions(request.user)
                user_role = get_base_role_name(request.user)
                cached = (permissions, user_role)
                cache.set(cache_key, cached, 120)
            else:
                permissions, user_role = cached

            def check_perm(permission):
                return has_permission(request.user, permission)

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
