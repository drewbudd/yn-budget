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
- Includes a Vue + TypeScript dashboard scaffold for spending visualizations.
- Future ML-based category prediction can use the stored transaction rows.

## Frontend setup

The frontend lives in the `frontend/` folder and is built with Vue 3, TypeScript, Vite, and ECharts.

1. Install Node dependencies:

```bash
cd frontend
npm install
```

2. Build the frontend assets:

```bash
npm run build
```

3. Run Django normally:

```bash
cd ..
python manage.py runserver
```

4. Open the dashboard at `http://127.0.0.1:8000/dashboard/`.

If you want to work on the frontend interactively, run `npm run dev` inside `frontend/` and use the Vite dev server.

## Notes

- The `Category` field is stored as a nullable text field so later ML can fill it when missing.
- The app is lightweight and ready to be extended with visualization endpoints and frontend pages.
