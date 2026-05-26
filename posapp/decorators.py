from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

def is_admin(user):
    """Check if user is an admin"""
    try:
        return user.is_superuser or (hasattr(user, 'profile') and user.profile and user.profile.role and user.profile.role.name == 'Admin')
    except:
        return user.is_superuser

def is_branch_manager(user):
    """Check if user is a branch manager"""
    try:
        return hasattr(user, 'profile') and user.profile and user.profile.role and user.profile.role.name == 'Branch Manager'
    except:
        return False

def admin_required(view_func):
    """
    Decorator for views that checks if the user is an admin.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "You don't have permission to access this page. Admin access required.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def management_required(view_func):
    """
    Decorator for views that checks if the user is an admin or branch manager.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (is_admin(request.user) or is_branch_manager(request.user)):
            messages.error(request, "You don't have permission to access this page. Management access required.")
            return redirect('pos')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def permission_required(permission_name, redirect_url='dashboard'):
    """
    Decorator to check if user has specific permission
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Superusers have all permissions
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # Check if user has the required permission
            try:
                if hasattr(request.user, 'profile') and request.user.profile:
                    if getattr(request.user.profile, permission_name, False):
                        return view_func(request, *args, **kwargs)
            except:
                pass
            
            # User doesn't have permission
            messages.error(request, f"Access Restricted: You don't have permission to perform this action.")
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Access Restricted: You don\'t have permission to perform this action.'
                }, status=403)
            
            return redirect(redirect_url)
        return _wrapped_view
    return decorator

def can_edit_orders_required(view_func):
    """Decorator to check if user can edit orders"""
    return permission_required('can_edit_orders')(view_func)

def can_cancel_orders_required(view_func):
    """Decorator to check if user can cancel orders"""
    return permission_required('can_cancel_orders')(view_func)

def can_apply_manual_discounts_required(view_func):
    """Decorator to check if user can apply manual discounts"""
    return permission_required('can_apply_manual_discounts')(view_func)

def can_apply_discount_codes_required(view_func):
    """Decorator to check if user can apply discount codes"""
    return permission_required('can_apply_discount_codes')(view_func)

def has_permission(user, permission_name):
    """
    Helper function to check if user has specific permission
    Returns True if user has permission, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    # Check user profile permission
    try:
        if hasattr(user, 'profile') and user.profile:
            return getattr(user.profile, permission_name, False)
    except:
        pass
    
    return False

def get_user_permissions(user):
    """
    Get all permissions for a user
    Returns dictionary with permission status
    """
    if not user.is_authenticated:
        return {
            'can_edit_orders': False,
            'can_cancel_orders': False,
            'can_apply_manual_discounts': False,
            'can_apply_discount_codes': False,
            'can_edit_orders_with_password': False,
        }
    
    # Superusers have all permissions
    if user.is_superuser:
        return {
            'can_edit_orders': True,
            'can_cancel_orders': True,
            'can_apply_manual_discounts': True,
            'can_apply_discount_codes': True,
            'can_edit_orders_with_password': True,
        }
    
    # Get permissions from user profile
    try:
        if hasattr(user, 'profile') and user.profile:
            profile = user.profile
            return {
                'can_edit_orders': getattr(profile, 'can_edit_orders', False),
                'can_cancel_orders': getattr(profile, 'can_cancel_orders', False),
                'can_apply_manual_discounts': getattr(profile, 'can_apply_manual_discounts', False),
                'can_apply_discount_codes': getattr(profile, 'can_apply_discount_codes', False),
                'can_edit_orders_with_password': getattr(profile, 'can_edit_orders_with_password', False),
            }
    except:
        pass
    
    return {
        'can_edit_orders': False,
        'can_cancel_orders': False,
        'can_apply_manual_discounts': False,
        'can_apply_discount_codes': False,
        'can_edit_orders_with_password': False,
    } 

# --- INVENTORY SPECIFIC DECORATORS ---

def can_view_stock_required(view_func):
    """Decorator to check if user can view stock"""
    return permission_required('can_view_stock')(view_func)

def can_manage_stock_required(view_func):
    """Decorator to check if user can manage stock (Add/Edit/Delete)"""
    return permission_required('can_manage_stock')(view_func)

def can_manage_categories_required(view_func):
    """Decorator to check if user can manage categories"""
    return permission_required('can_manage_categories')(view_func)