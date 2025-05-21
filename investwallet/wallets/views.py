from collections import defaultdict
import os
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.db.models import Max, Q
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
    calcular_valor_investido,
)
import pandas as pd
import json


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
                    try:
                        papel = Papel.objects.get(codigo=codigo)
                    except Papel.DoesNotExist:
                        continue

                    cotacao = (
                        Cotacao.objects.filter(papel=papel).order_by("-data").first()
                    )
                    if not cotacao or (
                        (cotacao.preco_abertura or 0) <= 0
                        and (cotacao.preco_fechamento or 0) <= 0
                    ):
                        continue

                    preco = obter_preco_atual(papel)
                    if preco is None or preco <= 0:
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
            total_investido += papel.valor_total
            total_atual += papel.valor_total
            
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
            # Transforma a string em lista de códigos
            novos_codigos_str = form.cleaned_data["papeis_lista"]
            novos_codigos = [
                codigo.strip().upper()
                for codigo in novos_codigos_str.split(",")
                if codigo.strip()
            ]

            # Lista antiga de códigos
            antigos = PapelCarteiraRecomendada.objects.filter(
                carteira=carteira
            ).select_related("papel")
            lista_antiga = [p.papel.codigo for p in antigos]

            # Atualiza papeis e registra movimentações
            atualizar_movimentacoes_por_lista_antiga_nova(
                carteira, lista_antiga, novos_codigos
            )

            return redirect("wallets:criar_carteira_recomendada")
    else:
        papeis_atuais = PapelCarteiraRecomendada.objects.filter(
            carteira=carteira
        ).select_related("papel")
        codigos_atuais = ", ".join([p.papel.codigo for p in papeis_atuais])
        form = CarteiraForm(initial={"papeis_lista": codigos_atuais})

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
    carteiras_usuario = list(CarteiraUsuario.objects.filter(usuario=usuario))
    carteira_recomendada = CarteiraRecomendada.objects.first()

    ultima_data = (
        Cotacao.objects.order_by("-data").values_list("data", flat=True).first()
    )

    papeis_disponiveis = (
        Papel.objects.filter(cotacoes__data=ultima_data)
        .filter(Q(cotacoes__preco_abertura__gt=0) | Q(cotacoes__preco_fechamento__gt=0))
        .distinct()
    )

    # Juntando carteiras do usuário com a recomendada (se existir)
    todas_carteiras = carteiras_usuario.copy()
    if carteira_recomendada:
        carteira_recomendada.recomendada = True  # atributo dinâmico
        todas_carteiras.insert(0, carteira_recomendada)

    precos_atuais = {}
    totais_por_carteira = {}
    movimentacoes_por_carteira = defaultdict(list)

    for carteira in todas_carteiras:
        is_usuario = isinstance(carteira, CarteiraUsuario)

        movimentacoes = Movimentacao.objects.filter(
            carteira_usuario=carteira if is_usuario else None,
            carteira_recomendada=None if is_usuario else carteira,
        )
        movimentacoes_por_carteira[carteira.id] = movimentacoes

        papeis = carteira.papeis.all()

        # Atualiza preços e valores
        for item in papeis:
            codigo = item.papel.codigo
            if codigo not in precos_atuais:
                preco = obter_preco_atual(item.papel)
                precos_atuais[codigo] = preco if preco is not None else 0

        # Atualiza atributos dinâmicos nos papéis da carteira
        for item in papeis:
            preco = precos_atuais.get(item.papel.codigo, 0)
            item.preco_atual = preco
            item.valor_total_atualizado = preco * item.quantidade if item.quantidade else 0


# Cálculo de totais
        if is_usuario:
            total_investido = calcular_valor_investido(carteira)
        else:
            total_investido = sum(
                item.quantidade * precos_atuais.get(item.papel.codigo, 0)
                for item in papeis
            )

        total_atual = sum(
            item.quantidade * precos_atuais.get(item.papel.codigo, 0)
            for item in papeis
        )

        variacao = (
            ((total_atual - total_investido) / total_investido) * 100
            if total_investido > 0 else 0
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
    # Pega a última data disponível de cotação
    ultima_data = (
        Cotacao.objects.order_by("-data").values_list("data", flat=True).first()
    )

    # Filtra apenas papéis com cotação válida (abertura ou fechamento > 0) na última data
    papeis_validos = (
        Papel.objects.filter(cotacoes__data=ultima_data)
        .filter(Q(cotacoes__preco_abertura__gt=0) | Q(cotacoes__preco_fechamento__gt=0))
        .distinct()
        .values("codigo")
    )

    # Lista dos papéis recomendados (com ticker e quantidade)
    recomendada = list(
        PapelCarteiraRecomendada.objects.select_related("papel").values(
            "papel__codigo", "quantidade"
        )
    )
    recomendada_js = [
        {"codigo": r["papel__codigo"], "quantidade": r["quantidade"]}
        for r in recomendada
        if any(
            p["codigo"] == r["papel__codigo"] for p in papeis_validos
        )  # garante que só papéis válidos vão pro JS também
    ]

    if request.method == "POST":
        form = CarteiraUsuarioForm(request.POST)
        if form.is_valid():
            usar_recomendada = "usar_recomendada" in request.POST
            tickers = [key for key in request.POST if key.startswith("ticker_")]
            papeis_data = []
            for t in tickers:
                idx = t.split("_")[1]
                codigo = request.POST.get(f"ticker_{idx}")
                try:
                    quantidade = int(request.POST.get(f"quantidade_{idx}"))
                except (TypeError, ValueError):
                    continue
                if quantidade >= 0:
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
        {"form": form, "papeis": list(papeis_validos), "recomendada": recomendada_js},
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
                try:
                    papel = Papel.objects.get(codigo=codigo)
                except Papel.DoesNotExist:
                    continue
                cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
                if cotacao and (
                    (cotacao.preco_abertura or 0) > 0
                    or (cotacao.preco_fechamento or 0) > 0
                ):
                    processar_movimentacao(carteira, papel, nova_qtd)

        novo_codigo = request.POST.get("nova_acao")
        nova_qtd = request.POST.get("nova_quantidade")
        if novo_codigo and nova_qtd:
            novo_codigo = novo_codigo.upper()
            nova_qtd = int(nova_qtd)
            papel = Papel.objects.get(codigo=novo_codigo)
            cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
            if cotacao and (
                (cotacao.preco_abertura or 0) > 0 or (cotacao.preco_fechamento or 0) > 0
            ):
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
    papeis = Papel.objects.all()
    dados = []

    for papel in papeis:
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

        item = {
            "papel": papel.codigo,
            "cotacao": ultima_cotacao.preco_fechamento if ultima_cotacao else "—",
            "graham": dados_dict.get("graham", "—"),
            "ativo_total": dados_dict.get("ativo_total", "—"),
            "caixa_e_equivalentes": dados_dict.get(
                "caixa_e_equivalentes_de_caixa", "—"
            ),
            "patrimonio_liquido": dados_dict.get("patrimonio_liquido", "—"),
            "receita_liquida": dados_dict.get(
                "receita_liquida_de_vendas_e_ou_servicos", "—"
            ),
            "lucro_prejuizo_do_periodo": dados_dict.get(
                "lucro_prejuizo_do_periodo", "—"),
            "roe": dados_dict.get("roe", "—"),
            "lpa": dados_dict.get("lpa", "—"),
            "vpa": dados_dict.get("vpa", "—"),
            "pl": dados_dict.get("pl", "—"),
        }

        dados.append(item)

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

    # Extras calculados
    numero_acoes = ultima_cotacao.numero_total_acoes if ultima_cotacao else None
    volume = ultima_cotacao.volume if ultima_cotacao else None

    dados_gcharts = []
    for c in cotacoes:
        dados_gcharts.append(
            {
                "data": c.data.strftime("%Y-%m-%d"),
                "preco_abertura": float(c.preco_abertura) if c.preco_abertura else None,
                "preco_fechamento": (
                    float(c.preco_fechamento) if c.preco_fechamento else None
                ),
            }
        )

    dados_gcharts_json = json.dumps(dados_gcharts)  # Converte para JSON string

    return render(
        request,
        "wallets/pagina_acao.html",
        {
            "papel": papel,
            "dados_dict": dados_dict,
            "ultima_cotacao": ultima_cotacao,
            "cotacoes": cotacoes,
            "ultima_data": ultima_data,
            "numero_acoes": numero_acoes,
            "volume": volume,
            "dados_gcharts": dados_gcharts,
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
        "wallets/visualizar_planilha.html",
        {"tabela_html": tabela_html, "codigo": codigo},
    )
