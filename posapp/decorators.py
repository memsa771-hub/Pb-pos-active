from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .permissions import (
    is_admin,
    is_branch_manager,
    has_permission,
    get_user_permissions,
)

__all__ = [
    'is_admin',
    'is_branch_manager',
    'admin_required',
    'management_required',
    'permission_required',
    'has_permission',
    'get_user_permissions',
    'can_edit_orders_required',
    'can_cancel_orders_required',
    'can_apply_manual_discounts_required',
    'can_apply_discount_codes_required',
    'can_view_stock_required',
    'can_manage_stock_required',
    'can_manage_categories_required',
]


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "You don't have permission to access this page. Admin access required.")
            return redirect('pos')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def management_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not (is_admin(request.user) or is_branch_manager(request.user)):
            messages.error(request, "You don't have permission to access this page. Management access required.")
            return redirect('pos')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def permission_required(permission_name, redirect_url='pos'):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if has_permission(request.user, permission_name):
                return view_func(request, *args, **kwargs)

            messages.error(request, "Access Restricted: You don't have permission to perform this action.")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': "Access Restricted: You don't have permission to perform this action.",
                }, status=403)

            return redirect(redirect_url)
        return _wrapped_view
    return decorator


def can_edit_orders_required(view_func):
    return permission_required('can_edit_orders')(view_func)


def can_cancel_orders_required(view_func):
    return permission_required('can_cancel_orders')(view_func)


def can_apply_manual_discounts_required(view_func):
    return permission_required('can_apply_manual_discounts')(view_func)


def can_apply_discount_codes_required(view_func):
    return permission_required('can_apply_discount_codes')(view_func)


def can_view_stock_required(view_func):
    return permission_required('can_view_stock', redirect_url='dashboard')(view_func)


def can_manage_stock_required(view_func):
    return permission_required('can_manage_stock', redirect_url='dashboard')(view_func)


def can_manage_categories_required(view_func):
    return permission_required('can_manage_categories', redirect_url='dashboard')(view_func)
