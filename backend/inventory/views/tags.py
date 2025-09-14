"""
Views for tag and tag group management.

This module handles CRUD operations for tags and tag groups,
including creation, viewing, editing, and deletion of both
tag groups and individual tags.
"""

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import UpdateView, CreateView, ListView, DeleteView

from inventory import models
from inventory.forms_tags import TagGroupForm, TagForm, TagBulkCreateForm
from inventory.models import Tag, TagGroup
from .utils import audit_log_state, audit_log_event


class TagGroupListView(LoginRequiredMixin, ListView):
    """List all tag groups with their associated tags"""
    model = TagGroup
    template_name = 'tags/tag_group_list.html'
    context_object_name = 'tag_groups'
    ordering = ['sort_order', 'name']
    
    def get_queryset(self):
        return TagGroup.objects.prefetch_related(
            'tags'
        ).order_by('sort_order', 'name')


class TagGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new tag group"""
    model = TagGroup
    form_class = TagGroupForm
    template_name = 'tags/tag_group_form.html'
    success_url = reverse_lazy('tag_groups_list')
    
    def form_valid(self, form):
        # Save the changes
        response = super().form_valid(form)
        
        # Log the create event
        audit_log_event(
            self.request.user,
            f'Created tag group "{form.instance.name}"',
            audit_log_state(None),
            audit_log_state(form.instance)
        )
        
        messages.success(self.request, f'Tag group "{form.instance.name}" created successfully.')
        return response


class TagGroupUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing tag group"""
    model = TagGroup
    form_class = TagGroupForm
    template_name = 'tags/tag_group_form.html'
    success_url = reverse_lazy('tag_groups_list')
    
    def form_valid(self, form):
        # Get the current state before changes for audit logging
        before_model = TagGroup.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(form.instance)
        audit_log_event(
            self.request.user,
            f'Updated tag group "{before_model.name}"',
            before_state,
            after_state
        )
        
        messages.success(self.request, f'Tag group "{form.instance.name}" updated successfully.')
        return response


@login_required
def tag_group_delete_view(request, uuid):
    """Delete a tag group (soft delete by setting is_active=False)"""
    tag_group = get_object_or_404(TagGroup, id=uuid)
    
    if request.method == 'POST':
        # Check if tag group has associated tags
        active_tags_count = tag_group.tags.filter(is_active=True).count()
        if active_tags_count > 0:
            messages.error(
                request, 
                f'Cannot delete tag group "{tag_group.name}" because it has {active_tags_count} active tags. '
                'Please delete or move the tags first.'
            )
        else:
            before_state = audit_log_state(tag_group)
            tag_group.is_active = False
            tag_group.save()
            
            audit_log_event(
                request.user,
                f'Deleted tag group "{tag_group.name}"',
                before_state,
                audit_log_state(tag_group)
            )
            
            messages.success(request, f'Tag group "{tag_group.name}" deleted successfully.')
        
        return redirect('tag_groups_list')
    
    # Check dependencies for confirmation
    active_tags = tag_group.tags.filter(is_active=True)
    
    context = {
        'tag_group': tag_group,
        'active_tags': active_tags,
        'can_delete': active_tags.count() == 0,
    }
    
    template = loader.get_template('tags/tag_group_confirm_delete.html')
    return HttpResponse(template.render(context, request))


class TagListView(LoginRequiredMixin, ListView):
    """List all tags organized by tag group"""
    model = Tag
    template_name = 'tags/tag_list.html'
    context_object_name = 'tags'
    
    def get_queryset(self):
        return Tag.objects.select_related('tag_group').filter(
            is_active=True, 
            tag_group__is_active=True
        ).order_by(
            'tag_group__sort_order', 
            'tag_group__name', 
            'sort_order', 
            'name'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group tags by tag group for better display
        tags_by_group = {}
        for tag in context['tags']:
            group_name = tag.tag_group.name
            if group_name not in tags_by_group:
                tags_by_group[group_name] = {
                    'tag_group': tag.tag_group,
                    'tags': []
                }
            tags_by_group[group_name]['tags'].append(tag)
        
        context['tags_by_group'] = tags_by_group
        return context


class TagCreateView(LoginRequiredMixin, CreateView):
    """Create a new tag"""
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag_form.html'
    success_url = reverse_lazy('tag_list')
    
    def form_valid(self, form):
        # Save the changes
        response = super().form_valid(form)
        
        # Log the create event
        audit_log_event(
            self.request.user,
            f'Created tag "{form.instance.name}"',
            audit_log_state(None),
            audit_log_state(form.instance)
        )
        
        messages.success(self.request, f'Tag "{form.instance.name}" created successfully.')
        return response


class TagUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing tag"""
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag_form.html'
    success_url = reverse_lazy('tag_list')
    
    def form_valid(self, form):
        # Get the current state before changes for audit logging
        before_model = Tag.objects.get(pk=form.instance.pk)
        before_state = audit_log_state(before_model)
        
        # Save the changes
        response = super().form_valid(form)
        
        # Log the update event
        after_state = audit_log_state(form.instance)
        audit_log_event(
            self.request.user,
            f'Updated tag "{before_model.name}"',
            before_state,
            after_state
        )
        
        messages.success(self.request, f'Tag "{form.instance.name}" updated successfully.')
        return response


@login_required
def tag_delete_view(request, uuid):
    """Delete a tag (soft delete by setting is_active=False)"""
    tag = get_object_or_404(Tag, id=uuid)
    
    if request.method == 'POST':
        # Check if tag is assigned to any items
        items_count = tag.items.count()
        if items_count > 0:
            messages.error(
                request, 
                f'Cannot delete tag "{tag.name}" because it is assigned to {items_count} items. '
                'Please remove the tag from all items first.'
            )
        else:
            before_state = audit_log_state(tag)
            tag.is_active = False
            tag.save()
            
            audit_log_event(
                request.user,
                f'Deleted tag "{tag.name}"',
                before_state,
                audit_log_state(tag)
            )
            
            messages.success(request, f'Tag "{tag.name}" deleted successfully.')
        
        return redirect('tag_list')
    
    # Check dependencies for confirmation
    assigned_items = tag.items.all()[:10]  # Limit for display
    total_items_count = tag.items.count()
    
    context = {
        'tag': tag,
        'assigned_items': assigned_items,
        'total_items_count': total_items_count,
        'can_delete': total_items_count == 0,
    }
    
    template = loader.get_template('tags/tag_confirm_delete.html')
    return HttpResponse(template.render(context, request))


@login_required
def tag_bulk_create_view(request):
    """Bulk create tags within a tag group"""
    if request.method == 'POST':
        form = TagBulkCreateForm(request.POST)
        if form.is_valid():
            tag_group = form.cleaned_data['tag_group']
            tag_names = form.cleaned_data['tag_names'].strip()
            
            # Parse tag names (one per line or comma-separated)
            names = []
            for line in tag_names.split('\n'):
                line_names = [name.strip() for name in line.split(',') if name.strip()]
                names.extend(line_names)
            
            created_count = 0
            skipped_count = 0
            errors = []
            
            for i, name in enumerate(names):
                if not name:
                    continue
                    
                # Check if tag already exists in this group
                if Tag.objects.filter(name__iexact=name, tag_group=tag_group).exists():
                    skipped_count += 1
                    continue
                
                try:
                    tag = Tag.objects.create(
                        name=name,
                        tag_group=tag_group,
                        sort_order=i * 10  # Space them out for easy reordering
                    )
                    
                    audit_log_event(
                        request.user,
                        f'Created tag "{tag.name}" via bulk create',
                        audit_log_state(None),
                        audit_log_state(tag)
                    )
                    
                    created_count += 1
                except Exception as e:
                    errors.append(f'Error creating tag "{name}": {str(e)}')
            
            # Show results
            if created_count > 0:
                messages.success(request, f'Created {created_count} tags in "{tag_group.name}".')
            if skipped_count > 0:
                messages.info(request, f'Skipped {skipped_count} duplicate tags.')
            for error in errors:
                messages.error(request, error)
            
            return redirect('tag_list')
    else:
        form = TagBulkCreateForm()
    
    context = {
        'form': form,
    }
    
    template = loader.get_template('tags/tag_bulk_create.html')
    return HttpResponse(template.render(context, request))


def tag_autocomplete_api(request):
    """API endpoint for tag autocomplete in forms"""
    query = request.GET.get('q', '').strip()
    tag_group_id = request.GET.get('tag_group', '')
    
    tags_query = Tag.objects.filter(is_active=True, tag_group__is_active=True)
    
    if query:
        tags_query = tags_query.filter(name__icontains=query)
    
    if tag_group_id:
        try:
            tags_query = tags_query.filter(tag_group__id=tag_group_id)
        except (ValueError, TypeError):
            pass
    
    tags = tags_query.select_related('tag_group').order_by(
        'tag_group__sort_order', 
        'tag_group__name', 
        'sort_order', 
        'name'
    )[:20]  # Limit results
    
    results = []
    for tag in tags:
        results.append({
            'id': str(tag.id),
            'name': tag.name,
            'tag_group': {
                'id': str(tag.tag_group.id),
                'name': tag.tag_group.name,
                'color': tag.tag_group.color,
            },
            'color': tag.display_color,
        })
    
    return JsonResponse({'results': results})


def tag_group_autocomplete_api(request):
    """API endpoint for tag group autocomplete in forms"""
    query = request.GET.get('q', '').strip()
    
    tag_groups_query = TagGroup.objects.filter(is_active=True)
    
    if query:
        tag_groups_query = tag_groups_query.filter(name__icontains=query)
    
    tag_groups = tag_groups_query.order_by('sort_order', 'name')[:20]
    
    results = []
    for tag_group in tag_groups:
        results.append({
            'id': str(tag_group.id),
            'name': tag_group.name,
            'color': tag_group.color,
            'tag_count': tag_group.tags.filter(is_active=True).count(),
        })
    
    return JsonResponse({'results': results})