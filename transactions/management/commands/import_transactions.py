import csv
import io
import re
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from transactions.models import Transaction


def parse_decimal(raw_value):
    if raw_value is None:
        return None
    raw_value = str(raw_value).strip()
    if not raw_value:
        return None
    cleaned = re.sub(r'[^\,\d\-\.]+', '', raw_value)
    cleaned = cleaned.replace(',', '')
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def parse_date(raw_value):
    if raw_value is None:
        return None
    raw_value = str(raw_value).strip()
    if not raw_value:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(raw_value, fmt).date()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = 'Import transactions from a CSV file into the database.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the transactions CSV file.')

    def handle(self, *args, **options):
        path = options['csv_path']
        created = 0
        with open(path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                booking_date = parse_date(row.get('Booking Date'))
                if not booking_date:
                    continue
                value_date = parse_date(row.get('Value Date')) or booking_date
                transaction = Transaction(
                    booking_date=booking_date,
                    value_date=value_date,
                    partner_name=row.get('Partner Name', '').strip(),
                    category=row.get('Category', '').strip() or None,
                    amount_eur=parse_decimal(row.get('Amount (EUR)')) or Decimal('0.00'),
                    payment_reference=row.get('Payment Reference', '').strip(),
                    partner_iban=row.get('Partner Iban', '').strip(),
                    transaction_type=row.get('Type', '').strip(),
                    account_name=row.get('Account Name', '').strip(),
                    original_amount=parse_decimal(row.get('Original Amount')),
                    original_currency=row.get('Original Currency', '').strip(),
                    exchange_rate=parse_decimal(row.get('Exchange Rate')),
                )
                transaction.save()
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Imported {created} transactions from {path}'))
