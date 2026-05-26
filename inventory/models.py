from django.db import models
from django.utils import timezone
from posapp.models import PosProduct

class InventoryCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    """Stores vendor details from whom materials are purchased"""
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Litre'),
        ('ml', 'Millilitre'),
        ('pcs', 'Pieces'),
        ('box', 'Box'),
    ]

    category = models.ForeignKey(InventoryCategory, on_delete=models.SET_NULL, null=True, related_name='items')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Barcode or Stock Code")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Last purchase price per unit")
    current_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs')
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=3, default=5, help_text="Alert when stock goes below this level")
    is_active = models.BooleanField(default=True, help_text="Uncheck if this item is no longer used")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.current_stock} {self.unit})"

class Purchase(models.Model):
    """Bill Header - Represents a purchase invoice"""
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    purchase_date = models.DateField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inv#{self.invoice_number} - {self.purchase_date}"

class PurchaseItem(models.Model):
    """Bill Items - Individual items within a purchase invoice"""
    
    COST_TYPE_CHOICES = [
        ('Total', 'Total Cost'),
        ('Unit', 'Per Unit Cost'),
    ]

    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Quantity purchased")
    cost_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Enter the cost amount")
    cost_type = models.CharField(max_length=10, choices=COST_TYPE_CHOICES, default='Total', help_text="Is this amount for the Total or Per Unit?")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)

    def save(self, *args, **kwargs):
        # Calculation Logic based on user selection
        if self.quantity > 0:
            if self.cost_type == 'Total':
                # If user entered Total Amount (e.g. 16000 for 25kg)
                self.total_cost = self.cost_amount
                self.unit_cost = self.cost_amount / self.quantity
            else:
                # If user entered Unit Price (e.g. 640 per kg)
                self.unit_cost = self.cost_amount
                self.total_cost = self.cost_amount * self.quantity
        else:
            self.total_cost = 0
            self.unit_cost = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.inventory_item.name} - {self.quantity} ({self.cost_type})"

class Recipe(models.Model):
    """Links a POS Product to an Inventory Item (Ingredient)"""
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Litre'),
        ('ml', 'Millilitre'),
        ('pcs', 'Pieces'),
    ]
    pos_product = models.ForeignKey('posapp.PosProduct', on_delete=models.CASCADE, related_name='recipes')
    ingredient = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=3, help_text="Quantity used per 1 unit of Product")
    unit_used = models.CharField(max_length=5, choices=UNIT_CHOICES, default='pcs')

    def __str__(self):
        return f"{self.pos_product.name} uses {self.quantity_required} {self.unit_used} of {self.ingredient.name}"
    
class StockAdjustment(models.Model):
    """Used for Wastage, Theft, or Manual Corrections"""
    REASON_CHOICES = [
        ('Wastage', 'Wastage (Damaged/Expired)'),
        ('Theft', 'Theft'),
        ('Correction', 'Inventory Correction'),
        ('Return', 'Return to Supplier'),
    ]

    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=20, choices=REASON_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, help_text="Quantity to adjust (e.g. 1.5 kg)")
    action = models.CharField(max_length=10, choices=[('ADD', 'Add Stock'), ('REMOVE', 'Remove Stock')], default='REMOVE')
    notes = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.adjustment_type} - {self.inventory_item.name}"