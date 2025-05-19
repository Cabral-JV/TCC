from django.db import transaction, models
from django.shortcuts import get_object_or_404
from .models import (
    Papel,
    PapelCarteiraUsuario,
    PapelCarteiraRecomendada,
    Movimentacao,
    CarteiraRecomendada,
)
from .utils import obter_preco_atual


def aplicar_carteira_recomendada(carteira, lista_recomendada):
    for item in lista_recomendada:
        try:
            papel = Papel.objects.get(codigo=item["codigo"])
            quantidade = item["quantidade"]
            preco_unitario = obter_preco_atual(papel)
            if preco_unitario is None:
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
    if preco_unitario is None:
        raise ValueError(f"Cotação indisponível para {papel.codigo}.")

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
        preco_medio = Movimentacao.objects.filter(
            carteira_usuario=carteira, papel=papel, tipo="COMPRA"
        ).aggregate(
            total_valor=models.Sum(models.F("quantidade") * models.F("preco_unitario")),
            total_qtd=models.Sum("quantidade"),
        )
        if preco_medio["total_qtd"]:
            preco_medio_compra = preco_medio["total_valor"] / preco_medio["total_qtd"]
            lucro = (preco_unitario - preco_medio_compra) * qtd_mov
            carteira.saldo += lucro
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
                papel = get_object_or_404(Papel, codigo=codigo)
                preco_unitario = obter_preco_atual(papel)
                if preco_unitario is None:
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
        papel = get_object_or_404(Papel, codigo=codigo)
        preco_unitario = obter_preco_atual(papel)
        if preco_unitario is None:
            continue

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
        papel = get_object_or_404(Papel, codigo=codigo)
        preco_unitario = obter_preco_atual(papel)
        if preco_unitario is None:
            continue

        PapelCarteiraRecomendada.objects.filter(carteira=carteira, papel=papel).delete()

        Movimentacao.objects.create(
            carteira_recomendada=carteira,
            papel=papel,
            tipo="VENDA",
            quantidade=1,
            preco_unitario=preco_unitario,
        )
