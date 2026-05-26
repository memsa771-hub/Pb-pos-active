from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.db import transaction

from ..models import Setting, BusinessLogo
from ..forms import BusinessLogoForm
from ..views.user_views import is_admin

class SettingsForm(forms.Form):
    """Base form for settings with dynamic field generation"""
    def __init__(self, *args, **kwargs):
        settings = kwargs.pop('settings', {})
        super().__init__(*args, **kwargs)
        
        # Dynamically create fields based on settings
        for key, setting_data in settings.items():
            field_type = setting_data.get('type', 'text')
            required = setting_data.get('required', True)
            choices = setting_data.get('choices', None)
            initial = setting_data.get('value', '')
            help_text = setting_data.get('help_text', '')
            
            if field_type == 'text':
                self.fields[key] = forms.CharField(
                    required=required,
                    initial=initial,
                    help_text=help_text,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            elif field_type == 'textarea':
                self.fields[key] = forms.CharField(
                    required=required,
                    initial=initial,
                    help_text=help_text,
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                )
            elif field_type == 'number':
                self.fields[key] = forms.DecimalField(
                    required=required,
                    initial=initial,
                    help_text=help_text,
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
                )
            elif field_type == 'checkbox':
                self.fields[key] = forms.BooleanField(
                    required=False,
                    initial=bool(initial),
                    help_text=help_text,
                )
            elif field_type == 'select' and choices:
                self.fields[key] = forms.ChoiceField(
                    choices=choices,
                    required=required,
                    initial=initial,
                    help_text=help_text,
                    widget=forms.Select(attrs={'class': 'form-control'})
                )


def get_or_create_settings(keys, settings_config=None):
    """Get or create settings with the specified keys"""
    settings_config = settings_config or {}
    existing_settings = {s.setting_key: s for s in Setting.objects.filter(setting_key__in=keys)}
    
    result = {}
    for key in keys:
        if key in existing_settings:
            result[key] = existing_settings[key]
        else:
            # Get default value and description from config if available
            default_value = ''
            description = key.replace('_', ' ').title()
            
            if settings_config and key in settings_config:
                config = settings_config[key]
                default_value = config.get('value', '')
                description = config.get('help_text', description)
            
            # Create setting with default value if it doesn't exist
            result[key] = Setting.objects.create(
                setting_key=key,
                setting_value=default_value,
                setting_description=description
            )
    
    return result


def update_settings(settings_data):
    """Update settings in the database"""
    with transaction.atomic():
        for key, value in settings_data.items():
            Setting.set_value(key, value)
    
    return True


@login_required
def settings_dashboard(request):
    """Main settings dashboard"""
    # Only allow admin users to view settings
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access settings.")
        return redirect('dashboard')
    
    # Get system information for display
    import django
    import sys
    import platform
    import socket
    import pytz
    from django.utils import timezone
    
    # Get current time in Pakistan Standard Time (PKT)
    utc_now = timezone.now()
    pakistan_tz = pytz.timezone('Asia/Karachi')
    pakistan_time = utc_now.astimezone(pakistan_tz)
    
    context = {
        'title': 'Settings Dashboard',
        'django_version': django.get_version(),
        'python_version': platform.python_version(),
        'server_time': pakistan_time.strftime('%Y-%m-%d %H:%M:%S PKT'),
        'server_os': platform.platform(),
        'server_software': 'Django Development Server',
        'server_ip': socket.gethostbyname(socket.gethostname()),
    }
    
    return render(request, 'posapp/settings/dashboard.html', context)


@login_required
def business_settings(request):
    """Business information settings"""
    # Only allow admin users to edit settings
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to edit settings.")
        return redirect('dashboard')
    
    # Define business settings fields
    business_settings_fields = {
        'business_name': {'type': 'text', 'required': True, 'help_text': 'Your business name'},
        'business_address': {'type': 'textarea', 'required': True, 'help_text': 'Full business address'},
        'business_phone': {'type': 'text', 'required': True, 'help_text': 'Contact phone number'},
        'business_email': {'type': 'text', 'required': False, 'help_text': 'Contact email address'},
        'business_website': {'type': 'text', 'required': False, 'help_text': 'Business website URL'},
        'business_tagline': {'type': 'text', 'required': False, 'help_text': 'Your business tagline or slogan'},
        'currency_symbol': {'type': 'text', 'required': True, 'help_text': 'Currency symbol (e.g., $, €, £)'},
        'tax_rate_card': {'type': 'number', 'required': True, 'help_text': 'Tax rate (%) for card payments', 'value': '5.0'},
        'tax_rate_cash': {'type': 'number', 'required': True, 'help_text': 'Tax rate (%) for cash payments', 'value': '15.0'},
        'default_service_charge': {'type': 'number', 'required': True, 'help_text': 'Default service charge (%) for Dine In orders', 'value': '5.0'},
    }
    
    # Get existing settings
    settings = get_or_create_settings(business_settings_fields.keys(), business_settings_fields)
    
    # Prepare initial data
    initial_data = {key: settings[key].setting_value for key in business_settings_fields.keys()}
    
    # Update business settings fields with current values
    for key in business_settings_fields:
        business_settings_fields[key]['value'] = initial_data.get(key, '')
    
    # Get current logo
    current_logo = BusinessLogo.get_logo_url()
    logo_form = BusinessLogoForm()
    
    # Initialize form for both GET and POST requests
    form = SettingsForm(initial=initial_data, settings=business_settings_fields)
    
    if request.method == 'POST':
        if 'upload_logo' in request.POST:
            # Handle logo upload
            logo_form = BusinessLogoForm(request.POST, request.FILES)
            if logo_form.is_valid():
                try:
                    # Save the form which will handle the image processing
                    logo_form.save()
                    messages.success(request, "Business logo uploaded successfully.")
                    return redirect('business_settings')
                except Exception as e:
                    messages.error(request, f"Error uploading logo: {str(e)}")
            else:
                # Show form validation errors
                for field, errors in logo_form.errors.items():
                    for error in errors:
                        messages.error(request, f"Logo upload error: {error}")
        else:
            # Handle regular settings form
            form = SettingsForm(request.POST, settings=business_settings_fields)
            if form.is_valid():
                update_settings(form.cleaned_data)
                messages.success(request, "Business settings updated successfully.")
                return redirect('business_settings')
    
    context = {
        'title': 'Business Settings',
        'form': form,
        'logo_form': logo_form,
        'current_logo': current_logo,
        'settings_section': 'business',
    }
    
    return render(request, 'posapp/settings/business_form.html', context)


@login_required
def receipt_settings(request):
    """Receipt configuration settings"""
    # Only allow admin users to edit settings
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to edit settings.")
        return redirect('dashboard')
    
    # Define receipt settings fields
    receipt_settings_fields = {
        'receipt_header': {'type': 'textarea', 'required': False, 'help_text': 'Text to show at the top of receipts'},
        'receipt_footer': {'type': 'textarea', 'required': False, 'help_text': 'Text to show at the bottom of receipts'},
        'receipt_show_logo': {'type': 'checkbox', 'required': False, 'help_text': 'Show business logo on receipts'},
        'receipt_show_cashier': {'type': 'checkbox', 'required': False, 'help_text': 'Show cashier name on receipts'},
    }
    
    # Get existing settings
    settings = get_or_create_settings(receipt_settings_fields.keys(), receipt_settings_fields)
    
    # Prepare initial data
    initial_data = {key: settings[key].setting_value for key in receipt_settings_fields.keys()}
    
    # Update receipt settings fields with current values
    for key in receipt_settings_fields:
        receipt_settings_fields[key]['value'] = initial_data.get(key, '')
    
    if request.method == 'POST':
        form = SettingsForm(request.POST, settings=receipt_settings_fields)
        
        if form.is_valid():
            update_settings(form.cleaned_data)
            messages.success(request, "Receipt settings updated successfully.")
            return redirect('receipt_settings')
    else:
        form = SettingsForm(initial=initial_data, settings=receipt_settings_fields)
    
    context = {
        'title': 'Receipt Settings',
        'form': form,
        'settings_section': 'receipt',
    }
    
    return render(request, 'posapp/settings/receipt_form.html', context)


@login_required
def theme_settings(request):
    """Theme and appearance settings"""
    # Only allow admin users to edit settings
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to edit settings.")
        return redirect('dashboard')
    
    # Define theme settings fields with 5 beautiful color options
    theme_settings_fields = {
        'theme_color': {
            'type': 'select', 
            'required': True, 
            'help_text': 'Select a color theme for the application',
            'choices': [
                ('default', 'Default Blue'),
                ('indigo', 'Elegant Indigo'),
                ('teal', 'Modern Teal'),
                ('crimson', 'Vibrant Crimson'),
                ('amber', 'Warm Amber')
            ]
        }
    }
    
    # Get existing settings
    settings = get_or_create_settings(theme_settings_fields.keys(), theme_settings_fields)
    
    # Prepare initial data
    initial_data = {key: settings[key].setting_value for key in theme_settings_fields.keys()}
    
    # Update theme settings fields with current values
    for key in theme_settings_fields:
        theme_settings_fields[key]['value'] = initial_data.get(key, '')
    
    if request.method == 'POST':
        # Handle regular settings form
        form = SettingsForm(request.POST, settings=theme_settings_fields)
        if form.is_valid():
            update_settings(form.cleaned_data)
            messages.success(request, "Theme settings updated successfully.")
            return redirect('theme_settings')
    else:
        form = SettingsForm(initial=initial_data, settings=theme_settings_fields)
    
    # Prepare color previews for the template
    color_previews = {
        'default': {
            'primary': '#4e73df',
            'secondary': '#858796',
            'success': '#1cc88a',
            'danger': '#e74a3b',
            'name': 'Default Blue'
        },
        'indigo': {
            'primary': '#6610f2',
            'secondary': '#6c757d',
            'success': '#20c997',
            'danger': '#dc3545',
            'name': 'Elegant Indigo'
        },
        'teal': {
            'primary': '#20c997',
            'secondary': '#5a6268',
            'success': '#28a745',
            'danger': '#dd6b4d',
            'name': 'Modern Teal'
        },
        'crimson': {
            'primary': '#dc3545',
            'secondary': '#6c757d',
            'success': '#28a745',
            'danger': '#212529',
            'name': 'Vibrant Crimson'
        },
        'amber': {
            'primary': '#fd7e14',
            'secondary': '#6c757d',
            'success': '#28a745',
            'danger': '#dc3545',
            'name': 'Warm Amber'
        }
    }
    
    context = {
        'title': 'Theme Settings',
        'form': form,
        'settings_section': 'theme',
        'color_previews': color_previews,
        'current_theme': initial_data.get('theme_color', 'default')
    }
    
    return render(request, 'posapp/settings/theme_form.html', context) 