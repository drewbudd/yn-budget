from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('value_date', 'booking_date', 'partner_name', 'category', 'amount_eur', 'transaction_type')
    list_filter = ('category', 'transaction_type', 'value_date', 'booking_date')
    search_fields = ('partner_name', 'payment_reference', 'category')
