from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import PosCategory
from ..decorators import admin_required

@login_required
@admin_required
def category_list(request):
    """Display list of all categories"""
    # Get search parameters
    search_query = request.GET.get('search', '')
    
    # Filter categories based on search
    categories = PosCategory.objects.all().order_by('name')
    
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(categories, 10)  # Show 10 categories per page
    page_number = request.GET.get('page')
    categories_page = paginator.get_page(page_number)
    
    context = {
        'categories': categories_page,
        'search_query': search_query,
    }
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'posapp/categories/category_list.html', context)
    
    return render(request, 'posapp/categories/category_list.html', context)

@login_required
@admin_required
def category_detail(request, category_id):
    """Display details of a specific category"""
    category = get_object_or_404(PosCategory, id=category_id)
    products = category.products.all()
    
    # Pagination for products
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'products': products_page
    }
    return render(request, 'posapp/categories/category_detail.html', context)

@login_required
@admin_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        # Get form data from request.POST
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        # Basic validation
        errors = {}
        if not name:
            errors['name'] = "Name is required"
        
        # If no errors, create category
        if not errors:
            try:
                # Create category
                category = PosCategory.objects.create(
                    name=name,
                    description=description
                )
                
                messages.success(request, f'Category "{category.name}" created successfully.')
                return redirect('category_detail', category_id=category.id)
            except Exception as e:
                messages.error(request, f"Error creating category: {str(e)}")
        else:
            for field, error in errors.items():
                messages.error(request, error)
    
    # Default empty context for GET request
    context = {
        'category': {
            'name': '',
            'description': ''
        }
    }
    
    return render(request, 'posapp/categories/category_form.html', context)

@login_required
@admin_required
def category_edit(request, category_id):
    """Edit an existing category"""
    category = get_object_or_404(PosCategory, id=category_id)
    
    if request.method == 'POST':
        # Get form data from request.POST
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        # Basic validation
        errors = {}
        if not name:
            errors['name'] = "Name is required"
        
        # If no errors, update category
        if not errors:
            try:
                # Update category fields
                category.name = name
                category.description = description
                
                category.save()
                messages.success(request, f'Category "{category.name}" updated successfully.')
                return redirect('category_detail', category_id=category.id)
            except Exception as e:
                messages.error(request, f"Error updating category: {str(e)}")
        else:
            for field, error in errors.items():
                messages.error(request, error)
    
    # Context for both GET and error cases in POST
    context = {
        'category': category
    }
    
    return render(request, 'posapp/categories/category_form.html', context)

@login_required
@admin_required
def category_delete(request, category_id):
    """Delete a category"""
    category = get_object_or_404(PosCategory, id=category_id)
    
    if request.method == 'POST':
        # Check if category has related products
        if category.product_set.exists():
            messages.error(request, f'Cannot delete category "{category.name}" because it has related products.')
            return redirect('category_detail', category_id=category.id)
        
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully.')
        return redirect('category_list')
    
    # If not POST, redirect to the category detail page
    return redirect('category_detail', category_id=category_id) 