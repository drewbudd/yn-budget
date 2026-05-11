from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .category_classifier import TransactionCategoryClassifier
from .forms import UploadCSVForm
from .models import Transaction


PENDING_IMPORT_SESSION_KEY = 'pending_transaction_import_rows'
AUTO_APPLY_MIN_CONFIDENCE = 0.45


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
    model_enabled = False
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

                payload_rows, predicted, model_enabled = _predict_missing_categories(payload_rows)
                duplicate_count = _mark_duplicates(payload_rows)

                request.session[PENDING_IMPORT_SESSION_KEY] = payload_rows
                preview_rows = payload_rows
                preview_total = len(payload_rows)
                category_choices = _build_category_choices(preview_rows)

                if preview_total == 0:
                    message = 'No valid transaction rows found in the CSV.'
                else:
                    message = 'Review duplicates and predicted categories. You can edit categories, delete rows, then confirm import.'
            else:
                preview_rows = []
        elif action == 'confirm_import' or action == 'update_preview' or action.startswith('delete_'):
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
                    if action == 'update_preview':
                        message = 'Preview updated. Category changes saved.'
                    preview_rows = pending_rows
                    preview_total = len(pending_rows)
                    predicted = sum(1 for row in pending_rows if row.get('was_predicted'))
                    model_enabled = any(row.get('was_predicted') for row in pending_rows)
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
            'model_enabled': model_enabled,
            'duplicate_count': duplicate_count,
            'category_choices': category_choices,
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
