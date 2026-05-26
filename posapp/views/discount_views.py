from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import Discount, Order
from ..forms import DiscountForm
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

@login_required
def discount_list(request):
    """Display list of all discounts"""
    # Get search parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Filter discounts based on search and status
    discounts = Discount.objects.all().order_by('-created_at')
    
    if search_query:
        discounts = discounts.filter(
            Q(name__icontains=search_query) | 
            Q(code__icontains=search_query)
        )
    
    if status_filter == 'active':
        discounts = discounts.filter(is_active=True)
    elif status_filter == 'inactive':
        discounts = discounts.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(discounts, 10)  # Show 10 discounts per page
    page_number = request.GET.get('page')
    discounts_page = paginator.get_page(page_number)
    
    context = {
        'discounts': discounts_page,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'posapp/discounts/discount_list.html', context)
    
    return render(request, 'posapp/discounts/discount_list.html', context)

@login_required
def discount_detail(request, discount_id):
    """Display details of a specific discount"""
    discount = get_object_or_404(Discount, id=discount_id)
    
    # Get orders that use this discount using the related name from Order.discount foreign key
    orders = Order.objects.filter(discount=discount).order_by('-created_at')[:10]
    
    context = {
        'discount': discount,
        'orders': orders,
    }
    return render(request, 'posapp/discounts/discount_detail.html', context)

@login_required
def discount_create(request):
    """Create a new discount"""
    if request.method == 'POST':
        form = DiscountForm(request.POST)
        if form.is_valid():
            discount = form.save()
            messages.success(request, f'Discount "{discount.name}" created successfully.')
            return redirect('discount_detail', discount_id=discount.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = DiscountForm()
    
    context = {
        'discount': {},  # Empty dict for template rendering of non-form fields
        'form': form,
        'discount_types': Discount.DISCOUNT_TYPE_CHOICES,
    }
    
    return render(request, 'posapp/discounts/discount_form.html', context)

@login_required
def discount_edit(request, discount_id):
    """Edit an existing discount"""
    discount = get_object_or_404(Discount, id=discount_id)
    
    if request.method == 'POST':
        form = DiscountForm(request.POST, instance=discount)
        if form.is_valid():
            discount = form.save()
            messages.success(request, f'Discount "{discount.name}" updated successfully.')
            return redirect('discount_detail', discount_id=discount.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = DiscountForm(instance=discount)
    
    context = {
        'discount': discount,
        'form': form,
        'discount_types': Discount.DISCOUNT_TYPE_CHOICES,
    }
    
    return render(request, 'posapp/discounts/discount_form.html', context)

@login_required
def discount_delete(request, discount_id):
    """Delete a discount"""
    discount = get_object_or_404(Discount, id=discount_id)
    
    if request.method == 'POST':
        # Check if discount has related orders
        if Order.objects.filter(discount=discount).exists():
            messages.error(request, f'Cannot delete discount "{discount.name}" because it is used in orders.')
            return redirect('discount_detail', discount_id=discount.id)
        
        discount_name = discount.name
        discount.delete()
        messages.success(request, f'Discount "{discount_name}" deleted successfully.')
        return redirect('discount_list')
    
    # If not POST, redirect to the discount detail page
    return redirect('discount_detail', discount_id=discount_id)

@login_required
@csrf_exempt
@require_POST
def validate_discount_code(request):
    """API endpoint to validate a discount code"""
    try:
        data = json.loads(request.body)
        code = data.get('code')
        
        if not code:
            return JsonResponse({"valid": False, "message": "Discount code is required"}, status=400)
        
        try:
            discount = Discount.objects.get(code=code, is_active=True)
            
            # Check if the discount is valid (within date range)
            today = timezone.now().date()
            
            if (discount.start_date and discount.start_date > today) or \
               (discount.end_date and discount.end_date < today):
                return JsonResponse(
                    {"valid": False, "message": "This discount code is not valid at this time"}
                )
            
            # Return discount details
            discount_data = {
                "id": discount.id,
                "name": discount.name,
                "code": discount.code,
                "type": discount.type,
                "value": float(discount.value),
                "start_date": discount.start_date.isoformat() if discount.start_date else None,
                "end_date": discount.end_date.isoformat() if discount.end_date else None
            }
            
            return JsonResponse({"valid": True, "discount": discount_data})
        except Discount.DoesNotExist:
            return JsonResponse({"valid": False, "message": "Invalid discount code"})
    except json.JSONDecodeError:
        return JsonResponse({"valid": False, "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"valid": False, "message": str(e)}, status=500) 