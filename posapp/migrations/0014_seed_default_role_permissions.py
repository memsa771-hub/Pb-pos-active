from django.db import migrations


def seed_role_permissions(apps, schema_editor):
    UserRole = apps.get_model('posapp', 'UserRole')

    admin_perms = {
        'can_create_orders': True,
        'can_edit_orders': True,
        'can_cancel_orders': True,
        'can_view_all_orders': True,
        'can_complete_orders': True,
        'can_apply_manual_discounts': True,
        'can_apply_discount_codes': True,
        'can_manage_discounts': True,
        'can_manage_products': True,
        'can_manage_categories': True,
        'can_view_stock': True,
        'can_manage_stock': True,
        'can_manage_users': True,
        'can_manage_roles': True,
        'can_view_reports': True,
        'can_view_detailed_reports': True,
        'can_manage_payments': True,
        'can_end_day': True,
        'can_manage_business_settings': True,
        'can_manage_system_settings': True,
        'can_view_audit_logs': True,
        'can_manage_bill_adjustments': True,
        'can_manage_advance_adjustments': True,
        'can_manage_delivery_persons': True,
        'can_assign_delivery_orders': True,
        'can_view_delivery_reports': True,
        'can_access_pos': True,
        'can_access_kitchen_view': True,
        'can_print_receipts': True,
    }

    branch_manager_perms = {
        'can_access_pos': True,
        'can_create_orders': True,
        'can_edit_orders': True,
        'can_cancel_orders': True,
        'can_view_all_orders': True,
        'can_complete_orders': True,
        'can_apply_manual_discounts': True,
        'can_apply_discount_codes': True,
        'can_end_day': True,
        'can_view_reports': True,
        'can_view_detailed_reports': True,
        'can_view_delivery_reports': True,
        'can_manage_bill_adjustments': True,
        'can_manage_advance_adjustments': True,
        'can_assign_delivery_orders': True,
        'can_print_receipts': True,
    }

    cashier_perms = {
        'can_access_pos': True,
        'can_create_orders': True,
        'can_print_receipts': True,
    }

    role_map = {
        'Admin': admin_perms,
        'Branch Manager': branch_manager_perms,
        'Cashier': cashier_perms,
    }

    for role_name, perms in role_map.items():
        try:
            role = UserRole.objects.get(name=role_name)
        except UserRole.DoesNotExist:
            continue
        for field, value in perms.items():
            setattr(role, field, value)
        role.save()


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0013_fix_role_names'),
    ]

    operations = [
        migrations.RunPython(seed_role_permissions, migrations.RunPython.noop),
    ]
