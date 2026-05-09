# yn-budget Django Backend

This repository contains a Django backend for uploading home budget transaction CSV files and storing them in SQLite.

## Setup

1. Install Python 3.11+.
2. Create a virtual environment and activate it.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create the database and apply migrations:

```bash
python manage.py migrate
```

5. Start the development server:

```bash
python manage.py runserver
```

6. Open the app at `http://127.0.0.1:8000/upload/`.

## Features

- Upload a transaction CSV file and persist rows to a SQLite database.
- Stores transaction metadata including category, partner, amount, currency, and exchange rate.
- Includes a JSON endpoint for aggregated stats by month and category.
- Automatically predicts missing `Category` values during CSV import using an ML model trained from existing labeled transactions.

## Notes

- CSV files can omit the `Category` column; rows are still imported.
- Prediction is only enabled when enough labeled training rows already exist in the database.
- The app is lightweight and ready to be extended with visualization endpoints and frontend pages.

## Model Evaluation

Run the dedicated evaluation command:

```bash
python manage.py evaluate_category_model
```

Useful options:

```bash
python manage.py evaluate_category_model --test-size 0.2 --random-state 42 --thresholds 0.30,0.45,0.60
python manage.py evaluate_category_model --output-json model_eval_report.json
```

This command does a train/test split from labeled transactions in the DB and prints:

- Accuracy, macro F1, weighted F1
- Per-class precision/recall/F1 report
- Confusion matrix
- Coverage vs quality by confidence threshold

For visual analysis, open:

- `model_evaluation.ipynb`

The notebook plots confusion matrix and threshold tradeoffs interactively.
