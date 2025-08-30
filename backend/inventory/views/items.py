"""
Item management views for the inventory application.

This module handles CRUD operations for inventory items, including
item creation, viewing, editing, deletion (soft delete), and restoration.
Items are the core entities in the inventory system.
"""

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import UpdateView, CreateView

from inventory import models
from inventory.forms import ItemForm
from inventory.models import Category, Item, Subcategory, AuditEvent
from .utils import audit_log_state, audit_log_event


def view_database(request):
    """
    Display the main database view with all categories and subcategories.
    
    Shows a hierarchical view of the database structure with categories
    and their related subcategories.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with categories and subcategories
    """
    # Use prefetch_related to efficiently load subcategories
    categories = Category.objects.prefetch_related('subcategories').all().order_by('name')

    context = {
        'categories': categories,
    }

    template = loader.get_template("view.html")
    return HttpResponse(template.render(context, request))


def view_all_items(request):
    """
    Display all items in the inventory system.
    
    Shows a comprehensive list of all items with their category and
    subcategory information.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with all items
    """
    # Fetch all items with related category and subcategory data
    items = (Item.objects
            .select_related('category', 'subcategory')
            .all()
            .order_by('name'))

    context = {
        'items': items,
        'category': "All Items"
    }

    template = loader.get_template("view/category.html")
    return HttpResponse(template.render(context, request))


def view_category_items(request, uuid):
    """
    Display all items belonging to a specific category.
    
    Args:
        request: HTTP request object
        uuid: UUID of the category to view
        
    Returns:
        HttpResponse: Rendered template with category items
        
    Raises:
        Http404: If category with given UUID doesn't exist
    """
    category = get_object_or_404(Category, id=uuid)
    
    # Fetch items in the category with related data
    items = (Item.objects
            .filter(category=category)
            .select_related('category', 'subcategory')
            .order_by('name'))

    context = {
        'category': category,
        'items': items,
    }

    template = loader.get_template("view/category.html")
    return HttpResponse(template.render(context, request))


def view_subcategory_items(request, uuid):
    """
    Display all items belonging to a specific subcategory.
    
    Args:
        request: HTTP request object
        uuid: UUID of the subcategory to view
        
    Returns:
        HttpResponse: Rendered template with subcategory items
        
    Raises:
        Http404: If subcategory with given UUID doesn't exist
    """
    subcategory = get_object_or_404(Subcategory, id=uuid)
    
    # Fetch items in the subcategory with related data
    items = (Item.objects
            .filter(subcategory=subcategory)
            .select_related('category', 'subcategory')
            .order_by('name'))

    context = {
        'subcategory': subcategory,
        'items': items,
    }
    
    template = loader.get_template("view/subcategory.html")
    return HttpResponse(template.render(context, request))


def view_item_detail(request, uuid):
    """
    Display detailed information for a specific item.
    
    Shows item details, associated images, and audit history.
    Handles permissions for viewing deleted items.
    
    Args:
        request: HTTP request object
        uuid: UUID of the item to view
        
    Returns:
        HttpResponse: Rendered template with item details
        HttpResponseForbidden: If user doesn't have permission to view deleted item
        
    Raises:
        Http404: If item with given UUID doesn't exist
    """
    # Use all_objects manager to include deleted items
    item = get_object_or_404(
        Item.all_objects.select_related('category', 'subcategory'),
        id=uuid
    )

    # Check permissions for viewing deleted items
    if (item.is_deleted and 
        (not request.user.is_authenticated or 
         not request.user.has_perm('inventory.view_deleteditem'))):
        return HttpResponseForbidden()

    # Fetch related images and audit events
    images = item.images.all().order_by('id')
    events = AuditEvent.objects.filter(entity_id=uuid).order_by('created_at')

    # Prepare audit events for template display
    for event in events:
        event.json_data = {
            'before': event.before,
            'after': event.after,
        }

    context = {
        'item': item,
        'images': images,
        'audit': events,
    }
    
    template = loader.get_template("view/item.html")
    return HttpResponse(template.render(context, request))


@login_required
@permission_required('inventory.delete_item', raise_exception=True)
def item_soft_delete_view(request, uuid):
    """
    Soft delete an item by marking it as deleted.
    
    This preserves the item data while hiding it from normal views.
    The item can be restored later if needed.
    
    Args:
        request: HTTP request object
        uuid: UUID of the item to delete
        
    Returns:
        HttpResponseRedirect: Redirect to dashboard after deletion
        
    Raises:
        Http404: If item with given UUID doesn't exist
        PermissionDenied: If user doesn't have delete_item permission
    """
    item = get_object_or_404(Item, id=uuid)
    
    # Log the state before deletion
    before_state = audit_log_state(item)
    
    # Perform soft delete
    item.is_deleted = True
    item.save()
    
    # Log the deletion event
    after_state = audit_log_state(item)
    audit_log_event(
        request.user, 
        f"Deleted item \"{item.name}\"", 
        before_state, 
        after_state
    )
    
    return redirect('dashboard')


@login_required
@permission_required('inventory.restore_deleteditem', raise_exception=True)
def item_restore_view(request, uuid):
    """
    Restore a previously deleted item.
    
    Undoes the soft delete operation by marking the item as active again.
    
    Args:
        request: HTTP request object
        uuid: UUID of the item to restore
        
    Returns:
        HttpResponseRedirect: Redirect to item detail view after restoration
        
    Raises:
        Http404: If item with given UUID doesn't exist
        PermissionDenied: If user doesn't have restore_deleteditem permission
    """
    item = get_object_or_404(Item.all_objects, id=uuid)
    
    # Log the state before restoration
    before_state = audit_log_state(item)
    
    # Restore the item
    item.is_deleted = False
    item.save()
    
    # Log the restoration event
    after_state = audit_log_state(item)
    audit_log_event(
        request.user, 
        f"Restored item \"{item.name}\"", 
        before_state, 
        after_state
    )
    
    return redirect('view_item', uuid=uuid)


@login_required
@permission_required('inventory.view_deleteditem', raise_exception=True)
def view_deleted_items(request):
    """
    Display all items that have been soft deleted.
    
    Shows a list of all deleted items for administrative review.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with deleted items
        
    Raises:
        PermissionDenied: If user doesn't have view_deleteditem permission
    """
    deleted_items = Item.all_objects.filter(is_deleted=True)
    context = {
        'category': {"name": "Deleted Items"}, 
        'items': deleted_items
    }
    
    return render(request, 'view/category.html', context)


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Class-based view for updating item information.
    
    Provides a form for editing item details and handles the update process
    with proper audit logging of changes.
    """
    model = models.Item
    form_class = ItemForm
    template_name = "edit/item.html"
    permission_required = 'inventory.change_item'

    def form_valid(self, form):
        """
        Process valid form submission and log the changes.
        
        Args:
            form: Valid ItemForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
        """
        # Get the current state before changes for audit logging
        before_model = models.Item.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(self.object)
        audit_log_event(
            self.request.user, 
            f"Updated item \"{before_model.name}\"", 
            before_state, 
            after_state
        )
        
        return response

    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the updated item's detail view
        """
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Class-based view for creating new items.
    
    Provides a form for creating new inventory items and handles the creation
    process with proper audit logging.
    """
    model = models.Item
    form_class = ItemForm
    template_name = "register/item.html"
    permission_required = 'inventory.add_item'

    def form_valid(self, form):
        """
        Process valid form submission and log the creation.
        
        Args:
            form: Valid ItemForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to new item's detail view
        """
        # Log the creation event
        before_state = audit_log_state(None)
        new_item = form.save(commit=False)
        after_state = audit_log_state(new_item)
        
        audit_log_event(
            self.request.user, 
            f"Created item \"{new_item.name}\"", 
            before_state, 
            after_state
        )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the new item's detail view
        """
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})