from django.urls import path
from . import views

app_name = 'wallets'
urlpatterns = [
    path('', views.home, name='home'),
]