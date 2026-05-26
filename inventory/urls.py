from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # ---------------- DASHBOARD ---------------- #
    path('', views.dashboard, name='dashboard'),

    # ---------------- CATEGORIES ---------------- #
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/edit/<int:category_id>/', views.category_update, name='category_update'),
    path('categories/delete/<int:category_id>/', views.category_delete, name='category_delete'),

    # ---------------- ITEMS (Raw Materials) ---------------- #
    path('items/', views.item_list, name='item_list'),
    path('items/add/', views.item_create, name='item_create'),
    path('items/edit/<int:pk>/', views.item_update, name='item_update'),
    path('items/delete/<int:pk>/', views.item_delete, name='item_delete'),

    # ---------------- TRANSACTIONS ---------------- #
    # Stock In (Purchase)
    path('purchase/add/', views.add_purchase, name='add_purchase'),
    
    # Stock Out (Wastage/Adjustment)
    path('adjustment/add/', views.add_adjustment, name='add_adjustment'),

    # ---------------- REPORTS & EXPORT ---------------- #
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/purchases/', views.purchase_report, name='purchase_report'),
    path('reports/export/stock/', views.export_inventory_excel, name='export_inventory_excel'),


    # ---------------- SUPPLIERS ---------------- #
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/edit/<int:pk>/', views.supplier_update, name='supplier_update'),
    path('suppliers/delete/<int:pk>/', views.supplier_delete, name='supplier_delete'),

    # ---------------- RECIPE MANAGEMENT ---------------- #
    path('recipes/', views.recipe_list, name='recipe_list'),
    path('recipes/manage/<int:product_id>/', views.manage_recipe, name='manage_recipe'),
]

