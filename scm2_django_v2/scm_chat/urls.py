from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, ChatMessageViewSet, ChatNoticeViewSet

router = DefaultRouter()
router.register('rooms',    ChatRoomViewSet,    basename='room')
router.register('messages', ChatMessageViewSet, basename='message')
router.register('notices',  ChatNoticeViewSet,  basename='notice')

urlpatterns = router.urls
