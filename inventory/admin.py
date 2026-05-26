from django.contrib import admin
from .models import (
    InventoryCategory, Supplier, InventoryItem, 
    Purchase, PurchaseItem, Recipe, StockAdjustment
)

# 1. Categories
@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

# 2. Supplier
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address')
    search_fields = ('name', 'phone')

# 3. Inventory Item (Raw Materials)
@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'current_stock', 'unit', 'cost_price', 'min_stock_level', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active', 'unit')
    search_fields = ('name', 'sku')
    list_editable = ('cost_price', 'min_stock_level', 'is_active')

# 4. Purchase Logic (Inline Items)
class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    fields = ('inventory_item', 'quantity', 'cost_amount', 'cost_type', 'unit_cost', 'total_cost')
    readonly_fields = ('unit_cost', 'total_cost') # System calculates these, user cannot edit

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'purchase_date', 'total_amount')
    list_filter = ('purchase_date', 'supplier')
    search_fields = ('invoice_number', 'supplier__name')
    inlines = [PurchaseItemInline] # Purchase page ke andar hi items add karne k liye

# 5. Recipe (Linking POS Product to Inventory)
@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('pos_product', 'ingredient', 'quantity_required')
    search_fields = ('pos_product__name', 'ingredient__name')
    list_filter = ('pos_product',)

# 6. Stock Adjustment (Wastage/Theft Logs)
@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'adjustment_type', 'quantity', 'action', 'date')
    list_filter = ('adjustment_type', 'action', 'date')
    search_fields = ('inventory_item__name', 'notes')