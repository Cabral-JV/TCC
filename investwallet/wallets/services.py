from django.db import transaction, models
from django.shortcuts import get_object_or_404
from .models import (
    Papel,
    PapelCarteiraUsuario,
    PapelCarteiraRecomendada,
    Movimentacao,
    Cotacao,
)
from .utils import obter_preco_atual
from django.db.models import Sum, F


def cotacao_valida(papel):
    cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
    if not cotacao:
        return False
    if (cotacao.preco_abertura or 0) <= 0 and (cotacao.preco_fechamento or 0) <= 0:
        return False
    if (cotacao.numero_total_acoes or 0) <= 0:
        return False
    return True


def aplicar_carteira_recomendada(carteira, lista_recomendada):
    for item in lista_recomendada:
        try:
            papel = Papel.objects.get(codigo=item["codigo"])
            quantidade = item["quantidade"]
            preco_unitario = obter_preco_atual(papel)
            if not cotacao_valida(papel):
                continue

            PapelCarteiraUsuario.objects.create(
                carteira=carteira,
                papel=papel,
                quantidade=quantidade,
            )

            Movimentacao.objects.create(
                carteira_usuario=carteira,
                papel=papel,
                tipo="COMPRA",
                quantidade=quantidade,
                preco_unitario=preco_unitario,
            )
        except Papel.DoesNotExist:
            continue


def processar_movimentacao(carteira, papel, nova_qtd):
    item = PapelCarteiraUsuario.objects.filter(carteira=carteira, papel=papel).first()
    qtd_atual = item.quantidade if item else 0

    if nova_qtd == qtd_atual:
        return

    preco_unitario = obter_preco_atual(papel)
    if not cotacao_valida(papel):
        return

    if nova_qtd == 0:
        if item:
            item.delete()
        tipo = "VENDA"
        qtd_mov = qtd_atual
    elif nova_qtd > qtd_atual:
        tipo = "COMPRA"
        qtd_mov = nova_qtd - qtd_atual
    else:
        tipo = "VENDA"
        qtd_mov = qtd_atual - nova_qtd

    if tipo == "VENDA":
        compras_anteriores = Movimentacao.objects.filter(
            carteira_usuario=carteira, papel=papel, tipo="COMPRA"
        )
        if not compras_anteriores:
            raise ValueError("Não há compras anteriores para realizar a venda.")
        preco_medio = Movimentacao.objects.filter(
            carteira_usuario=carteira, papel=papel, tipo="COMPRA"
        ).aggregate(
            total_valor=models.Sum(models.F("quantidade") * models.F("preco_unitario")),
            total_qtd=models.Sum("quantidade"),
        )
        if preco_medio["total_qtd"]:
            preco_medio_compra = preco_medio["total_valor"] / preco_medio["total_qtd"]
            valor_venda = preco_unitario * qtd_mov
            valor_custo = preco_medio_compra * qtd_mov
            lucro = valor_venda - valor_custo

            carteira.saldo += valor_venda
            carteira.save()

    if nova_qtd > 0:
        if item:
            item.quantidade = nova_qtd
            item.save()
        else:
            PapelCarteiraUsuario.objects.create(
                carteira=carteira, papel=papel, quantidade=nova_qtd
            )

    Movimentacao.objects.create(
        carteira_usuario=carteira,
        papel=papel,
        tipo=tipo,
        quantidade=qtd_mov,
        preco_unitario=preco_unitario,
    )

    atualizar_valores_carteira(carteira)


def criar_ou_atualizar_carteira_usuario(
    form, user, papeis_data, usar_recomendada=False
):
    with transaction.atomic():
        carteira = form.save(commit=False)
        carteira.usuario = user
        carteira.save()

        if usar_recomendada:
            aplicar_carteira_recomendada(carteira, papeis_data)
        else:
            for codigo, quantidade in papeis_data:
                try:
                    papel = Papel.objects.get(codigo=codigo)
                except Papel.DoesNotExist:
                    continue
                cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()

                preco_unitario = obter_preco_atual(papel)
                if not cotacao_valida(papel):
                    continue
                PapelCarteiraUsuario.objects.create(
                    carteira=carteira, papel=papel, quantidade=quantidade
                )
                Movimentacao.objects.create(
                    carteira_usuario=carteira,
                    papel=papel,
                    tipo="COMPRA",
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                )
        return carteira


def atualizar_movimentacoes_por_lista_antiga_nova(carteira, lista_antiga, lista_nova):
    codigos_antigos = set(p["papel__codigo"] for p in lista_antiga)
    codigos_novos = set(p["papel__codigo"] for p in lista_nova)

    codigos_adicionados = codigos_novos - codigos_antigos
    codigos_removidos = codigos_antigos - codigos_novos

    for codigo in codigos_adicionados:
        try:
            papel = Papel.objects.get(codigo=codigo)
        except Papel.DoesNotExist:
            continue
        cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
        if not cotacao_valida(papel):
            continue
        preco_unitario = obter_preco_atual(papel)

        PapelCarteiraRecomendada.objects.create(
            carteira=carteira,
            papel=papel,
            quantidade=1,
        )

        Movimentacao.objects.create(
            carteira_recomendada=carteira,
            papel=papel,
            tipo="COMPRA",
            quantidade=1,
            preco_unitario=preco_unitario,
        )

    for codigo in codigos_removidos:
        try:
            papel = Papel.objects.get(codigo=codigo)
        except Papel.DoesNotExist:
            continue

        if not cotacao_valida(papel):
            continue

        preco_unitario = obter_preco_atual(papel)
        if not preco_unitario:
            continue

        PapelCarteiraRecomendada.objects.filter(carteira=carteira, papel=papel).delete()

        Movimentacao.objects.create(
            carteira_recomendada=carteira,
            papel=papel,
            tipo="VENDA",
            quantidade=1,
            preco_unitario=preco_unitario,
        )


def calcular_valor_investido(carteira):
    valor_investido = 0

    papeis = PapelCarteiraUsuario.objects.filter(carteira=carteira)

    for item in papeis:
        papel = item.papel
        qtd_atual = item.quantidade

        # Total gasto em compras (quantidade * preco_unitario)
        total_compras = (
            Movimentacao.objects.filter(
                carteira_usuario=carteira, papel=papel, tipo="COMPRA"
            ).aggregate(total=Sum(F("quantidade") * F("preco_unitario")))["total"]
            or 0
        )

        # Quantidade total comprada
        qtd_comprada = (
            Movimentacao.objects.filter(
                carteira_usuario=carteira, papel=papel, tipo="COMPRA"
            ).aggregate(total=Sum("quantidade"))["total"]
            or 0
        )

        if qtd_comprada == 0:
            continue  # evita divisão por zero

        # Custo médio por ação (baseado nas compras)
        custo_medio = total_compras / qtd_comprada

        # Valor investido = custo médio * quantidade atual na carteira
        valor_investido += custo_medio * qtd_atual

    return valor_investido


def atualizar_valores_carteira(carteira):
    papeis = PapelCarteiraUsuario.objects.filter(carteira=carteira)
    valor_investido = calcular_valor_investido(carteira)
    valor_atual = 0

    for item in papeis:
        papel = item.papel
        qtd = item.quantidade

        # Total investido = soma de todas as compras
        total_compras = (
            Movimentacao.objects.filter(
                carteira_usuario=carteira, papel=papel, tipo="COMPRA"
            ).aggregate(
                total=models.Sum(models.F("quantidade") * models.F("preco_unitario"))
            )[
                "total"
            ]
            or 0
        )

        # Valor atual = qtd * preço atual
        preco_atual = obter_preco_atual(papel) or 0
        valor_atual += qtd * preco_atual

    carteira.valor_investido = valor_investido
    carteira.valor_atual = valor_atual
    carteira.save()
