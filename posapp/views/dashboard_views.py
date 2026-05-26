from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Value, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import PosCategory, PosProduct, Order, UserProfile, Setting, BusinessSettings, EndDay, BillAdjustment, AdvanceAdjustment, OrderItem

__all__ = ['is_admin', 'is_branch_manager', 'can_access_management', 'dashboard', 'pos', 'end_day', 'sales_summary']

# Helper function to check if user is admin
def is_admin(user):
    """Check if a user has admin privileges"""
    # Superusers always have admin privileges
    if user.is_superuser:
        return True
    
    # Check for user profile and role
    try:
        # Try to get the user's profile and check if their role is 'Admin'
        profile = UserProfile.objects.get(user=user)
        if profile.role and profile.role.name == 'Admin':
            return True
    except (UserProfile.DoesNotExist, AttributeError):
        # If there's no profile or role, they're not an admin
        pass
    
    return False

# Helper function to check if user is a branch manager
def is_branch_manager(user):
    """Check if a user has branch manager privileges"""
    # Check for user profile and role
    try:
        # Try to get the user's profile and check if their role is 'Branch Manager'
        profile = UserProfile.objects.get(user=user)
        if profile.role and profile.role.name == 'Branch Manager':
            return True
    except (UserProfile.DoesNotExist, AttributeError):
        # If there's no profile or role, they're not a branch manager
        pass
    
    return False

# Helper function to check if user can access management features (admin or branch manager)
def can_access_management(user):
    """Check if a user can access management features (admin or branch manager)"""
    return is_admin(user) or is_branch_manager(user)

@login_required
def dashboard(request):
    # Dashboard is admin-only
    if not is_admin(request.user):
        return redirect('pos')
    
    # Check if user is admin or branch manager
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role.name == 'Admin')
    is_branch_manager = hasattr(request.user, 'profile') and request.user.profile.role.name == 'Branch Manager'
    
    # Get the last end day timestamp
    last_end_day = EndDay.get_last_end_day()
    last_end_day_time = last_end_day.end_date if last_end_day else None
    
    # Check if end day was just completed
    end_day_completed = request.session.get('end_day_completed', False)
    end_day_timestamp = request.session.get('end_day_timestamp', '')
    sales_receipt_url = request.session.get('sales_receipt_url', '')
    
    # Clear the session variables after reading them
    if end_day_completed:
        request.session['end_day_completed'] = False
        if 'sales_receipt_url' in request.session:
            del request.session['sales_receipt_url']
        request.session.modified = True
    
    # Fetch summary data
    total_products = PosProduct.objects.count()
    total_categories = PosCategory.objects.count()
    total_users = User.objects.count()
    
    # Filter orders based on role and last end day
    if is_admin:
        # Admin sees all orders
        all_orders = Order.objects.all()
        active_orders = Order.objects.filter(order_status='Pending').count()
        total_revenue = Order.objects.exclude(order_status='Cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
        recent_orders = Order.objects.all().order_by('-created_at')[:5]
    else:
        # Branch manager sees only orders since last end day
        if last_end_day_time:
            all_orders = Order.objects.filter(created_at__gte=last_end_day_time)
            active_orders = Order.objects.filter(
                created_at__gte=last_end_day_time,
                order_status='Pending'
            ).count()
            total_revenue = Order.objects.filter(
                created_at__gte=last_end_day_time
            ).exclude(order_status='Cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
            recent_orders = Order.objects.filter(
                created_at__gte=last_end_day_time
            ).order_by('-created_at')[:5]
        else:
            # If no end day record exists, show all
            all_orders = Order.objects.all()
            active_orders = Order.objects.filter(order_status='Pending').count()
            total_revenue = Order.objects.exclude(order_status='Cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
            recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    # Count total orders
    total_orders = all_orders.count()
    
    # Recent products (latest 5)
    recent_products = PosProduct.objects.all().order_by('-created_at')[:5]
    
    # Top selling products - since sold_count doesn't exist, 
    # we'll just use the most expensive products instead
    top_products = PosProduct.objects.all().order_by('-price')[:5]
    
    # All categories
    categories = PosCategory.objects.all()
    
    # All users with their roles
    users = User.objects.select_related('profile__role').all()
    
    # Get business information
    business_settings = {}
    for setting in Setting.objects.filter(setting_key__in=['business_name', 'business_address', 'business_phone', 'tax_rate']):
        business_settings[setting.setting_key] = setting.setting_value
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_users': total_users,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'total_revenue': total_revenue,
        'recent_products': recent_products,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'categories': categories,
        'users': users,
        'business_settings': business_settings,
        'last_end_day': last_end_day,
        'is_admin': is_admin,
        'end_day_completed': end_day_completed,
        'end_day_timestamp': end_day_timestamp,
        'sales_receipt_url': sales_receipt_url,
    }
    
    return render(request, 'posapp/dashboard.html', context)

@login_required
def pos(request):
    # Fetch only available products and all categories for the POS interface
    # Exclude archived products
    products = PosProduct.objects.filter(is_available=True, is_archived=False)
    categories = PosCategory.objects.all()
    
    # Get delivery persons for the dropdown
    from ..models import DeliveryPerson
    delivery_persons = DeliveryPerson.objects.filter(is_active=True).order_by('name')
    
    # Get tax rates from business settings
    from ..views.settings_views import get_or_create_settings
    
    business_settings = get_or_create_settings([
        'tax_rate_card', 'tax_rate_cash', 'default_service_charge'
    ])
    
    # Get tax rates with fallback values
    card_tax_rate = float(Decimal(business_settings['tax_rate_card'].setting_value or '5.0'))
    standard_tax_rate = float(Decimal(business_settings['tax_rate_cash'].setting_value or '15.0'))
    default_service_charge = float(Decimal(business_settings['default_service_charge'].setting_value or '5.0'))
    
    context = {
        'products': products,
        'categories': categories,
        'delivery_persons': delivery_persons,
        'card_tax_rate': card_tax_rate,
        'standard_tax_rate': standard_tax_rate,
        'default_service_charge': default_service_charge,
    }
    
    return render(request, 'posapp/pos.html', context)

@login_required
def end_day(request):
    """End day functionality for admin and branch managers"""
    # Check if user has admin or branch manager access
    if not can_access_management(request.user):
        messages.error(request, "You don't have permission to access this feature.")
        return redirect('pos')
    
    # Get the last end day timestamp or use a default (30 days ago)
    last_end_day = EndDay.get_last_end_day()
    if last_end_day:
        start_date = last_end_day.end_date
    else:
        # Use exact time 30 days ago
        start_date = timezone.now() - timedelta(days=30)
    
    # Use current exact time
    end_date = timezone.now()
    
    # Check for any pending orders since the last end day
    pending_orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
        order_status='Pending'
    ).count()
    
    # If there are pending orders, don't allow end day
    if pending_orders > 0:
        messages.error(request, f"Cannot end day: There are {pending_orders} pending orders that need to be completed or cancelled first.")
        return redirect('order_list')
    
    # Check if this is a POST request (user confirmed end day)
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        
        # IMPORTANT: Calculate business day range BEFORE creating new EndDay record
        # This ensures we get the ACTUAL business period being ended
        business_start_date = start_date  # From last end day
        business_end_date = timezone.now()  # Until now
        
        # Create new EndDay record with the exact end time we calculated
        end_day = EndDay.objects.create(
            ended_by=request.user,
            notes=notes
        )
        
        # IMPORTANT: Update the end_date to match our business_end_date
        # This ensures consistency between what we're reporting and what's stored
        end_day.end_date = business_end_date
        end_day.save()
        
        # Format dates for sales receipt URL using the EXACT same dates
        start_date_str = business_start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = business_end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Add success message with notification
        messages.success(request, f"Day ended successfully at {timezone.localtime().strftime('%Y-%m-%d %H:%M')}.")
        
        # Store end day data in session for dashboard display
        request.session['end_day_completed'] = True
        request.session['end_day_timestamp'] = timezone.localtime().strftime('%Y-%m-%d %H:%M')
        
        # Redirect to sales receipt first with a redirect_to parameter to go to dashboard after
        return redirect(f"/reports/sales/receipt/?start_date={start_date_str}&end_date={end_date_str}&redirect_to=dashboard")
    
    # Get report data with exact timestamp filtering for completed/cancelled orders only
    orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    # Calculate order totals
    order_total = orders.exclude(order_status='Cancelled').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Get all adjustments since the last end day with exact timestamp filtering
    bill_adjustments = BillAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    # Calculate adjustments total
    adjustment_total = bill_adjustments.aggregate(Sum('price'))['price__sum'] or 0
    
    # Get all sold products since the last end day with exact timestamp filtering
    products_sold = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__created_at__lte=end_date,
        order__order_status='Completed'  # Only include completed orders
    ).values(
        'product__name', 
        'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum('total_price')
    ).order_by('-total_quantity')
    
    # Format dates for URL parameters - preserve time part as well
    start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
    
    context = {
        'last_end_day': last_end_day,
        'start_date': start_date,
        'end_date': end_date,
        'orders': orders,
        'order_total': order_total,
        'bill_adjustments': bill_adjustments,
        'adjustment_total': adjustment_total,
        'products_sold': products_sold,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'pending_orders': pending_orders,
    }
    
    return render(request, 'posapp/end_day.html', context)

@login_required
def sales_summary(request, end_day_id=None):
    """Generate a sales summary report for the end of day"""
    # Check if user has admin or branch manager access
    if not can_access_management(request.user):
        messages.error(request, "You don't have permission to access this feature.")
        return redirect('pos')
    
    # Get the end day record if provided
    end_day = None
    if end_day_id:
        try:
            end_day = EndDay.objects.get(id=end_day_id)
        except EndDay.DoesNotExist:
            messages.error(request, "End day record not found.")
            return redirect('end_day')
    
    # If we have an end_day_id, get the end date and previous end date for the redirect
    if end_day:
        prev_end_day = EndDay.objects.filter(end_date__lt=end_day.end_date).order_by('-end_date').first()
        
        if prev_end_day:
            start_date = prev_end_day.end_date
        else:
            # If no previous end day, use the start of day for end_day
            start_date = end_day.end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_date = end_day.end_date
    else:
        # If no end day provided, use the last end day
        last_end_day = EndDay.get_last_end_day()
        if last_end_day:
            # Get the previous end day
            prev_end_day = EndDay.objects.filter(end_date__lt=last_end_day.end_date).order_by('-end_date').first()
            
            if prev_end_day:
                start_date = prev_end_day.end_date
            else:
                # If no previous end day, use the start of day
                start_date = last_end_day.end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            end_date = last_end_day.end_date
        else:
            # If no end day records exist, use today
            start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = timezone.now()
    
    # Get all completed orders in the date range
    completed_orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
        order_status='Completed'
    )
    

    
    # Calculate revenue breakdown components
    revenue_breakdown = completed_orders.aggregate(
        total_amount=Coalesce(Sum('total_amount'), Decimal('0.00')),
        sales_revenue=Coalesce(Sum('subtotal'), Decimal('0.00')),
        service_charge_total=Coalesce(Sum('service_charge_amount'), Decimal('0.00'))
    )
    
    # Extract individual components
    total_sales = revenue_breakdown['total_amount']
    sales_revenue = revenue_breakdown['sales_revenue']
    total_service_charge = revenue_breakdown['service_charge_total']
    
    # Calculate the total paid amount
    total_paid = completed_orders.filter(
        payment_status='Paid'
    ).aggregate(
        total=Coalesce(Sum('total_amount'), Decimal('0.00'))
    )['total']
    
    # Calculate the total pending amount
    total_pending = completed_orders.filter(
        payment_status='Pending'
    ).aggregate(
        total=Coalesce(Sum('total_amount'), Decimal('0.00'))
    )['total']
    
    # Calculate order type breakdown
    takeaway_orders = completed_orders.filter(order_type='Takeaway')
    takeaway_stats = takeaway_orders.aggregate(
        count=Count('id'),
        total_amount=Coalesce(Sum('total_amount'), Decimal('0.00'))
    )
    
    dinein_orders = completed_orders.filter(order_type='Dine In')
    dinein_stats = dinein_orders.aggregate(
        count=Count('id'),
        total_amount=Coalesce(Sum('total_amount'), Decimal('0.00'))
    )
    
    delivery_orders = completed_orders.filter(order_type='Delivery')
    delivery_stats = delivery_orders.aggregate(
        count=Count('id'),
        total_amount=Coalesce(Sum('total_amount'), Decimal('0.00'))
    )
    
    # Calculate delivery person breakdown
    delivery_person_stats = delivery_orders.values('delivery_person__name').annotate(
        order_count=Count('id'),
        total_amount=Sum('total_amount')
    ).order_by('-total_amount')
    
    # Handle null delivery person (orders without assigned delivery person)
    delivery_person_stats = list(delivery_person_stats)
    for stat in delivery_person_stats:
        if stat['delivery_person__name'] is None:
            stat['delivery_person__name'] = 'Unassigned'
    
    # Get all bill adjustments in the date range
    bill_adjustments = BillAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # Calculate the total bill adjustments
    total_bill_adjustments = bill_adjustments.aggregate(
        total=Coalesce(Sum('price'), Decimal('0.00'))
    )['total']
    
    # Get all advance adjustments in the date range
    advance_adjustments = AdvanceAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    # Calculate the total advance adjustments
    total_advance_adjustments = advance_adjustments.aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'))
    )['total']
    
    # Calculate the total adjustments
    total_adjustments = total_bill_adjustments + total_advance_adjustments
    
    # Calculate total discounts given in completed orders
    total_discounts = completed_orders.aggregate(
        total=Coalesce(Sum('discount_amount'), Decimal('0.00'))
    )['total']
    
    # Calculate total delivery charges from completed orders
    total_delivery_charges = completed_orders.aggregate(
        total=Coalesce(Sum('delivery_charges'), Decimal('0.00'))
    )['total']
    
    # Calculate the net revenue
    net_revenue = total_sales - total_service_charge - total_discounts - total_adjustments - total_delivery_charges
    
    # Calculate total deductions for detailed breakdown
    total_deductions = total_service_charge + total_discounts + total_adjustments + total_delivery_charges
    
    # Determine if there's a shortage
    is_shortage = net_revenue < 0
    shortage_amount = abs(net_revenue) if is_shortage else Decimal('0.00')
    
    # Get products sold in the date range
    products_sold = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__created_at__lte=end_date,
        order__order_status='Completed'
    ).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum('total_price')
    ).order_by('-total_quantity')
    
    # Get business settings
    try:
        from ..views.settings_views import get_or_create_settings
        business_settings = get_or_create_settings([
            'business_name', 'business_address', 'business_phone', 
            'business_email', 'currency_symbol'
        ])
        
        currency_symbol = business_settings['currency_symbol'].setting_value or 'Rs.'
        business_name = business_settings['business_name'].setting_value or 'POS System'
        business_address = business_settings['business_address'].setting_value or ''
        business_phone = business_settings['business_phone'].setting_value or ''
    except Exception:
        currency_symbol = 'Rs.'
        business_name = 'POS System'
        business_address = ''
        business_phone = ''
    
    # Prepare context data
    context = {
        'completed_orders': completed_orders,
        'total_sales': total_sales,
        'sales_revenue': sales_revenue,
        'total_service_charge': total_service_charge,
        'total_delivery_charges': total_delivery_charges,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'bill_adjustments': bill_adjustments,
        'total_bill_adjustments': total_bill_adjustments,
        'advance_adjustments': advance_adjustments,
        'total_advance_adjustments': total_advance_adjustments,
        'total_adjustments': total_adjustments,
        'total_discounts': total_discounts,
        'total_deductions': total_deductions,
        'net_revenue': net_revenue,
        'is_shortage': is_shortage,
        'shortage_amount': shortage_amount,
        'products_sold': products_sold,
        'start_date': start_date,
        'end_date': end_date,
        'end_day': end_day,  # Add end_day to context
        'currency_symbol': currency_symbol,
        'business_name': business_name,
        'business_address': business_address,
        'business_phone': business_phone,
        # Order type breakdown
        'takeaway_stats': takeaway_stats,
        'dinein_stats': dinein_stats,
        'delivery_stats': delivery_stats,
        'delivery_person_stats': delivery_person_stats,
    }
    
    return render(request, 'posapp/sales_summary.html', context) 