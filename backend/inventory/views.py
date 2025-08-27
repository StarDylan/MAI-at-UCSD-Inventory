from dataclasses import dataclass
from django.dispatch import receiver
from django.forms.models import model_to_dict
import json
import logging
from typing import TypedDict, cast, Any
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django import forms
from django.urls import reverse, reverse_lazy
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.views.generic import UpdateView, CreateView, FormView
from django.conf import settings
from django.contrib import messages
from django.db.models import F
from django.core import serializers
from django.db.models.signals import pre_save


from inventory import models
from inventory.forms import CategoryForm, ItemForm, Search_QuantityAdd, Search_QuantityRemove, SubcategoryForm, UserCreationForm
from inventory.models import AuditEvent, Category, Image, Item, Subcategory, User

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Helper function to log audit events
@dataclass
class ObjState:
    json_data: str
    id: int
    class_name: str


def audit_log_state(obj):
    if obj is None:
        return ObjState(
            json_data=json.dumps({}),
            id=None,
            class_name=None
        )

    return ObjState(
        json_data=json.dumps(model_to_dict(obj), default=str),
        id=obj.id,
        class_name=obj.__class__.__name__
    )

def audit_log_event(user, event: str, before_state: ObjState, after_state: ObjState, entity_id: str = None):
    AuditEvent.objects.create(
        user=user,
        event=event,
        entity_type=before_state.class_name or after_state.class_name,
        entity_id=entity_id or before_state.id or after_state.id,
        before=before_state.json_data,
        after=after_state.json_data,
    )


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
    events = AuditEvent.objects.all().select_related("user").order_by('-created_at')

    events = cast(list[Any], events)

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
    categories = Category.objects.filter(subcategories__isnull=True).order_by('name')
    template = loader.get_template("delete/category.html")
    return HttpResponse(template.render({'categories': categories}, request))

@login_required
def delete_category(request, uuid):
    # Check for admin privileges
    # if not request.user.has_perm('inventory.delete_category'):
    #     return #redirect('permission_error') # You need to create this URL

    # Get the category object or return a 404 error if not found
    category = get_object_or_404(Category, pk=uuid)

    before = audit_log_state(category)
    category_name = category.name

    # Perform the deletion
    category.delete()

    after = audit_log_state(None)

    audit_log_event(request.user, f"Deleted category {category_name}", before, after)

    return redirect('dashboard')

def delete_image_list_view(request):
    images = Image.objects.select_related('item').all().order_by('item__name')
    return render(request, "delete/image.html", {'images': images})

def profile_view(request):
    return HttpResponseRedirect(reverse("dashboard"))


def delete_subcategory_list_view(request):
    """
    Fetches all subcategories from the database and pre-fetches
    their related category data using select_related() for efficiency.
    """
    subcategories = Subcategory.objects.select_related('category').filter(items__isnull=True).order_by('category__name', 'name')


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

    before = audit_log_state(subcategory)

    # Perform the deletion
    subcategory.delete()

    after = audit_log_state(None)

    audit_log_event(request.user, f"Deleted subcategory {subcategory.name}", before, after)

    return redirect('dashboard')


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "edit/category.html"
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        
        before_model = Category.objects.get(pk=form.instance.pk)
        before = audit_log_state(before_model)

        after = audit_log_state(self.object)

        audit_log_event(self.request.user, f"Updated category \"{before_model.name}\" to \"{self.object.name}\"", before, after)

        return super().form_valid(form)

class ItemUpdateView(LoginRequiredMixin, UpdateView):
    model = models.Item
    form_class = ItemForm
    template_name = "edit/item.html"

    def form_valid(self, form):
        
        before_model = models.Item.objects.get(pk=form.instance.pk)
        before = audit_log_state(before_model)

        after = audit_log_state(self.object)

        audit_log_event(self.request.user, f"Updated item \"{before_model.name}\"", before, after)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = models.Category
    form_class = CategoryForm
    template_name = "register/category.html"
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        before = audit_log_state(None)

        new_category = form.save(commit=False)

        after = audit_log_state(new_category)

        audit_log_event(self.request.user, f"Created category \"{new_category.name}\"", before, after)

        return super().form_valid(form)

class SubcategoryCreateView(LoginRequiredMixin, CreateView):
    model = models.Subcategory
    form_class = SubcategoryForm
    template_name = "register/subcategory.html"
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        before = audit_log_state(None)

        new_subcategory = form.save(commit=False)

        after = audit_log_state(new_subcategory)

        audit_log_event(self.request.user, f"Created subcategory \"{new_subcategory.name}\"", before, after)

        return super().form_valid(form)

class ItemCreateView(LoginRequiredMixin, CreateView):
    model = models.Item
    form_class = ItemForm
    template_name = "register/item.html"
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        before = audit_log_state(None)

        new_item = form.save(commit=False)

        after = audit_log_state(new_item)

        audit_log_event(self.request.user, f"Created item \"{new_item.name}\"", before, after)

        return super().form_valid(form)

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

# TODO: Viewing a deleted item requires extra permissions
def view_item(request, uuid):
    """
    Fetches a specific item and all its related data.
    """
    # Get the Item object based on the UUID, or return a 404 error.
    # Use select_related to get the related category and subcategory efficiently.
    item = get_object_or_404(
        Item.all_objects.select_related('category', 'subcategory'),
        id=uuid
    )
    
    # Fetch all images related to the item.
    images = Image.objects.filter(item=item).order_by('id')
    
    # Fetch all audit events for the item.
    events = AuditEvent.objects.filter(entity_id=uuid).order_by('created_at')

    for event in events:
        # Manually serialize the relevant data to a JSON string
        event.json_data = json.dumps({
            'before': event.before,
            'after': event.after,
        })

    context = {
        'item': item,
        'images': images,
        'audit': events,
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

    before = audit_log_state(subcategory)

    # Update the 'deleted' field and save the object.
    subcategory.is_deleted = False
    subcategory.save()

    after = audit_log_state(subcategory)

    audit_log_event(request.user, f"Restored subcategory \"{subcategory.name}\"", before, after)

    # Redirect to the view page for the restored subcategory.
    return redirect('view_subcategory_items', uuid=uuid)

@login_required
def delete_item(request, uuid):
    """
    Deletes an item by setting its 'deleted' status to True.
    """


    # Get the item or return a 404 error if it doesn't exist.
    item = get_object_or_404(Item, id=uuid)

    before = audit_log_state(item)

    # "Soft-delete" the item by setting the deleted flag.
    item.is_deleted = True
    item.save()

    after = audit_log_state(item)

    audit_log_event(request.user, f"Deleted item \"{item.name}\"", before, after)

    # Redirect to the item's view page after successful deletion.
    return redirect('view_item', uuid=uuid)

@login_required
def restore_item(request, uuid):
    """
    Restores a deleted item.
    """

    # Get the Item object or return a 404 error if it doesn't exist.
    item = get_object_or_404(Item.all_objects, id=uuid)

    before = audit_log_state(item)

    # Update the 'deleted' field and save the object.
    item.is_deleted = False
    item.save()

    after = audit_log_state(item)

    audit_log_event(request.user, f"Restored item \"{item.name}\"", before, after)

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
        new_image = Image.objects.create(
            image_url=optimize_url,
            public_id=upload_result["public_id"],
            item=item,
        )

        before = audit_log_state(None)
        after = audit_log_state(new_image)

        # We associate the uploaded image with the item, since that is where we create them
        audit_log_event(request.user, f"Uploaded photo for item \"{item.name}\"", before, after, entity_id=item.id)

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

    before = audit_log_state(category)

    # Update the 'deleted' field and save the object.
    category.is_deleted = False
    category.save()

    after = audit_log_state(category)

    audit_log_event(request.user, f"Restored category \"{category.name}\"", before, after)

    # Redirect to the view page for the restored item.
    return redirect('view_category', uuid=uuid)

@login_required
def delete_image(request, uuid):
    """
    Deletes an image
    """

    # Get the image or return a 404 error if it doesn't exist.
    image = get_object_or_404(Image, id=uuid)

    before = audit_log_state(image)

    # Don't actually delete from cloudinary

    if settings.DELETE_CLOUDINARY_IMAGES:
        try:
            cloudinary.uploader.destroy(image.public_id)
        except Exception as e:
            logging.error(f"An error occurred while deleting image from Cloudinary: {e}")
            raise e
    
    image.delete()

    after = audit_log_state(None)

    audit_log_event(request.user, f"Deleted image from item \"{image.item.name}\"", before, after, entity_id=image.item.id)

    referer = request.META.get('HTTP_REFERER')  # full URL of previous page
    if referer:
        return HttpResponseRedirect(referer)
    return HttpResponseRedirect(reverse('delete_image_list_view'))

class SearchCheckInView(LoginRequiredMixin, FormView):
    """
    A Django generic view to handle the "check in" item form.
    It combines LoginRequiredMixin and a custom PermissionRequiredMixin
    to handle authentication and authorization.
    """
    template_name = 'search/updateqty.html'  # Use the name of your template file
    form_class = Search_QuantityAdd

    def get_context_data(self, **kwargs):
        """
        Passes extra context variables to the template.
        """
        context = super().get_context_data(**kwargs)
        context['action'] = 'Check in'
        context['defaultQuantity'] = 1
        context["items"] = Item.objects.all().order_by('name')
        return context

    def form_valid(self, form):
        """
        This method is called when the form is submitted and all fields are valid.
        It handles the database update and redirection.
        """
        item = form.cleaned_data['item']
        quantity = form.cleaned_data['quantity']

        item = get_object_or_404(Item, id=item.id)
        before = audit_log_state(item)
        item.quantity_active += quantity
        item.save()
        after = audit_log_state(item)

        audit_log_event(self.request.user, f"Checked in {quantity} of item \"{item.name}\"", before, after)

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))

    def form_invalid(self, form):
        """
        This method is called when the form submission fails validation.
        The template will automatically display form errors.
        """
        messages.error(self.request, "Form submission failed. Please check the fields below.")
        return super().form_invalid(form)

class SearchCheckOutView(LoginRequiredMixin, FormView):
    """
    A Django generic view to handle the "check out" item form.
    It combines LoginRequiredMixin and a custom PermissionRequiredMixin
    to handle authentication and authorization.
    """
    template_name = 'search/updateqty.html'  # Use the name of your template file
    form_class = Search_QuantityRemove

    def get_context_data(self, **kwargs):
        """
        Passes extra context variables to the template.
        """
        context = super().get_context_data(**kwargs)
        context['action'] = 'Check out'
        # context['defaultQuantity'] = 1
        context["items"] = Item.objects.all().order_by('name')
        return context

    def form_valid(self, form: Search_QuantityRemove):
        """
        This method is called when the form is submitted and all fields are valid.
        It handles the database update and redirection.
        """
        item = form.cleaned_data['item']
        quantity = form.cleaned_data['quantity']

        item = get_object_or_404(Item, id=item.id)
        before = audit_log_state(item)

        if item.quantity_active < quantity:
            form.add_error('quantity', f"Cannot check out {quantity} items. Only {item.quantity_active} available.")
            return self.form_invalid(form)

        item.quantity_active -= quantity
        item.save()
        after = audit_log_state(item)

        audit_log_event(self.request.user, f"Checked out {quantity} of item \"{item.name}\"", before, after)

        return redirect(reverse_lazy('view_item', kwargs={'uuid': item.id}))


def view_deleted_items(request):
    """
    View to display all deleted items.
    """
    deleted_items = Item.all_objects.filter(is_deleted=True)
    return render(request, 'view/category.html', {'category': {"name": "Deleted Items"}, 'items': deleted_items})


def logout_view(request):
    logout(request)
    return redirect('home')



def is_admin(user):
    """
    Check if a user is in the 'Admin' group.
    This is used for the @user_passes_test decorator to restrict access.
    """
    return user.groups.filter(name='Admin').exists()

@login_required
def manage_users_view(request):
    """
    Renders the template for managing users based on group membership.
    Only users in the 'Admin' group can access this view.
    """
    # Fetch all users and pre-fetch their group information for efficiency.
    # This avoids a large number of database queries in the template loop.
    all_users = models.User.objects.all().prefetch_related('groups')

    users_data = []
    for user_obj in all_users:
        users_data.append({
            'id': user_obj.id,
            'username': user_obj.username,
            'is_active': user_obj.is_active,
            # Check for group membership and store as booleans.
            'is_user': user_obj.groups.filter(name='User').exists(),
            'is_member': user_obj.groups.filter(name='Member').exists(),
            'is_admin': user_obj.groups.filter(name='Admin').exists(),
        })

    context = {
        'users': users_data,
        'user': request.user,
    }

    return render(request, "view/users.html", context)


@login_required
def edit_user_role_api(request, pk):
    """
    API endpoint to change a user's role by assigning them to a new group.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        new_group_name = data.get("group_name")

        # Find the user and the new group, or return a 404 error.
        user_to_edit = get_object_or_404(models.User, pk=pk)
        new_group = get_object_or_404(Group, name=new_group_name)
        before = audit_log_state(user_to_edit)

        # Clear all current groups for the user before adding the new one.
        user_to_edit.groups.clear()
        user_to_edit.groups.add(new_group)

        after = audit_log_state(user_to_edit)

        audit_log_event(request.user, f"Changed user \"{user_to_edit.username}\" role to \"{new_group.name}\"", before, after)

        return HttpResponse(status=200)
    
    # Return an error for unsupported request methods.
    return HttpResponse(status=405)


@login_required
def view_user_profile_view(request, pk):
    """
    Renders a user's profile page, including their details and audit logs.
    This view is restricted to users in the 'Admin' group.

    Args:
        request: The HTTP request object.
        pk (int): The primary key of the user to view.
    """
    # Fetch the user object or return a 404 error if not found.
    # We use prefetch_related for groups and select_related for the profile
    # to reduce the number of database queries.
    viewed_user = get_object_or_404(models.User.objects.prefetch_related('groups'), pk=pk)

    # Determine the user's primary role based on group membership.
    user_role = "User" # Default role
    if viewed_user.groups.filter(name='Member').exists():
        user_role = "Member"
    if viewed_user.groups.filter(name='Admin').exists():
        user_role = "Admin"

    # Placeholder for fetching audit logs. You would replace this with
    # your actual database queries. The example data mimics the structure.
    # Here, we assume a model called AuditEvent exists with fields
    # like 'user_by_id', 'user_on_id', and 'timestamp'.
    
    # Example queries for audit logs
    audit_by_user = AuditEvent.objects.filter(user_id=pk).order_by('-created_at')
    audit_on_user = AuditEvent.objects.filter(entity_id=pk).order_by('-created_at')

    context = {
        'user_data': {
            'user_id': viewed_user.id,
            'user_name': viewed_user.username,
            'user_email': viewed_user.email,
            'user_role': user_role,
            'user_active': viewed_user.is_active,
            'user_picture': viewed_user.user_picture,
        },
        'audit_by_user': audit_by_user,
        'audit_on_user': audit_on_user,
    }

    return render(request, "view/user.html", context)


def delete_user_view(request, pk):
    """
    Handles the deletion of a user by setting their is_active status to False.
    This is a soft-delete, preserving the user's data.
    Restricted to users in the 'Admin' group.
    """
    user_to_delete = get_object_or_404(models.User, pk=pk)
    # Prevent an admin from deleting themselves
    if user_to_delete == request.user:
        return HttpResponse("You cannot delete your own account.", status=403)

    before = audit_log_state(user_to_delete)

    user_to_delete.is_active = False
    user_to_delete.save()

    after = audit_log_state(user_to_delete)

    audit_log_event(request.user, f"Deleted user \"{user_to_delete.username}\"", before, after)

    return redirect('view_user', pk=pk)


def restore_user_view(request, pk):
    """
    Handles the restoration of a user by setting their is_active status to True.
    Restricted to users in the 'Admin' group.
    """
    user_to_restore = get_object_or_404(models.User, pk=pk)
    before = audit_log_state(user_to_restore)

    user_to_restore.is_active = True
    user_to_restore.save()

    after = audit_log_state(user_to_restore)

    audit_log_event(request.user, f"Restored user \"{user_to_restore.username}\"", before, after)

    return redirect('view_user', pk=pk)

class UserCreateView(FormView):
    """
    View to display a user creation form and process its submission.
    """
    template_name = 'register/user.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('manage_users')  # Replace with your success URL

    def form_valid(self, form):
        """
        This method is called when the form is valid.
        It creates a new user and saves them to the database.
        """
        username = form.cleaned_data['username']
        email = form.cleaned_data['email']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']

        if User.objects.filter(username=username).exists():
            form.add_error('username', 'Username already exists.')
            return self.form_invalid(form)
    
        if User.objects.filter(email=email).exists():
            form.add_error('email', 'Email already exists.')
            return self.form_invalid(form)
            

        # Use Django's built-in create_user to handle password hashing securely.
        new_user = User.objects.create_user(username=username, email=email, first_name=first_name, last_name=last_name)

        before = audit_log_state(None)
        after = audit_log_state(new_user)

        audit_log_event(self.request.user, f"Created user \"{new_user.username}\"", before, after)

        return super().form_valid(form)
