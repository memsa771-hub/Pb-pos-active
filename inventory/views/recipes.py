from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from posapp.decorators import can_manage_stock_required
from posapp.models import PosProduct
from inventory.models import Recipe, InventoryItem

# ----------------- RECIPE LIST (Select Product) ----------------- #

@login_required
@can_manage_stock_required
def recipe_list(request):
    """List all Recipe-Based Products to manage their ingredients"""
    products = PosProduct.objects.filter(
        is_recipe_based=True, 
        is_archived=False
    ).order_by('name')

    return render(request, 'inventory/recipe_list.html', {'products': products})

# ----------------- MANAGE RECIPE (Add/Remove Ingredients) ----------------- #

@login_required
@can_manage_stock_required
def manage_recipe(request, product_id):
    """Add or Remove ingredients for a specific product"""
    
    product = get_object_or_404(PosProduct, id=product_id)
    current_recipe = Recipe.objects.filter(pos_product=product)
    
    # Available raw items to add
    raw_items = InventoryItem.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        # Add New Ingredient Logic
        if 'add_ingredient' in request.POST:
            item_id = request.POST.get('inventory_item')
            qty = request.POST.get('quantity')
            unit = request.POST.get('unit_used')
            
            if item_id and qty:
                # Check if already exists
                if Recipe.objects.filter(pos_product=product, ingredient_id=item_id).exists():
                    messages.error(request, "Ingredient already exists in recipe.")
                else:
                    Recipe.objects.create(
                        pos_product=product,
                        ingredient_id=item_id,
                        quantity_required=qty
                    )
                    messages.success(request, "Ingredient added.")
            else:
                messages.error(request, "Please select item and quantity.")
                
        # Remove Ingredient Logic
        elif 'delete_ingredient' in request.POST:
            recipe_id = request.POST.get('recipe_id')
            Recipe.objects.filter(id=recipe_id).delete()
            messages.success(request, "Ingredient removed.")
            
        return redirect('inventory:manage_recipe', product_id=product.id)

    return render(request, 'inventory/recipe_form.html', {
        'product': product,
        'recipe_items': current_recipe,
        'raw_items': raw_items
    })