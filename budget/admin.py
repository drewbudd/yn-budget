from django.contrib import admin
from .models import Transaction, Budget


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('value_date', 'booking_date', 'partner_name', 'category', 'amount_eur', 'transaction_type')
    list_filter = ('category', 'transaction_type', 'value_date', 'booking_date')
    search_fields = ('partner_name', 'payment_reference', 'category')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'category', 'amount', 'updated_at')
    list_filter = ('year', 'month', 'category')
    search_fields = ('category',)
