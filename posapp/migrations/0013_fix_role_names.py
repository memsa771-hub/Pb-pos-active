from django.db import migrations


def fix_role_names(apps, schema_editor):
    UserRole = apps.get_model('posapp', 'UserRole')
    UserProfile = apps.get_model('posapp', 'UserProfile')

    correct_names = ['Admin', 'Branch Manager', 'Cashier']

    for correct_name in correct_names:
        wrong_roles = UserRole.objects.filter(
            name__istartswith=correct_name + '_'
        )
        correct_role, created = UserRole.objects.get_or_create(name=correct_name)
        for wrong_role in wrong_roles:
            UserProfile.objects.filter(role=wrong_role).update(role=correct_role)
            wrong_role.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0012_posproduct_is_recipe_based'),
    ]

    operations = [
        migrations.RunPython(fix_role_names, migrations.RunPython.noop),
    ]
