from django.urls import path

from . import views

urlpatterns = [
    path("integrations/transactions/", views.BulkAccountTransactionView.as_view(), name="bulk-account-transactions"),
    path("reports/account/<str:account_id>/summary/", views.SummaryAccountView.as_view(), name="account-summary"),
]
