from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from posapp.decorators import can_manage_stock_required
from inventory.models import StockAdjustment, InventoryItem
from decimal import Decimal

# ----------------- ADD ADJUSTMENT (Stock Out/Correction) ----------------- #

@login_required
@can_manage_stock_required
def add_adjustment(request):
    """
    Record Stock Adjustment with Validation.
    """
    
    if request.method == 'POST':
        item_id = request.POST.get('item')
        quantity_str = request.POST.get('quantity')
        action = request.POST.get('action')       # 'ADD' or 'REMOVE'
        reason = request.POST.get('reason')       
        notes = request.POST.get('notes')

        # Validation 1: Required Fields
        if not item_id or not quantity_str or not action:
            messages.error(request, "Item, Quantity and Action are required.")
            return redirect('inventory:add_adjustment')

        try:
            # Convert Quantity to Decimal
            quantity = Decimal(quantity_str)
            
            # Get Item Logic
            item = get_object_or_404(InventoryItem, pk=item_id)

            # 🔥 VALIDATION 2: Check Negative Stock
            if action == 'REMOVE' and item.current_stock < quantity:
                messages.error(request, f"Error: Not enough stock! Current: {item.current_stock} {item.unit}, Trying to remove: {quantity}")
                return redirect('inventory:add_adjustment')

            # Create Record
            adjustment = StockAdjustment.objects.create(
                inventory_item_id=item_id,
                quantity=quantity,
                action=action,
                adjustment_type=reason,
                notes=notes
            )
            
            # 🔥 MANUAL STOCK UPDATE (Immediate Refresh)
            if action == 'ADD':
                item.current_stock += quantity
            elif action == 'REMOVE':
                item.current_stock -= quantity
            
            item.save() # Database update immediately
            
            # Success Message
            if action == 'REMOVE':
                messages.warning(request, f"Removed {quantity} {item.unit} from {item.name}")
            else:
                messages.success(request, f"Added {quantity} {item.unit} to {item.name}")
            
            # Refresh Dashboard
            return redirect('inventory:dashboard')

        except Exception as e:
            messages.error(request, f"Error recording adjustment: {str(e)}")

    # Context Data
    items = InventoryItem.objects.filter(is_active=True).order_by('name')
    reasons = StockAdjustment.REASON_CHOICES

    context = {
        'title': 'Record Stock Adjustment',
        'items': items,
        'reasons': reasons,
        'type': 'adjustment'
    }
    
    return render(request, 'inventory/transaction_form.html', context)