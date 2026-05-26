from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from posapp.decorators import can_manage_stock_required
from inventory.models import Supplier

# ----------------- SUPPLIER LIST ----------------- #

@login_required
@can_manage_stock_required
def supplier_list(request):
    """List all Suppliers"""
    search_query = request.GET.get('search', '')
    
    suppliers = Supplier.objects.all().order_by('name')
    
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    return render(request, 'inventory/supplier_list.html', {
        'suppliers': suppliers,
        'search_query': search_query
    })

# ----------------- ADD SUPPLIER ----------------- #

@login_required
@can_manage_stock_required
def supplier_create(request):
    """Add New Supplier"""
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        if not name:
            messages.error(request, "Supplier Name is required.")
        else:
            Supplier.objects.create(name=name, phone=phone, address=address)
            messages.success(request, f"Supplier '{name}' added successfully.")
            return redirect('inventory:supplier_list')

    return render(request, 'inventory/supplier_form.html')

# ----------------- EDIT SUPPLIER ----------------- #

@login_required
@can_manage_stock_required
def supplier_update(request, pk):
    """Edit Supplier Details"""
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.phone = request.POST.get('phone')
        supplier.address = request.POST.get('address')
        supplier.save()
        
        messages.success(request, "Supplier updated successfully.")
        return redirect('inventory:supplier_list')

    return render(request, 'inventory/supplier_form.html', {'supplier': supplier})

# ----------------- DELETE SUPPLIER ----------------- #

@login_required
@can_manage_stock_required
def supplier_delete(request, pk):
    """Delete Supplier"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, "Supplier deleted successfully.")
    
    return redirect('inventory:supplier_list')