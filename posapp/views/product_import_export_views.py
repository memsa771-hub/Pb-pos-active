import csv
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone

from ..decorators import admin_required
from ..forms import ProductForm
from ..models import PosCategory, PosProduct

EXCEL_AVAILABLE = False
try:
    import pandas as pd
    import openpyxl  # noqa: F401
    EXCEL_AVAILABLE = True
except ImportError:
    pd = None

EXPORT_COLUMNS = [
    'name',
    'product_code',
    'category',
    'price',
    'sku',
    'stock_quantity',
    'is_available',
    'running_item',
    'is_recipe_based',
    'calculate_price_per_kg',
    'description',
    'is_archived',
]

HEADER_ALIASES = {
    'name': {'name', 'product name', 'product_name'},
    'product_code': {'product_code', 'product code', 'code', 'product id', 'product_id'},
    'category': {'category', 'category name', 'category_name'},
    'price': {'price', 'unit price', 'unit_price', 'selling price', 'selling_price'},
    'sku': {'sku', 'barcode'},
    'stock_quantity': {'stock_quantity', 'stock quantity', 'stock', 'quantity'},
    'is_available': {'is_available', 'available', 'is available'},
    'running_item': {'running_item', 'running item', 'running'},
    'is_recipe_based': {'is_recipe_based', 'recipe based', 'recipe_based', 'recipe'},
    'calculate_price_per_kg': {
        'calculate_price_per_kg',
        'price per kg',
        'price_per_kg',
        'per kg',
        'weight based',
    },
    'description': {'description', 'notes'},
    'is_archived': {'is_archived', 'archived', 'is archived'},
}

BOOL_TRUE = {'yes', 'y', 'true', '1', 'on'}
BOOL_FALSE = {'no', 'n', 'false', '0', 'off'}


def _products_queryset(include_archived=True):
    qs = PosProduct.objects.select_related('category').order_by('name')
    if not include_archived:
        qs = qs.filter(is_archived=False)
    return qs


def _product_to_row(product):
    return {
        'name': product.name,
        'product_code': product.product_code,
        'category': product.category.name if product.category else '',
        'price': float(product.price),
        'sku': product.sku or '',
        'stock_quantity': product.stock_quantity,
        'is_available': 'Yes' if product.is_available else 'No',
        'running_item': 'Yes' if product.running_item else 'No',
        'is_recipe_based': 'Yes' if product.is_recipe_based else 'No',
        'calculate_price_per_kg': 'Yes' if product.calculate_price_per_kg else 'No',
        'description': product.description or '',
        'is_archived': 'Yes' if product.is_archived else 'No',
    }


def _normalize_header(value):
    return re.sub(r'[\s_]+', ' ', str(value).strip().lower())


def _map_row_headers(row):
    mapped = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized = _normalize_header(key)
        field_name = None
        for target, aliases in HEADER_ALIASES.items():
            if normalized in aliases:
                field_name = target
                break
        if field_name:
            mapped[field_name] = value
    return mapped


def _parse_bool(value, default=None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == '':
        return default
    if text in BOOL_TRUE:
        return True
    if text in BOOL_FALSE:
        return False
    raise ValueError(f'Invalid yes/no value: {value}')


def _parse_decimal(value):
    if value is None:
        return None
    text = str(value).strip().replace(',', '')
    if text == '':
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValueError(f'Invalid price: {value}')


def _parse_int(value, default=None):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if text == '':
        return default
    if not text.isdigit():
        raise ValueError(f'Invalid number: {value}')
    return int(text)


def _get_or_create_category(name):
    clean_name = str(name).strip()
    if not clean_name:
        return None
    category, _ = PosCategory.objects.get_or_create(
        name=clean_name,
        defaults={'description': ''},
    )
    return category


def _build_product_payload(row_data, update_existing=False):
    payload = {}
    errors = []

    name = str(row_data.get('name', '')).strip()
    if not name:
        errors.append('Name is required.')
    else:
        payload['name'] = name

    product_code = str(row_data.get('product_code', '')).strip()
    if not product_code:
        errors.append('Product code is required.')
    elif not product_code.isdigit():
        errors.append('Product code must contain only numbers.')
    else:
        payload['product_code'] = product_code

    price = _parse_decimal(row_data.get('price'))
    if price is None:
        errors.append('Price is required.')
    elif price < 0:
        errors.append('Price cannot be negative.')
    else:
        payload['price'] = price

    category_name = row_data.get('category')
    if category_name is not None and str(category_name).strip():
        payload['category'] = _get_or_create_category(category_name)
    else:
        payload['category'] = None

    sku = row_data.get('sku')
    payload['sku'] = str(sku).strip() if sku is not None and str(sku).strip() else None

    try:
        payload['is_available'] = _parse_bool(row_data.get('is_available'), default=True)
        payload['running_item'] = _parse_bool(row_data.get('running_item'), default=False)
        payload['is_recipe_based'] = _parse_bool(row_data.get('is_recipe_based'), default=False)
        payload['calculate_price_per_kg'] = _parse_bool(
            row_data.get('calculate_price_per_kg'),
            default=False,
        )
        payload['is_archived'] = _parse_bool(row_data.get('is_archived'), default=False)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        stock_quantity = _parse_int(row_data.get('stock_quantity'), default=0)
        payload['stock_quantity'] = stock_quantity
    except ValueError as exc:
        errors.append(str(exc))

    description = row_data.get('description')
    payload['description'] = str(description).strip() if description is not None else None

    if payload.get('running_item') or payload.get('is_recipe_based'):
        payload['stock_quantity'] = 0
    elif payload.get('stock_quantity') is None:
        errors.append('Stock quantity is required for standard items.')
    elif payload['stock_quantity'] < 0:
        errors.append('Stock cannot be negative.')

    existing = None
    if product_code and product_code.isdigit():
        existing = PosProduct.objects.filter(product_code=product_code).first()

    if existing and not update_existing:
        errors.append(f'Product code {product_code} already exists. Enable "Update existing" to overwrite.')

    return payload, existing, errors


def _save_product(payload, existing=None):
    form_data = {
        'name': payload['name'],
        'product_code': payload['product_code'],
        'category': payload['category'].id if payload['category'] else '',
        'price': payload['price'],
        'sku': payload['sku'] or '',
        'stock_quantity': payload.get('stock_quantity', 0),
        'is_available': payload.get('is_available', True),
        'running_item': payload.get('running_item', False),
        'is_recipe_based': payload.get('is_recipe_based', False),
        'calculate_price_per_kg': payload.get('calculate_price_per_kg', False),
        'description': payload.get('description') or '',
    }

    form = ProductForm(form_data, instance=existing)
    if not form.is_valid():
        return None, [f'{field}: {error}' for field, errors in form.errors.items() for error in errors]

    product = form.save(commit=False)
    product.is_archived = payload.get('is_archived', False)
    product.save()
    return product, []


def _read_uploaded_rows(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith('.csv'):
        decoded = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(decoded))
        return [row for row in reader if any(str(v).strip() for v in row.values() if v is not None)]

    if not EXCEL_AVAILABLE:
        raise ValueError('Excel import requires pandas and openpyxl.')

    if filename.endswith(('.xlsx', '.xls')):
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, dtype=str)
        df = df.fillna('')
        return df.to_dict(orient='records')

    raise ValueError('Unsupported file type. Upload a .csv, .xlsx, or .xls file.')


def _export_filename(extension):
    stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f'products_export_{stamp}.{extension}'


@login_required
@admin_required
def export_products(request):
    export_format = request.GET.get('format', 'xlsx').lower()
    include_archived = request.GET.get('include_archived', '1') == '1'
    rows = [_product_to_row(product) for product in _products_queryset(include_archived)]

    if export_format == 'csv':
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{_export_filename("csv")}"'
        return response

    if not EXCEL_AVAILABLE:
        messages.error(request, 'Excel export requires pandas and openpyxl.')
        return redirect('category_list')

    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{_export_filename("xlsx")}"'
    return response


@login_required
@admin_required
def download_product_import_template(request):
    template_format = request.GET.get('format', 'xlsx').lower()
    example_row = {
        'name': 'Chicken Burger',
        'product_code': '100001',
        'category': 'Burgers',
        'price': 12.50,
        'sku': 'CHK-BRG-01',
        'stock_quantity': 50,
        'is_available': 'Yes',
        'running_item': 'No',
        'is_recipe_based': 'No',
        'calculate_price_per_kg': 'No',
        'description': 'Optional notes',
        'is_archived': 'No',
    }

    if template_format == 'csv':
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerow(example_row)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="products_import_template.csv"'
        return response

    if not EXCEL_AVAILABLE:
        messages.error(request, 'Excel template requires pandas and openpyxl.')
        return redirect('category_list')

    df = pd.DataFrame([example_row], columns=EXPORT_COLUMNS)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="products_import_template.xlsx"'
    return response


@login_required
@admin_required
def import_products(request):
    if request.method != 'POST':
        return redirect('category_list')

    uploaded_file = request.FILES.get('import_file')
    if not uploaded_file:
        messages.error(request, 'Please choose a CSV or Excel file to import.')
        return redirect('category_list')

    if uploaded_file.size > 10 * 1024 * 1024:
        messages.error(request, 'File is too large. Maximum upload size is 10 MB.')
        return redirect('category_list')

    update_existing = request.POST.get('update_existing') == 'on'

    try:
        raw_rows = _read_uploaded_rows(uploaded_file)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('category_list')

    if not raw_rows:
        messages.warning(request, 'The uploaded file has no product rows to import.')
        return redirect('category_list')

    created_count = 0
    updated_count = 0
    error_rows = []

    for index, raw_row in enumerate(raw_rows, start=2):
        mapped_row = _map_row_headers(raw_row)
        if not any(str(v).strip() for v in mapped_row.values() if v is not None):
            continue

        payload, existing, row_errors = _build_product_payload(mapped_row, update_existing=update_existing)
        if row_errors:
            error_rows.append(f'Row {index}: {"; ".join(row_errors)}')
            continue

        try:
            with transaction.atomic():
                product, form_errors = _save_product(payload, existing=existing if update_existing else None)
                if form_errors:
                    error_rows.append(f'Row {index}: {"; ".join(form_errors)}')
                    continue
                if existing and update_existing:
                    updated_count += 1
                else:
                    created_count += 1
        except Exception as exc:
            error_rows.append(f'Row {index}: {exc}')

    if created_count or updated_count:
        summary = []
        if created_count:
            summary.append(f'{created_count} created')
        if updated_count:
            summary.append(f'{updated_count} updated')
        messages.success(request, f'Import complete: {", ".join(summary)}.')
    else:
        messages.warning(request, 'No products were imported.')

    if error_rows:
        preview = '; '.join(error_rows[:5])
        extra = f' (+{len(error_rows) - 5} more)' if len(error_rows) > 5 else ''
        messages.error(request, f'Import issues: {preview}{extra}')

    return redirect('category_list')
