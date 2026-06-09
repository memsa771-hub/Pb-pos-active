from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from ..decorators import management_required
from ..models import BusinessLogo, BillAdjustmentImage

def serve_business_logo(request, logo_id):
    """Serve a business logo from the database"""
    logo = get_object_or_404(BusinessLogo, id=logo_id)
    
    if not logo.image:
        raise Http404("No image found")
    
    response = HttpResponse(logo.image, content_type=logo.image_type or 'image/jpeg')
    response['Content-Disposition'] = f'inline; filename="{logo.image_name or "logo.jpg"}"'
    return response

@login_required
@management_required
def serve_bill_adjustment_image(request, image_id):
    """Serve a bill adjustment image from the database"""
    image = get_object_or_404(BillAdjustmentImage, id=image_id)
    
    if not image.image:
        raise Http404("No image found")
    
    response = HttpResponse(image.image, content_type=image.image_type or 'image/jpeg')
    response['Content-Disposition'] = f'inline; filename="{image.image_name or "bill.jpg"}"'
    return response 