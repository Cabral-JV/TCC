from django.urls import path
from .views import home, login_view, register_view, logout_view

app_name = 'wallets'
urlpatterns = [
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
]