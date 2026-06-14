from django.db import migrations


def remove_per_user_custom_roles(apps, schema_editor):
    UserRole = apps.get_model('posapp', 'UserRole')
    UserProfile = apps.get_model('posapp', 'UserProfile')

    standard_roles = ['Admin', 'Branch Manager', 'Cashier']

    for standard_name in standard_roles:
        standard_role, _ = UserRole.objects.get_or_create(
            name=standard_name,
            defaults={'description': f'{standard_name} role'},
        )
        custom_roles = UserRole.objects.filter(name__istartswith=f'{standard_name}_')
        for custom_role in custom_roles:
            UserProfile.objects.filter(role=custom_role).update(role=standard_role)
            custom_role.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0017_preserve_order_item_product_history'),
    ]

    operations = [
        migrations.RunPython(remove_per_user_custom_roles, migrations.RunPython.noop),
    ]
