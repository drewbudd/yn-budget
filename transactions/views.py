import csv
import io
import re
from datetime import datetime
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .forms import UploadCSVForm
from .models import Transaction


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


def upload_csv(request):
    message = None
    created = 0
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['file']
            decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8-sig')
            reader = csv.DictReader(decoded_file)
            rows = list(reader)
            for row in rows:
                booking_date = parse_date(row.get('Booking Date'))
                if not booking_date:
                    continue
                transaction = Transaction(
                    booking_date=booking_date,
                    value_date=parse_date(row.get('Value Date')),
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
            message = f'{created} transactions imported successfully.'
    else:
        form = UploadCSVForm()

    recent_transactions = Transaction.objects.order_by('-booking_date')[:10]
    return render(
        request,
        'transactions/upload.html',
        {
            'form': form,
            'message': message,
            'created': created,
            'recent_transactions': recent_transactions,
            'stats_url': reverse('transaction_stats'),
        },
    )


def transaction_stats(request):
    monthly = (
        Transaction.objects
        .annotate(year=ExtractYear('booking_date'), month=ExtractMonth('booking_date'))
        .values('year', 'month')
        .annotate(total=Sum('amount_eur'))
        .order_by('year', 'month')
    )

    category = (
        Transaction.objects
        .values('category')
        .annotate(total=Sum('amount_eur'))
        .order_by('-total')
    )

    return JsonResponse({
        'monthly_totals': list(monthly),
        'category_totals': [
            {'category': item['category'] or 'Uncategorized', 'total': item['total']}
            for item in category
        ],
    })
