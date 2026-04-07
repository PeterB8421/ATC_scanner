from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/get_recs', views.get_recs, name='get_recs'),
    path('api/month_counts', views.get_month_counts, name='get_month_counts'),
    path('api/transcript', views.receive_transcription, name='receive_transcription'),
    path('api/stats', views.get_stats, name='get_stats'),
    path('api/get_deleted_log', views.get_del_log, name='get_deleted_log'),
    path('api/get_delete_reasons', views.get_deletion_reasons, name='get_deletion_reasons'),
    path('settings/', views.settings, name='settings'),
    path('deleted_log/', views.deleted_log, name='deleted_log'),
    path('stats/', views.stats, name='stats'),
    path('<str:year>/<str:month>/<str:day>/<int:pk>', views.detail, name='detail'),
    path('<str:year>/<str:month>/<str:day>/<str:fname>', views.detail, name='detail'),
    path('<str:year>/<str:month>/<str:day>', views.day, name='day'),
    path('<str:year>/<str:month>', views.month, name='month'),
    path('<str:year>', views.year, name='year'),
]
