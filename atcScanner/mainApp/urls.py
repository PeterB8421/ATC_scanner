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
    path('api/get_monthly_snr', views.get_monthly_snr, name='get_monthly_snr'),
    path('api/get_daily_snr', views.get_daily_snr, name='get_daily_snr'),
    path('api/export/list_files', views.get_export_archives, name='get_export_archives'),
    path('settings/', views.settings, name='settings'),
    path('settins/conf_upload', views.upload_airband_config, name='upload_airband_config'),
    path('deleted_log/', views.deleted_log, name='deleted_log'),
    path('stats/', views.stats, name='stats'),
    path('export/', views.export_page, name='export'),
    path('export/new', views.new_export, name='export_new'),
    path('export/delete', views.delete_export_archive, name='delete_export_archive'),
    path('<str:year>/<str:month>/<str:day>/<int:pk>', views.detail, name='detail'),
    path('<str:year>/<str:month>/<str:day>/<str:fname>', views.detail, name='detail'),
]
