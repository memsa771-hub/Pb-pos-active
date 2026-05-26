from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, OrderViewSet,
    UserViewSet, DiscountViewSet, SettingViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'users', UserViewSet)
router.register(r'discounts', DiscountViewSet)
router.register(r'settings', SettingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add additional API endpoints here
] 