from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db.models import Sum, F, DecimalField
from django.utils import timezone
from datetime import timedelta
from posapp.decorators import can_view_stock_required
from inventory.models import InventoryItem, Purchase, StockAdjustment

@never_cache
@login_required
@can_view_stock_required
def dashboard(request):
    """
    Inventory Main Dashboard.
    @never_cache ensures browsers don't show old versions of this page.
    """
    
    # 1. Live Stock Value & Count (Directly from InventoryItem Table)
    # Yeh table har purchase/adjustment k baad update hota hai, tu ye hamesha latest hoga.
    items_query = InventoryItem.objects.filter(is_active=True)
    
    # Calculate Total Value (Stock * Cost)
    stock_metric = items_query.aggregate(
        total_val=Sum(F('cost_price') * F('current_stock'), output_field=DecimalField())
    )
    stock_value = stock_metric['total_val'] or 0
    total_items_count = items_query.count()
    
    # 2. Low Stock Calculation (Real-time loop)
    # Hum DB level par filter kar rahy hain ta k python ko mehnat na karni pary
    low_stock_items = [
        item for item in items_query 
        if item.current_stock <= item.min_stock_level
    ]
    
    # 3. Monthly Stats (Date Calculation)
    today = timezone.now()
    first_day_month = today.replace(day=1, hour=0, minute=0, second=0)
    
    # Monthly Purchase Total
    monthly_purchases = Purchase.objects.filter(
        purchase_date__gte=first_day_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Monthly Wastage Calculation
    # Hum wastage ki value calculate kar rahy hain (Qty * Item Cost)
    wastage_adjustments = StockAdjustment.objects.filter(
        date__gte=first_day_month,
        adjustment_type__in=['Wastage', 'Theft'],
        action='REMOVE'
    ).select_related('inventory_item') # Optimization
    
    monthly_wastage_value = sum(
        adj.quantity * adj.inventory_item.cost_price 
        for adj in wastage_adjustments
    )

    # 4. Recent Logs (Sirf dikhanay k liye)
    recent_purchases = Purchase.objects.order_by('-created_at')[:5]
    recent_adjustments = StockAdjustment.objects.order_by('-date')[:5]

    context = {
        'total_stock_value': stock_value,
        'total_items': total_items_count,
        'low_stock_count': len(low_stock_items),
        'low_stock_items': low_stock_items,
        'monthly_purchase_total': monthly_purchases,
        'monthly_wastage_value': monthly_wastage_value,
        'recent_purchases': recent_purchases,
        'recent_adjustments': recent_adjustments,
    }
    
    return render(request, 'inventory/dashboard.html', context)