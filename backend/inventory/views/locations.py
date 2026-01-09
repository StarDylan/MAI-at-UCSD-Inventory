"""
Views for managing physical locations where stock items are stored.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect
from ..models import Location
from ..forms import LocationForm


class LocationListView(LoginRequiredMixin, ListView):
    """List all locations with their active status"""
    model = Location
    template_name = 'locations/location_list.html'
    context_object_name = 'locations'
    
    def get_queryset(self):
        return Location.objects.all().order_by('name')


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
