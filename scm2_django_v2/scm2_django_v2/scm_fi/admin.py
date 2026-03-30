from django.contrib import admin

from .models import Account, AccountMove, AccountMoveLine, TaxInvoice


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'root_type', 'is_group', 'is_active', 'company')
    list_filter = ('account_type', 'is_group', 'is_active', 'company')
    search_fields = ('code', 'name', 'root_type')
    ordering = ('code',)


class AccountMoveLineInline(admin.TabularInline):
    model = AccountMoveLine
    extra = 0
    fields = ('account', 'name', 'debit', 'credit', 'is_reconciled', 'due_date')
    readonly_fields = ()


@admin.register(AccountMove)
class AccountMoveAdmin(admin.ModelAdmin):
    list_display = ('move_number', 'move_type', 'posting_date', 'state', 'total_debit', 'total_credit', 'created_by', 'company')
    list_filter = ('move_type', 'state', 'company')
    search_fields = ('move_number', 'ref', 'created_by')
    ordering = ('-posting_date', '-created_at')
    date_hierarchy = 'posting_date'
    inlines = [AccountMoveLineInline]


@admin.register(AccountMoveLine)
class AccountMoveLineAdmin(admin.ModelAdmin):
    list_display = ('move', 'account', 'name', 'debit', 'credit', 'is_reconciled', 'due_date')
    list_filter = ('is_reconciled', 'account__account_type')
    search_fields = ('move__move_number', 'account__code', 'account__name', 'name')
    ordering = ('move',)


@admin.register(TaxInvoice)
class TaxInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'invoice_type', 'supplier_or_customer_name',
        'supply_amount', 'tax_amount', 'total_amount',
        'issue_date', 'status', 'company',
    )
    list_filter  = ('invoice_type', 'status', 'company')
    search_fields = ('invoice_number', 'supplier_or_customer_name')
    ordering     = ('-issue_date', '-created_at')
    date_hierarchy = 'issue_date'
    readonly_fields = ('created_by', 'created_at')
    raw_id_fields   = ('account_move',)
