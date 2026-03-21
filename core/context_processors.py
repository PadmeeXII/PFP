from .models import Request
from django.db.models import Q

def pending_notifications(request):

    if not request.user.is_authenticated:
        return {}

    user = request.user

    count = 0

    if user.role == "APPROVER":
        count = Request.objects.filter(
            Q(approver_step1=user, current_step=1, status="PENDING") |
            Q(approver_step2=user, current_step=2, status="IN_PROGRESS")
        ).count()

    elif user.role == "EMPLOYEE":
        count = Request.objects.filter(
            Q(created_by=user,status="IN_PROGRESS")
            ).count()

    return {
        "pending_notifications": count
    }