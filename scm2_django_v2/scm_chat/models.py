from django.db import models
from scm_accounts.models import User, Company

class ChatRoom(models.Model):
    ROOM_TYPE = [('dm','1:1'),('group','그룹'),('notice','공지')]
    company    = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    room_type  = models.CharField(max_length=20, choices=ROOM_TYPE)
    room_name  = models.CharField(max_length=100)
    room_key   = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    members    = models.ManyToManyField(User, through='ChatMember',
                                         related_name='chat_rooms')

    def __str__(self): return self.room_name


class ChatMember(models.Model):
    room         = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at    = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('room', 'user')


class ChatMessage(models.Model):
    MSG_TYPE = [('text','텍스트'),('file','파일'),('system','시스템')]
    room        = models.ForeignKey(ChatRoom, on_delete=models.CASCADE,
                                     related_name='messages')
    sender      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    sender_name = models.CharField(max_length=100)
    msg_type    = models.CharField(max_length=20, choices=MSG_TYPE, default='text')
    content     = models.TextField()
    ref_type    = models.CharField(max_length=50, blank=True)
    ref_id      = models.IntegerField(null=True, blank=True)
    ref_label   = models.CharField(max_length=200, blank=True)
    is_deleted  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self): return f"{self.sender_name}: {self.content[:30]}"


class ChatNotice(models.Model):
    company     = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    title       = models.CharField(max_length=200)
    content     = models.TextField()
    author      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    author_name = models.CharField(max_length=100)
    is_pinned   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
