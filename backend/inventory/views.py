import json
import logging
from typing import TypedDict, cast
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django import forms
from django.urls import reverse, reverse_lazy
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView, CreateView
from django.conf import settings

from inventory import models
from inventory.forms import CategoryForm, ItemForm, SubcategoryForm
from inventory.models import AuditEvent, Category, Image, Item, Subcategory

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


def index(request):
    # Redirect to dashboard
    return HttpResponseRedirect(reverse("dashboard"))

def dashboard(request):
    template = loader.get_template("dashboard.html")
    return HttpResponse(template.render({}, request))


def audit_view(request):
    """
    Renders the audit log page.
    """
    events = AuditEvent.objects.all().order_by('-created_at')

    # Prepare data for the template
    for event in events:
        # Manually serialize the relevant data to a JSON string
        event.json_data = json.dumps({
            'before': event.before,
            'after': event.after,
        })
        
    context = {
        'events': events,
    }
    template = loader.get_template("audit.html")
    return HttpResponse(template.render(context, request))

def delete_category_list_view(request):
    categories = Category.objects.all().order_by('name')
    template = loader.get_template("delete/category.html")
    return HttpResponse(template.render({'categories': categories}, request))

@login_required
def delete_category(request, uuid):
    # Check for admin privileges
    # if not request.user.has_perm('inventory.delete_category'):
    #     return #redirect('permission_error') # You need to create this URL

    # Get the category object or return a 404 error if not found
    category = get_object_or_404(Category, pk=uuid)

    # Perform the deletion
    category.delete()

    return redirect('dashboard')

def delete_image_list_view(request):
    # Use select_related('item') to join the Image and Item tables in the database query.
    # This makes the data available without additional queries in the template.
    images = Image.objects.select_related('item').all().order_by('item__name')

    print(images)
    
    # The template loader is not strictly necessary here, render() is a shortcut for this
    template = loader.get_template("delete/image.html")
    return HttpResponse(template.render({'images': images}, request))

def profile_view(request):
    return HttpResponseRedirect(reverse("dashboard"))

def delete_subcategory_list_view(request):
    """
    Fetches all subcategories from the database and pre-fetches
    their related category data using select_related() for efficiency.
    """
    subcategories = Subcategory.objects.select_related('category').all().order_by('category__name', 'name')


    context = {
        'subcategories': subcategories
    }
    
    # Render the template and pass the context data.
    template = loader.get_template("delete/subcategory.html")
    return HttpResponse(template.render(context, request))


@login_required
def delete_subcategory(request, uuid):
    # Check for admin privileges
    # if not request.user.has_perm('inventory.delete_subcategory'):
    #     return #redirect('permission_error') # You need to create this URL

    # Get the subcategory object or return a 404 error if not found
    subcategory = get_object_or_404(Subcategory, pk=uuid)

    # Perform the deletion
    subcategory.delete()

    return redirect('dashboard')


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "edit/category.html"
    success_url = reverse_lazy('dashboard')

class ItemUpdateView(LoginRequiredMixin, UpdateView):
    model = models.Item
    form_class = ItemForm
    template_name = "edit/item.html"
    success_url = reverse_lazy('dashboard')

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = models.Category
    form_class = CategoryForm
    template_name = "register/category.html"
    success_url = reverse_lazy('dashboard')

class SubcategoryCreateView(LoginRequiredMixin, CreateView):
    model = models.Subcategory
    form_class = SubcategoryForm
    template_name = "register/subcategory.html"
    success_url = reverse_lazy('dashboard')

class ItemCreateView(LoginRequiredMixin, CreateView):
    model = models.Item
    form_class = ItemForm
    template_name = "register/item.html"
    success_url = reverse_lazy('dashboard')

def view_database(request):
    """
    Fetches all categories and their related subcategories.
    `prefetch_related` is used for efficiency to avoid N+1 query problem.
    """
    categories = Category.objects.prefetch_related('subcategories').all().order_by('name')

    context = {
        'categories': categories,
    }

    template = loader.get_template("view.html")
    return HttpResponse(template.render(context, request))

def view_all_items(request):
    """
    Fetches all items from the database.
    `select_related` is used to efficiently retrieve related category and subcategory data.
    """
    # Fetch all items and pre-fetch their related category and subcategory data.
    items = Item.objects.select_related('category', 'subcategory').all().order_by('name')

    context = {
        'items': items,
        'category': "All Items"
    }

    template = loader.get_template("view/category.html")
    return HttpResponse(template.render(context, request))

def view_category_items(request, uuid):
    """
    Fetches a specific category and all its related items.
    """
    # Get the Category object based on the UUID, or return a 404 error if it doesn't exist.
    category = get_object_or_404(Category, id=uuid)
    
    # Fetch all items belonging to the selected category.
    # Use `select_related` to optimize database queries for related data.
    items = Item.objects.filter(category=category).select_related('category', 'subcategory').order_by('name')

    context = {
        'category': category,
        'items': items,
    }

    template = loader.get_template("view/category.html")
    return HttpResponse(template.render(context, request))

def view_subcategory_items(request, uuid):
    """
    Fetches a specific subcategory and all its related items.
    """
    # Get the Subcategory object based on the UUID, or return a 404 error.
    subcategory = get_object_or_404(Subcategory, id=uuid)
    
    # Fetch all items belonging to the selected subcategory.
    # Use `select_related` to fetch the related category and subcategory data efficiently.
    items = Item.objects.filter(subcategory=subcategory).select_related('category', 'subcategory').order_by('name')

    context = {
        'subcategory': subcategory,
        'items': items,
    }
    
    template = loader.get_template("view/subcategory.html")
    return HttpResponse(template.render(context, request))

def view_item(request, uuid):
    """
    Fetches a specific item and all its related data.
    """
    # Get the Item object based on the UUID, or return a 404 error.
    # Use select_related to get the related category and subcategory efficiently.
    item = get_object_or_404(
        Item.objects.select_related('category', 'subcategory'),
        id=uuid
    )
    
    # Fetch all images related to the item.
    images = Image.objects.filter(item=item).order_by('id')
    
    # Fetch all audit events for the item.
    audit = AuditEvent.objects.filter(entity_id=uuid).order_by('created_at')

    context = {
        'item': item,
        'images': images,
        'audit': audit,
    }
    
    template = loader.get_template("view/item.html")
    return HttpResponse(template.render(context, request))

@login_required
def restore_subcategory(request, uuid):
    """
    Restores a deleted subcategory.
    """

    # Get the Subcategory object or return a 404 error if it doesn't exist.
    subcategory = get_object_or_404(Subcategory, id=uuid)

    # Update the 'deleted' field and save the object.
    subcategory.deleted = False
    subcategory.save()

    # Redirect to the view page for the restored subcategory.
    return redirect('view_subcategory_items', uuid=uuid)

@login_required
def delete_item(request, uuid):
    """
    Deletes an item by setting its 'deleted' status to True.
    """

    # Get the item or return a 404 error if it doesn't exist.
    item = get_object_or_404(Item, id=uuid)
    
    # "Soft-delete" the item by setting the deleted flag.
    item.deleted = True
    item.save()
    
    # Redirect to the item's view page after successful deletion.
    return redirect('view_item', uuid=uuid)

@login_required
def restore_item(request, uuid):
    """
    Restores a deleted item.
    """

    # Get the Item object or return a 404 error if it doesn't exist.
    item = get_object_or_404(Item, id=uuid)

    # Update the 'deleted' field and save the object.
    item.deleted = False
    item.save()

    # Redirect to the view page for the restored item.
    return redirect('view_item', uuid=uuid)

@login_required
def upload_photo(request, uuid):
    """
    Handles photo uploads for an item.
    """
    # Ensure the request method is POST.
    if request.method != 'POST':
        return HttpResponseForbidden("Method not allowed.")
    
    # Get the item or return a 404 error if it doesn't exist.
    item = get_object_or_404(Item, id=uuid)

    try:
        # Parse the JSON data from the request body.
        data = json.loads(request.body)
        image_data = data.get('img')
        
        # Check if the base64 image data is present.
        if not image_data:
            return HttpResponse('False')

        # Make a POST request to the Imgur API.
    
        # Configuration       
        cloudinary.config( 
            cloud_name = settings.CLOUDINARY_CLOUD_NAME, 
            api_key = settings.CLOUDINARY_API_KEY, 
            api_secret = settings.CLOUDINARY_API_SECRET, 
            secure=True
        )

        # Upload an image
        class UploadResult(TypedDict):
            secure_url: str
            public_id: str
            version: int

        try:

            upload_result = cast(UploadResult, cloudinary.uploader.upload(image_data, resource_type="auto"))
            # Optimize delivery by resizing and applying auto-format and auto-quality
            optimize_url, _ = cloudinary_url(upload_result["public_id"], fetch_format="auto", quality="auto")
        except Exception as e:
            logging.error(f"An error occurred during image upload: {e}")
            raise Exception("Cloudinary upload failed")

       
        # Create a new Image object and save it to the database.
        Image.objects.create(
            image_url=optimize_url,
            public_id=upload_result["public_id"],
            item=item,
        )
     
        return HttpResponse(status=201)

    except Exception as e:
        logging.error(f"An exception occurred during image upload: {e}")
        return HttpResponse('False')
    
@login_required
def restore_category(request, uuid):
    """
    Restores a deleted item.
    """

    # Get the Category object or return a 404 error if it doesn't exist.
    category = get_object_or_404(Category, id=uuid)

    # Update the 'deleted' field and save the object.
    category.deleted = False
    category.save()

    # Redirect to the view page for the restored item.
    return redirect('view_category', uuid=uuid)

@login_required
def delete_image(request, uuid):
    """
    Deletes an image by setting its 'deleted' status to True.
    """

    # Get the image or return a 404 error if it doesn't exist.
    image = get_object_or_404(Image, id=uuid)

    # Delete from cloudinary
    try:
        cloudinary.uploader.destroy(image.public_id)
    except Exception as e:
        logging.error(f"An error occurred while deleting image from Cloudinary: {e}")
        raise e
    
    image.delete()

    referer = request.META.get('HTTP_REFERER')  # full URL of previous page
    if referer:
        return HttpResponseRedirect(referer)
    return HttpResponseRedirect(reverse('delete_image_list_view'))