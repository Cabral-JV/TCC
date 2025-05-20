
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

                count = 0
                for index, row in df.iterrows():
                    data = index.date()
                    try:
                        preco_abertura = Decimal(row[("Open", papel.ticker)]).quantize(Decimal("0.01")) if not pd.isna(row[("Open", papel.ticker)]) else None
                        preco_fechamento = Decimal(row[("Close", papel.ticker)]).quantize(Decimal("0.01")) if not pd.isna(row[("Close", papel.ticker)]) else None
                        volume = Decimal(row[("Volume", papel.ticker)]).quantize(Decimal("1")) if not pd.isna(row[("Volume", papel.ticker)]) else None

                        shares = ticker_info.get("sharesOutstanding")
                        try:
                            numero_acoes = Decimal(shares)
                        except (TypeError, ValueError):
                            numero_acoes = None

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

