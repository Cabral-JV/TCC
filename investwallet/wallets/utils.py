import pandas as pd
import yfinance as yf
from django.utils import timezone

from datetime import time
import unicodedata
import re


def normalizar_nome_conta(nome):
    nome = nome.strip().lower()
    nome = unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode("ASCII")

    mapeamento = {
        "graham": "graham",
        "p/l": "pl",
        "p/vp": "pvp",
        "roe": "roe",
        "lucro/prejuizo do periodo": "lucro_prejuizo_do_periodo",
        "receita liquida de vendas e/ou servicos": "receita_liquida_de_vendas_e_ou_servicos",
        "caixa e equivalentes de caixa": "caixa_e_equivalentes_de_caixa",
        "ativo circulante": "ativo_circulante",
        "ativo total": "ativo_total",
        "patrimonio liquido": "patrimonio_liquido",
        "vpa": "vpa",
        "lpa": "lpa",
        "valor de mercado": "valor_mercado",
        "numero de acoes": "numero_acoes",
        "volume": "volume",
        "preco de fechamento": "preco_fechamento",
        "preco de abertura": "preco_abertura",
    }

    return mapeamento.get(nome, nome.replace(" ", "_"))


def obter_preco_atual(papel):
    from .models import Cotacao

    agora = timezone.localtime()
    agora_time = agora.time()

    # Busca a cotação mais recente para o papel
    cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
    if not cotacao:
        return None

    # Se estiver entre 10h e 18h (horário de pregão), tenta usar preco_abertura do dia
    if time(10, 0) <= agora_time <= time(18, 0):
        if cotacao.preco_abertura and cotacao.preco_abertura > 0:
            return cotacao.preco_abertura
        # Se preco_abertura inválido, tenta pegar preco_fechamento da cotação anterior
        cotacao_anterior = (
            Cotacao.objects.filter(papel=papel, data__lt=cotacao.data)
            .order_by("-data")
            .first()
        )
        if (
            cotacao_anterior
            and cotacao_anterior.preco_fechamento
            and cotacao_anterior.preco_fechamento > 0
        ):
            return cotacao_anterior.preco_fechamento
        return None

    # Fora do horário de pregão, usa preco_fechamento do último dia disponível
    if cotacao.preco_fechamento and cotacao.preco_fechamento > 0:
        return cotacao.preco_fechamento

    return None


def atualizar_preco_abertura():
    from .models import Papel, Cotacao

    for papel in Papel.objects.all():
        try:
            dados = yf.download(
                papel.ticker, period="1d", interval="1d", progress=False
            )

            # Verifica se dados retornaram e não estão vazios
            if dados.empty:
                print(f"Nenhum dado retornado para {papel.ticker}")
                continue

            # Se colunas são MultiIndex, pega o nível correto
            if isinstance(dados.columns, pd.MultiIndex):
                # Exemplo: ('Open', 'AERI3.SA')
                # Usa 'Open' e papel.ticker para pegar a coluna correta
                preco_abertura = dados.loc[:, ("Open", papel.ticker)].iloc[0]
            else:
                preco_abertura = dados["Open"].iloc[0]

            data_hoje = timezone.localdate()

            cotacao, created = Cotacao.objects.get_or_create(
                papel=papel,
                data=data_hoje,
                defaults={
                    "preco_abertura": preco_abertura,
                    "preco_fechamento": 0,
                    "numero_total_acoes": 0,
                },
            )

            if not created and cotacao.preco_abertura == 0:
                cotacao.preco_abertura = preco_abertura
                cotacao.save(update_fields=["preco_abertura"])

        except Exception as e:
            print(f"Erro ao atualizar abertura de {papel.codigo}: {e}")


def atualizar_preco_fechamento_e_acoes():
    from .models import Papel, Cotacao

    for papel in Papel.objects.all():
        try:
            dados = yf.download(
                papel.ticker, period="1d", interval="1d", progress=False
            )

            if dados.empty:
                print(f"Nenhum dado retornado para {papel.ticker}")
                continue

            if isinstance(dados.columns, pd.MultiIndex):
                preco_fechamento = dados.loc[:, ("Close", papel.ticker)].iloc[-1]
                volume = dados.loc[:, ("Volume", papel.ticker)].iloc[-1] or 0
                preco_abertura = dados.loc[:, ("Open", papel.ticker)].iloc[0] or 0
            else:
                preco_fechamento = dados["Close"].iloc[-1]
                volume = dados["Volume"].iloc[-1] or 0
                preco_abertura = dados["Open"].iloc[0] or 0

            numero_acoes = yf.Ticker(papel.ticker).info.get("sharesOutstanding") or 0

            data_hoje = timezone.localdate()

            cotacao, created = Cotacao.objects.get_or_create(
                papel=papel,
                data=data_hoje,
                defaults={
                    "preco_abertura": preco_abertura,
                    "preco_fechamento": preco_fechamento,
                    "volume": volume,
                    "numero_total_acoes": numero_acoes,
                },
            )

            atualizou = False
            if not created:
                if cotacao.preco_fechamento == 0:
                    cotacao.preco_fechamento = preco_fechamento
                    atualizou = True
                if cotacao.numero_total_acoes == 0 and numero_acoes:
                    cotacao.numero_total_acoes = numero_acoes
                    atualizou = True
                if atualizou:
                    cotacao.save(
                        update_fields=["preco_fechamento", "numero_total_acoes"]
                    )

        except Exception as e:
            print(f"Erro ao atualizar fechamento de {papel.codigo}: {e}")


def iniciar_agendamento():
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        atualizar_preco_abertura,
        "cron",
        hour=10,
        minute=0,
        timezone="America/Sao_Paulo",
    )
    scheduler.add_job(
        atualizar_preco_fechamento_e_acoes,
        "cron",
        hour=18,
        minute=0,
        timezone="America/Sao_Paulo",
    )
    scheduler.start()
