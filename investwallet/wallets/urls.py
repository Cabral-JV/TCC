from django.urls import path
from .views import (
    home,
    login_view,
    register_view,
    logout_view,
    search_stocks,
    users_list_view,
    upload_file,
)

app_name = "wallets"
urlpatterns = [
    path("", home, name="home"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    path("search/", search_stocks, name="search"),
    # path('stocks/', stock_list, name='stock_list'),
    path("users/", users_list_view, name="users_list"),
    path("upload/", upload_file, name="upload"),
]
