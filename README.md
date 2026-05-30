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

## Optional CLI Import

If you want to import a CSV via terminal (instead of the upload page), use:

```bash
python manage.py import_transactions /path/to/transactions.csv
```

This command imports rows and predicts missing categories when a trained model is available.

## Model Evaluation Notebook

Use `model_evaluation.ipynb` to evaluate the transaction category model in `budget/category_classifier.py`.

What the notebook does:

- Loads labeled transactions from the SQLite database.
- Trains the same scikit-learn pipeline used by the app.
- Evaluates with a train/test split.
- Shows classification metrics, a confusion matrix, and confidence-threshold analysis.

How to run:

1. Make sure migrations are applied and the database has labeled transactions.
2. Activate your virtual environment.
3. Open `model_evaluation.ipynb` in VS Code (or Jupyter) and run all cells.

If needed, install notebook tooling:

```bash
pip install notebook
```
