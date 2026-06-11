from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import (
    UserRole, UserProfile, PosCategory, PosProduct, 
    Order, OrderItem, Discount, Setting
)

class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    role = UserRoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        source='role',
        write_only=True
    )
    
    class Meta:
        model = UserProfile
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'profile')
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)
        
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        if profile_data:
            # Get or create profile safely
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults=profile_data
            )
            
            # If profile already existed, update it
            if not created:
                for key, value in profile_data.items():
                    setattr(profile, key, value)
                profile.save()
        
        return user
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)
        
        # Update user instance
        for key, value in validated_data.items():
            setattr(instance, key, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        
        # Update profile
        if profile_data:
            # Get or create profile safely
            profile, created = UserProfile.objects.get_or_create(
                user=instance,
                defaults=profile_data
            )
            
            # If profile already existed, update it
            if not created:
                for key, value in profile_data.items():
                    setattr(profile, key, value)
                profile.save()
        
        return instance

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PosCategory
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = PosProduct
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()

    def get_product_name(self, obj):
        return obj.display_name
    
    class Meta:
        model = OrderItem
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    order_time = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'

    def get_order_time(self, obj):
        import pytz
        pkt = pytz.timezone('Asia/Karachi')
        # obj.created_at is always UTC (USE_TZ=True); convert directly to PKT
        local_dt = obj.created_at.astimezone(pkt)
        return local_dt.strftime('%d/%m/%Y %H:%M:%S')
    
    def create(self, validated_data):
        items_data = self.context.get('items', [])
        
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        return order

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = '__all__'

class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = '__all__' 