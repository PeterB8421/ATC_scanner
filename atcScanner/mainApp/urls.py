from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('settings/', views.settings, name='settings'),
    path('<str:year>/<str:month>/<str:day>/<int:pk>', views.detail, name='detail'),
    path('<str:year>/<str:month>/<str:day>', views.day, name='day'),
    path('<str:year>/<str:month>', views.month, name='month'),
    path('<str:year>', views.year, name='year'),
]
