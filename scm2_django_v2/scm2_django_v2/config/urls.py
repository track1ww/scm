from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView
)

urlpatterns = [
    path('admin/',          admin.site.urls),

    # JWT 인증
    path('api/auth/login/',   TokenObtainPairView.as_view(),  name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('api/auth/verify/',  TokenVerifyView.as_view(),      name='token_verify'),

    # 앱별 API
    path('api/accounts/', include('scm_accounts.urls')),
    path('api/mm/',        include('scm_mm.urls')),
    path('api/sd/',        include('scm_sd.urls')),
    path('api/pp/',        include('scm_pp.urls')),
    path('api/qm/',        include('scm_qm.urls')),
    path('api/wm/',        include('scm_wm.urls')),
    path('api/tm/',        include('scm_tm.urls')),
    path('api/fi/',        include('scm_fi.urls')),
    path('api/hr/',        include('scm_hr.urls')),
    path('api/chat/',      include('scm_chat.urls')),
    path('api/wi/',        include('scm_wi.urls')),
]
