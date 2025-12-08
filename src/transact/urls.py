from django.urls import path

from . import views

urlpatterns = [
    path("", views.BulkAccountTransactionView.as_view(), name="ingest-transactions"),
]
