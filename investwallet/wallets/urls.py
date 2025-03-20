from django.urls import path
from .views import (
    home,
    login,
    register,
    logout,
    search_stocks,
    users_list,
    upload,
)

app_name = "wallets"  # Define o nome da aplicação
urlpatterns = [
    path("", home, name="home"),  # Define a URL da home
    path("login/", login, name="login"),  # Define a URL de login
    path("register/", register, name="register"),  # Define a URL de registro
    path("logout/", logout, name="logout"),  # Define a URL de logout
    path("search/", search_stocks, name="search"),  # Define a URL de busca
    # path('stocks/', stock_list, name='stock_list'), # Define a URL de listagem de ações
    path(
        "users/", users_list, name="users_list"
    ),  # Define a URL de listagem de usuários
    path("upload/", upload, name="upload"),  # Define a URL de upload de arquivos
]
