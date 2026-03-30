"""
Workflow notification signals.
Pushes real-time WebSocket notifications on approval events.

Signal responsibilities
-----------------------
* post_save on ApprovalRequest (created=True)
    — Notify every user whose department matches the first step's approver_role.
    — Uses the same role-matching logic as ApprovalRequestViewSet.pending_for_me.

* pre_save on ApprovalRequest
    — Detect a status transition to 'approved' or 'rejected'.
    — Notify the original requester of the outcome.

Field correctness notes
-----------------------
* ApprovalStep has no User FK; approvers are resolved by matching
  step.approver_role against User.department (CharField).
* Notification.ref_id is IntegerField (not CharField).
* Notification.title is required (not blank=True).
* notification_type must be one of the Notification.TYPES choices:
  'approval_request' or 'approval_result' are used here.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


def _create_and_push_notification(
    company, recipient, title, message,
    notif_type='system', ref_module='workflow', ref_id=None
):
    """
    Create a Notification record and push it via WebSocket.
    Failures are silently suppressed so notification errors never
    interrupt the main approval flow.
    """
    try:
        from scm_notifications.models import Notification
        from scm_notifications.push import push_notification
        from scm_notifications.serializers import NotificationSerializer

        notif = Notification.objects.create(
            company=company,
            recipient=recipient,
            notification_type=notif_type,
            title=title,
            message=message,
            ref_module=ref_module,
            ref_id=ref_id,   # IntegerField — pass int or None, not str
            is_read=False,
        )
        push_notification(recipient.pk, NotificationSerializer(notif).data)
    except Exception:
        pass  # best-effort; do not propagate


@receiver(post_save, sender='scm_workflow.ApprovalRequest')
def notify_on_approval_request(sender, instance, created, **kwargs):
    """
    When a new ApprovalRequest is created, notify every user whose
    department matches the first step's approver_role on the template.

    ApprovalStep does not store a direct User FK; the role-based lookup
    mirrors the logic in ApprovalRequestViewSet.pending_for_me.
    """
    if not created:
        return

    try:
        template = instance.template
        if not template:
            return

        first_step = template.steps.filter(step_no=instance.current_step).first()
        if not first_step:
            return

        approver_role = first_step.approver_role
        requester_name = getattr(instance.requester, 'username', '누군가')
        title_text = instance.title or f'결재요청 #{instance.pk}'

        # Resolve approvers: users in the same company whose department
        # matches the step's approver_role (empty role = any user in company).
        from scm_accounts.models import User

        user_qs = User.objects.filter(company=instance.company)
        if approver_role:
            user_qs = user_qs.filter(department=approver_role)

        for approver in user_qs.exclude(pk=instance.requester_id):
            _create_and_push_notification(
                company=instance.company,
                recipient=approver,
                title='결재 요청',
                message=(
                    f'[결재 요청] {requester_name}님이 '
                    f'"{title_text}" 결재를 요청했습니다.'
                ),
                notif_type='approval_request',
                ref_module='workflow',
                ref_id=instance.pk,
            )
    except Exception:
        pass


@receiver(pre_save, sender='scm_workflow.ApprovalRequest')
def notify_on_approval_decision(sender, instance, **kwargs):
    """
    When an existing ApprovalRequest transitions to 'approved' or
    'rejected', notify the requester of the outcome.

    Uses pre_save so we can compare the incoming status against the
    currently-persisted value before the write occurs.
    """
    if not instance.pk:
        return  # New instance — handled by post_save above

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.status == instance.status:
        return  # No status change; nothing to do

    requester = instance.requester
    if not requester:
        return

    title_text = instance.title or f'결재요청 #{instance.pk}'

    if instance.status == 'approved':
        _create_and_push_notification(
            company=instance.company,
            recipient=requester,
            title='결재 승인',
            message=f'[결재 승인] "{title_text}" 결재가 승인되었습니다.',
            notif_type='approval_result',
            ref_module='workflow',
            ref_id=instance.pk,
        )
    elif instance.status == 'rejected':
        _create_and_push_notification(
            company=instance.company,
            recipient=requester,
            title='결재 반려',
            message=f'[결재 반려] "{title_text}" 결재가 반려되었습니다.',
            notif_type='approval_result',
            ref_module='workflow',
            ref_id=instance.pk,
        )
