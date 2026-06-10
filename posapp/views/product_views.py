from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from ..models import PosProduct, PosCategory, OrderItem
from ..forms import ProductForm
from ..decorators import admin_required
import django.db.models.deletion
from django.db import transaction

@login_required
@admin_required
def product_list(request):
    """Display list of all products"""
    # Get search parameters
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    show_archived = request.GET.get('show_archived') == 'on'
    
    # Filter products based on search and category
    products = PosProduct.objects.all().order_by('-created_at')
    
    # Hide archived products by default unless explicitly requested
    if not show_archived:
        products = products.filter(is_archived=False)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(product_code__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Pagination
    paginator = Paginator(products, 10)  # Show 10 products per page
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    categories = PosCategory.objects.all()
    
    context = {
        'products': products_page,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'show_archived': show_archived,
    }
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'posapp/products/product_list.html', context)
    
    return render(request, 'posapp/products/product_list.html', context)

@login_required
@admin_required
def product_detail(request, product_id):
    """Display details of a specific product"""
    product = get_object_or_404(PosProduct, id=product_id)
    context = {'product': product}
    return render(request, 'posapp/products/product_detail.html', context)

@login_required
@admin_required
def product_create(request):
    """Create a new product using Django Form"""
    
    if request.method == 'POST':
        # Form handle karega Validation aur Data Extraction
        form = ProductForm(request.POST)
        
        if form.is_valid():
            try:
                product = form.save() # Forms.py ki logic (clean method) khud stock set kr degi
                messages.success(request, f'Product "{product.name}" created successfully.')
                return redirect('product_detail', product_id=product.id)
            except Exception as e:
                messages.error(request, f"Error creating product: {str(e)}")
        else:
            # Agar validation fail hui to errors dikhao
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm()

    # Dropdown k liye categories
    categories = PosCategory.objects.all()
    
    context = {
        'categories': categories,
        'form': form # Template may form bhejna zaroori ha
    }
    
    return render(request, 'posapp/products/product_form.html', context)

@login_required
@admin_required
def product_edit(request, product_id):
    """Edit an existing product"""
    product = get_object_or_404(PosProduct, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        
        if form.is_valid():
            try:
                updated_prod = form.save()
                
                messages.success(request, f'Product "{updated_prod.name}" updated successfully.')
                return redirect('product_detail', product_id=product.id)
            except Exception as e:
                messages.error(request, f"Error updating product: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm(instance=product)

    categories = PosCategory.objects.all()
    
    context = {
        'categories': categories,
        'form': form,
        'product': product # For back button or other details
    }
    
    return render(request, 'posapp/products/product_form.html', context)

def _product_delete_response(request, success, message, level='success', redirect_name='product_list'):
    """Return JSON for AJAX deletes or redirect with a flash message."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message,
            'level': level,
        })
    if level == 'warning':
        messages.warning(request, message)
    elif level == 'error' or not success:
        messages.error(request, message)
    else:
        messages.success(request, message)
    return redirect(redirect_name)


@login_required
@admin_required
def product_delete(request, product_id):
    """Delete a product"""
    product = get_object_or_404(PosProduct, id=product_id)
    
    if request.method == 'POST':
        # Check if product is in any pending orders
        pending_order_items = OrderItem.objects.filter(
            product=product,
            order__order_status='Pending'
        )
        
        if pending_order_items.exists():
            # If product is in pending orders, archive it instead of deleting
            product.is_available = False
            product.is_archived = True
            product.save()
            
            message = (
                f'This product cannot be deleted because it is referenced in '
                f'{pending_order_items.count()} pending order(s). It has been archived instead.'
            )
            return _product_delete_response(
                request,
                success=True,
                message=message,
                level='warning',
            )
        
        try:
            # Find completed or cancelled order items
            completed_cancelled_items = OrderItem.objects.filter(
                product=product,
                order__order_status__in=['Completed', 'Cancelled']
            )
            
            item_count = completed_cancelled_items.count()
            
            with transaction.atomic():
                # First, delete the order items from completed/cancelled orders
                completed_cancelled_items.delete()
                
                # Now try to delete the product
                product_name = product.name
                product.delete()
                
            message = (
                f'Product "{product_name}" and its {item_count} references in '
                f'completed/cancelled orders deleted successfully.'
            )
            return _product_delete_response(
                request,
                success=True,
                message=message,
                level='success',
            )
            
        except Exception as e:
            # If any exception occurs
            product.is_available = False
            product.is_archived = True
            product.save()
            
            message = (
                f'This product could not be deleted due to an error: {str(e)}. '
                f'It has been archived instead.'
            )
            return _product_delete_response(
                request,
                success=True,
                message=message,
                level='warning',
            )
    
    return redirect('product_detail', product_id=product_id)

@login_required
@admin_required
def product_archive(request, product_id):
    """Archive or unarchive a product"""
    product = get_object_or_404(PosProduct, id=product_id)
    
    if request.method == 'POST':
        # Toggle archived status
        if product.is_archived:
            product.is_archived = False
            action_msg = "unarchived"
        else:
            product.is_archived = True
            # When archiving, also mark as unavailable
            product.is_available = False
            action_msg = "archived"
            
        product.save()
        messages.success(request, f'Product "{product.name}" {action_msg} successfully.')
        
    return redirect('product_detail', product_id=product_id)

@login_required
def check_product_stock(request, product_id):
    """API endpoint to check if a product has sufficient stock."""
    try:
        product = get_object_or_404(PosProduct, id=product_id)
        requested_quantity = int(request.GET.get('quantity', 1))
        
        # For running items OR Recipe based items, always return true (Infinite Stock)
        # 🔥 UPDATE: Is me recipe logic bhi daal di hai
        if product.running_item or product.is_recipe_based:
            return JsonResponse({
                'success': True,
                'product_id': product_id,
                'product_name': product.name,
                'running_item': True,
                'available_stock': float('inf'),
                'requested_quantity': requested_quantity,
                'available': True,
                'message': 'This item has unlimited/managed stock.'
            })
        
        # For regular items, check actual stock
        available_stock = product.stock_quantity
        is_available = product.is_available and not product.is_archived
        has_stock = available_stock >= requested_quantity
        
        return JsonResponse({
            'success': True,
            'product_id': product_id,
            'product_name': product.name,
            'running_item': False,
            'available_stock': available_stock,
            'requested_quantity': requested_quantity,
            'available': is_available and has_stock,
            'message': 'Stock check completed successfully.'
        })
    except PosProduct.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid quantity specified.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error checking stock: {str(e)}'}, status=500)

@login_required
def get_products_stock(request):
    """API endpoint to get stock information for all products."""
    try:
        # Get only relevant fields
        products = PosProduct.objects.all().values('id', 'name', 'stock_quantity', 'running_item', 'is_recipe_based', 'is_available', 'is_archived')
        
        product_data = []
        for product in products:
            product_data.append({
                'id': product['id'],
                'name': product['name'],
                'stock_quantity': product['stock_quantity'],
                'running_item': product['running_item'] or product['is_recipe_based'], # Treat recipe items as running for POS UI
                'is_available': product['is_available'] and not product['is_archived']
            })
        
        return JsonResponse({'success': True, 'products': product_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error fetching product stocks: {str(e)}'}, status=500)