"""Central permission helpers for roles and access control."""

PROFILE_PERMISSION_FIELDS = {
    'can_edit_orders',
    'can_cancel_orders',
    'can_apply_manual_discounts',
    'can_apply_discount_codes',
    'can_edit_orders_with_password',
}

BRANCH_MANAGER_PERMISSIONS = {
    'can_access_pos',
    'can_create_orders',
    'can_edit_orders',
    'can_cancel_orders',
    'can_view_all_orders',
    'can_complete_orders',
    'can_apply_manual_discounts',
    'can_apply_discount_codes',
    'can_end_day',
    'can_view_reports',
    'can_view_detailed_reports',
    'can_view_delivery_reports',
    'can_manage_bill_adjustments',
    'can_manage_advance_adjustments',
    'can_print_receipts',
    'can_assign_delivery_orders',
}

CASHIER_PERMISSIONS = {
    'can_access_pos',
    'can_create_orders',
    'can_print_receipts',
}

ADMIN_PERMISSIONS = {
    'can_view_stock',
    'can_manage_stock',
    'can_manage_categories',
    'can_manage_products',
    'can_manage_users',
    'can_manage_roles',
    'can_manage_discounts',
    'can_manage_delivery_persons',
    'can_manage_business_settings',
    'can_manage_system_settings',
}


def get_base_role_name(user):
    """Return standard role name even for per-user custom roles."""
    try:
        if not hasattr(user, 'profile') or not user.profile or not user.profile.role:
            return None
        role_name = user.profile.role.name
        for base in ('Admin', 'Branch Manager', 'Cashier'):
            if role_name == base or role_name.startswith(f'{base}_'):
                return base
        return role_name
    except Exception:
        return None


def is_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return get_base_role_name(user) == 'Admin'


def is_branch_manager(user):
    if not user.is_authenticated:
        return False
    return get_base_role_name(user) == 'Branch Manager'


def is_cashier(user):
    if not user.is_authenticated:
        return False
    return get_base_role_name(user) == 'Cashier'


def can_access_management(user):
    return is_admin(user) or is_branch_manager(user)


def has_permission(user, permission_name):
    """Check role defaults, custom role flags, and profile overrides."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    try:
        profile = user.profile
        if not profile or not profile.role:
            return False

        if permission_name in PROFILE_PERMISSION_FIELDS and getattr(profile, permission_name, False):
            return True

        base_role = get_base_role_name(user)
        if base_role == 'Admin':
            return True
        if base_role == 'Branch Manager':
            if permission_name in BRANCH_MANAGER_PERMISSIONS:
                return True
            return profile.role.has_permission(permission_name)
        if base_role == 'Cashier':
            if permission_name in CASHIER_PERMISSIONS:
                return True
            return False

        return profile.role.has_permission(permission_name)
    except Exception:
        return False


def get_user_permissions(user):
    """Template-friendly subset used by POS order actions."""
    keys = [
        'can_edit_orders',
        'can_cancel_orders',
        'can_apply_manual_discounts',
        'can_apply_discount_codes',
        'can_edit_orders_with_password',
    ]
    return {key: has_permission(user, key) for key in keys}
