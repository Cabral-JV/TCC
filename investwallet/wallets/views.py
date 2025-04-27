from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from .models import Empresa, ContaFinanceira, Periodo, DadoFinanceiro, Papel
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from .forms import UploadArquivoForm
from django.conf import settings
import pandas as pd
import os


# Função para verificar se o usuário é um administrador
def is_admin(user):
    return user.is_superuser


# View para a home
def home(request):
    return render(request, "wallets/home.html")


# View para Login
def login_view(request):
    if request.user.is_authenticated:
        return redirect("wallets:home")  # Se já estiver logado, redireciona para a home

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request, "Login realizado com sucesso!"
            )  # Mensagem de sucesso
            return redirect("wallets:home")
        else:
            messages.error(request, "Usuário ou senha inválidos.")  # Mensagem de erro

    else:
        form = AuthenticationForm()

    return render(request, "wallets/login.html", {"form": form})


# View para Registro
def register_view(request):
    if request.user.is_authenticated:
        return redirect("wallets:home")  # Se já estiver logado, redireciona para a home

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, "Cadastro realizado com sucesso! Bem-vindo(a) ao InvestWallet."
            )
            return redirect("wallets:home")
        else:
            messages.error(
                request, "Erro no cadastro. Verifique os dados informados."
            )  # Mensagem de erro

    else:
        form = UserCreationForm()

    return render(request, "wallets/register.html", {"form": form})


# View para Logout
def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu da conta.")
    return redirect("wallets:home")


# View para buscar ações
def search_stocks(request):
    query = request.GET.get("query", "")
    results = Empresa.objects.filter(symbol__icontains=query) if query else []
    # return render(request, 'wallets/search_results.html', {'query': query, 'results': results})


# View para listar usuários
@user_passes_test(is_admin)
def users_list(request):
    if not request.user.is_superuser:  # Verifica se o usuário é um administrador
        return redirect("wallets:home")  # Redireciona se não for um administrador

    users = User.objects.all()  # Obtém todos os usuários
    return render(request, "wallets/users_list.html", {"users": users})


@user_passes_test(is_admin)
def upload_view(request):
    if request.method == "POST":
        tipo_upload = request.POST.get("tipo_upload")

        if tipo_upload == "balanco":
            arquivos = request.FILES.getlist("file")
            if arquivos:
                upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads_bal")
                os.makedirs(upload_dir, exist_ok=True)
                erros, sucessos = [], []

                for arquivo in arquivos:
                    if not arquivo.name.endswith(".xlsx"):
                        erros.append(arquivo.name)
                        continue
                    caminho_arquivo = os.path.join(upload_dir, arquivo.name)
                    with open(caminho_arquivo, "wb+") as destination:
                        for chunk in arquivo.chunks():
                            destination.write(chunk)
                    sucessos.append(arquivo.name)

                if sucessos:
                    messages.success(
                        request, f"{len(sucessos)} arquivo(s) enviado(s) com sucesso."
                    )
                if erros:
                    messages.error(request, f"Erro em: {', '.join(erros)}")
            else:
                messages.error(request, "Nenhum arquivo selecionado.")

        elif tipo_upload == "banco":
            arquivo = request.FILES.get("database_file")
            if arquivo:
                if not arquivo.name.endswith(".xlsx"):
                    messages.error(request, f"{arquivo.name} não é um .xlsx válido.")
                else:
                    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads_db")
                    os.makedirs(upload_dir, exist_ok=True)
                    caminho_arquivo = os.path.join(upload_dir, arquivo.name)
                    with open(caminho_arquivo, "wb+") as destination:
                        for chunk in arquivo.chunks():
                            destination.write(chunk)
                    messages.success(request, f"{arquivo.name} enviado com sucesso!")
            else:
                messages.error(request, "Nenhum arquivo selecionado.")

        else:
            messages.error(request, "Tipo de upload não reconhecido.")

        return redirect("wallets:upload")

    return render(request, "wallets/upload.html")
