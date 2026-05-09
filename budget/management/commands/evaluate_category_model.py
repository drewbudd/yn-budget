from __future__ import annotations

import json
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from transactions.category_classifier import TransactionCategoryClassifier


class Command(BaseCommand):
    help = "Evaluate transaction category model with train/test split and threshold analysis."

    def add_arguments(self, parser):
        parser.add_argument("--test-size", type=float, default=0.2, help="Test set ratio. Default: 0.2")
        parser.add_argument("--random-state", type=int, default=42, help="Random seed for split. Default: 42")
        parser.add_argument(
            "--thresholds",
            type=str,
            default="0.30,0.45,0.60",
            help="Comma-separated confidence thresholds for coverage/quality analysis.",
        )
        parser.add_argument(
            "--output-json",
            type=str,
            default="",
            help="Optional path to save evaluation results as JSON.",
        )

    def handle(self, *args, **options):
        test_size = options["test_size"]
        random_state = options["random_state"]

        classifier = TransactionCategoryClassifier()
        texts, labels = classifier.build_dataset_from_db()

        if len(texts) < classifier.min_samples:
            raise CommandError(
                f"Not enough labeled rows to evaluate. Found {len(texts)}, need at least {classifier.min_samples}."
            )

        label_counts = Counter(labels)
        if len(label_counts) < classifier.min_classes:
            raise CommandError("Need at least 2 distinct categories for evaluation.")

        stratify = labels
        if min(label_counts.values()) < 2:
            stratify = None
            self.stdout.write(
                self.style.WARNING(
                    "At least one category has fewer than 2 rows; split is not stratified."
                )
            )

        x_train, x_test, y_train, y_test = train_test_split(
            texts,
            labels,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify,
        )

        if not x_train or not x_test:
            raise CommandError("Split produced an empty train or test set. Adjust --test-size.")

        model = classifier.create_pipeline()
        model.fit(x_train, y_train)

        y_pred = model.predict(x_test)
        y_proba = model.predict_proba(x_test)
        max_conf = y_proba.max(axis=1)

        accuracy = float(accuracy_score(y_test, y_pred))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
        weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))

        labels_order = sorted(set(labels))
        cm = confusion_matrix(y_test, y_pred, labels=labels_order)
        report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        self.stdout.write(self.style.SUCCESS("Model evaluation complete"))
        self.stdout.write(f"Total labeled rows: {len(texts)}")
        self.stdout.write(f"Train rows: {len(x_train)} | Test rows: {len(x_test)}")
        self.stdout.write(f"Distinct categories: {len(label_counts)}")
        self.stdout.write(f"Accuracy: {accuracy:.4f}")
        self.stdout.write(f"Macro F1: {macro_f1:.4f}")
        self.stdout.write(f"Weighted F1: {weighted_f1:.4f}")

        self.stdout.write("\nPer-class metrics:")
        self.stdout.write(classification_report(y_test, y_pred, zero_division=0, digits=4))

        self.stdout.write("Confusion Matrix (rows=true, cols=pred):")
        header = "\t" + "\t".join(labels_order)
        self.stdout.write(header)
        for idx, label in enumerate(labels_order):
            row_values = "\t".join(str(v) for v in cm[idx])
            self.stdout.write(f"{label}\t{row_values}")

        threshold_items = []
        raw_thresholds = [item.strip() for item in options["thresholds"].split(",") if item.strip()]
        parsed_thresholds = [float(value) for value in raw_thresholds]

        self.stdout.write("\nThreshold analysis:")
        for threshold in parsed_thresholds:
            accepted_idx = [i for i, conf in enumerate(max_conf) if conf >= threshold]
            coverage = len(accepted_idx) / len(y_test)

            if not accepted_idx:
                self.stdout.write(f"- threshold={threshold:.2f}: coverage=0.0000, no predictions accepted")
                threshold_items.append(
                    {
                        "threshold": threshold,
                        "coverage": coverage,
                        "accepted_count": 0,
                        "precision_macro": None,
                        "recall_macro": None,
                        "f1_macro": None,
                    }
                )
                continue

            accepted_true = [y_test[i] for i in accepted_idx]
            accepted_pred = [y_pred[i] for i in accepted_idx]
            precision, recall, f1, _ = precision_recall_fscore_support(
                accepted_true,
                accepted_pred,
                average="macro",
                zero_division=0,
            )

            self.stdout.write(
                f"- threshold={threshold:.2f}: coverage={coverage:.4f}, "
                f"accepted={len(accepted_idx)}, "
                f"precision_macro={precision:.4f}, recall_macro={recall:.4f}, f1_macro={f1:.4f}"
            )

            threshold_items.append(
                {
                    "threshold": threshold,
                    "coverage": coverage,
                    "accepted_count": len(accepted_idx),
                    "precision_macro": float(precision),
                    "recall_macro": float(recall),
                    "f1_macro": float(f1),
                }
            )

        output_json = options["output_json"].strip()
        if output_json:
            payload = {
                "summary": {
                    "total_rows": len(texts),
                    "train_rows": len(x_train),
                    "test_rows": len(x_test),
                    "distinct_categories": len(label_counts),
                    "accuracy": accuracy,
                    "macro_f1": macro_f1,
                    "weighted_f1": weighted_f1,
                },
                "labels_order": labels_order,
                "confusion_matrix": cm.tolist(),
                "classification_report": report_dict,
                "threshold_analysis": threshold_items,
            }
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f"Saved JSON report to {output_json}"))
