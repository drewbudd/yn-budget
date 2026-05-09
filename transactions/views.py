import csv
import io
import re
from datetime import datetime
from decimal import Decimal

from django.db.models import Case, DecimalField, Sum, Value, When
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import HttpResponseBadRequest, JsonResponse
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
            message = f'{created} transactions imported successfully.'
    else:
        form = UploadCSVForm()

    recent_transactions = Transaction.objects.order_by('-value_date', '-booking_date')[:10]
    return render(
        request,
        'transactions/upload.html',
        {
            'form': form,
            'message': message,
            'created': created,
            'recent_transactions': recent_transactions,
            'stats_url': reverse('transaction_stats'),
            'dashboard_url': reverse('dashboard'),
        },
    )


def dashboard(request):
    return render(request, 'transactions/dashboard.html')


def transaction_stats(request):
    monthly = (
        Transaction.objects
        .exclude(category__iexact='Savings')
        .annotate(year=ExtractYear('value_date'), month=ExtractMonth('value_date'))
        .values('year', 'month')
        .annotate(
            total=Sum('amount_eur'),
            spending=Sum(
                Case(
                    When(amount_eur__lt=0, then='amount_eur'),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            income=Sum(
                Case(
                    When(amount_eur__gt=0, then='amount_eur'),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by('year', 'month')
    )

    category = (
        Transaction.objects
        .exclude(category__iexact='Savings')
        .values('category')
        .annotate(total=Sum('amount_eur'))
        .order_by('-total')
    )

    return JsonResponse({
        'monthly_totals': [
            {
                'year': item['year'],
                'month': item['month'],
                'total': item['total'],
                'spending': item['spending'],
                'income': item['income'],
            }
            for item in monthly
        ],
        'category_totals': [
            {'category': item['category'] or 'Uncategorized', 'total': item['total']}
            for item in category
        ],
    })


def category_totals(request):
    period = request.GET.get('period', 'year')
    year = request.GET.get('year')
    month = request.GET.get('month')
    start_year = request.GET.get('start_year')
    start_month = request.GET.get('start_month')
    end_year = request.GET.get('end_year')
    end_month = request.GET.get('end_month')

    queryset = Transaction.objects.all()

    if start_year and start_month and end_year and end_month:
        try:
            start_year_val = int(start_year)
            start_month_val = int(start_month)
            end_year_val = int(end_year)
            end_month_val = int(end_month)
        except ValueError:
            return HttpResponseBadRequest('Invalid range parameters')
        from datetime import date
        start_date = date(start_year_val, start_month_val, 1)
        end_date = date(end_year_val, end_month_val, 1)
        # To include the entire end month, set to last day of month
        import calendar
        end_date = end_date.replace(day=calendar.monthrange(end_year_val, end_month_val)[1])
        queryset = queryset.filter(value_date__range=(start_date, end_date))
    else:
        if year:
            try:
                year_val = int(year)
            except ValueError:
                return HttpResponseBadRequest('Invalid year')
            queryset = queryset.filter(value_date__year=year_val)

        if period == 'month':
            if month is None:
                return HttpResponseBadRequest('Month is required for period=month')
            try:
                month_val = int(month)
            except ValueError:
                return HttpResponseBadRequest('Invalid month')
            queryset = queryset.filter(value_date__month=month_val)
        elif period not in ('year', 'all'):
            return HttpResponseBadRequest('Invalid period')

    savings_total_value = queryset.filter(category__iexact='Savings').aggregate(total=Sum('amount_eur'))['total'] or 0
    queryset = queryset.exclude(category__iexact='Savings')

    income_totals = (
        queryset
        .filter(amount_eur__gt=0)
        .values('category')
        .annotate(total=Sum('amount_eur'))
        .order_by('-total')
    )
    spending_totals = (
        queryset
        .filter(amount_eur__lt=0)
        .values('category')
        .annotate(total=Sum('amount_eur'))
        .order_by('total')
    )

    return JsonResponse({
        'period': period,
        'year': int(year) if year else None,
        'month': int(month) if month else None,
        'savings_total': abs(savings_total_value),
        'income_category_totals': [
            {
                'category': item['category'] or 'Uncategorized',
                'total': item['total'],
            }
            for item in income_totals
        ],
        'spending_category_totals': [
            {
                'category': item['category'] or 'Uncategorized',
                'total': abs(item['total']) if item['total'] is not None else 0,
            }
            for item in spending_totals
        ],
    })
