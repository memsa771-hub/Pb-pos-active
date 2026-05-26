from django.contrib import admin
from django import forms
from posapp.models import (
    UserRole, UserProfile, PosCategory, PosProduct, 
    Order, OrderItem, Discount, Setting,
    PaymentTransaction, AuditLog, BusinessLogo,
    BusinessSettings, UserSession, DeliveryPerson,
)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Order Management Permissions', {
            'fields': (
                'can_create_orders',
                'can_edit_orders', 
                'can_cancel_orders',
                'can_view_all_orders',
                'can_complete_orders'
            ),
            'classes': ('collapse',)
        }),
        ('Discount Permissions', {
            'fields': (
                'can_apply_manual_discounts',
                'can_apply_discount_codes',
                'can_manage_discounts'
            ),
            'classes': ('collapse',)
        }),
        ('Product Management Permissions', {
            'fields': (
                'can_manage_products',
                'can_manage_categories',
                'can_view_stock',
                'can_manage_stock'
            ),
            'classes': ('collapse',)
        }),
        ('User Management Permissions', {
            'fields': (
                'can_manage_users',
                'can_manage_roles',
                'can_view_user_sessions'
            ),
            'classes': ('collapse',)
        }),
        ('Financial Permissions', {
            'fields': (
                'can_view_reports',
                'can_view_detailed_reports',
                'can_manage_payments',
                'can_end_day'
            ),
            'classes': ('collapse',)
        }),
        ('System Settings Permissions', {
            'fields': (
                'can_manage_business_settings',
                'can_manage_system_settings',
                'can_view_audit_logs'
            ),
            'classes': ('collapse',)
        }),
        ('Adjustment Permissions', {
            'fields': (
                'can_manage_bill_adjustments',
                'can_manage_advance_adjustments'
            ),
            'classes': ('collapse',)
        }),
        ('Delivery Permissions', {
            'fields': (
                'can_manage_delivery_persons',
                'can_assign_delivery_orders',
                'can_view_delivery_reports'
            ),
            'classes': ('collapse',)
        }),
        ('POS Access Permissions', {
            'fields': (
                'can_access_pos',
                'can_access_kitchen_view',
                'can_print_receipts'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add custom CSS to make checkboxes more readable
        form.base_fields['can_create_orders'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_edit_orders'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_cancel_orders'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_view_all_orders'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_complete_orders'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_apply_manual_discounts'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_apply_discount_codes'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_discounts'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_manage_products'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_categories'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_view_stock'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_stock'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_manage_users'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_roles'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_view_user_sessions'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_view_reports'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_view_detailed_reports'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_payments'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_end_day'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_manage_business_settings'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_system_settings'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_view_audit_logs'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_manage_bill_adjustments'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_manage_advance_adjustments'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_manage_delivery_persons'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_assign_delivery_orders'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_view_delivery_reports'].widget.attrs.update({'class': 'permission-checkbox'})
        
        form.base_fields['can_access_pos'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_access_kitchen_view'].widget.attrs.update({'class': 'permission-checkbox'})
        form.base_fields['can_print_receipts'].widget.attrs.update({'class': 'permission-checkbox'})
        
        return form

class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict role choices to only Branch Manager and Cashier in admin
        self.fields['role'].queryset = UserRole.objects.filter(name__in=['Branch Manager', 'Cashier'])
        

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user', 'phone', 'role', 'is_active', 'created_at')
    list_filter = ('is_active', 'role')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')

@admin.register(PosCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')

@admin.register(PosProduct)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_quantity', 'is_available', 'is_archived')
    list_filter = ('category', 'is_available', 'is_archived', 'running_item')
    search_fields = ('name', 'sku', 'description')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('created_at',)

class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'user', 'customer_name', 'table_number', 'order_type', 'total_amount', 'payment_method', 'payment_status', 'order_status', 'created_at')
    list_filter = ('order_status', 'payment_status', 'payment_method', 'order_type', 'created_at')
    search_fields = ('reference_number', 'customer_name', 'customer_phone', 'table_number', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline, PaymentTransactionInline]

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type', 'value', 'is_active', 'start_date', 'end_date')
    list_filter = ('type', 'is_active', 'start_date', 'end_date')
    search_fields = ('name', 'code')

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('setting_key', 'setting_value', 'setting_description', 'updated_at')
    search_fields = ('setting_key', 'setting_value', 'setting_description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'entity', 'entity_id', 'ip_address', 'created_at')
    list_filter = ('entity', 'created_at')
    search_fields = ('action', 'details', 'user__username')
    readonly_fields = ('created_at',)

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'tax_rate_card', 'tax_rate_cash', 'default_service_charge', 'updated_at')
    fieldsets = (
        ('Business Information', {
            'fields': ('business_name', 'business_address', 'business_phone', 'business_email')
        }),
        ('Tax Settings', {
            'fields': ('tax_rate_card', 'tax_rate_cash', 'default_service_charge', 'currency_symbol')
        }),
    )

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key_short', 'login_time', 'last_activity', 'ip_address', 'user_agent_short')
    list_filter = ('login_time', 'last_activity')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'ip_address')
    readonly_fields = ('user', 'session_key', 'login_time', 'last_activity', 'ip_address', 'user_agent')
    ordering = ('-last_activity',)
    
    def session_key_short(self, obj):
        return f"{obj.session_key[:8]}..." if obj.session_key else "-"
    session_key_short.short_description = 'Session'
    
    def user_agent_short(self, obj):
        if obj.user_agent:
            return obj.user_agent[:50] + "..." if len(obj.user_agent) > 50 else obj.user_agent
        return "-"
    user_agent_short.short_description = 'User Agent'
    
    def has_add_permission(self, request):
        # Prevent manual creation of sessions
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow viewing but not editing
        return False
    
    actions = ['force_logout_selected']
    
    def force_logout_selected(self, request, queryset):
        """Admin action to force logout selected users"""
        from .session_manager import force_logout_user
        
        count = 0
        for session in queryset:
            if force_logout_user(session.user):
                count += 1
        
        if count:
            self.message_user(request, f'Successfully logged out {count} user(s).')
        else:
            self.message_user(request, 'No users were logged out.', level='WARNING')
    
    force_logout_selected.short_description = "Force logout selected users"

@admin.register(DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone')
    readonly_fields = ('created_at', 'updated_at')