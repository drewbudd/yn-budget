from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .models import Transaction


@dataclass
class CategoryPrediction:
    category: str
    confidence: float


class TransactionCategoryClassifier:
    """Train on labeled transactions and predict missing categories."""

    def __init__(self, min_samples: int = 20, min_classes: int = 2):
        self.min_samples = min_samples
        self.min_classes = min_classes
        self._model: Pipeline | None = None

    @staticmethod
    def _amount_bucket(amount: Decimal | None) -> str:
        if amount is None:
            return "amount_missing"
        if amount < 0:
            return "expense"
        if amount > 0:
            return "income"
        return "zero"

    @classmethod
    def _build_text(
        cls,
        *,
        partner_name: str = "",
        payment_reference: str = "",
        partner_iban: str = "",
        original_currency: str = "",
        amount_eur: Decimal | None = None,
    ) -> str:
        # Prefix field names so the model can learn field-specific token patterns.
        return " ".join(
            [
                f"partner_{partner_name}".strip(),
                f"ref_{payment_reference}".strip(),
                f"iban_{partner_iban}".strip(),
                f"currency_{original_currency}".strip(),
                f"amount_bucket_{cls._amount_bucket(amount_eur)}",
            ]
        )

    def _build_training_rows(self) -> tuple[list[str], list[str]]:
        rows: Iterable[Transaction] = (
            Transaction.objects.exclude(category__isnull=True)
            .exclude(category="")
            .only(
                "partner_name",
                "payment_reference",
                "partner_iban",
                "original_currency",
                "amount_eur",
                "category",
            )
        )

        texts: list[str] = []
        labels: list[str] = []
        for row in rows:
            category = (row.category or "").strip()
            if not category:
                continue
            texts.append(
                self._build_text(
                    partner_name=row.partner_name,
                    payment_reference=row.payment_reference,
                    partner_iban=row.partner_iban,
                    original_currency=row.original_currency,
                    amount_eur=row.amount_eur,
                )
            )
            labels.append(category)
        return texts, labels

    def build_dataset_from_db(self) -> tuple[list[str], list[str]]:
        """Return text features and labels from currently labeled DB rows."""
        return self._build_training_rows()

    @staticmethod
    def create_pipeline() -> Pipeline:
        return Pipeline(
            steps=[
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        min_df=1,
                        strip_accents="unicode",
                        lowercase=True,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(max_iter=1000),
                ),
            ]
        )

    def train_from_db(self) -> bool:
        texts, labels = self._build_training_rows()
        if len(texts) < self.min_samples:
            self._model = None
            return False

        distinct_classes = len(set(labels))
        if distinct_classes < self.min_classes:
            self._model = None
            return False

        self._model = self.create_pipeline()
        self._model.fit(texts, labels)
        return True

    def predict(
        self,
        *,
        partner_name: str = "",
        payment_reference: str = "",
        partner_iban: str = "",
        original_currency: str = "",
        amount_eur: Decimal | None = None,
        min_confidence: float = 0.45,
    ) -> CategoryPrediction | None:
        if self._model is None:
            return None

        text = self._build_text(
            partner_name=partner_name,
            payment_reference=payment_reference,
            partner_iban=partner_iban,
            original_currency=original_currency,
            amount_eur=amount_eur,
        )

        proba = self._model.predict_proba([text])[0]
        classes = self._model.classes_
        best_index = int(proba.argmax())
        confidence = float(proba[best_index])

        if confidence < min_confidence:
            return None

        return CategoryPrediction(category=str(classes[best_index]), confidence=confidence)
