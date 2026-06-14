from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.db import transaction
import django.db.models.deletion

from ..models import UserProfile, UserRole, UserSession
from ..permissions import is_admin

ASSIGNABLE_ROLES = ('Branch Manager', 'Cashier')


def _assignable_roles_queryset():
    return UserRole.objects.filter(name__in=ASSIGNABLE_ROLES)


def _resolve_standard_role(role):
    """Map legacy per-user roles (e.g. Cashier_csh1) back to Branch Manager or Cashier."""
    if not role:
        return None
    if role.name in ASSIGNABLE_ROLES:
        return role
    for base in ASSIGNABLE_ROLES:
        if role.name == base or role.name.startswith(f'{base}_'):
            return UserRole.objects.filter(name=base).first()
    return None
from ..session_manager import get_active_users, force_logout_user

# Custom Forms
class UserForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.id if self.instance else None
        
        # Check if email exists for another user
        if email and User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("This email is already in use. Please use a different email.")
        
        return email

class ProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict role choices to only Branch Manager and Cashier
        self.fields['role'].queryset = _assignable_roles_queryset()
        
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'role']

class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ModelChoiceField(
        queryset=_assignable_roles_queryset(),
        required=True,
        help_text="Select Branch Manager or Cashier"
    )
    phone = forms.CharField(max_length=20, required=False)
    
    # Only 5 Permission Fields
    can_edit_orders = forms.BooleanField(required=False, label="Edit Orders", help_text="Allow editing existing orders")
    can_cancel_orders = forms.BooleanField(required=False, label="Cancel Orders", help_text="Allow cancelling orders")
    can_apply_manual_discounts = forms.BooleanField(required=False, label="Apply Manual Discounts", help_text="Allow applying manual discounts")
    can_apply_discount_codes = forms.BooleanField(required=False, label="Apply Discount Codes", help_text="Allow applying discount codes")
    can_edit_orders_with_password = forms.BooleanField(required=False, label="Edit Orders with Password", help_text="Allow editing orders with admin password verification")
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
    
    def __init__(self, *args, **kwargs):
        # Extract user instance to get profile data
        user_instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # Add CSS classes for better styling
        for field_name, field in self.fields.items():
            if field_name.startswith('can_'):
                field.widget.attrs.update({'class': 'form-check-input permission-checkbox'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Pre-populate permission fields from user profile if editing
        if user_instance and hasattr(user_instance, 'profile'):
            profile = user_instance.profile
            
            # Set role and phone (map legacy Cashier_username roles to standard role)
            if profile.role:
                standard_role = _resolve_standard_role(profile.role)
                if standard_role:
                    self.fields['role'].initial = standard_role
            if profile.phone:
                self.fields['phone'].initial = profile.phone
            
            # Set all permission fields from profile
            permission_fields = [field for field in self.fields.keys() if field.startswith('can_')]
            for field_name in permission_fields:
                if hasattr(profile, field_name):
                    self.fields[field_name].initial = getattr(profile, field_name)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.id if self.instance else None
        
        # Check if email exists for another user
        if email and User.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("This email is already in use. Please use a different email.")
        
        return email

class UserCreationWithRoleForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    role = forms.ModelChoiceField(
        queryset=_assignable_roles_queryset(),
        required=True,
        help_text="Select Branch Manager or Cashier"
    )
    phone = forms.CharField(max_length=20, required=False)
    
    # Only 5 Permission Fields
    can_edit_orders = forms.BooleanField(required=False, label="Edit Orders", help_text="Allow editing existing orders")
    can_cancel_orders = forms.BooleanField(required=False, label="Cancel Orders", help_text="Allow cancelling orders")
    can_apply_manual_discounts = forms.BooleanField(required=False, label="Apply Manual Discounts", help_text="Allow applying manual discounts")
    can_apply_discount_codes = forms.BooleanField(required=False, label="Apply Discount Codes", help_text="Allow applying discount codes")
    can_edit_orders_with_password = forms.BooleanField(required=False, label="Edit Orders with Password", help_text="Allow editing orders with admin password verification")
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['role'].queryset = _assignable_roles_queryset()

        # Add CSS classes for better styling
        for field_name, field in self.fields.items():
            if field_name.startswith('can_'):
                field.widget.attrs.update({'class': 'form-check-input permission-checkbox'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if email exists for any user
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use. Please use a different email.")
        
        return email

@login_required
def user_list(request):
    """Display list of all users"""
    # Only allow admin users to view user list
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to view user list.")
        return redirect('dashboard')
    
    # Get search parameter
    search_query = request.GET.get('search', '')
    
    # Filter users based on search
    users = User.objects.select_related('profile__role').all().order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 10)  # Show 10 users per page
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'search_query': search_query,
    }
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'posapp/users/user_list.html', context)
    
    return render(request, 'posapp/users/user_list.html', context)

@login_required
def user_detail(request, user_id):
    """Display details of a specific user"""
    # Only allow admin users to view user details
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to view user details.")
        return redirect('dashboard')
    
    user = get_object_or_404(User.objects.select_related('profile__role'), id=user_id)
    
    # Get user's order statistics
    from ..models import Order, EndDay
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import datetime, timedelta, time
    
    # Get today's date range based on manual end day system
    last_end_day = EndDay.get_last_end_day()
    if last_end_day:
        today_start = last_end_day.end_date
    else:
        # If no end day exists, use start of today
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
    
    today_end = timezone.now()
    
    # Get total orders (all time)
    total_orders = Order.objects.filter(user=user).count()
    total_completed_orders = Order.objects.filter(user=user, order_status='Completed').count()
    total_pending_orders = Order.objects.filter(user=user, order_status='Pending').count()
    
    # Get today's orders (since last end day)
    daily_orders = Order.objects.filter(user=user, created_at__gte=today_start, created_at__lte=today_end).count()
    daily_completed_orders = Order.objects.filter(
        user=user, 
        created_at__gte=today_start,
        created_at__lte=today_end,
        order_status='Completed'
    ).count()
    
    # Get revenue statistics
    total_revenue = Order.objects.filter(
        user=user,
        order_status='Completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    daily_revenue = Order.objects.filter(
        user=user,
        created_at__gte=today_start,
        created_at__lte=today_end,
        order_status='Completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Get today's orders only (since last end day) - not all orders
    recent_orders = Order.objects.filter(
        user=user,
        created_at__gte=today_start,
        created_at__lte=today_end
    ).order_by('-created_at')
    
    # Get monthly revenue - last 6 months
    today = timezone.now().date()
    six_months_ago = today - timedelta(days=180)
    monthly_revenue = []
    
    for i in range(6):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        if i == 0:
            month_end = today
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        
        month_start_aware = timezone.make_aware(datetime.combine(month_start, time.min))
        month_end_aware = timezone.make_aware(datetime.combine(month_end, time.max))
        
        month_revenue = Order.objects.filter(
            user=user,
            created_at__range=(month_start_aware, month_end_aware),
            order_status='Completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': month_revenue
        })
    
    # Reverse the list to show oldest to newest
    monthly_revenue.reverse()
    
    # Calculate percentages for the progress bars
    if total_orders > 0:
        pending_percentage = (total_pending_orders / total_orders) * 100
        completed_percentage = (total_completed_orders / total_orders) * 100
    else:
        pending_percentage = 0
        completed_percentage = 0
        
    if daily_orders > 0:
        daily_completed_percentage = (daily_completed_orders / daily_orders) * 100
    else:
        daily_completed_percentage = 0
    
    # Format dates for URL parameters - preserve time part as well
    start_date_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = today_end.strftime('%Y-%m-%d %H:%M:%S')
    
    context = {
        'user_obj': user,
        'total_orders': total_orders,
        'total_completed_orders': total_completed_orders,
        'total_pending_orders': total_pending_orders,
        'daily_orders': daily_orders,
        'daily_completed_orders': daily_completed_orders,
        'total_revenue': total_revenue,
        'daily_revenue': daily_revenue,
        'recent_orders': recent_orders,
        'monthly_revenue': monthly_revenue,
        'pending_percentage': pending_percentage,
        'completed_percentage': completed_percentage,
        'daily_completed_percentage': daily_completed_percentage,
        'last_end_day': last_end_day,
        'today_start': today_start,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
    }
    
    return render(request, 'posapp/users/user_detail.html', context)

@login_required
def user_create(request):
    """Create a new user"""
    # Only allow admin users to create users
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to create users.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreationWithRoleForm(request.POST)
        if form.is_valid():
            # Use transaction to ensure all operations succeed or fail together
            try:
                with transaction.atomic():
                    user = form.save()

                    selected_role = form.cleaned_data['role']
                    permission_fields = [field for field in form.fields.keys() if field.startswith('can_')]

                    profile_defaults = {
                        'phone': form.cleaned_data['phone'],
                        'role': selected_role,
                        'is_active': True,
                    }
                    if not user.is_superuser:
                        for field in permission_fields:
                            profile_defaults[field] = form.cleaned_data.get(field, False)

                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults=profile_defaults,
                    )

                    if not created:
                        profile.phone = form.cleaned_data['phone']
                        profile.role = selected_role
                        if not user.is_superuser:
                            for field in permission_fields:
                                setattr(profile, field, form.cleaned_data.get(field, False))
                        profile.save()

                messages.success(request, f'User {user.username} created successfully.')
                return redirect('user_list')
            except Exception as e:
                # If something went wrong, display the error
                messages.error(request, f"Error creating user: {str(e)}")
        else:
            # Display form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationWithRoleForm()
    
    context = {
        'form': form,
        'title': 'Create New User',
    }
    
    return render(request, 'posapp/users/user_form.html', context)

@login_required
def user_edit(request, user_id):
    """Edit an existing user"""
    # Only allow admin users to edit users
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to edit users.")
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    # Try to get the profile, but don't fail if it doesn't exist
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save user data
                    user = form.save()
                    
                    # Get or create profile safely
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'phone': form.cleaned_data.get('phone', ''),
                            'role': form.cleaned_data['role'],
                            'is_active': True
                        }
                    )
                    
                    # If profile already existed, update it
                    if not created:
                        profile.phone = form.cleaned_data.get('phone', '')
                        profile.role = form.cleaned_data['role']
                    
                    # Save all permission fields to profile (skip for superusers)
                    if not user.is_superuser:
                        permission_fields = [field for field in form.cleaned_data.keys() if field.startswith('can_')]
                        for field_name in permission_fields:
                            setattr(profile, field_name, form.cleaned_data[field_name])
                    
                    profile.save()
                
                messages.success(request, f'User {user.username} updated successfully.')
                return redirect('user_detail', user_id=user.id)
            except Exception as e:
                messages.error(request, f"Error updating user: {str(e)}")
        else:
            # Display form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserEditForm(instance=user)
    
    context = {
        'form': form,
        'title': f'Edit User {user.username}',
        'user_obj': user,
    }
    
    return render(request, 'posapp/users/user_edit.html', context)

@login_required
def user_delete(request, user_id):
    """Delete a user"""
    # Only allow admin users to delete users
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to delete users.")
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent self-deletion
    if user.id == request.user.id:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')
    
    if request.method == 'POST':
        try:
            username = user.username
            user.delete()
            messages.success(request, f'User {username} deleted successfully.')
            return redirect('user_list')
        except django.db.models.deletion.ProtectedError as e:
            # Deactivate the user instead of deleting
            deactivate_user(user)
            messages.warning(request, f"User {user.username} could not be deleted because they have associated orders. The user has been deactivated instead.")
            return redirect('user_list')
    
    context = {
        'user_obj': user,
    }
    
    return render(request, 'posapp/users/user_confirm_delete.html', context)

def deactivate_user(user):
    """Deactivate a user instead of deleting them"""
    # Set is_active to False on the User
    user.is_active = False
    user.save()
    
    # Also deactivate their profile if it exists
    try:
        if hasattr(user, 'profile'):
            user.profile.is_active = False
            user.profile.save()
    except Exception:
        pass  # If there's no profile, just continue
    
    return True

@login_required
def active_sessions(request):
    """Display list of active user sessions"""
    # Only allow admin users to view active sessions
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to view active sessions.")
        return redirect('dashboard')
    
    # Get active users
    active_users = get_active_users()
    
    # Handle force logout if requested
    if request.method == 'POST' and 'force_logout' in request.POST:
        user_id = request.POST.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            if force_logout_user(user):
                messages.success(request, f'Successfully logged out {user.username}')
            else:
                messages.warning(request, f'User {user.username} was not logged in')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
        
        return redirect('active_sessions')
    
    # Get today's date range based on manual end day system
    from ..models import EndDay, Order
    from django.db.models import Sum, Count
    from django.utils import timezone
    
    # Get the last end day timestamp
    last_end_day = EndDay.get_last_end_day()
    if last_end_day:
        today_start = last_end_day.end_date
    else:
        # If no end day exists, use start of today
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    today_end = timezone.now()
    
    # Enhance active users with their today's order statistics
    active_users_with_orders = []
    for user_session in active_users:
        user = user_session.user
        
        # Get today's orders for this user (since last end day)
        today_orders = Order.objects.filter(
            user=user,
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        
        # Calculate statistics
        total_orders_today = today_orders.count()
        completed_orders_today = today_orders.filter(order_status='Completed').count()
        pending_orders_today = today_orders.filter(order_status='Pending').count()
        cancelled_orders_today = today_orders.filter(order_status='Cancelled').count()
        
        # Calculate revenue from completed orders
        today_revenue = today_orders.filter(order_status='Completed').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Add order statistics to user session
        user_session.orders_today = total_orders_today
        user_session.completed_orders_today = completed_orders_today
        user_session.pending_orders_today = pending_orders_today
        user_session.cancelled_orders_today = cancelled_orders_today
        user_session.revenue_today = today_revenue
        
        active_users_with_orders.append(user_session)
    
    context = {
        'active_users': active_users_with_orders,
        'total_active': active_users.count() if active_users else 0,
        'last_end_day': last_end_day,
        'today_start': today_start,
    }
    
    return render(request, 'posapp/users/active_sessions.html', context) 