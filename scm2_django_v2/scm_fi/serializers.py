import uuid
from rest_framework import serializers
from .models import Account, AccountMove, AccountMoveLine, Budget, FixedAsset, DepreciationSchedule, TaxInvoice, AccountingPeriod


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'code', 'name', 'account_type', 'root_type', 'is_group', 'is_active']


class AccountMoveLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_code = serializers.CharField(source='account.code', read_only=True)

    class Meta:
        model = AccountMoveLine
        fields = ['id', 'account', 'account_code', 'account_name', 'name',
                  'debit', 'credit', 'is_reconciled', 'due_date']


class AccountMoveSerializer(serializers.ModelSerializer):
    lines = AccountMoveLineSerializer(many=True, read_only=True)

    class Meta:
        model = AccountMove
        fields = ['id', 'move_number', 'move_type', 'posting_date', 'ref',
                  'state', 'total_debit', 'total_credit', 'created_by',
                  'created_at', 'posted_at', 'lines']
        read_only_fields = ['move_number', 'state', 'total_debit', 'total_credit',
                            'created_at', 'posted_at']


class AccountMoveWriteSerializer(serializers.ModelSerializer):
    lines = AccountMoveLineSerializer(many=True, required=False)

    class Meta:
        model = AccountMove
        fields = ['id', 'move_number', 'move_type', 'posting_date', 'ref', 'created_by', 'lines']
        read_only_fields = ['move_number']

    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        move = AccountMove.objects.create(**validated_data)
        total_debit = total_credit = 0
        for line_data in lines_data:
            line = AccountMoveLine.objects.create(move=move, **line_data)
            total_debit  += float(line.debit  or 0)
            total_credit += float(line.credit or 0)
        move.total_debit  = total_debit
        move.total_credit = total_credit
        move.save(update_fields=['total_debit', 'total_credit'])
        return move


class BudgetSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_code = serializers.CharField(source='account.code', read_only=True)

    class Meta:
        model = Budget
        fields = ['id', 'budget_year', 'budget_month', 'account', 'account_code', 'account_name',
                  'budgeted_amount', 'actual_amount', 'variance', 'note']


class DepreciationScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepreciationSchedule
        fields = ['id', 'period_year', 'period_month', 'depreciation_amount',
                  'accumulated_amount', 'book_value_after', 'is_posted']


class FixedAssetSerializer(serializers.ModelSerializer):
    schedules = DepreciationScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = FixedAsset
        fields = ['id', 'asset_code', 'asset_name', 'category', 'acquisition_date',
                  'acquisition_cost', 'useful_life_years', 'salvage_value',
                  'depreciation_method', 'accumulated_depreciation', 'book_value',
                  'status', 'location', 'schedules']
        read_only_fields = ['accumulated_depreciation', 'book_value']


class TaxInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxInvoice
        fields = ['id', 'invoice_number', 'invoice_type', 'issue_date', 'counterpart',
                  'supply_amount', 'vat_amount', 'total_amount', 'status', 'remark', 'created_at']
        read_only_fields = ['invoice_number', 'created_at']


class AccountingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingPeriod
        fields = '__all__'
        read_only_fields = ['closed_by', 'closed_at']
