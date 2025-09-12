from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from inventory.models import AuditEvent

@login_required
@permission_required('inventory.view_auditevent', raise_exception=True)

def audit_by_user_api(request, user_id):
    try:
        limit = int(request.GET.get('limit', 15))
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        limit = 15
        offset = 0
    search = request.GET.get('search', '').strip()
    qs = AuditEvent.objects.filter(user_id=user_id).select_related('user').order_by('-created_at')
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(event__icontains=search) |
            Q(entity_type__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    total = qs.count()
    events = qs[offset:offset+limit]
    data = []
    for event in events:
        data.append({
            'created_at': event.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'entity_type': event.entity_type,
            'user': str(event.user),
            'event': event.event,
            'before': event.before,
            'after': event.after,
            'json_data': {'before': event.before, 'after': event.after},
        })
    return JsonResponse({'events': data, 'total': total})

@login_required
@permission_required('inventory.view_auditevent', raise_exception=True)

def audit_on_user_api(request, user_id):
    try:
        limit = int(request.GET.get('limit', 15))
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        limit = 15
        offset = 0
    search = request.GET.get('search', '').strip()
    qs = AuditEvent.objects.filter(entity_id=user_id).select_related('user').order_by('-created_at')
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(event__icontains=search) |
            Q(entity_type__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    total = qs.count()
    events = qs[offset:offset+limit]
    data = []
    for event in events:
        data.append({
            'created_at': event.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'entity_type': event.entity_type,
            'user': str(event.user),
            'event': event.event,
            'before': event.before,
            'after': event.after,
            'json_data': {'before': event.before, 'after': event.after},
        })
    return JsonResponse({'events': data, 'total': total})
