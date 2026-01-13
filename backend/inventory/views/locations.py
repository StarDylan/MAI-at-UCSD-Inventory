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


class LocationCreateView(LoginRequiredMixin, CreateView):
    """Create a new location"""
    model = Location
    form_class = LocationForm
    template_name = 'locations/location_form.html'
    success_url = reverse_lazy('location_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Location "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class LocationUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing location"""
    model = Location
    form_class = LocationForm
    template_name = 'locations/location_form.html'
    success_url = reverse_lazy('location_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Location "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


class LocationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a location (only if it has no associated stock items)"""
    model = Location
    template_name = 'locations/location_confirm_delete.html'
    success_url = reverse_lazy('location_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            if not self.object.can_delete():
                messages.error(
                    request, 
                    f'Cannot delete location "{self.object.name}" because it has associated stock items.'
                )
                return redirect('location_list')
            messages.success(request, f'Location "{self.object.name}" deleted successfully.')
            return super().delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f'Cannot delete location "{self.object.name}" because it is being used by stock items.'
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
                # Update all stock items to point to the target location
                updated_count = self.source_location.stock_items.update(
                    location_new=target_location
                )
                
                # Delete the source location
                self.source_location.delete()
                
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
