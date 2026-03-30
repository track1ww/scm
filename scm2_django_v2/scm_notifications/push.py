"""Helper to push notifications to connected WebSocket clients."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def push_notification(user_id: int, notification_data: dict):
    """
    Push a notification to a specific user's WebSocket channel.
    Call this from anywhere: views, signals, tasks.

    notification_data should include: id, message, notification_type, is_read, created_at
    """
    try:
        channel_layer = get_channel_layer()
        group_name = f'notifications_user_{user_id}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'data': {
                    'type': 'new_notification',
                    **notification_data,
                },
            }
        )
    except Exception:
        pass  # WebSocket push is best-effort; don't fail the main request


def push_unread_count(user_id: int, count: int):
    """Push updated unread count to user."""
    try:
        channel_layer = get_channel_layer()
        group_name = f'notifications_user_{user_id}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'data': {'type': 'unread_count', 'count': count},
            }
        )
    except Exception:
        pass
