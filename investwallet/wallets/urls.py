from django.urls import path
from .views import (
    home,
    login_view,
    register_view,
    logout_view,
    search_stocks,
    users_list,
    upload_view,
    all_stocks,
    criar_carteira_recomendada,
    editar_carteira_usuario,
    deletar_carteira_usuario,
    criar_carteira_usuario,
    minhas_carteiras,
    pagina_acao,
    autocomplete_papeis,
    visualizar_planilha,
    atualizar_carteira_recomendada,
    deletar_carteira_recomendada,
)

app_name = "wallets"  # Define o nome da aplicação
urlpatterns = [
    path("", home, name="home"),  # Define a URL da home
    path("login/", login_view, name="login"),  # Define a URL de login
    path("register/", register_view, name="register"),  # Define a URL de registro
    path("logout/", logout_view, name="logout"),  # Define a URL de logout
    path("search/", search_stocks, name="search"),  # Define a URL de busca
    path("acoes/", all_stocks, name="all_stocks"),
    path(
        "users/", users_list, name="users_list"
    ),  # Define a URL de listagem de usuários
    path("upload/", upload_view, name="upload"),  # Define a URL de upload de arquivos
    path(
        "criar-carteira/", criar_carteira_recomendada, name="criar_carteira_recomendada"
    ),
    path(
        "carteira-recomendada/atualizar/",
        atualizar_carteira_recomendada,
        name="atualizar_carteira_recomendada",
    ),
    path(
        "recomendada/excluir/<int:carteira_id>/",
        deletar_carteira_recomendada,
        name="excluir_carteira_recomendada",
    ),
    path(
        "carteiras/<int:carteira_id>/editar/",
        editar_carteira_usuario,
        name="editar_carteira_user",
    ),
    path(
        "carteiras/<int:carteira_id>/deletar/",
        deletar_carteira_usuario,
        name="deletar_carteira_user",
    ),
    path("carteiras/criar/", criar_carteira_usuario, name="criar_carteira_user"),
    path("carteiras/", minhas_carteiras, name="minhas_carteiras"),
    path("acao/<str:codigo>/", pagina_acao, name="pagina_acao"),
    path("autocomplete/", autocomplete_papeis, name="autocomplete"),
    path(
        "papel/<str:codigo>/planilha/", visualizar_planilha, name="visualizar_planilha"
    ),
]
