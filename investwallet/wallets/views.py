from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages

def home(request):
    return render(request, 'wallets/home.html')

# View para Login
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")  # Se já estiver logado, redireciona para a home

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login realizado com sucesso!")  # Mensagem de sucesso
            return redirect("home")  
        else:
            messages.error(request, "Usuário ou senha inválidos.")  # Mensagem de erro

    else:
        form = AuthenticationForm()
    
    return render(request, "wallets/login.html", {"form": form})

# View para Registro
def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")  # Se já estiver logado, redireciona para a home

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cadastro realizado com sucesso! Bem-vindo(a) ao InvestWallet.")
            return redirect("home")
        else:
            messages.error(request, "Erro no cadastro. Verifique os dados informados.")  # Mensagem de erro

    else:
        form = UserCreationForm()

    return render(request, "wallets/register.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu da conta.")
    return redirect("home")
