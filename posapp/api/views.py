from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ..models import (
    UserRole, UserProfile, PosCategory, PosProduct, 
    Order, OrderItem, Discount, Setting
)
from .serializers import (
    UserSerializer, CategorySerializer, ProductSerializer,
    OrderSerializer, OrderItemSerializer, DiscountSerializer,
    SettingSerializer
)
from django_filters.rest_framework import DjangoFilterBackend

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    """
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS requests
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user has admin role
        return request.user.is_authenticated and request.user.profile.role.name == 'Admin'

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    @action(detail=False, methods=['get'])
    def cashiers(self, request):
        cashier_role = UserRole.objects.get(name='Cashier')
        cashiers = User.objects.filter(profile__role=cashier_role)
        serializer = self.get_serializer(cashiers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def admins(self, request):
        admin_role = UserRole.objects.get(name='Admin')
        admins = User.objects.filter(profile__role=admin_role)
        serializer = self.get_serializer(admins, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = PosCategory.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows products to be viewed or edited.
    """
    queryset = PosProduct.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_available']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'price', 'stock_quantity', 'created_at']
    permission_classes = [IsAdminOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if category_id:
            products = PosProduct.objects.filter(category_id=category_id, is_available=True)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "Category ID is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        available_products = PosProduct.objects.filter(is_available=True)
        serializer = self.get_serializer(available_products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        threshold = int(request.query_params.get('threshold', 10))
        low_stock_products = PosProduct.objects.filter(stock_quantity__lt=threshold)
        serializer = self.get_serializer(low_stock_products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        product = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response(
                {"error": "Quantity is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            product.stock_quantity = quantity
            product.save()
            serializer = self.get_serializer(product)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"error": "Quantity must be an integer"},
                status=status.HTTP_400_BAD_REQUEST
            )

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['reference_number', 'customer_name', 'customer_phone']
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        today_orders = Order.objects.filter(created_at__date=today)
        serializer = self.get_serializer(today_orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        status_param = request.query_params.get('status')
        if status_param:
            orders = Order.objects.filter(order_status=status_param)
            serializer = self.get_serializer(orders, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "Status parameter is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        order = self.get_object()
        
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        unit_price = request.data.get('unit_price')
        
        if not all([product_id, quantity, unit_price]):
            return Response(
                {"error": "product_id, quantity and unit_price are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
            quantity = float(quantity)
            unit_price = float(unit_price)
            
            # Create the order item
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                total_price=quantity * unit_price
            )
            
            # Update the order totals
            order.subtotal = sum(item.total_price for item in order.items.all())
            
            # Calculate tax based on settings or default
            tax_rate = float(Setting.objects.get(setting_key='tax_rate').setting_value) / 100
            order.tax_amount = order.subtotal * tax_rate
            
            # Calculate total
            order.total_amount = order.subtotal + order.tax_amount - order.discount_amount
            order.save()
            
            # Return the updated order with its items
            serializer = self.get_serializer(order)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {"error": "Invalid quantity or unit price"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        order = self.get_object()
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response(
                {"error": "item_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order_item = OrderItem.objects.get(id=item_id, order=order)
            order_item.delete()
            
            # Update the order totals
            order.subtotal = sum(item.total_price for item in order.items.all())
            
            # Calculate tax based on settings or default
            tax_rate = float(Setting.objects.get(setting_key='tax_rate').setting_value) / 100
            order.tax_amount = order.subtotal * tax_rate
            
            # Calculate total
            order.total_amount = order.subtotal + order.tax_amount - order.discount_amount
            order.save()
            
            serializer = self.get_serializer(order)
            return Response(serializer.data)
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Order item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def apply_discount(self, request, pk=None):
        order = self.get_object()
        discount_code = request.data.get('discount_code')
        
        if not discount_code:
            return Response(
                {"error": "discount_code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            discount = Discount.objects.get(code=discount_code, is_active=True)
            
            # Check if the discount is valid (within date range)
            from django.utils import timezone
            today = timezone.now().date()
            
            if (discount.start_date and discount.start_date > today) or \
               (discount.end_date and discount.end_date < today):
                return Response(
                    {"error": "This discount code is not valid at this time"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Apply the discount
            if discount.type == 'Percentage':
                order.discount_amount = order.subtotal * (discount.value / 100)
            else:  # Fixed amount
                order.discount_amount = min(discount.value, order.subtotal)  # Don't exceed subtotal
            
            # Update total
            order.total_amount = order.subtotal + order.tax_amount - order.discount_amount
            order.save()
            
            serializer = self.get_serializer(order)
            return Response(serializer.data)
        except Discount.DoesNotExist:
            return Response(
                {"error": "Invalid discount code"},
                status=status.HTTP_404_NOT_FOUND
            )

class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        active_discounts = Discount.objects.filter(is_active=True)
        serializer = self.get_serializer(active_discounts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        code = request.data.get('code')
        
        if not code:
            return Response(
                {"error": "Discount code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            discount = Discount.objects.get(code=code, is_active=True)
            
            # Check if the discount is valid (within date range)
            from django.utils import timezone
            today = timezone.now().date()
            
            if (discount.start_date and discount.start_date > today) or \
               (discount.end_date and discount.end_date < today):
                return Response(
                    {"valid": False, "message": "This discount code is not valid at this time"}
                )
            
            serializer = self.get_serializer(discount)
            return Response({"valid": True, "discount": serializer.data})
        except Discount.DoesNotExist:
            return Response(
                {"valid": False, "message": "Invalid discount code"}
            )

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def by_key(self, request):
        key = request.query_params.get('key')
        if key:
            setting = get_object_or_404(Setting, setting_key=key)
            serializer = self.get_serializer(setting)
            return Response(serializer.data)
        return Response(
            {"error": "Key parameter is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def business_info(self, request):
        keys = ['business_name', 'business_address', 'business_phone', 'currency_symbol']
        settings = Setting.objects.filter(setting_key__in=keys)
        
        result = {}
        for setting in settings:
            result[setting.setting_key] = setting.setting_value
        
        return Response(result) 