"""
Image management views for the inventory application.

This module handles image upload, deletion, and management functionality
for inventory items. Images are stored using Cloudinary service.
"""

import json
import logging
from typing import TypedDict, cast
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from inventory.models import Item, Image
from .utils import audit_log_state, audit_log_event


def generate_thumbnail_url(public_id, width=150, height=150):
    """
    Generate a thumbnail URL using Cloudinary transformations.
    
    Args:
        public_id: Cloudinary public ID of the image
        width: Thumbnail width (default: 150)
        height: Thumbnail height (default: 150)
        
    Returns:
        Thumbnail URL string using Cloudinary transformations
    """
    try:
        thumbnail_url, _ = cloudinary_url(
            public_id,
            width=width,
            height=height,
            crop="fill",
            quality="auto",
            fetch_format="auto"
        )
        return thumbnail_url
    except Exception as e:
        logging.error(f"Thumbnail URL generation failed: {e}")
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
            
            # Generate thumbnail URL using Cloudinary transformations
            thumbnail_url = generate_thumbnail_url(upload_result["public_id"])
            
            # Use the original image URL as fallback if thumbnail URL generation fails
            if not thumbnail_url:
                thumbnail_url = optimize_url
            
        except Exception as e:
            logging.error(f"Cloudinary upload failed: {e}")
            raise Exception("Cloudinary upload failed")

        # Create new Image record in database with both URLs
        new_image = Image.objects.create(
            image_url=optimize_url,
            thumbnail_url=thumbnail_url,
            public_id=upload_result["public_id"],
            thumbnail_public_id="",  # No separate thumbnail uploaded - using transformations
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
            # Delete the main image - thumbnails are generated via transformations
            if image.public_id:
                cloudinary.uploader.destroy(image.public_id)
                
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