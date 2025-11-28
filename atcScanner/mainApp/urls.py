from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add-record', views.insert_rec, name='insert_rec'),
]
