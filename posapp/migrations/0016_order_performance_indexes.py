from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0015_remove_posproduct_image_fields'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['order_type', 'order_status', 'table_number'], name='order_dine_table_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['order_status', 'user'], name='order_status_user_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['order_status', 'created_at'], name='order_status_created_idx'),
        ),
    ]
