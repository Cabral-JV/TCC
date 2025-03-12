from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from .models import Empresa, ContaFinanceira, Periodo, DadoFinanceiro
from django.contrib.auth.models import User

def home(request):
    return render(request, 'wallets/home.html')

# View para Login
def login_view(request):
    if request.user.is_authenticated:
        return redirect("wallets:home")  # Se já estiver logado, redireciona para a home

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login realizado com sucesso!")  # Mensagem de sucesso
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
            messages.success(request, "Cadastro realizado com sucesso! Bem-vindo(a) ao InvestWallet.")
            return redirect("wallets:home")
        else:
            messages.error(request, "Erro no cadastro. Verifique os dados informados.")  # Mensagem de erro

    else:
        form = UserCreationForm()

    return render(request, "wallets/register.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu da conta.")
    return redirect("wallets:home")

def search_stocks(request):
    query = request.GET.get('query', '')
    results = Empresa.objects.filter(symbol__icontains=query) if query else []
    #return render(request, 'wallets/search_results.html', {'query': query, 'results': results})

def users_list_view(request):
    if not request.user.is_superuser:  # Verifica se o usuário é um administrador
        return redirect("wallets:home")  # Redireciona se não for um administrador

    users = User.objects.all()  # Obtém todos os usuários
    return render(request, "wallets/users_list.html", {"users": users})