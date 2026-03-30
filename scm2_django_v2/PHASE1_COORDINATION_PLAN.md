# SCM Phase 1 Multi-Agent Coordination Plan

## 1. Current State Summary

| Module | Models | Serializers | Views/API | Signals |
|--------|--------|-------------|-----------|---------|
| scm_fi | Account, AccountMove, AccountMoveLine | NONE | EMPTY | NONE |
| scm_mm | Supplier, Material, PurchaseOrder, GoodsReceipt | DONE | DONE (ViewSet) | NONE |
| scm_sd | Customer, SalesOrder, Delivery | NONE | EMPTY | NONE |
| scm_wm | Warehouse, Inventory | NONE | EMPTY | NONE |

- DB: PostgreSQL, Auth: JWT (SimpleJWT), API: DRF ViewSet pattern
- Channel Layer: InMemoryChannelLayer (needs Redis for prod)
- settings.py SECRET_KEY: hardcoded fallback (needs env-only)

---

## 2. Dependency Graph & Execution Order

```
Track A (Security/Infra) ────────────────────────> DONE
        |                                            |
        | (no blocker)                               |
        v                                            |
Track B (FI Module)  ────────────────────────────> DONE
        |                                            |
        | Track C depends on Track B model interface  |
        v                                            |
Track C (Cross-module Signals) ──────────────────> DONE
```

**Parallel Execution Rules:**
- Track A: fully independent, start immediately
- Track B: fully independent, start immediately
- Track C: depends on Track B model interface (Account, AccountMove, AccountMoveLine field names) AND scm_wm model additions. Can start coding once the Interface Contract below is agreed upon, but must merge AFTER Track B.

---

## 3. Interface Contract (All Tracks MUST use these exact names)

### 3.1 FI Model Interface (Track B produces, Track C consumes)

```python
# scm_fi.models.Account
#   PK: id (BigAutoField)
#   Fields: company(FK), code(CharField), name, account_type, is_active
#   Lookup: Account.objects.get(company=company, code=CODE)

# scm_fi.models.AccountMove
#   PK: id (BigAutoField)
#   Fields: company(FK), move_number, move_type, posting_date, state,
#           total_debit, total_credit, ref, created_by, created_at, posted_at
#   move_type choices: 'ENTRY','PURCHASE','SALE','PAYMENT','RECEIPT','ADJUST'
#   state choices: 'DRAFT','POSTED','CANCELLED'

# scm_fi.models.AccountMoveLine
#   PK: id (BigAutoField)
#   Fields: move(FK->AccountMove, related_name='lines'),
#           account(FK->Account), name, debit, credit, is_reconciled, due_date
```

### 3.2 WM Model Interface (Track C adds, all tracks reference)

```python
# scm_wm.models.InventoryMovement (NEW - Track C adds this)
#   PK: id (BigAutoField)
#   company       = FK(Company)
#   inventory     = FK(Inventory, related_name='movements')
#   movement_type = CharField choices: 'IN','OUT','ADJUST','TRANSFER'
#   quantity      = IntegerField
#   reference     = CharField(max_length=100)  # GR번호 or DN번호
#   source_module = CharField(max_length=20)   # 'MM','SD','WM'
#   created_by    = CharField(max_length=100)
#   created_at    = DateTimeField(auto_now_add=True)
```

### 3.3 Standard Account Codes (Track A seeds, Track B/C reference)

| Code | Name | Type | Used By |
|------|------|------|---------|
| 1010 | 현금및현금성자산 | ASSET | Payment/Receipt |
| 1040 | 매출채권 | ASSET | SD sale |
| 1050 | 재고자산 | ASSET | MM receipt / SD shipment |
| 2010 | 매입채무 | LIABILITY | MM purchase |
| 4010 | 매출 | REVENUE | SD sale |
| 5010 | 매출원가 | EXPENSE | SD shipment |
| 5020 | 매입비용 | EXPENSE | MM purchase |

### 3.4 API URL Patterns (Track B implements)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `api/fi/accounts/` | GET | 계정과목 목록 |
| `api/fi/accounts/` | POST | 계정과목 생성 |
| `api/fi/accounts/{id}/` | GET/PUT/PATCH/DELETE | 계정과목 상세 |
| `api/fi/moves/` | GET | 전표 목록 |
| `api/fi/moves/` | POST | 전표 생성 (lines 포함) |
| `api/fi/moves/{id}/` | GET/PUT/DELETE | 전표 상세 |
| `api/fi/moves/{id}/post/` | POST | 전표 확정 (대차 검증 후) |
| `api/fi/moves/{id}/cancel/` | POST | 전표 취소 |
| `api/fi/moves/trial-balance/` | GET | 시산표 조회 |
| `api/fi/moves/dashboard/` | GET | FI 대시보드 |

### 3.5 Signal Flow (Track C implements)

```
MM GoodsReceipt post_save (status change -> created)
  |
  +--> Create AccountMove(type='PURCHASE')
  |      Line 1: debit  재고자산(1050)  = received_qty * unit_price
  |      Line 2: credit 매입채무(2010)  = received_qty * unit_price
  |
  +--> WM Inventory.stock_qty += received_qty
  |
  +--> Create InventoryMovement(type='IN', reference=gr_number)


SD Delivery post_save (status change -> '배송중')
  |
  +--> Create AccountMove(type='SALE')
  |      Line 1: debit  매출채권(1040)  = delivery_qty * unit_price
  |      Line 2: credit 매출(4010)      = delivery_qty * unit_price
  |
  +--> WM Inventory.stock_qty -= delivery_qty
  |
  +--> Create InventoryMovement(type='OUT', reference=delivery_number)
```

---

## 4. Track A - Security/Infra Agent Specification

### 4.1 Files to Modify
- `config/settings.py`
- `scm_fi/admin.py`, `scm_mm/admin.py`, `scm_sd/admin.py`, `scm_wm/admin.py`
- `scm_pp/admin.py`, `scm_qm/admin.py`, `scm_tm/admin.py`, `scm_hr/admin.py`
- `requirements.txt`

### 4.2 Detailed Tasks

#### settings.py Changes
```python
# 1. SECRET_KEY: remove fallback, require env var in production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-insecure-key-do-not-use-in-production'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production')

# 2. ALLOWED_HOSTS: restrict from '*'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# 3. CHANNEL_LAYERS: switch to Redis for production
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.environ.get('REDIS_HOST', '127.0.0.1'), 6379)],
        },
    } if not DEBUG else {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# 4. Security headers for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'

# 5. LOGGING configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'scm.log',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
}
```

#### admin.py Registration (all modules)
Register all existing models with appropriate list_display, search_fields, list_filter.

Example for scm_fi/admin.py:
```python
from django.contrib import admin
from .models import Account, AccountMove, AccountMoveLine

class AccountMoveLineInline(admin.TabularInline):
    model = AccountMoveLine
    extra = 1

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'account_type', 'company', 'is_active')
    list_filter   = ('account_type', 'is_active', 'company')
    search_fields = ('code', 'name')

@admin.register(AccountMove)
class AccountMoveAdmin(admin.ModelAdmin):
    list_display  = ('move_number', 'move_type', 'posting_date', 'state',
                     'total_debit', 'total_credit', 'company')
    list_filter   = ('state', 'move_type', 'company')
    search_fields = ('move_number', 'ref')
    inlines       = [AccountMoveLineInline]
```

#### requirements.txt Additions
```
django-environ>=0.11
gunicorn>=21.2
whitenoise>=6.5
sentry-sdk>=1.40
```

---

## 5. Track B - FI Module Agent Specification

### 5.1 Files to Create/Modify
- `scm_fi/models.py` (MODIFY: add validation methods)
- `scm_fi/serializers.py` (CREATE)
- `scm_fi/views.py` (REWRITE)
- `scm_fi/urls.py` (REWRITE)

### 5.2 models.py Additions

Add these methods to AccountMove:
```python
class AccountMove(models.Model):
    # ... existing fields ...

    def validate_balance(self):
        """Check debit == credit across all lines"""
        from django.db.models import Sum
        totals = self.lines.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        d = totals['total_debit'] or 0
        c = totals['total_credit'] or 0
        if d != c:
            raise ValidationError(
                f'Debit({d}) != Credit({c}). Difference: {d - c}'
            )
        return d, c

    def action_post(self):
        """Validate and post the move"""
        if self.state != 'DRAFT':
            raise ValidationError('Only DRAFT moves can be posted')
        if not self.lines.exists():
            raise ValidationError('Cannot post a move with no lines')
        d, c = self.validate_balance()
        self.total_debit = d
        self.total_credit = c
        self.state = 'POSTED'
        self.posted_at = timezone.now()
        self.save()

    def action_cancel(self):
        """Cancel a posted move"""
        if self.state != 'POSTED':
            raise ValidationError('Only POSTED moves can be cancelled')
        self.state = 'CANCELLED'
        self.save()
```

### 5.3 serializers.py (NEW)

```python
from rest_framework import serializers
from .models import Account, AccountMove, AccountMoveLine

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Account
        fields = '__all__'

class AccountMoveLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model  = AccountMoveLine
        fields = ['id', 'account', 'account_name', 'name',
                  'debit', 'credit', 'is_reconciled', 'due_date']

class AccountMoveSerializer(serializers.ModelSerializer):
    lines = AccountMoveLineSerializer(many=True)

    class Meta:
        model  = AccountMove
        fields = '__all__'
        read_only_fields = ('total_debit', 'total_credit', 'posted_at')

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        move = AccountMove.objects.create(**validated_data)
        for line_data in lines_data:
            AccountMoveLine.objects.create(move=move, **line_data)
        return move

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                AccountMoveLine.objects.create(move=instance, **line_data)
        return instance

class AccountMoveListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    line_count = serializers.IntegerField(source='lines.count', read_only=True)

    class Meta:
        model  = AccountMove
        fields = ['id', 'move_number', 'move_type', 'posting_date',
                  'state', 'total_debit', 'total_credit', 'line_count']
```

### 5.4 views.py (REWRITE)

```python
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Account, AccountMove, AccountMoveLine
from .serializers import (AccountSerializer, AccountMoveSerializer,
                          AccountMoveListSerializer)

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['code', 'name']
    filterset_fields = ['account_type', 'is_active']

    def get_queryset(self):
        return Account.objects.filter(company=self.request.user.company)

class AccountMoveViewSet(viewsets.ModelViewSet):
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend,
                        filters.OrderingFilter]
    search_fields    = ['move_number', 'ref']
    filterset_fields = ['state', 'move_type']
    ordering_fields  = ['posting_date', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AccountMoveListSerializer
        return AccountMoveSerializer

    def get_queryset(self):
        return AccountMove.objects.filter(
            company=self.request.user.company
        ).prefetch_related('lines').order_by('-posting_date')

    @action(detail=True, methods=['post'])
    def post_move(self, request, pk=None):
        """POST api/fi/moves/{id}/post/ - validate balance & post"""
        move = self.get_object()
        try:
            move.action_post()
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        return Response(AccountMoveSerializer(move).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """POST api/fi/moves/{id}/cancel/"""
        move = self.get_object()
        try:
            move.action_cancel()
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        return Response(AccountMoveSerializer(move).data)

    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """GET api/fi/moves/trial-balance/?from=YYYY-MM-DD&to=YYYY-MM-DD"""
        date_from = request.query_params.get('from')
        date_to   = request.query_params.get('to')
        qs = AccountMoveLine.objects.filter(
            move__company=request.user.company,
            move__state='POSTED'
        )
        if date_from:
            qs = qs.filter(move__posting_date__gte=date_from)
        if date_to:
            qs = qs.filter(move__posting_date__lte=date_to)
        rows = qs.values(
            'account__code', 'account__name', 'account__account_type'
        ).annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        ).order_by('account__code')
        return Response(list(rows))

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':     qs.count(),
            'draft':     qs.filter(state='DRAFT').count(),
            'posted':    qs.filter(state='POSTED').count(),
            'cancelled': qs.filter(state='CANCELLED').count(),
        })
```

### 5.5 urls.py (REWRITE)

```python
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, AccountMoveViewSet

router = DefaultRouter()
router.register('accounts', AccountViewSet, basename='account')
router.register('moves',    AccountMoveViewSet, basename='move')

urlpatterns = router.urls
```

---

## 6. Track C - Cross-Module Signals Agent Specification

### 6.1 Files to Create/Modify
- `scm_wm/models.py` (MODIFY: add InventoryMovement)
- `scm_mm/signals.py` (CREATE)
- `scm_sd/signals.py` (CREATE)
- `scm_mm/apps.py` (MODIFY: register signals)
- `scm_sd/apps.py` (MODIFY: register signals)

### 6.2 scm_wm/models.py Addition

```python
class InventoryMovement(models.Model):
    """Inventory movement history for audit trail"""
    MOVEMENT_TYPE = [
        ('IN', 'Input'),
        ('OUT', 'Output'),
        ('ADJUST', 'Adjustment'),
        ('TRANSFER', 'Transfer'),
    ]
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    inventory     = models.ForeignKey(Inventory, on_delete=models.CASCADE,
                                       related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE)
    quantity      = models.IntegerField()
    reference     = models.CharField(max_length=100, blank=True)
    source_module = models.CharField(max_length=20, blank=True)
    created_by    = models.CharField(max_length=100, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movement_type} {self.quantity} - {self.reference}"
```

### 6.3 scm_mm/signals.py (NEW)

```python
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from scm_mm.models import GoodsReceipt

logger = logging.getLogger(__name__)

@receiver(post_save, sender=GoodsReceipt)
def on_goods_receipt_created(sender, instance, created, **kwargs):
    """When GoodsReceipt is created:
       1. Create FI AccountMove (PURCHASE) with debit 1050 / credit 2010
       2. Increase WM Inventory.stock_qty
       3. Create InventoryMovement record
    """
    if not created:
        return

    gr = instance
    company = gr.company
    amount = gr.received_qty * (gr.po.unit_price if gr.po else 0)

    # --- 1. FI Journal Entry ---
    try:
        from scm_fi.models import Account, AccountMove, AccountMoveLine

        move = AccountMove.objects.create(
            company=company,
            move_number=f"FI-GR-{gr.gr_number}",
            move_type='PURCHASE',
            posting_date=date.today(),
            ref=f"Goods Receipt {gr.gr_number}",
            state='POSTED',
            total_debit=amount,
            total_credit=amount,
            created_by='system:mm_signal',
        )
        acct_inventory = Account.objects.get(company=company, code='1050')
        acct_payable   = Account.objects.get(company=company, code='2010')

        AccountMoveLine.objects.create(
            move=move, account=acct_inventory,
            name=f"Inventory In - {gr.item_name}",
            debit=amount, credit=0
        )
        AccountMoveLine.objects.create(
            move=move, account=acct_payable,
            name=f"AP - {gr.item_name}",
            debit=0, credit=amount
        )
        logger.info(f"FI move {move.move_number} created for GR {gr.gr_number}")
    except Exception as e:
        logger.error(f"FI journal creation failed for GR {gr.gr_number}: {e}")

    # --- 2 & 3. WM Inventory Update + Movement ---
    try:
        from scm_wm.models import Inventory, InventoryMovement

        inv, _ = Inventory.objects.get_or_create(
            item_code=gr.po.material_code if hasattr(gr.po, 'material_code') else gr.item_name,
            warehouse=None,  # resolve from gr.warehouse string
            lot_number='',
            defaults={
                'company': company,
                'item_name': gr.item_name,
                'stock_qty': 0,
                'system_qty': 0,
            }
        )
        inv.stock_qty  += gr.received_qty
        inv.system_qty += gr.received_qty
        inv.save()

        InventoryMovement.objects.create(
            company=company,
            inventory=inv,
            movement_type='IN',
            quantity=gr.received_qty,
            reference=gr.gr_number,
            source_module='MM',
            created_by='system:mm_signal',
        )
        logger.info(f"WM stock updated +{gr.received_qty} for GR {gr.gr_number}")
    except Exception as e:
        logger.error(f"WM inventory update failed for GR {gr.gr_number}: {e}")
```

### 6.4 scm_sd/signals.py (NEW)

```python
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from scm_sd.models import Delivery

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Delivery)
def on_delivery_shipped(sender, instance, created, **kwargs):
    """When Delivery status becomes '배송중':
       1. Create FI AccountMove (SALE) with debit 1040 / credit 4010
       2. Decrease WM Inventory.stock_qty
       3. Create InventoryMovement record
    """
    dn = instance
    if dn.status != '배송중':
        return

    company = dn.company
    order = dn.order
    unit_price = order.unit_price if order else 0
    amount = dn.delivery_qty * unit_price

    # --- 1. FI Journal Entry ---
    try:
        from scm_fi.models import Account, AccountMove, AccountMoveLine

        move_number = f"FI-DN-{dn.delivery_number}"
        if AccountMove.objects.filter(move_number=move_number).exists():
            return  # idempotency guard

        move = AccountMove.objects.create(
            company=company,
            move_number=move_number,
            move_type='SALE',
            posting_date=date.today(),
            ref=f"Delivery {dn.delivery_number}",
            state='POSTED',
            total_debit=amount,
            total_credit=amount,
            created_by='system:sd_signal',
        )
        acct_receivable = Account.objects.get(company=company, code='1040')
        acct_revenue    = Account.objects.get(company=company, code='4010')

        AccountMoveLine.objects.create(
            move=move, account=acct_receivable,
            name=f"AR - {dn.item_name}",
            debit=amount, credit=0
        )
        AccountMoveLine.objects.create(
            move=move, account=acct_revenue,
            name=f"Revenue - {dn.item_name}",
            debit=0, credit=amount
        )
        logger.info(f"FI move {move.move_number} created for DN {dn.delivery_number}")
    except Exception as e:
        logger.error(f"FI journal creation failed for DN {dn.delivery_number}: {e}")

    # --- 2 & 3. WM Inventory Update + Movement ---
    try:
        from scm_wm.models import Inventory, InventoryMovement

        inv = Inventory.objects.filter(
            company=company, item_name=dn.item_name
        ).first()
        if inv:
            inv.stock_qty  -= dn.delivery_qty
            inv.system_qty -= dn.delivery_qty
            inv.save()

            InventoryMovement.objects.create(
                company=company,
                inventory=inv,
                movement_type='OUT',
                quantity=dn.delivery_qty,
                reference=dn.delivery_number,
                source_module='SD',
                created_by='system:sd_signal',
            )
            logger.info(f"WM stock updated -{dn.delivery_qty} for DN {dn.delivery_number}")
        else:
            logger.warning(f"No inventory found for item {dn.item_name}")
    except Exception as e:
        logger.error(f"WM inventory update failed for DN {dn.delivery_number}: {e}")
```

### 6.5 apps.py Modifications

scm_mm/apps.py:
```python
from django.apps import AppConfig

class MmConfig(AppConfig):
    name = 'scm_mm'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import scm_mm.signals  # noqa
```

scm_sd/apps.py:
```python
from django.apps import AppConfig

class SdConfig(AppConfig):
    name = 'scm_sd'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import scm_sd.signals  # noqa
```

---

## 7. Execution Timeline

```
Time  Track A (Infra)         Track B (FI API)         Track C (Signals)
----  --------------------    --------------------     --------------------
T+0   START                   START                    START (wm/models.py only)
      settings.py hardening   models.py validation     InventoryMovement model
      requirements.txt        serializers.py           Wait for Track B interface
T+1   admin.py (all apps)     views.py                 signals.py (mm, sd)
                               urls.py                  apps.py (mm, sd)
T+2   DONE                    DONE                     Integration test
T+3   ---                     ---                      DONE
```

## 8. Merge Order

1. Track A merges FIRST (infra changes, no model conflicts)
2. Track B merges SECOND (FI models are dependency for Track C)
3. Track C merges LAST (depends on both A and B)

After all merges:
```bash
python manage.py makemigrations scm_fi scm_wm
python manage.py migrate
```

## 9. Validation Checklist

- [ ] `python manage.py check` passes with no errors
- [ ] `python manage.py makemigrations --check` shows no pending migrations
- [ ] FI API CRUD works: POST /api/fi/moves/ with nested lines
- [ ] FI balance validation rejects unbalanced entries
- [ ] GoodsReceipt creation triggers FI journal + WM stock increase
- [ ] Delivery status='배송중' triggers FI journal + WM stock decrease
- [ ] Admin site shows all models with proper list views
- [ ] settings.py has no hardcoded secrets in production mode
- [ ] Channel layer uses Redis when DEBUG=False

## 10. Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Account codes not seeded | Track C signals use try/except, log errors gracefully |
| Signal runs before migration | Lazy imports inside signal handlers |
| Duplicate FI entries on re-save | Idempotency guard: check move_number exists |
| Inventory not found for SD | Fallback: log warning, skip WM update |
| Circular import | All cross-module imports inside functions, not at module level |
