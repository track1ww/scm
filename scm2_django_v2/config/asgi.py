import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from scm_chat.routing import websocket_urlpatterns as chat_patterns
from scm_notifications.routing import websocket_urlpatterns as notif_patterns
from scm_notifications.middleware import JwtAuthMiddleware

all_websocket_patterns = chat_patterns + notif_patterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JwtAuthMiddleware(
            URLRouter(all_websocket_patterns)
        )
    ),
})
