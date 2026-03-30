from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .models import UserPermission, Role, UserRole, ROLE_DEFAULT_PERMISSIONS, ROLE_PRESETS
from .serializers import UserSerializer, RegisterSerializer, PermissionSerializer, RoleSerializer, UserRoleSerializer

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


class RoleViewSet(viewsets.ModelViewSet):
    """역할 템플릿 CRUD + 유저 일괄 권한 적용."""
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Role.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'], url_path='presets')
    def presets(self, request):
        """사용 가능한 역할 프리셋 목록과 각 역할의 기본 권한 반환."""
        result = []
        for code, label in ROLE_PRESETS.items():
            perms = ROLE_DEFAULT_PERMISSIONS.get(code, {})
            result.append({
                'code': code,
                'label': label,
                'permissions': [
                    {'module': m, 'can_read': r, 'can_write': w}
                    for m, (r, w) in perms.items()
                ],
            })
        return Response(result)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """역할을 특정 유저에게 할당하고 권한을 즉시 적용."""
        if not request.user.is_admin:
            return Response({'detail': '관리자만 역할을 할당할 수 있습니다.'},
                            status=status.HTTP_403_FORBIDDEN)
        role = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id 필드가 필요합니다.'}, status=400)
        try:
            target = User.objects.get(pk=user_id, company=request.user.company)
        except User.DoesNotExist:
            return Response({'detail': '해당 유저를 찾을 수 없습니다.'}, status=404)

        ur, created = UserRole.objects.get_or_create(
            user=target, role=role,
            defaults={'assigned_by': request.user},
        )
        role.apply_to_user(target)  # UserPermission 일괄 갱신

        return Response({
            'detail': f'{target.name}님에게 [{role.name}] 역할을 {"할당" if created else "재적용"}했습니다.',
            'user_role_id': ur.pk,
        })

    @action(detail=True, methods=['delete'], url_path='revoke')
    def revoke(self, request, pk=None):
        """역할 회수 (UserRole 삭제, 권한은 유지 — 별도로 수정 가능)."""
        if not request.user.is_admin:
            return Response({'detail': '관리자만 역할을 회수할 수 있습니다.'},
                            status=status.HTTP_403_FORBIDDEN)
        role = self.get_object()
        user_id = request.data.get('user_id')
        deleted, _ = UserRole.objects.filter(user_id=user_id, role=role).delete()
        if deleted:
            return Response({'detail': '역할이 회수되었습니다.'})
        return Response({'detail': '해당 유저-역할 관계가 없습니다.'}, status=404)
