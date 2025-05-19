from collections import defaultdict
import os
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.db.models import Max
from django.db import transaction
from django.conf import settings
from .forms import CarteiraUsuarioForm, CarteiraForm
from .models import (
    Empresa,
    ContaFinanceira,
    DadoFinanceiro,
    Cotacao,
    PapelCarteiraUsuario,
    CarteiraUsuario,
    CarteiraRecomendada,
    PapelCarteiraUsuario,
    Movimentacao,
    Papel,
    PapelCarteiraRecomendada,
    User,
)
from .utils import obter_preco_atual, normalizar_nome_conta
from .services import (
    aplicar_carteira_recomendada,
    criar_ou_atualizar_carteira_usuario,
    processar_movimentacao,
    atualizar_movimentacoes_por_lista_antiga_nova,
)
import pandas as pd


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


@user_passes_test(is_admin)
def criar_carteira_recomendada(request):
    carteira = CarteiraRecomendada.objects.first()
    totais_por_carteira = {}
    movimentacoes_por_carteira = {}

    # ⇩⇩ NOVO BLOCO PARA CRIAR UMA NOVA CARTEIRA ⇩⇩
    if request.method == "POST":
        form = CarteiraForm(request.POST)
        if form.is_valid():
            codigos = form.cleaned_data["papeis_lista"]

            if CarteiraRecomendada.objects.exists():
                # Só permite uma recomendada
                return redirect("wallets:criar_carteira_recomendada")

            carteira = CarteiraRecomendada()
            carteira.save()

            for codigo in codigos:
                try:
                    papel = Papel.objects.get(codigo=codigo)
                    preco = obter_preco_atual(papel)
                    if preco is None:
                        continue

                    PapelCarteiraRecomendada.objects.create(
                        carteira=carteira, papel=papel, quantidade=1
                    )
                    Movimentacao.objects.create(
                        carteira_recomendada=carteira,
                        papel=papel,
                        tipo="COMPRA",
                        quantidade=1,
                        preco_unitario=preco,
                    )
                except Papel.DoesNotExist:
                    continue

            return redirect("wallets:criar_carteira_recomendada")
    else:
        form = CarteiraForm()
    # ⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧⇧

    # Se houver carteira existente, preenche os dados para exibição
    if carteira:
        total_investido = total_atual = 0
        for papel in carteira.papeis.all():
            preco = papel.preco_atual() or 0
            total_investido += preco
            total_atual += preco

        variacao = (
            ((total_atual - total_investido) / total_investido) * 100
            if total_investido
            else 0
        )

        totais_por_carteira[carteira.id] = {
            "total_investido": total_investido,
            "total_atual": total_atual,
            "variacao": variacao,
            "variacao_percentual": variacao,
        }

        movimentacoes_por_carteira[carteira.id] = list(
            Movimentacao.objects.filter(carteira_recomendada=carteira).select_related(
                "papel"
            )
        )

    return render(
        request,
        "wallets/criar_carteira_recomendada.html",
        {
            "form": form,
            "carteira_recomendada": carteira,
            "totais_por_carteira": totais_por_carteira,
            "movimentacoes_por_carteira": movimentacoes_por_carteira,
            "precos_atuais": (
                {p.papel.codigo: p.preco_atual() for p in carteira.papeis.all()}
                if carteira
                else {}
            ),
        },
    )


@user_passes_test(is_admin)
def atualizar_carteira_recomendada(request):
    carteira = get_object_or_404(CarteiraRecomendada)

    if request.method == "POST":
        form = CarteiraForm(request.POST)
        if form.is_valid():
            novos_codigos = form.cleaned_data["papeis_lista"]

            papeis_novos = Papel.objects.filter(codigo__in=novos_codigos)
            lista_nova = [{"papel__codigo": p.codigo} for p in papeis_novos]

            antigos = PapelCarteiraRecomendada.objects.filter(
                carteira=carteira
            ).select_related("papel")
            lista_antiga = [{"papel__codigo": p.papel.codigo} for p in antigos]

            # Atualiza papeis e registra movimentações
            atualizar_movimentacoes_por_lista_antiga_nova(
                carteira, lista_antiga, lista_nova
            )

            return redirect("wallets:criar_carteira_recomendada")  # ou outro
    else:
        papeis_atuais = PapelCarteiraRecomendada.objects.filter(
            carteira=carteira
        ).select_related("papel")
        codigos_atuais = ", ".join([p.papel.codigo for p in papeis_atuais])
        form = CarteiraForm(
            initial={"nome": carteira.nome, "papeis_lista": codigos_atuais}
        )

    return render(
        request, "wallets/atualizar_carteira_recomendada.html", {"form": form}
    )


@user_passes_test(is_admin)
def deletar_carteira_recomendada(request, carteira_id):
    carteira = get_object_or_404(CarteiraRecomendada, id=carteira_id)
    if request.method == "POST":
        carteira.delete()
        return redirect("wallets:criar_carteira_recomendada")
    return render(
        request,
        "wallets/confirmar_delete.html",
        {"carteira": carteira, "tipo": "Carteira Recomendada"},
    )


@login_required
def minhas_carteiras(request):
    usuario = request.user
    carteiras_usuario = CarteiraUsuario.objects.filter(usuario=usuario)
    carteira_recomendada = CarteiraRecomendada.objects.first()
    papeis_disponiveis = Papel.objects.all()

    precos_atuais = {}
    totais_por_carteira = {}
    movimentacoes_por_carteira = defaultdict(list)

    todas_carteiras = list(carteiras_usuario)
    if carteira_recomendada:
        carteira_recomendada.recomendada = True  # ← adiciona dinamicamente
        todas_carteiras.insert(0, carteira_recomendada)

    for carteira in todas_carteiras:
        if isinstance(carteira, CarteiraUsuario):
            movimentacoes = Movimentacao.objects.filter(carteira_usuario=carteira)
        else:
            movimentacoes = Movimentacao.objects.filter(carteira_recomendada=carteira)

        movimentacoes_por_carteira[carteira.id] = movimentacoes
        total_investido = total_atual = 0

        if isinstance(carteira, CarteiraUsuario):
            for mov in movimentacoes:
                preco_atual = obter_preco_atual(mov.papel) or 0
                precos_atuais[mov.papel.codigo] = preco_atual
                total_investido += mov.quantidade * mov.preco_unitario
                total_atual += mov.quantidade * preco_atual
        else:
            for item in carteira.papeis.all():
                preco = obter_preco_atual(item.papel) or 0
                precos_atuais[item.papel.codigo] = preco
                total_investido += (
                    item.quantidade * preco
                )  # assume preço atual = investido para visual
                total_atual += item.quantidade * preco

        variacao = (
            ((total_atual - total_investido) / total_investido * 100)
            if total_investido
            else 0
        )

        totais_por_carteira[carteira.id] = {
            "total_investido": total_investido,
            "total_atual": total_atual,
            "variacao": variacao,
            "variacao_percentual": variacao,
        }

    context = {
        "carteiras": todas_carteiras,
        "papeis_disponiveis": papeis_disponiveis,
        "movimentacoes_por_carteira": dict(movimentacoes_por_carteira),
        "totais_por_carteira": totais_por_carteira,
        "precos_atuais": precos_atuais,
    }
    return render(request, "wallets/minhas_carteiras.html", context)


@login_required
def criar_carteira_usuario(request):
    # Lista de todos os códigos disponíveis (para o <select>)
    papeis = list(Papel.objects.values("codigo"))

    # Lista dos papéis da recomendada (para carregar no JS)
    recomendada = list(
        PapelCarteiraRecomendada.objects.select_related("papel").values(
            "papel__codigo", "quantidade"
        )
    )
    recomendada_js = [
        {"codigo": r["papel__codigo"], "quantidade": r["quantidade"]}
        for r in recomendada
    ]

    if request.method == "POST":
        form = CarteiraUsuarioForm(request.POST)
        if form.is_valid():
            usar_recomendada = "usar_recomendada" in request.POST

            # Em ambos os casos, usamos os dados que o usuário enviou via POST
            tickers = [key for key in request.POST if key.startswith("ticker_")]
            papeis_data = []
            for t in tickers:
                idx = t.split("_")[1]
                codigo = request.POST.get(f"ticker_{idx}")
                try:
                    quantidade = int(request.POST.get(f"quantidade_{idx}"))
                except (TypeError, ValueError):
                    continue
                if quantidade > 0:
                    papeis_data.append((codigo, quantidade))

            carteira = criar_ou_atualizar_carteira_usuario(
                form, request.user, papeis_data
            )

            return redirect("wallets:minhas_carteiras")
    else:
        form = CarteiraUsuarioForm()

    return render(
        request,
        "wallets/criar_carteira_user.html",
        {"form": form, "papeis": papeis, "recomendada": recomendada_js},
    )


@login_required
def editar_carteira_usuario(request, carteira_id):
    carteira = get_object_or_404(CarteiraUsuario, id=carteira_id, usuario=request.user)

    if request.method == "POST":
        for key in request.POST:
            if key.startswith("quantidades["):
                papel_id = key.replace("quantidades[", "").replace("]", "")
                nova_qtd = int(request.POST[key])
                codigo = request.POST.get(f"codigos[{papel_id}]")
                papel = get_object_or_404(Papel, codigo=codigo)
                processar_movimentacao(carteira, papel, nova_qtd)

        novo_codigo = request.POST.get("nova_acao")
        nova_qtd = request.POST.get("nova_quantidade")
        if novo_codigo and nova_qtd:
            novo_codigo = novo_codigo.upper()
            nova_qtd = int(nova_qtd)
            papel = get_object_or_404(Papel, codigo=novo_codigo)
            atual = PapelCarteiraUsuario.objects.filter(
                carteira=carteira, papel=papel
            ).first()
            qtd_final = nova_qtd + (atual.quantidade if atual else 0)
            processar_movimentacao(carteira, papel, qtd_final)

        return redirect("wallets:minhas_carteiras")

    return redirect("wallets:minhas_carteiras")


@login_required
def deletar_carteira_usuario(request, carteira_id):
    carteira = get_object_or_404(CarteiraUsuario, id=carteira_id, usuario=request.user)
    if request.method == "POST":
        carteira.delete()
        return redirect("wallets:minhas_carteiras")
    return render(request, "wallets/confirmar_delete.html", {"carteira": carteira})


def all_stocks(request):
    contas_desejadas = [
        "Ativo Total",
        "Caixa e Equivalentes de Caixa",
        "Patrimônio Líquido",
        "Receita Líquida de Vendas e/ou Serviços",
    ]

    alias = {
        "Ativo Total": "Ativo_Total",
        "Caixa e Equivalentes de Caixa": "Caixa_e_Equivalentes",
        "Patrimônio Líquido": "Patrimonio_Liquido",
        "Receita Líquida de Vendas e/ou Serviços": "Receita_Liquida",
    }

    # Contas necessárias para cálculo
    contas_extra = {
        "Lucro/Prejuízo do Período": "lucro_liquido",
    }

    contas_todas = {**alias, **contas_extra}
    contas_obj = {
        apelido: ContaFinanceira.objects.filter(nome=nome).first()
        for nome, apelido in contas_todas.items()
    }

    ultima_data_cotacao = Cotacao.objects.aggregate(ultima=Max("data"))["ultima"]

    dados = []

    for papel in Papel.objects.all():
        dados_papel = {
            "papel": papel.codigo,
        }

        # Cotação e volume (número de ações)
        cotacao = Cotacao.objects.filter(papel=papel, data=ultima_data_cotacao).first()
        preco = float(cotacao.preco_fechamento) if cotacao else None
        volume = float(cotacao.numero_total_acoes) if cotacao else None

        dados_papel["cotacao"] = preco if preco else "—"

        # Buscar dados diretos (sem cálculo)
        for nome, chave in alias.items():
            conta = ContaFinanceira.objects.filter(nome=nome).first()
            if conta:
                dado = (
                    DadoFinanceiro.objects.filter(papel=papel, conta=conta)
                    .order_by("-periodo__data")
                    .first()
                )
                dados_papel[chave] = float(dado.valor) if dado else "—"
            else:
                dados_papel[chave] = "—"

        # Buscar valores para cálculo
        lucro = patrimonio = None

        lucro_conta = contas_obj.get("lucro_liquido")
        patrimonio_conta = contas_obj.get("Patrimonio_Liquido")

        if lucro_conta:
            dado_lucro = (
                DadoFinanceiro.objects.filter(papel=papel, conta=lucro_conta)
                .order_by("-periodo__data")
                .first()
            )
            lucro = float(dado_lucro.valor) if dado_lucro else None

        if patrimonio_conta:
            dado_patrimonio = (
                DadoFinanceiro.objects.filter(papel=papel, conta=patrimonio_conta)
                .order_by("-periodo__data")
                .first()
            )
            patrimonio = float(dado_patrimonio.valor) if dado_patrimonio else None

        # Cálculo dos indicadores
        if lucro and volume:
            lpa = lucro / volume
        else:
            lpa = None

        if patrimonio and volume:
            vpa = patrimonio / volume
        else:
            vpa = None

        if lucro and patrimonio:
            roe = lucro / patrimonio
        else:
            roe = None

        graham = 0
        if lpa and vpa:
            produto = 22.5 * lpa * vpa
            graham = round(produto**0.5, 2) if produto >= 0 else 0

        dados_papel["LPA"] = round(lpa, 2) if lpa else "—"
        dados_papel["VPA"] = round(vpa, 2) if vpa else "—"
        dados_papel["ROE"] = round(roe * 100, 2) if roe else "—"
        dados_papel["Graham"] = round(graham, 2) if graham else "—"

        # P/L, P/ATIVO, DY — usando Ativo Total se disponível
        try:
            ativo_total = float(dados_papel["Ativo_Total"])
        except:
            ativo_total = None

        dados_papel["P_L"] = round(preco / lpa, 2) if preco and lpa else "—"
        dados_papel["P_ATIVO"] = (
            round(preco / ativo_total, 2) if preco and ativo_total else "—"
        )
        dados_papel["DY"] = round((lpa / preco) * 100, 2) if preco and lpa else "—"

        dados.append(dados_papel)

    return render(request, "wallets/all_stocks.html", {"dados": dados})


def pagina_acao(request, codigo):
    papel = get_object_or_404(Papel, codigo=codigo)

    # Obter última data disponível
    ultima_data = DadoFinanceiro.objects.filter(papel=papel).aggregate(
        Max("periodo__data")
    )["periodo__data__max"]

    dados_financeiros = DadoFinanceiro.objects.filter(
        papel=papel, periodo__data=ultima_data
    ).select_related("conta")

    dados_dict = {
        normalizar_nome_conta(df.conta.nome): df.valor for df in dados_financeiros
    }

    ultima_cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
    cotacoes = Cotacao.objects.filter(papel=papel).order_by("data")

    return render(
        request,
        "wallets/pagina_acao.html",
        {
            "papel": papel,
            "dados_dict": dados_dict,
            "ultima_cotacao": ultima_cotacao,
            "cotacoes": cotacoes,
            "ultima_data": ultima_data,
        },
    )


# View para buscar ações
def search_stocks(request):
    query = request.GET.get("q", "").strip().upper()

    if not query:
        return render(
            request, "wallets/search_results.html", {"query": query, "results": []}
        )

    # Tenta encontrar o Papel com código ou ticker correspondente
    papel = Papel.objects.filter(codigo__iexact=query).first()
    if not papel:
        papel = Papel.objects.filter(ticker__iexact=query).first()

    if papel:
        return redirect("wallets:pagina_acao", codigo=papel.codigo)

    # Se não encontrar, renderiza uma página de resultados vazia
    return render(
        request, "wallets/search_results.html", {"query": query, "results": []}
    )


def autocomplete_papeis(request):
    term = request.GET.get("term", "").upper()
    results = []

    if term:
        papeis = Papel.objects.filter(codigo__icontains=term)[:10]
        results = [
            {"label": f"{p.codigo} - {p.empresa.nome}", "value": p.codigo}
            for p in papeis
        ]

    return JsonResponse(results, safe=False)


def visualizar_planilha(request, codigo):
    # Caminho da planilha
    filename = f"{codigo.upper()}.xlsx"
    filepath = os.path.join(settings.MEDIA_ROOT, "planilhas", filename)

    if not os.path.exists(filepath):
        raise Http404("Planilha não encontrada.")

    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        raise Http404("Erro ao ler a planilha.")

    tabela_html = df.to_html(
        classes="table table-bordered table-sm table-striped text-center",
        index=False,
        na_rep="-",
    )

    return render(
        request,
        "planilhas/visualizar_planilha.html",
        {"tabela_html": tabela_html, "codigo": codigo},
    )
