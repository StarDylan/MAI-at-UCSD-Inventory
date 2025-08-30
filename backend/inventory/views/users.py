"""
User management views for the inventory application.

This module handles user administration functionality including user creation,
role management, user profile viewing, and user activation/deactivation.
Access is restricted to users with appropriate administrative permissions.
"""

import json
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.views.generic import FormView

from inventory import models
from inventory.forms import UserCreationForm
from inventory.models import User, AuditEvent
from .utils import audit_log_state, audit_log_event


def is_admin(user):
    """
    Check if a user is in the 'Admin' group.
    
    This helper function is used for permission checking and can be used
    with the @user_passes_test decorator to restrict access.
    
    Args:
        user: User instance to check
        
    Returns:
        bool: True if user is in Admin group, False otherwise
    """
    return user.groups.filter(name='Admin').exists()


@login_required
@permission_required('inventory.change_user', raise_exception=True)
@permission_required('inventory.view_user', raise_exception=True)
def manage_users_view(request):
    """
    Display the user management interface.
    
    Shows all users with their group memberships and activation status.
    Only accessible to users with appropriate admin permissions.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered template with user management interface
        
    Raises:
        PermissionDenied: If user doesn't have required permissions
    """
    # Fetch all users with their group information
    all_users = models.User.objects.all().prefetch_related('groups')

    users_data = []
    for user_obj in all_users:
        users_data.append({
            'id': user_obj.pk,
            'user': user_obj,
            'is_active': user_obj.is_active,
            # Check for group membership and store as booleans
            'is_user': user_obj.groups.filter(name='User').exists(),
            'is_member': user_obj.groups.filter(name='Member').exists(),
            'is_admin': user_obj.groups.filter(name='Admin').exists(),
            'is_superuser': user_obj.is_superuser
        })

    context = {
        'users': users_data,
        'user': request.user,
    }

    return render(request, "users/list.html", context)


@login_required
@permission_required('inventory.change_user', raise_exception=True)
def edit_user_role_api(request, pk):
    """
    API endpoint to change a user's role by assigning them to a new group.
    
    Accepts POST requests with JSON data containing the new group name.
    Clears all existing groups and assigns the user to the specified group.
    
    Args:
        request: HTTP request object (must be POST with JSON body)
        pk: Primary key of the user to modify
        
    Returns:
        HttpResponse: Status 200 on success, 405 for unsupported methods
        
    Raises:
        Http404: If user or group with given identifiers don't exist
        PermissionDenied: If user doesn't have change_user permission
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        new_group_name = data.get("group_name")

        # Find the user and the new group
        user_to_edit = get_object_or_404(models.User, pk=pk)
        new_group = get_object_or_404(Group, name=new_group_name)
        
        # Log the current state before changes
        before_state = audit_log_state(user_to_edit)

        # Update user's group membership
        user_to_edit.groups.clear()
        user_to_edit.groups.add(new_group)

        # Log the role change event
        after_state = audit_log_state(user_to_edit)
        audit_log_event(
            request.user, 
            f"Changed user \"{user_to_edit.username}\" role to \"{new_group.name}\"", 
            before_state, 
            after_state
        )

        return HttpResponse(status=200)
    
    return HttpResponse(status=405)


@login_required
@permission_required('inventory.view_user', raise_exception=True)
def view_user_profile_view(request, pk):
    """
    Display a user's profile page with details and audit logs.
    
    Shows user information, their current role, and audit history both
    of actions performed by the user and actions performed on the user.
    
    Args:
        request: HTTP request object
        pk: Primary key of the user to view
        
    Returns:
        HttpResponse: Rendered template with user profile information
        
    Raises:
        Http404: If user with given primary key doesn't exist
        PermissionDenied: If user doesn't have view_user permission
    """
    # Fetch the user with related group data
    viewed_user = get_object_or_404(
        models.User.objects.prefetch_related('groups'), 
        pk=pk
    )

    # Determine the user's primary role based on group membership
    user_role = "User"  # Default role
    if viewed_user.groups.filter(name='Member').exists():
        user_role = "Member"
    if viewed_user.groups.filter(name='Admin').exists():
        user_role = "Admin"

    # Fetch audit logs related to this user
    audit_by_user = (AuditEvent.objects
                    .filter(user_id=pk)
                    .order_by('-created_at'))
    audit_on_user = (AuditEvent.objects
                    .filter(entity_id=pk)
                    .order_by('-created_at'))

    context = {
        'user_data': {
            'user_id': viewed_user.pk,
            'user_name': viewed_user.username,
            'user_email': viewed_user.email,
            'user_role': user_role,
            'user_active': viewed_user.is_active,
            'user_picture': viewed_user.user_picture,
        },
        'audit_by_user': audit_by_user,
        'audit_on_user': audit_on_user,
    }

    return render(request, "users/detail.html", context)


@login_required
@permission_required('inventory.delete_user', raise_exception=True)
def delete_user_view(request, pk):
    """
    Soft delete a user by setting their is_active status to False.
    
    This preserves the user's data while preventing them from accessing
    the system. Users cannot delete themselves.
    
    Args:
        request: HTTP request object
        pk: Primary key of the user to delete
        
    Returns:
        HttpResponse: Error message if user tries to delete themselves
        HttpResponseRedirect: Redirect to user profile after deletion
        
    Raises:
        Http404: If user with given primary key doesn't exist
        PermissionDenied: If user doesn't have delete_user permission
    """
    user_to_delete = get_object_or_404(models.User, pk=pk)
    
    # Prevent users from deleting themselves
    if user_to_delete == request.user:
        return HttpResponse("You cannot delete your own account.", status=403)

    # Log the current state before deletion
    before_state = audit_log_state(user_to_delete)

    # Perform soft delete
    user_to_delete.is_active = False
    user_to_delete.save()

    # Log the deletion event
    after_state = audit_log_state(user_to_delete)
    audit_log_event(
        request.user, 
        f"Deleted user \"{user_to_delete.username}\"", 
        before_state, 
        after_state
    )

    return redirect('view_user', pk=pk)


@login_required
@permission_required('inventory.restore_user', raise_exception=True)
def restore_user_view(request, pk):
    """
    Restore a previously deleted user by setting their is_active status to True.
    
    Undoes the soft delete operation and allows the user to access the system again.
    
    Args:
        request: HTTP request object
        pk: Primary key of the user to restore
        
    Returns:
        HttpResponseRedirect: Redirect to user profile after restoration
        
    Raises:
        Http404: If user with given primary key doesn't exist
        PermissionDenied: If user doesn't have restore_user permission
    """
    user_to_restore = get_object_or_404(models.User, pk=pk)
    
    # Log the current state before restoration
    before_state = audit_log_state(user_to_restore)

    # Restore the user
    user_to_restore.is_active = True
    user_to_restore.save()

    # Log the restoration event
    after_state = audit_log_state(user_to_restore)
    audit_log_event(
        request.user, 
        f"Restored user \"{user_to_restore.username}\"", 
        before_state, 
        after_state
    )

    return redirect('view_user', pk=pk)


class UserCreateView(FormView, PermissionRequiredMixin, LoginRequiredMixin):
    """
    View for creating new user accounts.
    
    Provides a form-based interface for creating new users with validation
    to prevent duplicate usernames and email addresses.
    """
    template_name = 'users/create.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('manage_users')
    permission_required = 'inventory.add_user'

    def form_valid(self, form):
        """
        Process valid form submission and create the new user.
        
        Validates that username and email are unique before creating
        the user account and logs the creation event.
        
        Args:
            form: Valid UserCreationForm instance
            
        Returns:
            HttpResponseRedirect: Redirect to user management page
            HttpResponse: Form with errors if validation fails
        """
        username = form.cleaned_data['username']
        email = form.cleaned_data['email']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']

        # Check for existing username
        if User.objects.filter(username=username).exists():
            form.add_error('username', 'Username already exists.')
            return self.form_invalid(form)
    
        # Check for existing email
        if User.objects.filter(email=email).exists():
            form.add_error('email', 'Email already exists.')
            return self.form_invalid(form)

        # Create the new user using Django's built-in method for secure password handling
        new_user = User.objects.create_user(
            username=username, 
            email=email, 
            first_name=first_name, 
            last_name=last_name
        )

        # Log the user creation event
        before_state = audit_log_state(None)
        after_state = audit_log_state(new_user)
        audit_log_event(
            self.request.user, 
            f"Created user \"{new_user.username}\"", 
            before_state, 
            after_state
        )

        return super().form_valid(form)