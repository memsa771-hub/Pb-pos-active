from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum, Value, F, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponseRedirect
from django.forms import inlineformset_factory
from django import forms
from django.utils import timezone
from datetime import datetime, timedelta

from posapp.decorators import management_required
from posapp.models import BillAdjustment, BillAdjustmentImage, AdvanceAdjustment, EndDay, Setting, BusinessLogo
from posapp.permissions import is_admin, can_access_management

# Custom mixin to check if user is admin only
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page. Admin access required.")
        return redirect('pos')

# Custom mixin to check if user is admin or branch manager
class AdminOrBranchManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return can_access_management(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page. Management access required.")
        return redirect('pos')

# Form for multiple image uploads
class BillAdjustmentForm(forms.ModelForm):
    class Meta:
        model = BillAdjustment
        fields = ['name', 'quantity', 'price', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'placeholder': 'Optional'}),
        }

# Bill Adjustment Views
class BillAdjustmentListView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, ListView):
    model = BillAdjustment
    template_name = 'posapp/adjustments/bill_adjustment_list.html'
    context_object_name = 'bill_adjustments'
    ordering = ['-created_at']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        
        user_is_admin = is_admin(self.request.user)

        if not user_is_admin:
            # Get the last end day timestamp
            last_end_day = EndDay.get_last_end_day()
            if last_end_day:
                # If there's a last end day, only show adjustments since the last end day
                queryset = queryset.filter(created_at__gte=last_end_day.end_date)
        
        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        # Apply date filters (for admins only)
        if user_is_admin:
            if start_date:
                try:
                    start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__gte=start_date)
                except ValueError:
                    pass
                    
            if end_date:
                try:
                    end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__lte=end_date)
                except ValueError:
                    pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['is_admin'] = is_admin(self.request.user)
        context['last_end_day'] = EndDay.get_last_end_day()
        return context

class BillAdjustmentDetailView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, DetailView):
    model = BillAdjustment
    template_name = 'posapp/adjustments/bill_adjustment_detail.html'
    context_object_name = 'bill_adjustment'

class BillAdjustmentCreateView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, CreateView):
    model = BillAdjustment
    form_class = BillAdjustmentForm
    template_name = 'posapp/adjustments/bill_adjustment_form.html'
    success_url = reverse_lazy('bill_adjustment_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        self.object = form.save()
        
        # Handle multiple image uploads
        images = self.request.FILES.getlist('images')
        for image_file in images:
            bill_image = BillAdjustmentImage(bill_adjustment=self.object)
            bill_image.set_image(image_file)
            bill_image.save()
        
        messages.success(self.request, 'Bill adjustment created successfully.')
        return HttpResponseRedirect(self.get_success_url())

class BillAdjustmentUpdateView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, UpdateView):
    model = BillAdjustment
    form_class = BillAdjustmentForm
    template_name = 'posapp/adjustments/bill_adjustment_form.html'
    success_url = reverse_lazy('bill_adjustment_list')
    
    def form_valid(self, form):
        self.object = form.save()
        
        # Handle multiple image uploads
        images = self.request.FILES.getlist('images')
        for image_file in images:
            bill_image = BillAdjustmentImage(bill_adjustment=self.object)
            bill_image.set_image(image_file)
            bill_image.save()
            
        messages.success(self.request, 'Bill adjustment updated successfully.')
        return HttpResponseRedirect(self.get_success_url())

class BillAdjustmentDeleteView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, DeleteView):
    model = BillAdjustment
    template_name = 'posapp/adjustments/bill_adjustment_confirm_delete.html'
    context_object_name = 'bill_adjustment'
    success_url = reverse_lazy('bill_adjustment_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if adjustment can be deleted (not before last end day)
        last_end_day = EndDay.get_last_end_day()
        if last_end_day and self.object.created_at < last_end_day.end_date:
            context['cannot_delete'] = True
            context['last_end_day'] = last_end_day
        else:
            context['cannot_delete'] = False
        return context
    
    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            
            # Check if adjustment was created before last end day
            last_end_day = EndDay.get_last_end_day()
            if last_end_day and self.object.created_at < last_end_day.end_date:
                messages.error(self.request, f'Cannot delete bill adjustment created before the last end day operation on {last_end_day.end_date.strftime("%B %d, %Y at %I:%M %p")}. This adjustment is part of a closed day and cannot be modified.')
                return HttpResponseRedirect(reverse_lazy('bill_adjustment_list'))
            
            success_url = self.get_success_url()
            self.object.delete()
            messages.success(self.request, 'Bill adjustment deleted successfully.')
            return HttpResponseRedirect(success_url)
        except Exception as e:
            messages.error(request, f"Error deleting bill adjustment: {str(e)}")
            return HttpResponseRedirect(reverse_lazy('bill_adjustment_list'))

class BillAdjustmentImageDeleteView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, DeleteView):
    model = BillAdjustmentImage
    template_name = 'posapp/adjustments/bill_adjustment_image_confirm_delete.html'
    context_object_name = 'bill_adjustment_image'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj:
            messages.error(self.request, "The requested image could not be found.")
            return None
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        if obj and obj.bill_adjustment:
            # Ensure we have the related bill_adjustment
            context['bill_adjustment'] = obj.bill_adjustment
        return context
    
    def get_success_url(self):
        # Store the bill_adjustment_id before deleting the image
        if hasattr(self, 'bill_adjustment_id') and self.bill_adjustment_id:
            return reverse_lazy('bill_adjustment_detail', kwargs={'pk': self.bill_adjustment_id})
        return reverse_lazy('bill_adjustment_list')
    
    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            # Store bill_adjustment_id before deletion
            if self.object and hasattr(self.object, 'bill_adjustment') and self.object.bill_adjustment:
                self.bill_adjustment_id = self.object.bill_adjustment.pk
            else:
                self.bill_adjustment_id = None
                
            success_url = self.get_success_url()
            self.object.delete()
            messages.success(self.request, 'Image deleted successfully.')
            return HttpResponseRedirect(success_url)
        except Exception as e:
            messages.error(request, f"Error deleting image: {str(e)}")
            return HttpResponseRedirect(reverse_lazy('bill_adjustment_list'))

# Advance Adjustment Views
class AdvanceAdjustmentListView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, ListView):
    model = AdvanceAdjustment
    template_name = 'posapp/adjustments/advance_adjustment_list.html'
    context_object_name = 'advance_adjustments'
    ordering = ['-date']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        
        user_is_admin = is_admin(self.request.user)

        if not user_is_admin:
            # Get the last end day timestamp
            last_end_day = EndDay.get_last_end_day()
            if last_end_day:
                # If there's a last end day, only show adjustments since the last end day
                queryset = queryset.filter(created_at__gte=last_end_day.end_date)
        
        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        # Apply date filters (for admins only)
        if user_is_admin:
            if start_date:
                try:
                    start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__gte=start_date)
                except ValueError:
                    pass
                    
            if end_date:
                try:
                    end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__lte=end_date)
                except ValueError:
                    pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['is_admin'] = is_admin(self.request.user)
        context['last_end_day'] = EndDay.get_last_end_day()
        return context

class AdvanceAdjustmentDetailView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, DetailView):
    model = AdvanceAdjustment
    template_name = 'posapp/adjustments/advance_adjustment_detail.html'
    context_object_name = 'advance_adjustment'

class AdvanceAdjustmentCreateView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, CreateView):
    model = AdvanceAdjustment
    template_name = 'posapp/adjustments/advance_adjustment_form.html'
    fields = ['name', 'amount', 'notes']
    success_url = reverse_lazy('advance_adjustment_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Advance adjustment created successfully.')
        return super().form_valid(form)

class AdvanceAdjustmentUpdateView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, UpdateView):
    model = AdvanceAdjustment
    template_name = 'posapp/adjustments/advance_adjustment_form.html'
    fields = ['name', 'amount', 'notes']
    success_url = reverse_lazy('advance_adjustment_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Advance adjustment updated successfully.')
        return super().form_valid(form)

class AdvanceAdjustmentDeleteView(LoginRequiredMixin, AdminOrBranchManagerRequiredMixin, DeleteView):
    model = AdvanceAdjustment
    template_name = 'posapp/adjustments/advance_adjustment_confirm_delete.html'
    context_object_name = 'advance_adjustment'
    success_url = reverse_lazy('advance_adjustment_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if adjustment can be deleted (not before last end day)
        last_end_day = EndDay.get_last_end_day()
        if last_end_day and self.object.created_at < last_end_day.end_date:
            context['cannot_delete'] = True
            context['last_end_day'] = last_end_day
        else:
            context['cannot_delete'] = False
        return context
    
    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            
            # Check if adjustment was created before last end day
            last_end_day = EndDay.get_last_end_day()
            if last_end_day and self.object.created_at < last_end_day.end_date:
                messages.error(self.request, f'Cannot delete advance adjustment created before the last end day operation on {last_end_day.end_date.strftime("%B %d, %Y at %I:%M %p")}. This adjustment is part of a closed day and cannot be modified.')
                return HttpResponseRedirect(reverse_lazy('advance_adjustment_list'))
            
            success_url = self.get_success_url()
            self.object.delete()
            messages.success(self.request, 'Advance adjustment deleted successfully.')
            return HttpResponseRedirect(success_url)
        except Exception as e:
            messages.error(request, f"Error deleting advance adjustment: {str(e)}")
            return HttpResponseRedirect(reverse_lazy('advance_adjustment_list'))

# Adjustment Dashboard
@login_required
@management_required
def adjustment_dashboard(request):
    # Check if user is admin or branch manager
    user_is_admin = is_admin(request.user)
    
    # For branch managers, only show adjustments since last end day
    if not user_is_admin:
        # Get the last end day timestamp
        last_end_day = EndDay.get_last_end_day()
        if last_end_day:
            # If there's a last end day, only show adjustments since the last end day
            bill_adjustments = BillAdjustment.objects.filter(created_at__gte=last_end_day.end_date).order_by('-created_at')[:5]
            advance_adjustments = AdvanceAdjustment.objects.filter(created_at__gte=last_end_day.end_date).order_by('-created_at')[:5]
        else:
            # If there's no last end day, show all adjustments (same as admin)
            bill_adjustments = BillAdjustment.objects.order_by('-created_at')[:5]
            advance_adjustments = AdvanceAdjustment.objects.order_by('-created_at')[:5]
    else:
        # For admins, show all recent adjustments
        bill_adjustments = BillAdjustment.objects.order_by('-created_at')[:5]
        advance_adjustments = AdvanceAdjustment.objects.order_by('-created_at')[:5]
    
    context = {
        'bill_adjustments': bill_adjustments,
        'advance_adjustments': advance_adjustments,
        'is_admin': user_is_admin,
        'last_end_day': EndDay.get_last_end_day(),
    }

    return render(request, 'posapp/adjustments/adjustment_dashboard.html', context)

# Adjustment Report
@login_required
@management_required
def adjustment_report(request):
    # Check if user is admin or branch manager
    user_is_admin = is_admin(request.user)
    
    # Get the last end day timestamp
    last_end_day = EndDay.get_last_end_day()
    last_end_day_time = last_end_day.end_date if last_end_day else None
    
    # Get date range from request
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    
    # Set default date range to current month if not provided
    today = timezone.now()
    
    if not start_date_param or not end_date_param:
        start_date = timezone.make_aware(datetime.combine(today.replace(day=1).date(), datetime.min.time()))
        end_date = timezone.make_aware(datetime.combine(today.date(), datetime.max.time()))
    else:
        try:
            # Try to parse as datetime with time first
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d %H:%M:%S')
                # Make timezone aware
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except ValueError:
                # Fall back to date only format
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                # Convert to datetime at start of day
                start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
                
            # Try to parse as datetime with time first
            try:
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d %H:%M:%S')
                # Make timezone aware
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except ValueError:
                # Fall back to date only format
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
                # Convert to datetime at end of day
                end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        except ValueError:
            # If there's any issue parsing the dates, use default values
            start_date = timezone.make_aware(datetime.combine(today.replace(day=1).date(), datetime.min.time()))
            end_date = timezone.make_aware(datetime.combine(today.date(), datetime.max.time()))
    
    # For branch managers, further limit by last end day if needed
    if not user_is_admin and last_end_day_time:
        # For branch managers, only show adjustments since the last end day
        # Override the date range to be from last end day to now
        start_date = last_end_day_time
        end_date = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Get bill adjustments for the date range with exact timestamp filtering
    bill_adjustments = BillAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    # Get advance adjustments for the date range
    # For advance adjustments, we need to check the created_at timestamp instead of just date
    advance_adjustments = AdvanceAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    # Calculate totals
    bill_total = bill_adjustments.aggregate(Sum('price'))['price__sum'] or 0
    advance_total = advance_adjustments.aggregate(Sum('amount'))['amount__sum'] or 0
    total_adjustments = bill_total + advance_total
    
    context = {
        'bill_adjustments': bill_adjustments,
        'advance_adjustments': advance_adjustments,
        'bill_total': bill_total,
        'advance_total': advance_total,
        'total_adjustments': total_adjustments,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date.strftime('%Y-%m-%d %H:%M:%S'),
        'end_date_str': end_date.strftime('%Y-%m-%d %H:%M:%S'),
        'is_admin': user_is_admin,
        'last_end_day': last_end_day,
    }
    
    return render(request, 'posapp/adjustments/adjustment_report.html', context)

@login_required
def adjustment_receipt(request):
    """Display a printable receipt for adjustment report"""
    if not (request.user.is_superuser or 
            request.user.profile.role.name == 'Admin' or 
            request.user.profile.role.name == 'Branch Manager'):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Check if user is admin or branch manager
    user_is_admin = is_admin(request.user)
    
    # Get the last end day timestamp
    last_end_day = EndDay.get_last_end_day()
    last_end_day_time = last_end_day.end_date if last_end_day else None
    
    # Get date range from request
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    
    # Set default date range to current month if not provided
    today = timezone.now()
    
    if not start_date_param or not end_date_param:
        start_date = timezone.make_aware(datetime.combine(today.replace(day=1).date(), datetime.min.time()))
        end_date = timezone.make_aware(datetime.combine(today.date(), datetime.max.time()))
    else:
        try:
            # Try to parse as datetime with time first
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d %H:%M:%S')
                # Make timezone aware
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            except ValueError:
                # Fall back to date only format
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                # Convert to datetime at start of day
                start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
                
            # Try to parse as datetime with time first
            try:
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d %H:%M:%S')
                # Make timezone aware
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
            except ValueError:
                # Fall back to date only format
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
                # Convert to datetime at end of day
                end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        except ValueError:
            # If there's any issue parsing the dates, use default values
            start_date = timezone.make_aware(datetime.combine(today.replace(day=1).date(), datetime.min.time()))
            end_date = timezone.make_aware(datetime.combine(today.date(), datetime.max.time()))
    
    # For branch managers, further limit by last end day if needed
    if not user_is_admin and last_end_day_time:
        # For branch managers, only show adjustments since the last end day
        # Override the date range to be from last end day to now
        start_date = last_end_day_time
        end_date = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Get bill adjustments for the date range with exact timestamp filtering
    bill_adjustments = BillAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    # Get advance adjustments for the date range
    # For advance adjustments, we need to check the created_at timestamp instead of just date
    advance_adjustments = AdvanceAdjustment.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('-created_at')
    
    # Calculate totals
    bill_total = bill_adjustments.aggregate(Sum('price'))['price__sum'] or 0
    advance_total = advance_adjustments.aggregate(Sum('amount'))['amount__sum'] or 0
    total_adjustments = bill_total + advance_total
    
    # Get business information for the receipt
    business_settings = {'business_name': 'POS System', 'business_address': '', 'business_phone': '', 'business_email': ''}
    for setting in Setting.objects.filter(
        setting_key__in=['business_name', 'business_address', 'business_phone', 'business_email']
    ):
        business_settings[setting.setting_key] = setting.setting_value
    
    # Get business logo URL
    logo_url = BusinessLogo.get_logo_url()
    
    # Get currency symbol
    currency_symbol = Setting.get_currency_symbol()
    
    # Get receipt settings
    try:
        receipt_show_logo = Setting.objects.get(setting_key='receipt_show_logo').setting_value == 'True'
        receipt_header = Setting.objects.get(setting_key='receipt_header').setting_value
        receipt_footer = Setting.objects.get(setting_key='receipt_footer').setting_value
        receipt_paper_size = Setting.objects.get(setting_key='receipt_paper_size').setting_value
        receipt_custom_css = Setting.objects.get(setting_key='receipt_custom_css').setting_value
    except Setting.DoesNotExist:
        receipt_show_logo = False
        receipt_header = ''
        receipt_footer = ''
        receipt_paper_size = ''
        receipt_custom_css = ''
    
    context = {
        'bill_adjustments': bill_adjustments,
        'advance_adjustments': advance_adjustments,
        'bill_total': bill_total,
        'advance_total': advance_total,
        'total_adjustments': total_adjustments,
        'report_date': timezone.now(),
        'start_date': start_date,
        'end_date': end_date,
        'business_name': business_settings['business_name'],
        'business_address': business_settings['business_address'],
        'business_phone': business_settings['business_phone'],
        'business_email': business_settings['business_email'],
        'business_logo': logo_url,
        'currency_symbol': currency_symbol,
        'is_admin': user_is_admin,
        'last_end_day': last_end_day,
        'receipt_show_logo': receipt_show_logo,
        'receipt_header': receipt_header,
        'receipt_footer': receipt_footer,
        'receipt_paper_size': receipt_paper_size,
        'receipt_custom_css': receipt_custom_css,
    }
    
    return render(request, 'posapp/adjustments/adjustment_receipt.html', context) 