import yfinance as yf
from django.utils import timezone
from .models import Papel, Cotacao
from datetime import time
import unidecode
import re

def normalizar_nome_conta(nome):
    nome = unidecode.unidecode(nome).lower()
    nome = re.sub(r"[^\w]+", "", nome)
    return nome.strip("")

def obter_preco_atual(papel):
    now = timezone.localtime().time()
    cotacao = Cotacao.objects.filter(papel=papel).order_by("-data").first()
    if not cotacao:
        return None
    if time(10, 0) <= now <= time(18, 0):
        return cotacao.preco_abertura or cotacao.preco_fechamento
    return cotacao.preco_fechamento


def atualizar_preco_abertura():
    for papel in Papel.objects.all():
        try:
            dados = yf.download(papel.ticker, period="1d", interval="1d")
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
    for papel in Papel.objects.all():
        try:
            dados = yf.download(papel.ticker, period="1d", interval="1d")
            preco_fechamento = dados["Close"].iloc[-1]
            volume = dados["Volume"].iloc[-1] or 0
            preco_abertura = dados["Open"].iloc[0] or 0
            numero_acoes = yf.Ticker(papel.ticker).info.get("sharesOutstanding", 0)

            data_hoje = timezone.localdate()

            cotacao, created = Cotacao.objects.get_or_create(
                papel=papel,
                data=data_hoje,
                defaults={
                    "preco_abertura": preco_abertura,
                    "preco_fechamento": preco_fechamento,
                    "volume": volume,
                    "numero_total_acoes": numero_acoes or 0,
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
