import os
import pandas as pd
from django.core.management.base import BaseCommand
from wallets.models import Empresa, ContaFinanceira, Papel
from django.conf import settings


class Command(BaseCommand):
    help = "Importa dados estruturais e valores financeiros para o banco de dados"

    def handle(self, *args, **kwargs):
        self.importar_estrutura()
        self.stdout.write(self.style.SUCCESS("\n✅ Importação completa!"))

    def importar_estrutura(self):
        caminho = os.path.join(settings.MEDIA_ROOT, "uploads_db","Fill_database.xlsx")
        df = pd.read_excel(caminho)
        df = df.dropna(how="all")  # Remove linhas totalmente vazias

        empresas = {}
        papeis = {}
        contas = {}
        periodos = {}

        # ====== Empresas e Papeis ======
        self.stdout.write("\n🔎 Verificando Empresas e Papeis...")
        empresas_df = df.dropna(subset=["Empresa", "Codigo", "Ticker"])

        for _, row in empresas_df.iterrows():
            nome = str(row["Empresa"]).strip()
            codigo = str(row["Codigo"]).strip()
            ticker = str(row["Ticker"]).strip()

            empresa, _ = Empresa.objects.get_or_create(nome=nome)
            empresas[nome] = empresa

            papel, created = Papel.objects.get_or_create(
                codigo=codigo, ticker=ticker, defaults={"empresa": empresa}
            )
            papeis[codigo] = papel

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Papel criado: {codigo} ({empresa.nome})")
                )
            else:
                self.stdout.write(self.style.WARNING(f"Papel já existia: {codigo}"))

        self.stdout.write(self.style.SUCCESS(f"🏢 Total de empresas: {len(empresas)}"))
        self.stdout.write(self.style.SUCCESS(f"📄 Total de papeis: {len(papeis)}"))

        # ====== Contas Financeiras ======
        self.stdout.write("\n🔎 Verificando Contas Financeiras...")
        contas_df = df.dropna(subset=["Conta Financeira"])

        for conta_nome in contas_df["Conta Financeira"].unique():
            conta_nome = str(conta_nome).strip()
            conta, created = ContaFinanceira.objects.get_or_create(nome=conta_nome)
            contas[conta_nome] = conta

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Conta Financeira criada: {conta_nome}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Conta Financeira já existia: {conta_nome}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"💵 Total de contas financeiras: {len(contas)}")
        )

        # Salvar para uso posterior
        self.empresas = empresas
        self.papeis = papeis
        self.contas = contas

        self.stdout.write(self.style.SUCCESS("\n✅ Estrutura validada!"))
