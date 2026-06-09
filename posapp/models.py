from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.files.base import ContentFile
import base64
import uuid
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class UserRole(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    
    # Permission fields - detailed permission system
    # Order Management Permissions
    can_create_orders = models.BooleanField(default=False, help_text="Allow creating new orders")
    can_edit_orders = models.BooleanField(default=False, help_text="Allow editing existing orders")
    can_cancel_orders = models.BooleanField(default=False, help_text="Allow cancelling orders")
    can_view_all_orders = models.BooleanField(default=False, help_text="Allow viewing all orders")
    can_complete_orders = models.BooleanField(default=False, help_text="Allow marking orders as completed")
    
    # Discount Permissions
    can_apply_manual_discounts = models.BooleanField(default=False, help_text="Allow applying manual discounts")
    can_apply_discount_codes = models.BooleanField(default=False, help_text="Allow applying discount codes")
    can_manage_discounts = models.BooleanField(default=False, help_text="Allow creating/editing discount codes")
    
    # Product Management Permissions
    can_manage_products = models.BooleanField(default=False, help_text="Allow creating/editing products")
    can_manage_categories = models.BooleanField(default=False, help_text="Allow creating/editing categories")
    can_view_stock = models.BooleanField(default=False, help_text="Allow viewing stock levels")
    can_manage_stock = models.BooleanField(default=False, help_text="Allow adjusting stock levels")
    
    # User Management Permissions
    can_manage_users = models.BooleanField(default=False, help_text="Allow creating/editing users")
    can_manage_roles = models.BooleanField(default=False, help_text="Allow creating/editing user roles")
    can_view_user_sessions = models.BooleanField(default=False, help_text="Allow viewing active user sessions")
    
    # Financial Permissions
    can_view_reports = models.BooleanField(default=False, help_text="Allow viewing sales reports")
    can_view_detailed_reports = models.BooleanField(default=False, help_text="Allow viewing detailed financial reports")
    can_manage_payments = models.BooleanField(default=False, help_text="Allow managing payment transactions")
    can_end_day = models.BooleanField(default=False, help_text="Allow ending the business day")
    
    # System Settings Permissions
    can_manage_business_settings = models.BooleanField(default=False, help_text="Allow editing business settings")
    can_manage_system_settings = models.BooleanField(default=False, help_text="Allow editing system settings")
    can_view_audit_logs = models.BooleanField(default=False, help_text="Allow viewing audit logs")
    
    # Adjustment Permissions
    can_manage_bill_adjustments = models.BooleanField(default=False, help_text="Allow managing bill adjustments")
    can_manage_advance_adjustments = models.BooleanField(default=False, help_text="Allow managing advance adjustments")
    
    # Delivery Permissions
    can_manage_delivery_persons = models.BooleanField(default=False, help_text="Allow managing delivery persons")
    can_assign_delivery_orders = models.BooleanField(default=False, help_text="Allow assigning orders to delivery persons")
    can_view_delivery_reports = models.BooleanField(default=False, help_text="Allow viewing delivery reports")
    
    # POS Access Permissions
    can_access_pos = models.BooleanField(default=True, help_text="Allow access to POS system")
    can_access_kitchen_view = models.BooleanField(default=False, help_text="Allow access to kitchen view")
    can_print_receipts = models.BooleanField(default=True, help_text="Allow printing receipts")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def has_permission(self, permission):
        """Check if role has a specific permission"""
        return getattr(self, permission, False)
    
    def get_all_permissions(self):
        """Get all permissions for this role"""
        permission_fields = [field.name for field in self._meta.fields if field.name.startswith('can_')]
        permissions = {}
        for field in permission_fields:
            permissions[field] = getattr(self, field, False)
        return permissions

    @classmethod
    def create_default_roles(cls):
        """Create default roles if they don't exist"""
        default_roles = [
            {
                'name': 'Admin',
                'description': 'Administrator with full access'
            },
            {
                'name': 'Cashier',
                'description': 'Cashier with limited access'
            },
            {
                'name': 'Branch Manager',
                'description': 'Branch Manager role'
            }
        ]
        
        for role in default_roles:
            cls.objects.get_or_create(
                name=role['name'],
                defaults={'description': role['description']}
            )

# Signal to create default roles after migrations
@receiver(post_migrate)
def create_roles_after_migrate(sender, **kwargs):
    if sender.name == 'posapp':  # Only run for our app
        UserRole.create_default_roles()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.ForeignKey(UserRole, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    
    # Individual Permissions
    can_edit_orders = models.BooleanField(default=False, help_text="Allow editing orders")
    can_cancel_orders = models.BooleanField(default=False, help_text="Allow cancelling orders")
    can_apply_manual_discounts = models.BooleanField(default=False, help_text="Allow applying manual discounts")
    can_apply_discount_codes = models.BooleanField(default=False, help_text="Allow applying discount codes")
    can_edit_orders_with_password = models.BooleanField(default=False, help_text="Allow editing orders with admin password verification")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class UserSession(models.Model):
    """Track active user sessions to enforce single login per user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='active_session')
    session_key = models.CharField(max_length=40, unique=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.session_key[:8]}..."

    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

class PosCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class PosProduct(models.Model):
    """Product model for POS system"""
    name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=20, unique=True, default='000000', help_text="Unique numeric identifier for the product")
    category = models.ForeignKey(PosCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=100, blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False, help_text="If checked, product is archived and hidden from active listings")
    is_recipe_based = models.BooleanField(default=False, help_text="Check this if product is made in kitchen using raw ingredients")
    running_item = models.BooleanField(default=False, help_text="If checked, stock will not decrease when ordered")
    calculate_price_per_kg = models.BooleanField(default=False, help_text="If checked, product will be sold by weight (per kg)")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
        
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'product_id': self.pk})
    
    class Meta:
        ordering = ['name']

class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]
    
    ORDER_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, help_text="Internal system reference (not displayed to users)")
    daily_order_number = models.IntegerField(default=0, help_text="Daily order number that resets after end day")
    reference_number = models.CharField(max_length=10, null=True, blank=True, help_text="Unique reference number with format PB plus 4 digits")
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    discount = models.ForeignKey('Discount', on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Fields for manual discount information
    discount_code = models.CharField(max_length=50, blank=True, null=True, default='', help_text="For manual discounts, this will be 'MANUAL'")
    discount_type = models.CharField(max_length=20, blank=True, null=True, default='fixed', help_text="'percentage' or 'fixed' for manual discounts")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0, help_text="Value of the manual discount")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, default='Cash')
    # Cash payment details
    cash_given = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount of cash given by customer")
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Change amount to return to customer")
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    order_status = models.CharField(max_length=10, choices=ORDER_STATUS_CHOICES, default='Pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_type = models.CharField(max_length=20, default='Dine In', blank=True, null=True)
    delivery_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_address = models.TextField(blank=True, null=True)
    table_number = models.CharField(max_length=10, blank=True, null=True, help_text="Table number for Dine In orders")
    service_charge_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Service charge percentage for Dine In orders")
    service_charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Service charge amount calculated from percentage")
    delivery_person = models.ForeignKey('DeliveryPerson', on_delete=models.SET_NULL, null=True, blank=True, help_text="Delivery person assigned to the order")

    def __str__(self):
        return self.reference_number
        
    def get_subtotal(self):
        """Calculate subtotal from order items"""
        from decimal import Decimal
        return self.items.aggregate(total=models.Sum(models.F('unit_price') * models.F('quantity')))['total'] or Decimal('0.00')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(PosProduct, on_delete=models.PROTECT, help_text="Products can only be deleted if they're not in pending orders")
    quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Quantity - supports decimal values for weight-based products")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_temporary = models.BooleanField(default=False, help_text="Indicates if this item is temporary and not yet saved")
    original_quantity = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Original quantity for tracking stock adjustments")

    def __str__(self):
        return f"{self.order.reference_number} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Set original quantity on first save if not already set
        if self.pk is None and self.original_quantity is None:
            self.original_quantity = self.quantity
        super().save(*args, **kwargs)

    class Meta:
        # No DB constraint here, we'll handle it in the view for more flexibility
        pass

class Discount(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('Percentage', 'Percentage'),
        ('Fixed', 'Fixed'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Setting(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    setting_description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.setting_key

    @classmethod
    def get_value(cls, key, default=None):
        """Get setting value by key with optional default value"""
        try:
            return cls.objects.get(setting_key=key).setting_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, key, value, description=None):
        """Set setting value by key with optional description"""
        obj, created = cls.objects.update_or_create(
            setting_key=key,
            defaults={
                'setting_value': str(value),
                'setting_description': description or key.replace('_', ' ').title()
            }
        )
        return obj

class PaymentTransaction(models.Model):
    TRANSACTION_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    transaction_number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_status = models.CharField(max_length=10, choices=TRANSACTION_STATUS_CHOICES, default='Pending')
    transaction_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction_number

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    entity = models.CharField(max_length=50)
    entity_id = models.IntegerField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.user.username if self.user else 'Unknown'}"

class BusinessLogo(models.Model):
    """Store the business logo image"""
    image = models.BinaryField(null=True, blank=True)
    image_name = models.CharField(max_length=255, null=True, blank=True)
    image_type = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Business Logo (uploaded at {self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def get_logo_url(cls):
        """Get the current business logo URL"""
        logo = cls.objects.order_by('-uploaded_at').first()
        if logo and logo.image:
            # Generate a unique ID for the image URL
            unique_id = uuid.uuid4().hex
            return f"/business_logo/{logo.id}/?v={unique_id}"
        return None
    
    def set_image(self, image_file):
        if image_file:
            # Store image content in BinaryField
            self.image_name = image_file.name
            self.image_type = image_file.content_type
            self.image = image_file.read()

class BusinessSettings(models.Model):
    """Store business settings like name, address, tax rates, etc."""
    business_name = models.CharField(max_length=255, default='PickBug Solutions')
    business_address = models.TextField(blank=True, null=True)
    business_phone = models.CharField(max_length=20, blank=True, null=True)
    business_email = models.EmailField(blank=True, null=True)
    tax_rate_card = models.DecimalField(max_digits=5, decimal_places=2, default=5.0, 
                                       help_text='Tax rate for card payments in percentage')
    tax_rate_cash = models.DecimalField(max_digits=5, decimal_places=2, default=15.0, 
                                       help_text='Tax rate for cash payments in percentage')
    default_service_charge = models.DecimalField(max_digits=5, decimal_places=2, default=5.0,
                                               help_text='Default service charge percentage for Dine In orders')
    currency_symbol = models.CharField(max_length=5, default='Rs.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Business Setting'
        verbose_name_plural = 'Business Settings'
        
    def __str__(self):
        return self.business_name
    
    @classmethod
    def get_settings(cls):
        """Get or create business settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings 

class BillAdjustment(models.Model):
    """Model for bill adjustments"""
    name = models.CharField(max_length=255, help_text="Name of the person or entity")
    quantity = models.IntegerField(null=True, blank=True, help_text="Quantity of items (optional)")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total bill amount")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the adjustment")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bill_adjustments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bill Adjustment for {self.name} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def get_absolute_url(self):
        return reverse('bill_adjustment_detail', kwargs={'pk': self.pk})

class BillAdjustmentImage(models.Model):
    """Model for bill adjustment images"""
    bill_adjustment = models.ForeignKey(BillAdjustment, on_delete=models.CASCADE, related_name='images')
    image = models.BinaryField(help_text="Picture of the bill")
    image_name = models.CharField(max_length=255, null=True, blank=True)
    image_type = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.bill_adjustment.name} ({self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"
    
    def set_image(self, image_file):
        if image_file:
            # Store image content in BinaryField
            self.image_name = image_file.name
            self.image_type = image_file.content_type
            self.image = image_file.read()
    
    def get_image_url(self):
        if self.image:
            # Generate a unique ID for the image URL
            unique_id = uuid.uuid4().hex
            return f"/bill_adjustment_image/{self.id}/?v={unique_id}"
        return None

class AdvanceAdjustment(models.Model):
    """Model for advance adjustments"""
    name = models.CharField(max_length=255, help_text="Name of the person or entity")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Advance amount")
    date = models.DateField(default=timezone.now, editable=False, help_text="Date of advance (automatically set to today)")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the adjustment")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='advance_adjustments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}: {self.amount}"
    
    def get_absolute_url(self):
        return reverse('advance_adjustment_detail', kwargs={'pk': self.pk})

class EndDay(models.Model):
    """Model to track end day events"""
    end_date = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the day was ended")
    ended_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='end_days')
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about ending the day")
    
    def __str__(self):
        return f"End Day: {self.end_date.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def get_last_end_day(cls):
        """Get the latest end day timestamp or None if no end days exist"""
        try:
            return cls.objects.order_by('-end_date').first()
        except:
            return None

class DeliveryPerson(models.Model):
    """Model for delivery persons"""
    name = models.CharField(max_length=255, help_text="Name of the delivery person")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number of the delivery person")
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Commission percentage per delivery order")
    is_active = models.BooleanField(default=True, help_text="Whether the delivery person is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Delivery Person'
        verbose_name_plural = 'Delivery Persons' 