from django.urls import path

from . import views

urlpatterns = [
    path('upload/', views.upload_csv, name='upload_csv'),
    path('stats/', views.transaction_stats, name='transaction_stats'),
    path('', views.upload_csv, name='home'),
]
