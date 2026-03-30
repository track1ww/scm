import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group = f"chat_{self.room_id}"

        self.user = await self.get_user_from_token()
        if self.user is None:
            return

        if not await self.is_member():
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content", "").strip()
        if not content:
            return
        msg = await self.save_message(content)
        await self.channel_layer.group_send(self.room_group, {
            "type": "chat_message",
            "id": msg["id"],
            "content": msg["content"],
            "sender_id": msg["sender_id"],
            "sender_name": msg["sender_name"],
            "created_at": msg["created_at"],
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "message",
            "id": event["id"],
            "content": event["content"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "created_at": event["created_at"],
        }))

    @database_sync_to_async
    def get_user_from_token(self):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            query_string = self.scope.get("query_string", b"").decode()
            token_str = None
            for part in query_string.split("&"):
                if part.startswith("token="):
                    token_str = part[6:]
                    break
            if not token_str:
                return None
            token = AccessToken(token_str)
            User = get_user_model()
            return User.objects.get(id=token["user_id"])
        except Exception:
            return None

    @database_sync_to_async
    def is_member(self):
        from scm_chat.models import ChatMember
        return ChatMember.objects.filter(
            room_id=self.room_id, user_id=self.user.id
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        from scm_chat.models import ChatMessage, ChatMember
        msg = ChatMessage.objects.create(
            room_id=self.room_id,
            sender=self.user,
            sender_name=self.user.name,
            content=content,
        )
        ChatMember.objects.filter(
            room_id=self.room_id, user_id=self.user.id
        ).update(last_read_at=timezone.now())
        return {
            "id": msg.id,
            "content": msg.content,
            "sender_id": self.user.id,
            "sender_name": self.user.name,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
        }
