from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from .models import Account, AccountMove, AccountMoveLine, TaxInvoice


class AccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(
        source='get_account_type_display', read_only=True
    )
    # Expose code/name as account_code/account_name for frontend compatibility
    account_code = serializers.CharField(source='code', required=False, allow_blank=True)
    account_name = serializers.CharField(source='name', required=False, allow_blank=True)

    class Meta:
        model  = Account
        fields = [
            'id', 'company', 'code', 'name', 'account_code', 'account_name',
            'account_type', 'account_type_display',
            'root_type', 'is_group', 'is_active',
        ]
        read_only_fields = ['company']
        extra_kwargs = {
            'code': {'required': False, 'allow_blank': True},
            'name': {'required': False, 'allow_blank': True},
        }


class AccountMoveLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    # Accept debit_amount/credit_amount as aliases for debit/credit
    debit_amount  = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0, write_only=True)
    credit_amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0, write_only=True)

    def to_internal_value(self, data):
        data = data.copy()
        if 'debit_amount' in data and not data.get('debit'):
            data['debit'] = data.pop('debit_amount')
        if 'credit_amount' in data and not data.get('credit'):
            data['credit'] = data.pop('credit_amount')
        return super().to_internal_value(data)

    class Meta:
        model  = AccountMoveLine
        fields = [
            'id', 'move',
            'account', 'account_code', 'account_name',
            'name', 'debit', 'credit',
            'debit_amount', 'credit_amount',
            'is_reconciled', 'due_date',
        ]
        read_only_fields = ['move']
        extra_kwargs = {
            'debit':  {'required': False, 'default': 0},
            'credit': {'required': False, 'default': 0},
        }


class AccountMoveSerializer(serializers.ModelSerializer):
    """전표 헤더 + 라인 nested 직렬화"""
    lines             = AccountMoveLineSerializer(many=True)
    state_display     = serializers.CharField(source='get_state_display',     read_only=True)
    move_type_display = serializers.CharField(source='get_move_type_display', read_only=True)
    move_number       = serializers.CharField(required=False, allow_blank=True)
    # Accept description as alias for ref
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)

    MOVE_TYPE_MAP = {'GENERAL': 'ENTRY'}

    def to_internal_value(self, data):
        data = data.copy()
        # Map GENERAL → ENTRY
        if data.get('move_type') in self.MOVE_TYPE_MAP:
            data['move_type'] = self.MOVE_TYPE_MAP[data['move_type']]
        # Map description → ref
        if 'description' in data and not data.get('ref'):
            data['ref'] = data.pop('description')
        return super().to_internal_value(data)

    class Meta:
        model  = AccountMove
        fields = [
            'id', 'company',
            'move_number', 'move_type', 'move_type_display',
            'posting_date', 'ref', 'description',
            'state', 'state_display',
            'total_debit', 'total_credit',
            'period_year', 'period_month',
            'is_locked',
            'created_by', 'created_at', 'posted_at',
            'lines',
        ]
        read_only_fields = [
            'company', 'total_debit', 'total_credit',
            'created_at', 'posted_at', 'is_locked',
        ]

    # ------------------------------------------------------------------ #
    #  대차 검증                                                           #
    # ------------------------------------------------------------------ #
    def _validate_balance(self, lines_data: list) -> tuple[Decimal, Decimal]:
        """라인 데이터의 차변/대변 합계를 반환하고, 금액 음수를 방지."""
        total_debit  = Decimal('0')
        total_credit = Decimal('0')
        for idx, line in enumerate(lines_data, start=1):
            debit  = Decimal(str(line.get('debit',  0)))
            credit = Decimal(str(line.get('credit', 0)))
            if debit < 0 or credit < 0:
                raise serializers.ValidationError(
                    {f'lines[{idx}]': '차변/대변 금액은 0 이상이어야 합니다.'}
                )
            if debit > 0 and credit > 0:
                raise serializers.ValidationError(
                    {f'lines[{idx}]': '한 라인에 차변과 대변을 동시에 입력할 수 없습니다.'}
                )
            total_debit  += debit
            total_credit += credit
        return total_debit, total_credit

    def validate(self, attrs):
        lines_data = attrs.get('lines', [])
        if not lines_data:
            raise serializers.ValidationError({'lines': '전표 라인이 최소 1건 이상 필요합니다.'})

        state = attrs.get('state', 'DRAFT')
        total_debit, total_credit = self._validate_balance(lines_data)

        # POSTED 상태로 저장하는 경우 즉시 대차 검증
        if state == 'POSTED' and total_debit != total_credit:
            raise serializers.ValidationError(
                f'대차가 일치하지 않습니다. '
                f'차변 합계({total_debit}) ≠ 대변 합계({total_credit})'
            )

        attrs['_total_debit']  = total_debit
        attrs['_total_credit'] = total_credit
        return attrs

    # ------------------------------------------------------------------ #
    #  Create / Update                                                     #
    # ------------------------------------------------------------------ #
    def create(self, validated_data):
        lines_data   = validated_data.pop('lines')
        total_debit  = validated_data.pop('_total_debit',  Decimal('0'))
        total_credit = validated_data.pop('_total_credit', Decimal('0'))

        validated_data['total_debit']  = total_debit
        validated_data['total_credit'] = total_credit

        move = AccountMove(**validated_data)
        move.save()  # model.save()의 locked/posted 검증 포함

        AccountMoveLine.objects.bulk_create([
            AccountMoveLine(move=move, **line) for line in lines_data
        ])
        return move

    def update(self, instance, validated_data):
        lines_data   = validated_data.pop('lines', None)
        total_debit  = validated_data.pop('_total_debit',  None)
        total_credit = validated_data.pop('_total_credit', None)

        if total_debit  is not None:
            validated_data['total_debit']  = total_debit
        if total_credit is not None:
            validated_data['total_credit'] = total_credit

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()  # model.save()의 locked/posted 검증 포함

        if lines_data is not None:
            instance.lines.all().delete()
            AccountMoveLine.objects.bulk_create([
                AccountMoveLine(move=instance, **line) for line in lines_data
            ])

        instance.refresh_from_db()
        return instance


class TaxInvoiceSerializer(serializers.ModelSerializer):
    """세금계산서 직렬화"""
    invoice_type_display = serializers.CharField(
        source='get_invoice_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.name', read_only=True, default=''
    )
    account_move_number = serializers.CharField(
        source='account_move.move_number', read_only=True, default=''
    )
    invoice_number = serializers.CharField(required=False, allow_blank=True)
    # Accept frontend alias fields
    counterpart_name   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    counterpart_reg_no = serializers.CharField(write_only=True, required=False, allow_blank=True)
    invoice_date       = serializers.DateField(write_only=True, required=False, allow_null=True)

    def to_internal_value(self, data):
        data = data.copy()
        if 'counterpart_name' in data and not data.get('supplier_or_customer_name'):
            data['supplier_or_customer_name'] = data.pop('counterpart_name')
        if 'invoice_date' in data and not data.get('issue_date'):
            data['issue_date'] = data.pop('invoice_date')
        data.pop('counterpart_reg_no', None)
        return super().to_internal_value(data)

    class Meta:
        model  = TaxInvoice
        fields = [
            'id', 'company',
            'invoice_number', 'invoice_type', 'invoice_type_display',
            'supplier_or_customer_name',
            'supply_amount', 'tax_amount', 'total_amount',
            'issue_date',
            'account_move', 'account_move_number',
            'status', 'status_display',
            'created_by', 'created_by_name', 'created_at',
            # write-only aliases
            'counterpart_name', 'counterpart_reg_no', 'invoice_date',
        ]
        read_only_fields = ['company', 'created_by', 'created_at']
        extra_kwargs = {
            'supplier_or_customer_name': {'required': False, 'allow_blank': True},
            'issue_date': {'required': False},
            'total_amount': {'required': False},
        }

    def validate(self, attrs):
        supply_amount = attrs.get('supply_amount')
        tax_amount    = attrs.get('tax_amount')

        if supply_amount is not None and tax_amount is not None:
            expected_tax = (Decimal(str(supply_amount)) * Decimal('0.1')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if Decimal(str(tax_amount)) != expected_tax:
                raise serializers.ValidationError(
                    {'tax_amount': f'세액은 공급가액의 10%이어야 합니다. 기대값: {expected_tax}'}
                )
            # Auto-calculate total_amount if not provided
            if not attrs.get('total_amount'):
                attrs['total_amount'] = Decimal(str(supply_amount)) + Decimal(str(tax_amount))

        return attrs
