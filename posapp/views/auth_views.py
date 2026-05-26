from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.models import User
from ..forms import CustomAuthenticationForm
from ..models import AuditLog, UserProfile, UserRole, Order

class LoginView(View):
    template_name = 'posapp/auth/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = CustomAuthenticationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Check if user already has an active session before logging in
                from ..models import UserSession
                had_previous_session = UserSession.objects.filter(user=user).exists()
                
                login(request, user)
                
                # Show message if previous session was terminated
                if had_previous_session:
                    messages.info(request, 'Your previous session has been terminated. Only one login per user is allowed.')
                
                # Ensure user profile exists
                if not hasattr(user, 'profile'):
                    # Get default role (Cashier or create it if it doesn't exist)
                    default_role, _ = UserRole.objects.get_or_create(
                        name='Cashier',
                        defaults={'description': 'Cashier with limited access'}
                    )
                    
                    # If user is superuser or staff, make them Admin
                    if user.is_superuser or user.is_staff:
                        admin_role, _ = UserRole.objects.get_or_create(
                            name='Admin',
                            defaults={'description': 'Administrator with full access'}
                        )
                        UserProfile.objects.get_or_create(
                            user=user, 
                            defaults={'role': admin_role, 'is_active': True}
                        )
                    else:
                        UserProfile.objects.get_or_create(
                            user=user, 
                            defaults={'role': default_role, 'is_active': True}
                        )
                
                # Check if next URL is specified in the query params
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                # Redirect based on user role
                if user.is_superuser or (hasattr(user, 'profile') and user.profile.role and user.profile.role.name == 'Admin'):
                    return redirect('dashboard')
                else:
                    # Cashiers go directly to POS
                    return redirect('pos')
        
        # If form is invalid, show error messages
        messages.error(request, 'Invalid username or password')
        return render(request, self.template_name, {'form': form})

class LogoutView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
            
        # Check if the user is an admin (can always logout)
        is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role.name == 'Admin')
        
        if not is_admin:
            # Check for incomplete orders (Pending orders)
            has_incomplete_orders = Order.objects.filter(
                user=request.user, 
                order_status='Pending'
            ).exists()
            
            if has_incomplete_orders:
                messages.error(request, "You cannot logout until all your orders are completed. Please complete your pending orders first.")
                return redirect('order_list')
        
        logout(request)
        return redirect('login')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'posapp/auth/change_password.html', {'form': form})