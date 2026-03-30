from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, ProfileView, UserListView, PermissionView, RoleViewSet

router = DefaultRouter()
router.register('roles', RoleViewSet, basename='role')

urlpatterns = [
    path('register/',    RegisterView.as_view(),    name='register'),
    path('profile/',     ProfileView.as_view(),     name='profile'),
    path('users/',       UserListView.as_view(),    name='users'),
    path('permissions/', PermissionView.as_view(),  name='permissions'),
    path('', include(router.urls)),
]
