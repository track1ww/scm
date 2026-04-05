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


# ---------------------------------------------------------------------------
# Status-transition map for linked documents.
#
# Key   : (app_label, model_name_lower) as stored in ContentType.
# Value : (status_field_name, approved_value, rejected_value_or_None)
#
# Entries with rejected_value=None mean "leave the document status unchanged
# on rejection — only log."
#
# AccountMove uses the field named 'state', not 'status'; all others use
# 'status'.  WorkInstruction is the actual model in scm_wi (there is no
# WorkOrder model).
# ---------------------------------------------------------------------------
import logging  # noqa: E402  — placed here to stay close to the handler below

logger = logging.getLogger(__name__)

_TRANSITION_MAP: dict[tuple[str, str], tuple[str, str, str | None]] = {
    # (app_label, model_name_lower): (field, approved_value, rejected_value)
    ('scm_mm', 'purchaseorder'):    ('status', '발주확정',    None),
    ('scm_sd', 'salesorder'):       ('status', '생산/조달중', None),
    ('scm_pp', 'productionorder'):  ('status', '확정',        None),
    ('scm_fi', 'accountmove'):      ('state',  'POSTED',      None),   # FI uses 'state' field
    ('scm_wi', 'workinstruction'):  ('status', '진행중',      None),   # actual model in scm_wi
}


@receiver(pre_save, sender='scm_workflow.ApprovalRequest')
def auto_transition_on_approval(sender, instance, **kwargs):
    """
    When an ApprovalRequest transitions to 'approved' or 'rejected',
    automatically update the status of the linked document.

    Document resolution uses the GenericForeignKey stored on ApprovalRequest
    (content_type + object_id).  The transition target is looked up in
    _TRANSITION_MAP by (app_label, model_name_lower).

    On approval  : sets the configured field to the approved value.
    On rejection : logs the event; document status is intentionally left
                   unchanged (business rule: human intervention required).

    All failures are caught and logged so that a broken cross-module
    reference never interrupts the approval workflow itself.
    """
    if not instance.pk:
        return  # New record — no status transition possible yet.

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.status == instance.status:
        return  # No status change — nothing to do.

    new_status = instance.status
    if new_status not in ('approved', 'rejected'):
        return  # Only act on terminal approval outcomes.

    # ------------------------------------------------------------------ #
    # Resolve the linked document via GenericForeignKey.                  #
    # ------------------------------------------------------------------ #
    content_type = instance.content_type
    object_id    = instance.object_id

    if content_type is None or object_id is None:
        logger.warning(
            'auto_transition_on_approval: ApprovalRequest #%s has no linked '
            'document (content_type=%s, object_id=%s). Skipping transition.',
            instance.pk, content_type, object_id,
        )
        return

    app_label  = content_type.app_label
    model_name = content_type.model  # already lowercase

    map_key = (app_label, model_name)
    if map_key not in _TRANSITION_MAP:
        # Unknown document type — not an error, just not configured.
        logger.debug(
            'auto_transition_on_approval: No transition rule for (%s, %s). '
            'ApprovalRequest #%s — skipping.',
            app_label, model_name, instance.pk,
        )
        return

    field_name, approved_value, rejected_value = _TRANSITION_MAP[map_key]

    # ------------------------------------------------------------------ #
    # Fetch the linked document.                                          #
    # ------------------------------------------------------------------ #
    try:
        from django.apps import apps as django_apps
        Model = django_apps.get_model(app_label, model_name)
        doc   = Model.objects.get(pk=object_id)
    except LookupError:
        logger.error(
            'auto_transition_on_approval: Could not resolve model %s.%s '
            'for ApprovalRequest #%s.',
            app_label, model_name, instance.pk,
        )
        return
    except Model.DoesNotExist:
        logger.error(
            'auto_transition_on_approval: %s.%s pk=%s does not exist '
            '(referenced by ApprovalRequest #%s).',
            app_label, model_name, object_id, instance.pk,
        )
        return
    except Exception as exc:
        logger.exception(
            'auto_transition_on_approval: Unexpected error fetching %s.%s '
            'pk=%s for ApprovalRequest #%s: %s',
            app_label, model_name, object_id, instance.pk, exc,
        )
        return

    # ------------------------------------------------------------------ #
    # Apply the status transition.                                        #
    # ------------------------------------------------------------------ #
    try:
        if new_status == 'approved':
            old_field_value = getattr(doc, field_name, None)
            setattr(doc, field_name, approved_value)
            doc.save(update_fields=[field_name])
            logger.info(
                'auto_transition_on_approval: [APPROVED] %s.%s pk=%s — '
                '%s: %r → %r  (ApprovalRequest #%s)',
                app_label, model_name, object_id,
                field_name, old_field_value, approved_value, instance.pk,
            )

        else:  # 'rejected'
            if rejected_value is not None:
                old_field_value = getattr(doc, field_name, None)
                setattr(doc, field_name, rejected_value)
                doc.save(update_fields=[field_name])
                logger.info(
                    'auto_transition_on_approval: [REJECTED] %s.%s pk=%s — '
                    '%s: %r → %r  (ApprovalRequest #%s)',
                    app_label, model_name, object_id,
                    field_name, old_field_value, rejected_value, instance.pk,
                )
            else:
                logger.info(
                    'auto_transition_on_approval: [REJECTED] %s.%s pk=%s — '
                    'no status revert configured; document left unchanged. '
                    '(ApprovalRequest #%s)',
                    app_label, model_name, object_id, instance.pk,
                )

    except Exception as exc:
        logger.exception(
            'auto_transition_on_approval: Failed to update %s field on '
            '%s.%s pk=%s for ApprovalRequest #%s: %s',
            field_name, app_label, model_name, object_id, instance.pk, exc,
        )
