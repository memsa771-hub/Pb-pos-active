from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from posapp.decorators import can_manage_categories_required
from inventory.models import InventoryCategory

# ----------------- CATEGORY LIST ----------------- #

@login_required
@can_manage_categories_required
def category_list(request):
    """Display list of all inventory categories with search & pagination"""
    
    # Get search query
    search_query = request.GET.get('search', '')

    # Fetch all categories ordered by name
    categories = InventoryCategory.objects.all().order_by('name')

    # Filter if search query exists
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Pagination (12 items per page)
    paginator = Paginator(categories, 12)
    page_number = request.GET.get('page')
    categories_page = paginator.get_page(page_number)

    context = {
        'categories': categories_page,
        'search_query': search_query,
    }

    # Support for AJAX search (if needed later)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'inventory/category_list.html', context)

    return render(request, 'inventory/category_list.html', context)


# ----------------- CREATE CATEGORY ----------------- #

@login_required
@can_manage_categories_required
def category_create(request):
    """Create a new inventory category"""
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        # Validation
        if not name:
            messages.error(request, "Category name is required")
        else:
            try:
                # Check duplicate
                if InventoryCategory.objects.filter(name__iexact=name).exists():
                    messages.error(request, f"Category '{name}' already exists.")
                else:
                    InventoryCategory.objects.create(name=name, description=description)
                    messages.success(request, f'Category "{name}" created successfully.')
                    return redirect('inventory:category_list')
            except Exception as e:
                messages.error(request, f"Error creating category: {str(e)}")

    return render(request, 'inventory/category_form.html')


# ----------------- UPDATE CATEGORY ----------------- #

@login_required
@can_manage_categories_required
def category_update(request, category_id):
    """Edit an existing inventory category"""
    
    category = get_object_or_404(InventoryCategory, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if not name:
            messages.error(request, "Category name is required")
        else:
            try:
                # Check duplicate (exclude self)
                if InventoryCategory.objects.filter(name__iexact=name).exclude(id=category.id).exists():
                    messages.error(request, f"Category '{name}' already exists.")
                else:
                    category.name = name
                    category.description = description
                    category.save()
                    messages.success(request, "Category updated successfully.")
                    return redirect('inventory:category_list')
            except Exception as e:
                messages.error(request, f"Error updating category: {str(e)}")

    return render(request, 'inventory/category_form.html', {'category': category})


# ----------------- DELETE CATEGORY ----------------- #

@login_required
@can_manage_categories_required
def category_delete(request, category_id):
    """Delete a category safely"""
    
    category = get_object_or_404(InventoryCategory, id=category_id)
    
    if request.method == 'POST':
        # Check if items are attached to this category
        # Note: 'items' is the related_name we defined in InventoryItem model
        if category.items.exists(): 
            messages.error(request, f"Cannot delete '{category.name}' because it contains items. Please move items to another category first.")
        else:
            category.delete()
            messages.success(request, "Category deleted successfully.")
    
    return redirect('inventory:category_list')