"""
Views for managing physical locations where stock items are stored.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib import messages
from django.db.models import ProtectedError, Count
from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from ..models import Location
from ..forms import LocationForm, LocationMergeForm
from .utils import audit_log_state, audit_log_event


class LocationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all locations with their active status"""
    model = Location
    template_name = 'locations/location_list.html'
    context_object_name = 'locations'
    permission_required = 'inventory.view_location'
    
    def get_queryset(self):
        # Annotate with stock item count to avoid N+1 queries
        return Location.objects.annotate(
            stock_item_count=Count('stock_items')
        ).order_by('name')


class LocationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new location"""
    model = Location
    form_class = LocationForm
    template_name = 'locations/location_form.html'
    success_url = reverse_lazy('location_list')
    permission_required = 'inventory.add_location'
    
    def form_valid(self, form):
        # Save the new location
        response = super().form_valid(form)
        
        # Log the creation event
        audit_log_event(
            self.request.user,
            f'Created location "{form.instance.name}"',
            audit_log_state(None),
            audit_log_state(form.instance)
        )
        
        messages.success(self.request, f'Location "{form.instance.name}" created successfully.')
        return response


class LocationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edit an existing location"""
    model = Location
    form_class = LocationForm
    template_name = 'locations/location_form.html'
    permission_required = 'inventory.change_location'
    success_url = reverse_lazy('location_list')
    
    def form_valid(self, form):
        # Get the current state before changes for audit logging
        before_model = Location.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        old_name = before_model.name
        
        # Save the changes
        response = super().form_valid(form)
        new_name = form.instance.name
        
        # If the location name changed, update all stock items with this location
        if old_name != new_name:
            with transaction.atomic():
                stock_items = list(form.instance.stock_items.all())
                for stock_item in stock_items:
                    # Capture state before update
                    before_stock_state = audit_log_state(stock_item)
                    
                    # Update the location string field for backward compatibility
                    stock_item.location = new_name
                    stock_item.save()
                    
                    # Capture state after update
                    after_stock_state = audit_log_state(stock_item)
                    
                    # Log the stock item location name change
                    audit_log_event(
                        self.request.user,
                        f'Location name changed from "{old_name}" to "{new_name}" '
                        f'(via location rename)',
                        before_stock_state,
                        after_stock_state
                    )
        
        # Log the location update event
        after_state = audit_log_state(form.instance)
        audit_log_event(
            self.request.user,
            f'Updated location "{old_name}"',
            before_state,
            after_state
        )
        
        messages.success(self.request, f'Location "{form.instance.name}" updated successfully.')
        return response


class LocationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a location (only if it has no associated stock items)"""
    model = Location
    template_name = 'locations/location_confirm_delete.html'
    success_url = reverse_lazy('location_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        location_name = self.object.name
        
        try:
            if not self.object.can_delete():
                messages.error(
                    request, 
                    f'Cannot delete location "{location_name}" because it has associated stock items.'
                )
                return redirect('location_list')
            
            # Log the state before deletion
            before_state = audit_log_state(self.object)
            
            # Perform the deletion
            response = super().delete(request, *args, **kwargs)
            
            # Log the deletion event
            audit_log_event(
                request.user,
                f'Deleted location "{location_name}"',
                before_state,
                audit_log_state(None)
            )
            
            messages.success(request, f'Location "{location_name}" deleted successfully.')
            return response
        except ProtectedError:
            messages.error(
                request, 
                f'Cannot delete location "{location_name}" because it is being used by stock items.'
            )
            return redirect('location_list')


class LocationMergeView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Merge one location into another, transferring all stock items"""
    template_name = 'locations/location_merge.html'
    form_class = LocationMergeForm
    success_url = reverse_lazy('location_list')
    permission_required = 'inventory.delete_location'
    
    def dispatch(self, request, *args, **kwargs):
        # Get and store the source location
        self.source_location = get_object_or_404(Location, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['source_location'] = self.source_location
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['source_location'] = self.source_location
        context['stock_item_count'] = self.source_location.stock_items.count()
        return context
    
    def form_valid(self, form):
        target_location = form.cleaned_data['target_location']
        source_name = self.source_location.name
        target_name = target_location.name
        
        try:
            with transaction.atomic():
                # Log the state before merge
                before_state = audit_log_state(self.source_location)
                
                # Get all stock items that will be moved
                stock_items = list(self.source_location.stock_items.all())
                
                # Update each stock item and create audit events
                for stock_item in stock_items:
                    # Capture state before update
                    before_stock_state = audit_log_state(stock_item)
                    
                    # Update both location fields for backward compatibility
                    stock_item.location_new = target_location
                    stock_item.location = target_location.name
                    stock_item.save()
                    
                    # Capture state after update
                    after_stock_state = audit_log_state(stock_item)
                    
                    # Log the stock item location change
                    audit_log_event(
                        self.request.user,
                        f'Location changed from "{source_name}" to "{target_name}" '
                        f'(via location merge)',
                        before_stock_state,
                        after_stock_state
                    )
                
                updated_count = len(stock_items)
                
                # Delete the source location
                self.source_location.delete()
                
                # Log the merge event
                audit_log_event(
                    self.request.user,
                    f'Merged location "{source_name}" into "{target_name}" '
                    f'({updated_count} stock item(s) transferred)',
                    before_state,
                    audit_log_state(None)
                )
                
                messages.success(
                    self.request,
                    f'Successfully merged "{source_name}" into "{target_name}". '
                    f'{updated_count} stock item(s) were transferred.'
                )
        except Exception as e:
            messages.error(
                self.request,
                f'Error merging locations: {str(e)}'
            )
            return redirect('location_list')
        
        return super().form_valid(form)
