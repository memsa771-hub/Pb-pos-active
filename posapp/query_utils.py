from django.db.models import CharField, F, Value
from django.db.models.functions import Coalesce, NullIf

SOLD_PRODUCT_NAME_EXPR = Coalesce(
    NullIf(F('product_name'), Value('')),
    F('product__name'),
    Value('Removed product'),
    output_field=CharField(),
)
