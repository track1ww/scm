from django.contrib import admin

from .models import ChatRoom, ChatMember, ChatMessage


class ChatMemberInline(admin.TabularInline):
    model = ChatMember
    extra = 0
    fields = ('user', 'joined_at', 'last_read_at')
    readonly_fields = ('joined_at',)


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('room_name', 'room_type', 'room_key', 'created_by', 'created_at', 'company')
    list_filter = ('room_type', 'company')
    search_fields = ('room_name', 'room_key', 'created_by__email', 'created_by__name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    inlines = [ChatMemberInline]


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'joined_at', 'last_read_at')
    list_filter = ('room__room_type',)
    search_fields = ('room__room_name', 'user__email', 'user__name')
    ordering = ('-joined_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender_name', 'msg_type', 'content_preview', 'ref_type', 'is_deleted', 'created_at')
    list_filter = ('msg_type', 'is_deleted', 'room__room_type')
    search_fields = ('sender_name', 'content', 'room__room_name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    @admin.display(description='내용 미리보기')
    def content_preview(self, obj: ChatMessage) -> str:
        return obj.content[:50]
