from django.db import migrations


def normalize_currency_symbol(apps, schema_editor):
    Setting = apps.get_model('posapp', 'Setting')
    try:
        setting = Setting.objects.get(setting_key='currency_symbol')
        value = (setting.setting_value or '').strip()
        if value in ('$', '') or value.lower() in ('rs', 'rs.'):
            setting.setting_value = 'Rs'
            setting.save(update_fields=['setting_value'])
    except Setting.DoesNotExist:
        Setting.objects.create(
            setting_key='currency_symbol',
            setting_value='Rs',
            setting_description='Currency symbol (e.g., Rs, $, €)',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('posapp', '0015_remove_posproduct_image_fields'),
    ]

    operations = [
        migrations.RunPython(normalize_currency_symbol, migrations.RunPython.noop),
    ]
