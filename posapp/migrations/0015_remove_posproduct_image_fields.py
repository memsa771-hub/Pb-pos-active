from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0014_seed_default_role_permissions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='posproduct',
            name='image',
        ),
        migrations.RemoveField(
            model_name='posproduct',
            name='image_name',
        ),
        migrations.RemoveField(
            model_name='posproduct',
            name='image_type',
        ),
    ]
