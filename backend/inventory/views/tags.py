"""
Views for tag and tag group management.
"""
    
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import UpdateView, CreateView, ListView, DeleteView
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Count
import json

from inventory.models import Tag, TagGroup
from inventory.forms_tags import TagGroupForm, TagForm, TagBulkCreateForm
from .utils import audit_log_state, audit_log_event

@login_required
@require_GET
@permission_required("inventory.delete_tag", raise_exception=True)
def check_tag_dependencies(request, uuid):
    """API endpoint to check if a tag can be deleted"""
    try:
        tag = get_object_or_404(Tag, id=uuid)
        items_count = tag.items.count()  # Use the related_name from Item.tags
        
        return JsonResponse({
            'can_delete': items_count == 0,
            'items_count': items_count,
            'tag_name': tag.name,
            'message': f'Cannot delete tag "{tag.name}" because it is assigned to {items_count} items. Please remove the tag from all items first.' if items_count > 0 else None
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
@permission_required("inventory.delete_taggroup", raise_exception=True)
def check_tag_group_dependencies(request, uuid):
    """API endpoint to check if a tag group can be deleted"""
    try:
        tag_group = get_object_or_404(TagGroup, id=uuid)
        
        # Count all tags (both active and hidden)
        total_tags_count = tag_group.tags.count()
        active_tags_count = tag_group.tags.filter(is_active=True).count()
        hidden_tags_count = total_tags_count - active_tags_count
        
        # Cannot delete if there are ANY tags (active or hidden)
        can_delete = total_tags_count == 0
        
        # Build detailed message
        if total_tags_count > 0:
            if active_tags_count > 0 and hidden_tags_count > 0:
                message = f'Cannot delete tag group "{tag_group.name}" because it has {active_tags_count} active tags and {hidden_tags_count} hidden tags. Please delete or move all tags first.'
            elif active_tags_count > 0:
                message = f'Cannot delete tag group "{tag_group.name}" because it has {active_tags_count} active tags. Please delete or move the tags first.'
            else:
                message = f'Cannot delete tag group "{tag_group.name}" because it has {hidden_tags_count} hidden tags. Please delete the hidden tags first.'
        else:
            message = None
        
        return JsonResponse({
            'can_delete': can_delete,
            'total_tags_count': total_tags_count,
            'active_tags_count': active_tags_count,
            'hidden_tags_count': hidden_tags_count,
            'tag_group_name': tag_group.name,
            'message': message
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
@permission_required("inventory.hide_tag", raise_exception=True)
def hide_tag(request, uuid):
    """Hide a tag (soft delete by setting is_active=False)"""
    try:
        tag = get_object_or_404(Tag, id=uuid)
        
        before_state = audit_log_state(tag)
        tag.is_active = False
        tag.save()
        
        audit_log_event(
            request.user,
            f'Hidden tag "{tag.name}"',
            before_state,
            audit_log_state(tag)
        )
        
        return JsonResponse({'success': True, 'message': f'Tag "{tag.name}" hidden successfully.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


class TagGroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all tag groups with their associated tags"""
    model = TagGroup
    template_name = 'tags/tag_group_list.html'
    context_object_name = 'tag_groups'
    ordering = ['sort_order', 'name']
    permission_required = "inventory.view_tag"
    
    def get_queryset(self):
        return TagGroup.objects.prefetch_related(
            'tags'
        ).filter(is_active=True).order_by('sort_order', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add tag counts for each tag group
        for tag_group in context['tag_groups']:
            tag_group.active_tags_count = tag_group.tags.filter(is_active=True).count()
            tag_group.hidden_tags_count = tag_group.tags.filter(is_active=False).count()
        return context


class TagGroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new tag group"""
    model = TagGroup
    form_class = TagGroupForm
    template_name = 'tags/tag_group_form.html'
    success_url = reverse_lazy('tag_groups_list')
    permission_required = "inventory.add_taggroup"
    
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


class TagGroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edit an existing tag group"""
    model = TagGroup
    form_class = TagGroupForm
    template_name = 'tags/tag_group_form.html'
    success_url = reverse_lazy('tag_groups_list')
    permission_required = "inventory.change_taggroup"
    
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
@permission_required("inventory.delete_taggroup", raise_exception=True)
def tag_group_delete_view(request, uuid):
    """Delete a tag group (HARD DELETE - actually removes from database)"""
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
            tag_group_name = tag_group.name  # Store name before deletion
            
            # HARD DELETE - actually remove from database
            tag_group.delete()
            
            audit_log_event(
                request.user,
                f'Permanently deleted tag group "{tag_group_name}"',
                before_state,
                audit_log_state(None)
            )
            
            messages.success(request, f'Tag group "{tag_group_name}" permanently deleted.')
        
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


class TagListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all tags organized by tag group"""
    model = Tag
    template_name = 'tags/tag_list.html'
    context_object_name = 'tags'
    permission_required = "inventory.view_tag"
    
    
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
        
        # Add hidden tags to context
        context['hidden_tags'] = Tag.objects.select_related('tag_group').filter(
            is_active=False
        ).order_by('tag_group__name', 'name')
        
        # Check if we should focus on a specific tag group
        focus_group = self.request.GET.get('focus_group')
        if focus_group:
            context['focus_group'] = focus_group
        
        return context


class TagCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new tag"""
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag_form.html'
    success_url = reverse_lazy('tag_list')
    permission_required = "inventory.add_tag"
    
    def get_initial(self):
        """Pre-populate form with tag_group if provided in URL"""
        initial = super().get_initial()
        
        # Check if tag_group is provided in URL parameters
        tag_group_id = self.request.GET.get('tag_group')
        if tag_group_id:
            try:
                tag_group = TagGroup.objects.get(id=tag_group_id, is_active=True)
                initial['tag_group'] = tag_group
            except TagGroup.DoesNotExist:
                pass  # Invalid tag group ID, ignore
        
        return initial
    
    def get_context_data(self, **kwargs):
        """Add tag group context if creating tag for specific group"""
        context = super().get_context_data(**kwargs)
        
        # Add all active tag groups for the JavaScript to access their colors
        tag_groups = TagGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        tag_groups_data = {}
        for tg in tag_groups:
            tag_groups_data[str(tg.id)] = {
                'name': tg.name,
                'color': tg.color,
                'text_color': tg.text_color
            }
        context['tag_groups_data_json'] = json.dumps(tag_groups_data)
        
        tag_group_id = self.request.GET.get('tag_group')
        if tag_group_id:
            try:
                tag_group = TagGroup.objects.get(id=tag_group_id, is_active=True)
                context['creating_for_tag_group'] = tag_group
            except TagGroup.DoesNotExist:
                pass
        
        return context
    
    def get_success_url(self):
        """Return to tag group list if came from there, otherwise go to tag list"""
        tag_group_id = self.request.GET.get('tag_group')
        if tag_group_id:
            try:
                TagGroup.objects.get(id=tag_group_id, is_active=True)
                return reverse_lazy('tag_groups_list')
            except TagGroup.DoesNotExist:
                pass
        return self.success_url
    
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


class TagUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edit an existing tag"""
    model = Tag
    form_class = TagForm
    template_name = 'tags/tag_form.html'
    success_url = reverse_lazy('tag_list')
    permission_required = "inventory.change_tag"

    def get_context_data(self, **kwargs):
        """Add tag groups data for JavaScript access"""
        context = super().get_context_data(**kwargs)
        
        # Add all active tag groups for the JavaScript to access their colors
        tag_groups = TagGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        tag_groups_data = {}
        for tg in tag_groups:
            tag_groups_data[str(tg.id)] = {
                'name': tg.name,
                'color': tg.color,
                'text_color': tg.text_color
            }
        context['tag_groups_data_json'] = json.dumps(tag_groups_data)
        
        return context
    
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
@permission_required("inventory.delete_tag", raise_exception=True)
def tag_delete_view(request, uuid):
    """Delete a tag (HARD DELETE - actually removes from database)"""
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
            tag_name = tag.name  # Store name before deletion
            
            # HARD DELETE - actually remove from database
            tag.delete()
            
            audit_log_event(
                request.user,
                f'Permanently deleted tag "{tag_name}"',
                before_state,
                audit_log_state(None)
            )
            
            messages.success(request, f'Tag "{tag_name}" permanently deleted.')
        
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
@permission_required("inventory.add_tag", raise_exception=True)
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

@login_required
@permission_required("inventory.view_tag", raise_exception=True)
def api_hidden_tags(request):
    """API endpoint to get hidden tags"""
    hidden_tags = Tag.objects.filter(is_active=False).annotate(
        items_count=Count('items')
    ).order_by('name')
    
    tags_data = []
    for tag in hidden_tags:
        tags_data.append({
            'id': str(tag.id),
            'name': tag.name,
            'display_color': tag.display_color,
            'text_color': tag.text_color,
            'items_count': tag.items_count
        })
    
    return JsonResponse({
        'success': True,
        'tags': tags_data
    })


@login_required
@permission_required("inventory.hide_tag", raise_exception=True)
def api_restore_tag(request, tag_id):
    """API endpoint to restore a hidden tag"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        tag = Tag.objects.get(id=tag_id)
        
        # Capture before state for audit
        before_state = audit_log_state(tag)
        
        tag.is_active = True
        tag.save()
        
        # Capture after state and log the audit event
        after_state = audit_log_state(tag)
        audit_log_event(
            user=request.user,
            event=f'Restored tag "{tag.name}"',
            before_state=before_state,
            after_state=after_state
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Tag "{tag.name}" has been restored.'
        })
    except Tag.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Tag not found'}, status=404)