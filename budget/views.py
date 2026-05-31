from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, Sum, Value, When
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .category_classifier import TransactionCategoryClassifier
from .forms import UploadCSVForm
from .models import Transaction, Budget


PENDING_IMPORT_SESSION_KEY = 'pending_transaction_import_rows'
AUTO_APPLY_MIN_CONFIDENCE = 0.25


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


def _build_transaction_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    booking_date = parse_date(row.get('Booking Date'))
    if not booking_date:
        return None

    value_date = parse_date(row.get('Value Date'))

    amount_eur = parse_decimal(row.get('Amount (EUR)')) or Decimal('0.00')
    original_amount = parse_decimal(row.get('Original Amount'))
    exchange_rate = parse_decimal(row.get('Exchange Rate'))
    transaction_type = row.get('Type', '').strip() or 'Presentment'
    original_currency = row.get('Original Currency', '').strip() or 'EUR'

    return {
        'booking_date': booking_date.isoformat(),
        'value_date': value_date.isoformat() if value_date else None,
        'partner_name': row.get('Partner Name', '').strip(),
        'category': row.get('Category', '').strip() or None,
        'amount_eur': str(amount_eur),
        'payment_reference': row.get('Payment Reference', '').strip(),
        'partner_iban': row.get('Partner Iban', '').strip(),
        'transaction_type': transaction_type,
        'account_name': row.get('Account Name', '').strip(),
        'original_amount': str(original_amount) if original_amount is not None else None,
        'original_currency': original_currency,
        'exchange_rate': str(exchange_rate) if exchange_rate is not None else None,
        'prediction_confidence': None,
        'was_predicted': False,
        'predicted_category': None,
        'is_low_confidence_suggestion': False,
        'duplicate_in_db': False,
    }


def _predict_missing_categories(payload_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, bool]:
    classifier = TransactionCategoryClassifier()
    has_model = classifier.load_or_train_from_db()
    predicted = 0

    if not has_model:
        return payload_rows, predicted, has_model

    for payload in payload_rows:
        if payload['category']:
            continue

        prediction = classifier.predict(
            partner_name=payload['partner_name'],
            payment_reference=payload['payment_reference'],
            transaction_type=payload['transaction_type'],
            original_currency=payload['original_currency'],
            amount_eur=Decimal(payload['amount_eur']),
            min_confidence=0.0,
        )
        if prediction:
            payload['prediction_confidence'] = round(prediction.confidence, 4)
            payload['predicted_category'] = prediction.category
            if prediction.confidence >= AUTO_APPLY_MIN_CONFIDENCE:
                payload['category'] = prediction.category
                payload['was_predicted'] = True
                payload['is_low_confidence_suggestion'] = False
                predicted += 1
            else:
                payload['was_predicted'] = False
                payload['is_low_confidence_suggestion'] = True

    return payload_rows, predicted, has_model


def _is_duplicate_payload(payload: dict[str, Any]) -> bool:
    return Transaction.objects.filter(
        booking_date=parse_date(payload['booking_date']),
        value_date=parse_date(payload['value_date']),
        partner_name=payload['partner_name'],
        amount_eur=Decimal(payload['amount_eur']),
    ).exists()


def _mark_duplicates(payload_rows: list[dict[str, Any]]) -> int:
    duplicate_count = 0
    for payload in payload_rows:
        is_duplicate = _is_duplicate_payload(payload)
        payload['duplicate_in_db'] = is_duplicate
        if is_duplicate:
            duplicate_count += 1
    return duplicate_count


def _apply_preview_category_updates(request_post, payload_rows: list[dict[str, Any]]) -> None:
    for payload in payload_rows:
        field_name = f"category_{payload['row_id']}"
        if field_name in request_post:
            payload['category'] = request_post.get(field_name, '').strip() or None


def _save_payload_rows(payload_rows: list[dict[str, Any]]) -> tuple[int, int]:
    created = 0
    skipped_duplicates = 0
    for payload in payload_rows:
        if payload.get('duplicate_in_db'):
            skipped_duplicates += 1
            continue

        # Safety recheck to avoid race conditions with parallel imports.
        if _is_duplicate_payload(payload):
            skipped_duplicates += 1
            continue

        transaction = Transaction(
            booking_date=parse_date(payload['booking_date']),
            value_date=parse_date(payload['value_date']),
            partner_name=payload['partner_name'],
            category=payload['category'],
            amount_eur=Decimal(payload['amount_eur']),
            payment_reference=payload['payment_reference'],
            partner_iban=payload['partner_iban'],
            transaction_type=payload['transaction_type'],
            account_name=payload['account_name'],
            original_amount=Decimal(payload['original_amount']) if payload['original_amount'] else None,
            original_currency=payload['original_currency'],
            exchange_rate=Decimal(payload['exchange_rate']) if payload['exchange_rate'] else None,
        )
        transaction.save()
        created += 1
    return created, skipped_duplicates


def _build_category_choices(payload_rows: list[dict[str, Any]]) -> list[str]:
    db_categories = (
        Transaction.objects.exclude(category__isnull=True)
        .exclude(category='')
        .order_by('category')
        .values_list('category', flat=True)
        .distinct()
    )
    options = set(db_categories)
    for payload in payload_rows:
        if payload.get('category'):
            options.add(payload['category'])
    return sorted(options)


def upload_csv(request):
    message = None
    created = 0
    predicted = 0
    preview_rows = []
    preview_total = 0
    duplicate_count = 0
    category_choices: list[str] = []

    if request.method == 'POST':
        action = request.POST.get('action', 'preview')

        if action == 'preview':
            form = UploadCSVForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data['file']
                decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                reader = csv.DictReader(decoded_file)

                payload_rows = []
                for index, row in enumerate(reader, start=1):
                    payload = _build_transaction_payload(row)
                    if payload:
                        payload['row_id'] = index
                        payload_rows.append(payload)

                payload_rows, predicted, _ = _predict_missing_categories(payload_rows)
                duplicate_count = _mark_duplicates(payload_rows)

                request.session[PENDING_IMPORT_SESSION_KEY] = payload_rows
                preview_rows = payload_rows
                preview_total = len(payload_rows)
                category_choices = _build_category_choices(preview_rows)

                if preview_total == 0:
                    message = 'No valid transaction rows found in the CSV.'
                    request.session.pop(PENDING_IMPORT_SESSION_KEY, None)
                else:
                    message = 'Review duplicates and predicted categories. You can edit categories, delete rows, then confirm import.'
            else:
                request.session.pop(PENDING_IMPORT_SESSION_KEY, None)
                preview_rows = []
        elif action == 'confirm_import' or action.startswith('delete_'):
            pending_rows = request.session.get(PENDING_IMPORT_SESSION_KEY, [])
            if not pending_rows:
                form = UploadCSVForm()
                message = 'No pending preview found. Please upload a CSV first.'
            else:
                _apply_preview_category_updates(request.POST, pending_rows)

                if action.startswith('delete_'):
                    row_id_text = action.replace('delete_', '', 1)
                    try:
                        row_id = int(row_id_text)
                    except ValueError:
                        row_id = None
                    if row_id is not None:
                        pending_rows = [row for row in pending_rows if row.get('row_id') != row_id]
                    message = 'Row deleted from preview.'

                duplicate_count = _mark_duplicates(pending_rows)
                request.session[PENDING_IMPORT_SESSION_KEY] = pending_rows

                if action == 'confirm_import':
                    created, skipped_duplicates = _save_payload_rows(pending_rows)
                    if created:
                        TransactionCategoryClassifier().refresh_from_db()
                    predicted = sum(1 for row in pending_rows if row.get('was_predicted'))
                    request.session.pop(PENDING_IMPORT_SESSION_KEY, None)
                    form = UploadCSVForm()
                    message = (
                        f'{created} transactions imported successfully. '
                        f'Predicted categories: {predicted}. '
                        f'Duplicates ignored: {skipped_duplicates}.'
                    )
                else:
                    form = UploadCSVForm()
                    preview_rows = pending_rows
                    preview_total = len(pending_rows)
                    predicted = sum(1 for row in pending_rows if row.get('was_predicted'))
                    category_choices = _build_category_choices(preview_rows)

                if action == 'confirm_import':
                    preview_rows = []
                    preview_total = 0
                    duplicate_count = 0
                    category_choices = []
                else:
                    preview_rows = pending_rows
                    preview_total = len(preview_rows)
                    category_choices = _build_category_choices(preview_rows)
        else:
            form = UploadCSVForm()
            message = 'Unknown action. Please upload the CSV again.'
    else:
        form = UploadCSVForm()

    if request.method != 'POST':
        request.session.pop(PENDING_IMPORT_SESSION_KEY, None)

    recent_transactions = Transaction.objects.order_by('-booking_date')[:10]
    return render(
        request,
        'budget/upload.html',
        {
            'form': form,
            'message': message,
            'created': created,
            'predicted': predicted,
            'preview_rows': preview_rows,
            'preview_total': preview_total,
            'duplicate_count': duplicate_count,
            'category_choices': category_choices,
            'recent_transactions': recent_transactions,
            'stats_url': reverse('transaction_stats'),
            'dashboard_url': reverse('dashboard'),
        },
    )


def dashboard(request):
    return render(request, 'budget/dashboard.html')


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


def category_trend(request):
    category = request.GET.get('category')
    if not category:
        return HttpResponseBadRequest('Category is required')

    period = request.GET.get('period', 'month')
    year = request.GET.get('year')
    month = request.GET.get('month')
    lookback_months = request.GET.get('lookback_months')

    if not year:
        return HttpResponseBadRequest('Year is required')
    try:
        year_val = int(year)
    except ValueError:
        return HttpResponseBadRequest('Invalid year')

    queryset = Transaction.objects.filter(category__iexact=category).exclude(category__iexact='Savings')

    if period == 'month':
        if month is None:
            return HttpResponseBadRequest('Month is required for period=month')
        try:
            month_val = int(month)
        except ValueError:
            return HttpResponseBadRequest('Invalid month')

        if lookback_months:
            try:
                lookback_val = int(lookback_months)
            except ValueError:
                return HttpResponseBadRequest('Invalid lookback_months')
            from datetime import date
            import calendar

            end_date = date(year_val, month_val, calendar.monthrange(year_val, month_val)[1])
            start_month = month_val - (lookback_val - 1)
            start_year = year_val
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            start_date = date(start_year, start_month, 1)
            end_day = calendar.monthrange(end_date.year, end_date.month)[1]
            end_date = end_date.replace(day=end_day)
            queryset = queryset.filter(value_date__range=(start_date, end_date))
        else:
            queryset = queryset.filter(value_date__year=year_val, value_date__month=month_val)
    elif period == 'year':
        queryset = queryset.filter(value_date__year=year_val)
    elif period not in ('all',):
        return HttpResponseBadRequest('Invalid period')

    monthly = (
        queryset
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

    return JsonResponse({
        'category': category,
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
    })


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def budget_list_create(request):
    import json
    from django.db import transaction as db_transaction

    if request.method == 'GET':
        year_str = request.GET.get('year')
        month_str = request.GET.get('month')
        if not year_str or not month_str:
            now = datetime.now()
            year = now.year
            month = now.month
        else:
            try:
                year = int(year_str)
                month = int(month_str)
            except ValueError:
                return HttpResponseBadRequest('Invalid year or month')

        expense_categories = Transaction.objects.filter(amount_eur__lt=0).exclude(category__iexact='Savings').values_list('category', flat=True).distinct()
        expense_categories = [c for c in expense_categories if c]

        budgeted_categories = Budget.objects.filter(year=year, month=month).values_list('category', flat=True).distinct()
        all_categories = sorted(list(set(list(expense_categories) + list(budgeted_categories))))

        actuals = (
            Transaction.objects.filter(
                value_date__year=year,
                value_date__month=month,
                amount_eur__lt=0
            )
            .exclude(category__iexact='Savings')
            .values('category')
            .annotate(total_spent=Sum('amount_eur'))
        )
        actual_map = {item['category']: abs(item['total_spent']) for item in actuals if item['category']}

        budgets = Budget.objects.filter(year=year, month=month)
        budget_map = {b.category: b.amount for b in budgets}

        category_budgets = []
        for cat in all_categories:
            category_budgets.append({
                'category': cat,
                'budget': float(budget_map.get(cat, 0)),
                'actual': float(actual_map.get(cat, 0)),
            })

        return JsonResponse({
            'year': year,
            'month': month,
            'budgets': category_budgets,
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            year = int(data.get('year'))
            month = int(data.get('month'))
            budgets_input = data.get('budgets', {})
        except (ValueError, TypeError, json.JSONDecodeError):
            return HttpResponseBadRequest('Invalid JSON data')

        with db_transaction.atomic():
            for category, amount_val in budgets_input.items():
                if amount_val is None or str(amount_val).strip() == '':
                    amount_dec = Decimal('0.00')
                else:
                    try:
                        amount_dec = Decimal(str(amount_val))
                    except (ValueError, TypeError):
                        continue

                if amount_dec > 0:
                    Budget.objects.update_or_create(
                        year=year,
                        month=month,
                        category=category,
                        defaults={'amount': amount_dec}
                    )
                else:
                    Budget.objects.filter(year=year, month=month, category=category).delete()

        return JsonResponse({'status': 'success'})
