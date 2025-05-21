import yfinance as yf
from django.core.management.base import BaseCommand
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from wallets.models import Papel, Cotacao
import pandas as pd


class Command(BaseCommand):
    help = "Importa cotações históricas dos últimos 5 anos do Yahoo Finance (com atualização inteligente)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticker",
            type=str,
            help="Ticker específico (ex: PETR4.SA). Se omitido, importa todos.",
        )

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        ontem = hoje - timedelta(days=1)

        if options["ticker"]:
            try:
                papeis = [Papel.objects.get(ticker=options["ticker"])]
            except Papel.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Ticker "{options["ticker"]}" não encontrado.')
                )
                return
        else:
            papeis = Papel.objects.all()

        for papel in papeis:
            self.stdout.write(f"\n🔎 Verificando {papel.ticker}...")

            # Verifica a última data salva no banco para esse papel
            ultima_cotacao = (
                Cotacao.objects.filter(papel=papel).order_by("-data").first()
            )

            if ultima_cotacao and ultima_cotacao.data >= ontem:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {papel.ticker}: Cotações já atualizadas até {ultima_cotacao.data}"
                    )
                )
                continue

            data_inicio = (
                ultima_cotacao.data + timedelta(days=1)
                if ultima_cotacao
                else hoje - timedelta(days=365 * 5)
            )
            data_fim = ontem

            self.stdout.write(
                f"📥 Importando cotações de {data_inicio} até {data_fim}..."
            )

            try:
                df = yf.download(
                    papel.ticker,
                    start=data_inicio,
                    end=data_fim + timedelta(days=1),
                    interval="1d",
                    progress=False,
                )

                if df.empty:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Nenhum dado encontrado para {papel.ticker}"
                        )
                    )
                    continue

                # pega número de ações em circulação
                ticker_info = yf.Ticker(papel.ticker).info
                shares = ticker_info.get("sharesOutstanding")
                try:
                    numero_acoes = Decimal(shares)
                except (TypeError, ValueError):
                    numero_acoes = None

                count = 0
                for index, row in df.iterrows():
                    data = index.date()
                    try:
                        preco_abertura = Decimal(row[("Open", papel.ticker)]).quantize(Decimal("0.01")) if not pd.isna(row[("Open", papel.ticker)]) else None
                        preco_fechamento = Decimal(row[("Close", papel.ticker)]).quantize(Decimal("0.01")) if not pd.isna(row[("Close", papel.ticker)]) else None
                        volume = Decimal(row[("Volume", papel.ticker)]).quantize(Decimal("1")) if not pd.isna(row[("Volume", papel.ticker)]) else None

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
                        self.stdout.write(
                            self.style.WARNING(f"⚠️ Erro em {papel.ticker} {data}: {e}")
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"📊 {papel.ticker}: {count} novas cotações importadas."
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro ao importar {papel.ticker}: {str(e)}")
                )
