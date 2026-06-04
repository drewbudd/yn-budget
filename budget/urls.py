from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stats/', views.transaction_stats, name='transaction_stats'),
    path('stats/categories/', views.category_totals, name='category_totals'),
    path('stats/category-trend/', views.category_trend, name='category_trend'),
    path('api/budgets/', views.budget_list_create, name='budget_list_create'),
    path('api/transactions/preview/', views.api_preview_import, name='api_preview_import'),
    path('api/transactions/confirm/', views.api_confirm_import, name='api_confirm_import'),
    path('api/transactions/recent/', views.api_recent_transactions, name='api_recent_transactions'),
    path('api/transactions/', views.api_transactions_list, name='api_transactions_list'),
    path('api/transactions/<int:id>/update/', views.api_transaction_update, name='api_transaction_update'),
    path('api/transactions/<int:id>/delete/', views.api_transaction_delete, name='api_transaction_delete'),
    path('upload/', views.dashboard, name='upload_csv'), # Keep legacy path pointing to dashboard SPA
    path('', views.dashboard, name='home'),
]

