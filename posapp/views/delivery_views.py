from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.utils import timezone

from ..models import DeliveryPerson, Order
from ..forms import DeliveryPersonForm
from ..decorators import management_required
from ..views.user_views import is_admin

def is_branch_manager(user):
    """Check if user is a branch manager"""
    if not user.is_authenticated:
        return False
    return hasattr(user, 'profile') and user.profile and user.profile.role and user.profile.role.name == 'Branch Manager'

@login_required
def delivery_person_list(request):
    """List all delivery persons - Admin and Branch Manager can view"""
    # Allow admin and branch manager to view delivery persons
    if not (is_admin(request.user) or is_branch_manager(request.user)):
        messages.error(request, "You don't have permission to view delivery persons.")
        return redirect('dashboard')
    """List all delivery persons"""
    search_query = request.GET.get('search', '')
    
    # Filter delivery persons based on search query
    delivery_persons = DeliveryPerson.objects.all().order_by('name')
    
    if search_query:
        delivery_persons = delivery_persons.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Paginate results
    paginator = Paginator(delivery_persons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'title': 'Delivery Persons',
        'is_admin': is_admin(request.user),
        'is_branch_manager': is_branch_manager(request.user)
    }
    
    return render(request, 'posapp/delivery/delivery_person_list.html', context)

@login_required
def delivery_person_create(request):
    """Create a new delivery person - Only Admin can create"""
    # Only allow admin users to create delivery persons
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to create delivery persons.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = DeliveryPersonForm(request.POST)
        if form.is_valid():
            delivery_person = form.save()
            messages.success(request, f'Delivery person "{delivery_person.name}" created successfully.')
            return redirect('delivery_person_list')
    else:
        form = DeliveryPersonForm()
    
    context = {
        'form': form,
        'title': 'Add Delivery Person',
        'form_action': 'Create'
    }
    
    return render(request, 'posapp/delivery/delivery_person_form.html', context)

@login_required
def delivery_person_edit(request, person_id):
    """Edit a delivery person - Only Admin can edit"""
    # Only allow admin users to edit delivery persons
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to edit delivery persons.")
        return redirect('dashboard')
    delivery_person = get_object_or_404(DeliveryPerson, id=person_id)
    
    if request.method == 'POST':
        form = DeliveryPersonForm(request.POST, instance=delivery_person)
        if form.is_valid():
            delivery_person = form.save()
            messages.success(request, f'Delivery person "{delivery_person.name}" updated successfully.')
            return redirect('delivery_person_list')
    else:
        form = DeliveryPersonForm(instance=delivery_person)
    
    context = {
        'form': form,
        'delivery_person': delivery_person,
        'title': 'Edit Delivery Person',
        'form_action': 'Update'
    }
    
    return render(request, 'posapp/delivery/delivery_person_form.html', context)

@login_required
def delivery_person_delete(request, person_id):
    """Delete a delivery person - Only Admin can delete"""
    # Only allow admin users to delete delivery persons
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to delete delivery persons.")
        return redirect('dashboard')
    delivery_person = get_object_or_404(DeliveryPerson, id=person_id)
    
    # Check if delivery person has any orders
    order_count = Order.objects.filter(delivery_person=delivery_person).count()
    
    if request.method == 'POST':
        if order_count > 0:
            messages.error(request, f'Cannot delete {delivery_person.name}. This delivery person has {order_count} orders associated.')
            return redirect('delivery_person_list')
        
        name = delivery_person.name
        delivery_person.delete()
        messages.success(request, f'Delivery person "{name}" deleted successfully.')
        return redirect('delivery_person_list')
    
    context = {
        'delivery_person': delivery_person,
        'order_count': order_count,
        'title': 'Delete Delivery Person'
    }
    
    return render(request, 'posapp/delivery/delivery_person_confirm_delete.html', context)

@login_required
def delivery_person_detail(request, person_id):
    """Show delivery person details and their orders - Admin and Branch Manager can view"""
    # Allow admin and branch manager to view delivery details
    if not (is_admin(request.user) or is_branch_manager(request.user)):
        messages.error(request, "You don't have permission to view delivery details.")
        return redirect('dashboard')
    delivery_person = get_object_or_404(DeliveryPerson, id=person_id)
    
    # Get date range for filtering orders
    today = timezone.now().date()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
    
    # Get orders for this delivery person
    orders_filter = {'delivery_person': delivery_person}
    
    # Only apply date filters if dates are provided
    if start_date:
        orders_filter['created_at__date__gte'] = start_date
    if end_date:
        orders_filter['created_at__date__lte'] = end_date
    
    orders = Order.objects.filter(**orders_filter).order_by('-created_at')
    
    # Calculate statistics
    total_orders = orders.count()
    pending_orders = orders.filter(order_status='Pending').count()
    completed_orders = orders.filter(order_status='Completed').count()
    total_amount = orders.filter(order_status='Completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    context = {
        'delivery_person': delivery_person,
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_amount': total_amount,
        'start_date': start_date or '',
        'end_date': end_date or '',
        'title': f'Delivery Person: {delivery_person.name}',
        'is_admin': is_admin(request.user),
        'is_branch_manager': is_branch_manager(request.user)
    }
    
    return render(request, 'posapp/delivery/delivery_person_detail.html', context)

@login_required
def delivery_report(request):
    """Generate delivery report for a specific date range and delivery person - Admin and Branch Manager can view"""
    # Allow admin and branch manager to view delivery reports
    if not (is_admin(request.user) or is_branch_manager(request.user)):
        messages.error(request, "You don't have permission to view delivery reports.")
        return redirect('dashboard')
    delivery_person_id = request.GET.get('delivery_person')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get all active delivery persons for the dropdown
    delivery_persons = DeliveryPerson.objects.filter(is_active=True).order_by('name')
    
    orders = None
    delivery_person = None
    
    if delivery_person_id:
        try:
            delivery_person = DeliveryPerson.objects.get(id=delivery_person_id)
            
            # Build order filter
            orders_filter = {'delivery_person': delivery_person}
            
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                orders_filter['created_at__date__gte'] = start_date_obj
                
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                orders_filter['created_at__date__lte'] = end_date_obj
            
            # Get orders for the delivery person (with optional date range)
            orders = Order.objects.filter(**orders_filter).order_by('-created_at')
            
        except (DeliveryPerson.DoesNotExist, ValueError):
            messages.error(request, 'Invalid delivery person or date range.')
    
    context = {
        'delivery_persons': delivery_persons,
        'selected_person_id': delivery_person_id,
        'delivery_person': delivery_person,
        'orders': orders,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Delivery Report'
    }
    
    return render(request, 'posapp/reports/delivery_report.html', context) 