from django.db import migrations, models
import django.db.models.deletion


def backfill_order_item_snapshots(apps, schema_editor):
    OrderItem = apps.get_model('posapp', 'OrderItem')
    PosProduct = apps.get_model('posapp', 'PosProduct')
    for item in OrderItem.objects.all().iterator():
        if not item.product_id:
            continue
        try:
            product = PosProduct.objects.get(pk=item.product_id)
        except PosProduct.DoesNotExist:
            continue
        item.product_name = product.name
        item.product_code = product.product_code or ''
        item.is_weight_based = product.calculate_price_per_kg
        item.save(update_fields=['product_name', 'product_code', 'is_weight_based'])


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0016_fix_currency_symbol'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='product_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product_code',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='is_weight_based',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(
                blank=True,
                help_text='Linked product; order history keeps snapshots if product is removed from catalog',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='posapp.posproduct',
            ),
        ),
        migrations.RunPython(backfill_order_item_snapshots, migrations.RunPython.noop),
    ]
