from django.core.management.base import BaseCommand
import os
import pandas as pd
from wallets.models import Empresa, ContaFinanceira, Periodo, DadoFinanceiro, Papel
from django.conf import settings


class Command(BaseCommand):
    help = "Preenche os dados financeiros a partir das planilhas em uploads_bal"

    def handle(self, *args, **kwargs):
        pasta = os.path.join(settings.MEDIA_ROOT, "uploads_bal")

        contas_selecionadas = {
            "Ativo Total",
            "Ativo Circulante",
            "Caixa e Equivalentes de Caixa",
            "Patrimônio Líquido",
            "Receita Líquida de Vendas e/ou Serviços",
            "Lucro/Prejuízo do Período",
        }

        for nome_arquivo in os.listdir(pasta):
            if not nome_arquivo.endswith(".xlsx"):
                continue

            caminho_arquivo = os.path.join(pasta, nome_arquivo)

            try:
                df = pd.read_excel(caminho_arquivo, header=None)
                codigo = df.iloc[0, 0] or nome_arquivo.split(".")[0]
                ticker = f"{codigo}.SA"

                papel = Papel.objects.filter(ticker=ticker).first()
                if not papel:
                    self.stderr.write(f"[ERRO] Papel '{ticker}' não encontrado.")
                    continue

                # === Últimas 4 datas da planilha ===
                datas_raw = df.iloc[0, 1:].tolist()
                datas_convertidas = []

                for data_str in datas_raw:
                    try:
                        data = pd.to_datetime(data_str, dayfirst=True).date()
                        datas_convertidas.append(data)
                    except Exception as e:
                        self.stderr.write(f"[ERRO] Data inválida '{data_str}': {e}")

                datas_validas = sorted(filter(None, datas_convertidas))[-4:]

                # Criação dos períodos se ainda não existirem
                periodos = {}
                for data in datas_validas:
                    periodo, _ = Periodo.objects.get_or_create(data=data)
                    periodos[data] = periodo

                # === Preenchendo dados apenas para essas 4 datas ===
                for linha in range(1, df.shape[0]):
                    nome_conta = df.iloc[linha, 0]
                    if pd.isna(nome_conta) or nome_conta not in contas_selecionadas:
                        continue

                    conta = ContaFinanceira.objects.filter(nome=nome_conta).first()
                    if not conta:
                        self.stderr.write(
                            f"[ERRO] Conta '{nome_conta}' não encontrada."
                        )
                        continue

                    for idx_data, data in enumerate(datas_validas):
                        periodo = periodos.get(data)
                        if not periodo:
                            continue

                        try:
                            # +1 porque os dados começam na coluna 1
                            valor = df.iloc[linha, idx_data + 1]
                            valor = float(valor) if pd.notna(valor) else 0.0
                        except Exception:
                            valor = 0.0

                        _, created = DadoFinanceiro.objects.get_or_create(
                            papel=papel,
                            conta=conta,
                            periodo=periodo,
                            defaults={"valor": valor},
                        )

                        if created:
                            self.stdout.write(
                                f"[OK] {papel.codigo} | {nome_conta} | {data} => {valor}"
                            )
                        else:
                            self.stdout.write(
                                f"[SKIP] Já existe: {papel.codigo} | {nome_conta} | {data}"
                            )

                self.stdout.write(
                    self.style.SUCCESS(f"[IMPORTADO] {ticker} processado com sucesso")
                )

            except Exception as e:
                self.stderr.write(f"[ERRO] Falha ao processar '{nome_arquivo}': {e}")
