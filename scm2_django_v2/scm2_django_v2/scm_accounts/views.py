from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from django.contrib.auth import get_user_model
from .models import UserPermission
from .serializers import UserSerializer, RegisterSerializer, PermissionSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class   = RegisterSerializer

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    def get_object(self): return self.request.user

class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    def get_queryset(self):
        return User.objects.filter(company=self.request.user.company)

class PermissionView(APIView):
    def get(self, request):
        perms = UserPermission.objects.filter(user=request.user)
        return Response(PermissionSerializer(perms, many=True).data)

    def post(self, request):
        """관리자: 사용자 권한 설정"""
        if not request.user.is_admin:
            return Response(status=status.HTTP_403_FORBIDDEN)
        s = PermissionSerializer(data=request.data, many=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
