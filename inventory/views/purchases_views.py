from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from decimal import Decimal
from posapp.decorators import can_manage_stock_required
from inventory.models import Purchase, PurchaseItem, Supplier, InventoryItem

# ----------------- ADD PURCHASE (Stock In) ----------------- #

@login_required
@can_manage_stock_required
def add_purchase(request):
    """
    Record a new Purchase Invoice and update Stock immediately.
    """
    
    if request.method == 'POST':
        # 1. Get Header Details
        supplier_id = request.POST.get('supplier')
        invoice_number = request.POST.get('invoice_number')
        notes = request.POST.get('notes')
        purchase_date = request.POST.get('purchase_date')

        # Validation
        if not supplier_id:
            messages.error(request, "Supplier is required.")
            return redirect('inventory:add_purchase')

        try:
            with transaction.atomic(): 
                
                # 2. Create Purchase Header
                purchase = Purchase.objects.create(
                    supplier_id=supplier_id,
                    invoice_number=invoice_number,
                    notes=notes
                )
                if purchase_date:
                    purchase.purchase_date = purchase_date
                    purchase.save()

                # 3. Handle Items
                item_ids = request.POST.getlist('items[]')
                quantities = request.POST.getlist('quantities[]')
                costs = request.POST.getlist('costs[]')
                cost_types = request.POST.getlist('cost_types[]')

                # Fallback for Single Item Form (Agar JavaScript fail ho jaye)
                if not item_ids: 
                    item_ids = [request.POST.get('item')]
                    quantities = [request.POST.get('quantity')]
                    costs = [request.POST.get('cost')]
                    cost_types = [request.POST.get('cost_type')]

                total_bill_amount = 0

                # 4. Loop through items and save
                for i in range(len(item_ids)):
                    if item_ids[i] and quantities[i]: 
                        
                        # Convert inputs to numbers
                        qty_val = Decimal(str(quantities[i])) # Decimal for precision
                        cost_val = Decimal(str(costs[i])) if costs[i] else Decimal('0')
                        
                        # Save Line Item (Record)
                        p_item = PurchaseItem.objects.create(
                            purchase=purchase,
                            inventory_item_id=item_ids[i],
                            quantity=qty_val,
                            cost_amount=cost_val,
                            cost_type=cost_types[i] or 'Total'
                        )
                        
                        #  MANUAL STOCK UPDATE (GUARANTEED FIX) 
                        inv_item = p_item.inventory_item
                        inv_item.current_stock += qty_val
                        
                        # Update Latest Cost Price
                        if p_item.unit_cost > 0:
                            inv_item.cost_price = p_item.unit_cost
                            
                        inv_item.save() # Save changes to database
                        
                        # Grand Total Calculation
                        total_bill_amount += p_item.total_cost

                # Update Grand Total in Header
                purchase.total_amount = total_bill_amount
                purchase.save()

                messages.success(request, f"Purchase Invoice #{invoice_number} saved & Stock Updated!")
                return redirect('inventory:dashboard')

        except Exception as e:
            messages.error(request, f"Error saving purchase: {str(e)}")

    # ---------------- GET REQUEST ---------------- #
    
    suppliers = Supplier.objects.all()
    items = InventoryItem.objects.filter(is_active=True).order_by('name')

    context = {
        'title': 'Add New Purchase',
        'suppliers': suppliers,
        'items': items,
        'type': 'purchase'
    }

    return render(request, 'inventory/transaction_form.html', context)