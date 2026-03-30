from django.urls import path
from .views import RegisterView, ProfileView, UserListView, PermissionView

urlpatterns = [
    path('register/',    RegisterView.as_view(),    name='register'),
    path('profile/',     ProfileView.as_view(),     name='profile'),
    path('users/',       UserListView.as_view(),    name='users'),
    path('permissions/', PermissionView.as_view(),  name='permissions'),
]
