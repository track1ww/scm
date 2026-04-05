from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    company_code = models.CharField(max_length=20, unique=True)
    company_name = models.CharField(max_length=200)
    business_no  = models.CharField(max_length=20, blank=True)
    plan         = models.CharField(max_length=20, default='BASIC',
                                    choices=[('BASIC','Basic'),
                                             ('STANDARD','Standard'),
                                             ('ENTERPRISE','Enterprise')])
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class User(AbstractUser):
    email      = models.EmailField(unique=True)
    name       = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    is_admin   = models.BooleanField(default=False)
    company    = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='users'
    )

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    def __str__(self):
        return f"{self.name} ({self.email})"


class UserPermission(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='module_permissions')
    module    = models.CharField(max_length=20)
    can_read   = models.BooleanField(default=False)
    can_write  = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'module')

    def __str__(self):
        return f"{self.user.name} — {self.module}"


# ──────────────────────────────────────────────
# RBAC 역할 템플릿
# ──────────────────────────────────────────────

ALL_MODULES = ['mm', 'sd', 'pp', 'qm', 'wm', 'tm', 'fi', 'hr', 'wi', 'workflow', 'chat']

# 사전 정의 역할 코드 (커스텀 역할도 허용)
ROLE_PRESETS = {
    'ADMIN':       '관리자',
    'ACCOUNTANT':  '회계담당자',
    'BUYER':       '구매담당자',
    'SALES':       '영업담당자',
    'WAREHOUSE':   '창고담당자',
    'HR_STAFF':    '인사담당자',
    'PRODUCTION':  '생산담당자',
    'VIEWER':      '조회전용',
    'CUSTOM':      '사용자 정의',
}

# 역할별 기본 권한 매핑 {module: (can_read, can_write, can_delete)}
ROLE_DEFAULT_PERMISSIONS = {
    'ADMIN':      {m: (True, True, True) for m in ALL_MODULES},
    'ACCOUNTANT': {**{m: (False, False, False) for m in ALL_MODULES},
                   'fi': (True, True, False), 'mm': (True, False, False), 'sd': (True, False, False)},
    'BUYER':      {**{m: (False, False, False) for m in ALL_MODULES},
                   'mm': (True, True, False), 'wm': (True, False, False), 'fi': (True, False, False)},
    'SALES':      {**{m: (False, False, False) for m in ALL_MODULES},
                   'sd': (True, True, False), 'wm': (True, False, False), 'fi': (True, False, False)},
    'WAREHOUSE':  {**{m: (False, False, False) for m in ALL_MODULES},
                   'wm': (True, True, False), 'mm': (True, False, False), 'tm': (True, True, False)},
    'HR_STAFF':   {**{m: (False, False, False) for m in ALL_MODULES},
                   'hr': (True, True, False), 'workflow': (True, True, False)},
    'PRODUCTION': {**{m: (False, False, False) for m in ALL_MODULES},
                   'pp': (True, True, False), 'wm': (True, False, False), 'qm': (True, True, False), 'wi': (True, True, False)},
    'VIEWER':     {m: (True, False, False) for m in ALL_MODULES},
    'CUSTOM':     {m: (False, False, False) for m in ALL_MODULES},
}


class Role(models.Model):
    """역할 템플릿 — 회사별로 생성하고 유저에게 할당합니다."""
    company     = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='roles')
    code        = models.CharField(max_length=20, choices=list(ROLE_PRESETS.items()), default='CUSTOM')
    name        = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'code')

    def __str__(self):
        return f"{self.company.company_name} / {self.name}"

    def apply_to_user(self, user: User):
        """이 역할의 기본 권한을 유저 UserPermission에 일괄 적용합니다."""
        perm_map = ROLE_DEFAULT_PERMISSIONS.get(self.code, ROLE_DEFAULT_PERMISSIONS['CUSTOM'])
        for module, (can_read, can_write, can_delete) in perm_map.items():
            UserPermission.objects.update_or_create(
                user=user, module=module,
                defaults={'can_read': can_read, 'can_write': can_write, 'can_delete': can_delete},
            )


class UserRole(models.Model):
    """유저 ↔ 역할 M:N (한 유저가 여러 역할 보유 가능)."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role       = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name='assigned_roles')

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.name} → {self.role.name}"