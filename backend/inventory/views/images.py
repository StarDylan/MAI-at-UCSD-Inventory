"""
Image management views for the inventory application.

This module handles image upload, deletion, and management functionality
for inventory items. Images are stored using Cloudinary service.
"""

import json
import logging
import io
import base64
from typing import TypedDict, cast
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from PIL import Image as PILImage

from inventory.models import Item, Image
from .utils import audit_log_state, audit_log_event


def generate_thumbnail(image_data, max_size=(150, 150), quality=85):
    """
    Generate a thumbnail from base64 image data.
    
    Args:
        image_data: Base64 encoded image data
        max_size: Tuple of (max_width, max_height) for the thumbnail
        quality: JPEG quality (1-100)
        
    Returns:
        Base64 encoded thumbnail data
    """
    try:
        # Remove data URL prefix if present
        if image_data.startswith('data:'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = PILImage.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = PILImage.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create thumbnail maintaining aspect ratio
        image.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        
        # Encode to base64
        thumbnail_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{thumbnail_b64}"
        
    except Exception as e:
        logging.error(f"Thumbnail generation failed: {e}")
        return None


@login_required
@permission_required('inventory.delete_image', raise_exception=True)
def image_delete_list_view(request):
    """
    Display a list of all images that can be deleted.
    
    Shows all images in the system with their associated items,
    ordered by item name for easy navigation.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with list of images
        
    Raises:
        PermissionDenied: If user doesn't have delete_image permission
    """
    images = (Image.objects
             .select_related('item')
             .all()
             .order_by('item__name'))
    
    return render(request, "images/delete.html", {'images': images})


@login_required
@permission_required('inventory.add_image', raise_exception=True)
def image_upload_view(request, uuid):
    """
    Handle photo uploads for a specific item.
    
    Accepts base64 encoded image data via POST request and uploads both
    full-size and thumbnail versions to Cloudinary. Creates a new Image 
    record with both URLs.
    
    Args:
        request: HTTP request object (must be POST with JSON body)
        uuid: UUID of the item to upload image for
        
    Returns:
        HttpResponse: Status 201 on success, 'False' on failure
        HttpResponseForbidden: If request method is not POST
        
    Raises:
        Http404: If item with given UUID doesn't exist
        PermissionDenied: If user doesn't have add_image permission
    """
    # Ensure the request method is POST
    if request.method != 'POST':
        return HttpResponseForbidden("Method not allowed.")
    
    item = get_object_or_404(Item, id=uuid)

    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        image_data = data.get('img')
        
        # Validate that image data is present
        if not image_data:
            return HttpResponse('False')

        # Configure Cloudinary
        cloudinary.config( 
            cloud_name=settings.CLOUDINARY_CLOUD_NAME, 
            api_key=settings.CLOUDINARY_API_KEY, 
            api_secret=settings.CLOUDINARY_API_SECRET, 
            secure=True
        )

        # Define type for upload result
        class UploadResult(TypedDict):
            secure_url: str
            public_id: str
            version: int

        try:
            # Upload full-size image to Cloudinary
            upload_result = cast(
                UploadResult, 
                cloudinary.uploader.upload(image_data, resource_type="auto")
            )
            
            # Generate optimized URL with auto-format and auto-quality
            optimize_url, _ = cloudinary_url(
                upload_result["public_id"], 
                fetch_format="auto", 
                quality="auto"
            )
            
            # Generate thumbnail
            thumbnail_data = generate_thumbnail(image_data)
            thumbnail_result = None
            thumbnail_url = ""
            
            if thumbnail_data:
                try:
                    # Upload thumbnail to Cloudinary with a different public_id
                    thumbnail_result = cast(
                        UploadResult,
                        cloudinary.uploader.upload(
                            thumbnail_data, 
                            resource_type="auto",
                            public_id=f"{upload_result['public_id']}_thumb"
                        )
                    )
                    
                    # Generate optimized thumbnail URL
                    thumbnail_url, _ = cloudinary_url(
                        thumbnail_result["public_id"], 
                        fetch_format="auto", 
                        quality="auto"
                    )
                    
                except Exception as e:
                    logging.warning(f"Thumbnail upload failed, continuing with full image: {e}")
                    # If thumbnail upload fails, use the full image URL as fallback
                    thumbnail_url = optimize_url
                    thumbnail_result = upload_result
            else:
                # If thumbnail generation fails, use the full image URL as fallback
                thumbnail_url = optimize_url
                thumbnail_result = upload_result
            
        except Exception as e:
            logging.error(f"Cloudinary upload failed: {e}")
            raise Exception("Cloudinary upload failed")

        # Create new Image record in database with both URLs
        new_image = Image.objects.create(
            image_url=optimize_url,
            thumbnail_url=thumbnail_url,
            public_id=upload_result["public_id"],
            thumbnail_public_id=thumbnail_result["public_id"] if thumbnail_result else "",
            item=item,
        )

        # Log the upload event for audit trail
        before_state = audit_log_state(None)
        after_state = audit_log_state(new_image)
        
        audit_log_event(
            request.user, 
            f"Uploaded photo for item \"{item.name}\"", 
            before_state, 
            after_state, 
            entity_id=str(item.id)
        )

        return HttpResponse(status=201)

    except Exception as e:
        logging.error(f"Image upload exception: {e}")
        return HttpResponse('False')


@login_required
@permission_required('inventory.delete_image', raise_exception=True)
def image_delete_view(request, uuid):
    """
    Delete a specific image from the system.
    
    Removes the image record from the database and optionally deletes
    both full-size and thumbnail images from Cloudinary based on system settings.
    
    Args:
        request: HTTP request object
        uuid: UUID of the image to delete
        
    Returns:
        HttpResponseRedirect: Redirect to previous page or image list
        
    Raises:
        Http404: If image with given UUID doesn't exist
        PermissionDenied: If user doesn't have delete_image permission
    """
    image = get_object_or_404(Image, id=uuid)
    
    # Log the state before deletion
    before_state = audit_log_state(image)
    item_name = image.item.name
    item_id = image.item.id
    
    # Delete from Cloudinary if configured to do so
    if settings.DELETE_CLOUDINARY_IMAGES:
        try:
            # Delete full-size image
            if image.public_id:
                cloudinary.uploader.destroy(image.public_id)
            
            # Delete thumbnail if it exists and is different from the main image
            if (image.thumbnail_public_id and 
                image.thumbnail_public_id != image.public_id):
                cloudinary.uploader.destroy(image.thumbnail_public_id)
                
        except Exception as e:
            logging.error(f"Error deleting image from Cloudinary: {e}")
            raise e
    
    # Delete the image record
    image.delete()
    
    # Log the deletion event
    after_state = audit_log_state(None)
    audit_log_event(
        request.user, 
        f"Deleted image from item \"{item_name}\"", 
        before_state, 
        after_state, 
        entity_id=str(item_id)
    )

    # Redirect to previous page if available, otherwise to image list
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    
    return HttpResponseRedirect(reverse('delete_image_list_view'))