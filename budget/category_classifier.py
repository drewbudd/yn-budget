from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd
from django.conf import settings
from django.db.models import Count, Max
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .models import Transaction


@dataclass
class CategoryPrediction:
    category: str
    confidence: float


class TransactionCategoryClassifier:
    """
    Train on labeled transactions and predict missing categories using structured feature engineering.
    
    Features:
    - partner_name: TF-IDF text features with explicit higher transformer weight
    - amount_eur: scaled numeric feature
    - transaction_type: one-hot encoded categorical
    - original_currency: one-hot encoded categorical
    - payment_reference: TF-IDF text features
    """

    MODEL_CACHE_DIRNAME = ".cache"
    MODEL_CACHE_FILENAME = "transaction_category_model.joblib"
    PARTNER_NAME_WEIGHT = 3.0

    def __init__(self, min_samples: int = 20, min_classes: int = 2):
        self.min_samples = min_samples
        self.min_classes = min_classes
        self._model: Pipeline | None = None
        self._category_labels: list[str] | None = None

    @classmethod
    def model_cache_path(cls) -> Path:
        return Path(settings.BASE_DIR) / cls.MODEL_CACHE_DIRNAME / cls.MODEL_CACHE_FILENAME

    @classmethod
    def _labeled_queryset(cls):
        return Transaction.objects.exclude(category__isnull=True).exclude(category="")

    @classmethod
    def _build_code_signature(cls) -> str:
        signature_parts = {
            "class": cls.__name__,
            "partner_name_weight": cls.PARTNER_NAME_WEIGHT,
            "create_pipeline_source": inspect.getsource(cls.create_pipeline),
            "build_training_rows_source": inspect.getsource(cls._build_training_rows),
        }
        serialized = json.dumps(signature_parts, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @classmethod
    def _build_dataset_signature(cls) -> dict[str, int]:
        aggregate = cls._labeled_queryset().aggregate(row_count=Count("id"), max_id=Max("id"))
        return {
            "code_signature": cls._build_code_signature(),
            "row_count": int(aggregate["row_count"] or 0),
            "max_id": int(aggregate["max_id"] or 0),
        }

    @staticmethod
    def _signatures_match(left: dict[str, int | str], right: dict[str, int | str]) -> bool:
        return (
            left.get("code_signature") == right.get("code_signature")
            and left.get("row_count") == right.get("row_count")
            and left.get("max_id") == right.get("max_id")
        )

    def _set_model(self, model: Pipeline) -> None:
        self._model = model
        self._category_labels = model.named_steps["clf"].classes_.tolist()

    def _clear_model(self) -> None:
        self._model = None
        self._category_labels = None

    def _delete_cached_model(self) -> None:
        cache_path = self.model_cache_path()
        if cache_path.exists():
            cache_path.unlink()

    def load_from_disk(self) -> bool:
        cache_path = self.model_cache_path()
        if not cache_path.exists():
            self._clear_model()
            return False

        payload = joblib.load(cache_path)
        cached_signature = payload.get("signature", {})
        current_signature = self._build_dataset_signature()

        if not self._signatures_match(cached_signature, current_signature):
            self._clear_model()
            return False

        cached_model = payload.get("model")
        if cached_model is None:
            self._clear_model()
            return False

        self._set_model(cached_model)
        return True

    def _save_to_disk(self, signature: dict[str, int]) -> None:
        cache_path = self.model_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = cache_path.with_suffix(".tmp")
        joblib.dump({"signature": signature, "model": self._model}, temp_path)
        temp_path.replace(cache_path)

    def _build_training_rows(self) -> tuple[list[dict], list[str]]:
        """Build feature dicts and labels from labeled DB rows."""
        rows: Iterable[Transaction] = (
            self._labeled_queryset().only(
                "partner_name",
                "payment_reference",
                "transaction_type",
                "original_currency",
                "amount_eur",
                "category",
            )
        )

        features: list[dict] = []
        labels: list[str] = []
        for row in rows:
            category = (row.category or "").strip()
            if not category:
                continue

            features.append(
                {
                    "partner_name": (row.partner_name or "").strip() or "unknown",
                    "payment_reference": (row.payment_reference or "").strip() or "none",
                    "amount_eur": float(row.amount_eur),
                    "transaction_type": (row.transaction_type or "").strip() or "unknown",
                    "original_currency": (row.original_currency or "EUR").strip() or "EUR",
                }
            )
            labels.append(category)

        return features, labels

    def build_dataset_from_db(self) -> tuple[list[dict], list[str]]:
        """Return feature dicts and labels from currently labeled DB rows."""
        return self._build_training_rows()

    @staticmethod
    def create_pipeline() -> Pipeline:
        """Create preprocessing + classification pipeline for structured features."""
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "partner_tfidf",
                    TfidfVectorizer(max_features=100, ngram_range=(1, 4), lowercase=True),
                    "partner_name",
                ),
                (
                    "reference_tfidf",
                    TfidfVectorizer(max_features=50, ngram_range=(1, 3), lowercase=True),
                    "payment_reference",
                ),
                (
                    "amount_scale",
                    StandardScaler(),
                    ["amount_eur"],
                ),
                (
                    "type_onehot",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    ["transaction_type"],
                ),
                (
                    "currency_onehot",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    ["original_currency"],
                ),
            ],
            remainder="drop",
            transformer_weights={"partner_tfidf": TransactionCategoryClassifier.PARTNER_NAME_WEIGHT},
        )

        return Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=100,
                        max_depth=15,
                        min_samples_split=5,
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        )

    def train_from_db(self, *, persist: bool = False) -> bool:
        """Train model on labeled DB rows. Returns True if model was trained successfully."""
        features, labels = self._build_training_rows()
        signature = self._build_dataset_signature()

        if len(features) < self.min_samples:
            self._clear_model()
            if persist:
                self._delete_cached_model()
            return False

        distinct_classes = len(set(labels))
        if distinct_classes < self.min_classes:
            self._clear_model()
            if persist:
                self._delete_cached_model()
            return False

        # Convert dicts to DataFrame for sklearn pipeline
        features_df = pd.DataFrame(features)

        model = self.create_pipeline()
        model.fit(features_df, labels)
        self._set_model(model)
        if persist:
            self._save_to_disk(signature)
        return True

    def load_or_train_from_db(self) -> bool:
        if self.load_from_disk():
            return True
        return self.train_from_db(persist=True)

    def refresh_from_db(self) -> bool:
        return self.train_from_db(persist=True)

    def predict(
        self,
        *,
        partner_name: str = "",
        payment_reference: str = "",
        transaction_type: str = "",
        original_currency: str = "",
        amount_eur: Decimal | None = None,
        min_confidence: float = 0.45,
    ) -> CategoryPrediction | None:
        """Predict category for a transaction. Returns None if confidence is below threshold."""
        if self._model is None:
            return None

        amount = float(amount_eur) if amount_eur is not None else 0.0

        feature_dict = {
            "partner_name": (partner_name or "").strip() or "unknown",
            "payment_reference": (payment_reference or "").strip() or "none",
            "amount_eur": amount,
            "transaction_type": (transaction_type or "").strip() or "unknown",
            "original_currency": (original_currency or "EUR").strip() or "EUR",
        }

        # Convert dict to DataFrame for sklearn pipeline
        feature_df = pd.DataFrame([feature_dict])

        proba = self._model.predict_proba(feature_df)[0]
        classes = self._model.named_steps["clf"].classes_
        best_index = int(proba.argmax())
        confidence = float(proba[best_index])

        if confidence < min_confidence:
            return None

        return CategoryPrediction(category=str(classes[best_index]), confidence=confidence)