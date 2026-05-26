from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from posapp.decorators import can_view_stock_required, can_manage_stock_required
from inventory.models import InventoryItem, InventoryCategory

# ----------------- ITEM LIST ----------------- #

@login_required
@can_view_stock_required
def item_list(request):
    """List all active Inventory Items"""
    
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    
    # Filter only active items (Soft Delete logic)
    items = InventoryItem.objects.filter(is_active=True).order_by('category__name', 'name')

    # Apply Search
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Apply Category Filter
    if category_filter:
        items = items.filter(category_id=category_filter)

    # Pagination
    paginator = Paginator(items, 15) # 15 items per page
    page_number = request.GET.get('page')
    items_page = paginator.get_page(page_number)
    
    # Context for filters
    categories = InventoryCategory.objects.all()

    context = {
        'items': items_page,
        'categories': categories,
        'search_query': search_query,
        'selected_category': int(category_filter) if category_filter else '',
    }

    return render(request, 'inventory/item_list.html', context)


# ----------------- CREATE ITEM ----------------- #

@login_required
@can_manage_stock_required
def item_create(request):
    """Add a new Raw Material/Item"""
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        unit = request.POST.get('unit')
        sku = request.POST.get('sku')
        cost_price = request.POST.get('cost_price')
        min_stock = request.POST.get('min_stock')
        description = request.POST.get('description')
        
        # Validation
        errors = []
        if not name: errors.append("Item Name is required.")
        if not cost_price: errors.append("Cost Price is required.")
        
        # Check SKU uniqueness
        if sku and InventoryItem.objects.filter(sku=sku).exists():
            errors.append("SKU/Barcode already exists.")

        if not errors:
            try:
                category = get_object_or_404(InventoryCategory, id=category_id) if category_id else None
                
                InventoryItem.objects.create(
                    name=name,
                    category=category,
                    unit=unit,
                    sku=sku,
                    cost_price=cost_price,
                    min_stock_level=min_stock or 5,
                    description=description,
                    current_stock=0, # Shuru may stock 0 hoga, Purchase se add hoga
                    is_active=True
                )
                messages.success(request, f"Item '{name}' added successfully.")
                return redirect('inventory:item_list')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            for error in errors:
                messages.error(request, error)

    # Context Data
    categories = InventoryCategory.objects.all()
    # Pass UNIT_CHOICES from model to template
    units = InventoryItem.UNIT_CHOICES 

    return render(request, 'inventory/item_form.html', {
        'categories': categories, 
        'units': units
    })


# ----------------- UPDATE ITEM ----------------- #

@login_required
@can_manage_stock_required
def item_update(request, pk):
    """Update Item Details (Price, Name, Unit etc)"""
    
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        unit = request.POST.get('unit')
        sku = request.POST.get('sku')
        cost_price = request.POST.get('cost_price')
        min_stock = request.POST.get('min_stock')
        description = request.POST.get('description')

        if not name or not cost_price:
            messages.error(request, "Name and Cost Price are required.")
        else:
            try:
                # Check SKU uniqueness (exclude current item)
                if sku and InventoryItem.objects.filter(sku=sku).exclude(id=item.id).exists():
                    messages.error(request, "SKU already assigned to another item.")
                else:
                    item.name = name
                    item.category = get_object_or_404(InventoryCategory, id=category_id) if category_id else None
                    item.unit = unit
                    item.sku = sku
                    item.cost_price = cost_price
                    item.min_stock_level = min_stock or 0
                    item.description = description
                    
                    item.save()
                    messages.success(request, "Item updated successfully.")
                    return redirect('inventory:item_list')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    categories = InventoryCategory.objects.all()
    units = InventoryItem.UNIT_CHOICES 

    return render(request, 'inventory/item_form.html', {
        'item': item, 
        'categories': categories,
        'units': units
    })


# ----------------- DELETE ITEM ----------------- #

@login_required
@can_manage_stock_required
def item_delete(request, pk):
    """Soft Delete (Deactivate) Item"""
    
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        # Hum item ko delete nahi krain gay, sirf deactivate krain gay
        # ta k reports may masla na aye.
        item.is_active = False 
        item.save()
        messages.success(request, f"Item '{item.name}' deactivated successfully.")
    
    return redirect('inventory:item_list')