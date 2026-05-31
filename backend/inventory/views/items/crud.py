"""
Item CRUD (Create, Read, Update) views for inventory items.
"""

from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.generic import UpdateView, CreateView
from django.db.models import Prefetch
from datetime import datetime

from inventory import models
from inventory.forms import StockItemEditForm
from inventory.forms_tags import TaggedItemForm, TaggedItemWithStockForm
from ..utils import audit_log_state, audit_log_event


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Class-based view for updating item information.
    
    Provides a form for editing item details and handles the update process
    with proper audit logging of changes.
    """
    model = models.Item
    form_class = TaggedItemForm
    template_name = "items/edit.html"
    permission_required = 'inventory.change_item'
    
    def get_object(self, queryset=None):
        """
        Override get_object to prefetch related tags with their tag_groups
        to avoid N+1 queries when rendering the form.
        """
        if queryset is None:
            queryset = self.get_queryset()
            
        # Use prefetch_related to efficiently load tags and their tag_groups
        queryset = queryset.prefetch_related(
            Prefetch(
                'tags',
                queryset=models.Tag.objects.filter(
                    is_active=True, 
                    tag_group__is_active=True
                ).select_related('tag_group')
            )
        )
        
        # Get the object using the pk from the URL
        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk)
            
        obj = queryset.get()
        return obj

    def form_valid(self, form):
        """
        Process valid form submission and log the changes.
        
        Args:
            form: Valid ItemForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to item detail view
        """
        # Check if at least one tag is selected
        if not form.cleaned_data.get('tags'):
            form.add_error('tags', 'At least one tag must be selected.')
            return self.form_invalid(form)
            
        # Get the current state before changes for audit logging
        before_model = models.Item.active_objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(self.object)
        audit_log_event(
            self.request.user, 
            f"Updated item \"{ before_model.name }\"", 
            before_state, 
            after_state
        )
        
        messages.success(self.request, f'Item "{self.object.name}" was successfully updated.')
        return response

    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the updated item's detail view
        """
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})
        
    def form_invalid(self, form):
        """
        Handle form validation errors.
        
        Args:
            form: Invalid ItemForm instance
            
        Returns:
            HttpResponse: Rendered template with form errors
        """
        # Add any additional error handling or logging here if needed
        return super().form_invalid(form)


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Class-based view for creating new items with initial stock.
    
    Provides a form for creating new inventory items along with their initial
    stock information including organization, expiration date, and quantity.
    """
    model = models.Item
    form_class = TaggedItemWithStockForm
    template_name = "items/create.html"
    permission_required = 'inventory.add_item'

    def form_valid(self, form):
        """
        Process valid form submission and log the creation.
        
        Creates both Item and initial StockItem, then logs separate creation events.
        
        Args:
            form: Valid ItemWithStockForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to new item's detail view
        """
        # Check if at least one tag is selected
        if not form.cleaned_data.get('tags'):
            form.add_error('tags', 'At least one tag must be selected.')
            return self.form_invalid(form)
            
        # Call the custom save method on the form.
        # It returns a tuple of (item, stock_item).
        new_item, stock_item = form.save()

        # Set the view's object to the new Item instance.
        # This is crucial for get_success_url to work correctly.
        self.object = new_item

        # Log item creation event
        audit_log_event(
            self.request.user, 
            f"Created item \"{new_item.name}\"", 
            audit_log_state(None), 
            audit_log_state(new_item)
        )
            
        # Log stock item creation event
        if stock_item:
            if stock_item.location_new:
                location_display = stock_item.location_new.name
            else:
                location_display = "Unknown location"
            audit_log_event(
                self.request.user, 
                f"Checked-in {stock_item.quantity} of \"{new_item.name}\" into location \"{location_display}\" (initial stock from {stock_item.organization.name})", 
                audit_log_state(None), 
                audit_log_state(stock_item)
            )
            messages.success(self.request, f'Item "{new_item.name}" was successfully created and checked in with {stock_item.quantity} units.')
        else:
            messages.success(self.request, f'Item "{new_item.name}" was successfully created.')
        
        # The parent class handles the redirection to success_url.
        return HttpResponseRedirect(self.get_success_url())
    
    def get_form_kwargs(self):
        """
        Overrides the default method to remove the 'instance' argument,
        which is not compatible with our custom forms.Form.
        """

        kwargs = super().get_form_kwargs()

        if 'instance' in kwargs:
            del kwargs['instance']

        return kwargs 

    def get_initial(self):
        """
        Get initial form data from URL parameters.
        
        Supports pre-populating fields via URL parameters:
        - name: Item name
        - manufacturer: Manufacturer name  
        - gtin: GTIN number
        - date_received: Date received (YYYY-MM-DD format)
        - organization: Organization ID or name
        - stock_location: Stock location
        - quantity: Quantity (integer)
        - lot_number: Lot number
        """
        initial = super().get_initial()
        
        # Get URL parameters for pre-populating fields
        if 'name' in self.request.GET:
            initial['name'] = self.request.GET['name']
            
        if 'manufacturer' in self.request.GET:
            initial['manufacturer'] = self.request.GET['manufacturer']
            
        if 'gtin' in self.request.GET:
            initial['gtin'] = self.request.GET['gtin']
            
        if 'date_received' in self.request.GET:
            try:
                # Parse date in YYYY-MM-DD format
                date_str = self.request.GET['date_received']
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                initial['date_received'] = parsed_date
            except (ValueError, TypeError):
                # If date parsing fails, ignore this parameter
                pass
                
        if 'organization' in self.request.GET:
            org_param = self.request.GET['organization']
            try:
                # Try to find organization by name (case-insensitive)
                org = models.Organization.objects.get(name__iexact=org_param)
                initial['organization'] = org
            except (models.Organization.DoesNotExist, ValueError):
                # If organization not found, ignore this parameter
                pass
                
        if 'stock_location' in self.request.GET:
            initial['stock_location'] = self.request.GET['stock_location']
            
        if 'quantity' in self.request.GET:
            try:
                quantity = int(self.request.GET['quantity'])
                if quantity > 0:
                    initial['quantity'] = quantity
            except (ValueError, TypeError):
                # If quantity parsing fails, ignore this parameter
                pass
                
        if 'lot_number' in self.request.GET:
            initial['lot_number'] = self.request.GET['lot_number']
            
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        """
        Get the URL to redirect to after successful form submission.
        
        Returns:
            str: URL to the new item's detail view
        """
        # self.object is now properly set to the new Item instance
        return reverse_lazy('view_item', kwargs={'uuid': self.object.pk})
