from django.urls import path

from . import views

urlpatterns = [
    path('upload/', views.upload_csv, name='upload_csv'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stats/', views.transaction_stats, name='transaction_stats'),
    path('stats/categories/', views.category_totals, name='category_totals'),
    path('stats/category-trend/', views.category_trend, name='category_trend'),
    path('api/budgets/', views.budget_list_create, name='budget_list_create'),
    path('', views.upload_csv, name='home'),
]

