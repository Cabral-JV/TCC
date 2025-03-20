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
def login(request):
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
def register(request):
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
def logout(request):
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


# View para upload de arquivos
@user_passes_test(is_admin)
def upload(request):
    if request.method == "POST":
        form = UploadArquivoForm(request.POST, request.FILES)
        arquivos = request.FILES.getlist("file")  # Obtém todos os arquivos enviados

        if arquivos:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)  # Garante que a pasta existe

            for arquivo in arquivos:
                if not arquivo.name.endswith(".xlsx"):
                    messages.error(
                        request, f"O arquivo {arquivo.name} não é um .xlsx válido."
                    )
                    continue  # Ignora arquivos inválidos

                # Salvar arquivo com nome correto na pasta "media/uploads/"
                caminho_arquivo = os.path.join(upload_dir, arquivo.name)
                with open(caminho_arquivo, "wb+") as destination:
                    for chunk in arquivo.chunks():
                        destination.write(chunk)

                messages.success(
                    request, f"Upload do arquivo {arquivo.name} realizado com sucesso!"
                )

            return redirect("wallets:upload")
        else:
            messages.error(request, "Nenhum arquivo selecionado.")

    else:
        form = UploadArquivoForm()

    return render(request, "wallets/upload.html", {"form": form})
