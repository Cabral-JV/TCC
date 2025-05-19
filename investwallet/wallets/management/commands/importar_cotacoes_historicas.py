
import yfinance as yf
from django.core.management.base import BaseCommand
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta
from wallets.models import Papel, Cotacao
import pandas as pd


class Command(BaseCommand):
    help = "Importa cotações históricas dos últimos 5 anos do Yahoo Finance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticker",
            type=str,
            help="Ticker específico (ex: PETR4.SA). Se omitido, importa todos.",
        )

    def handle(self, *args, **options):
        if options["ticker"]:
            try:
                papeis = [Papel.objects.get(ticker=options["ticker"])]
            except Papel.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Ticker "{options["ticker"]}" não encontrado.'))
                return
        else:
            papeis = Papel.objects.all()

        for papel in papeis:
            self.stdout.write(f"Importando {papel.ticker}...")

            try:
                df = yf.download(papel.ticker, period="5y", interval="1d", progress=False)

                if df.empty:
                    self.stdout.write(self.style.WARNING(f"Nenhum dado encontrado para {papel.ticker}"))
                    continue

                # pega número de ações em circulação (sharesOutstanding)
                ticker_info = yf.Ticker(papel.ticker).info
                numero_acoes = Decimal(ticker_info.get("sharesOutstanding", 0)) or Decimal("0")

                count = 0
                for index, row in df.iterrows():
                    data = index.date()
                    try:
                        preco_abertura = Decimal(row["Open"]).quantize(Decimal("0.01"))
                        preco_fechamento = Decimal(row["Close"]).quantize(Decimal("0.01"))
                        volume = Decimal(row["Volume"]).quantize(Decimal("1"))

                        _, created = Cotacao.objects.update_or_create(
                            papel=papel,
                            data=data,
                            defaults={
                                "preco_abertura": preco_abertura,
                                "preco_fechamento": preco_fechamento,
                                "volume": volume,
                                "numero_total_acoes": numero_acoes,
                            },
                        )
                        count += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Erro em {papel.ticker} {data}: {e}"))

                self.stdout.write(self.style.SUCCESS(f"{papel.ticker}: {count} cotações importadas."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao importar {papel.ticker}: {str(e)}"))

