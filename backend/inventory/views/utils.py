"""
Utility functions for the inventory application.

This module contains shared utilities used across multiple view modules,
including audit logging functionality and common helper functions.
"""

import json
from dataclasses import dataclass
from django.forms.models import model_to_dict
from inventory.models import AuditEvent


@dataclass
class ObjState:
    """
    Represents the state of an object for audit logging purposes.
    
    Attributes:
        json_data: JSON serialized representation of the object
        id: Primary key of the object (None if object doesn't exist)
        class_name: Name of the object's class (None if object doesn't exist)
    """
    json_data: str
    id: int | None
    class_name: str | None


def audit_log_state(obj):
    """
    Convert a Django model instance to an ObjState for audit logging.
    
    Args:
        obj: Django model instance or None
        
    Returns:
        ObjState: Serialized state of the object
    """
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


def audit_log_event(user, event: str, before_state: ObjState, after_state: ObjState, entity_id: str | None = None):
    """
    Create an audit log event record.
    
    Args:
        user: User who performed the action
        event: Description of the event
        before_state: State before the change
        after_state: State after the change
        entity_id: Optional entity ID if different from object ID
    """
    AuditEvent.objects.create(
        user=user,
        event=event,
        entity_type=before_state.class_name or after_state.class_name,
        entity_id=entity_id or before_state.id or after_state.id,
        before=before_state.json_data,
        after=after_state.json_data,
    )