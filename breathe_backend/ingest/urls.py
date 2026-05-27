from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check),
    path('ingest/sap/', views.ingest_sap),
    path('ingest/utility/', views.ingest_utility),
    path('ingest/navan/', views.ingest_navan),
    path('rows/normalized/', views.list_normalized),
    path('rows/normalized/<uuid:pk>/approve/', views.approve_row),
    path('rows/normalized/<uuid:pk>/flag/', views.flag_row),
    path('rows/normalized/<uuid:pk>/lock/', views.lock_row),
    path('rows/normalized/<uuid:pk>/', views.edit_row),
]
