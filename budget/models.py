from decimal import Decimal
from django.db import models

class Transaction(models.Model):
    booking_date = models.DateField()
    value_date = models.DateField(blank=True, null=True)
    partner_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=128, blank=True, null=True)
    amount_eur = models.DecimalField(max_digits=12, decimal_places=2)
    payment_reference = models.TextField(blank=True)
    partner_iban = models.CharField(max_length=64, blank=True)
    transaction_type = models.CharField(max_length=64, blank=True, verbose_name='Type')
    account_name = models.CharField(max_length=128, blank=True)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    original_currency = models.CharField(max_length=8, blank=True, default='EUR')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-value_date', '-booking_date', '-id']

    def __str__(self):
        date_value = self.value_date or self.booking_date
        return f'{date_value} {self.partner_name or "Unknown"} {self.amount_eur}'

    @staticmethod
    def parse_decimal(value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        value = value.replace('€', '').replace(',', '').strip()
        try:
            return Decimal(value)
        except Exception:
            return None
