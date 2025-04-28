import os
import pandas as pd
from django.core.management.base import BaseCommand
from wallets.models import Empresa, Papel, ContaFinanceira, DataRegistro, DadoFinanceiro
from django.conf import settings
from django.db import transaction


class Command(BaseCommand):
    help = "Importa dados estruturais e valores financeiros para o banco de dados"

    def handle(self, *args, **kwargs):
        self.importar_estrutura()
        self.importar_dados_financeiros()
        self.stdout.write(self.style.SUCCESS("\n✅ Importação completa!"))

    def importar_estrutura(self):
        caminho = os.path.join(
            settings.BASE_DIR, "media", "uploads_db", "Fill_database.xlsx"
        )
        df = pd.read_excel(caminho)

        df = df.dropna(how="all")  # Continua limpando linhas completamente vazias

        empresas = {}
        papeis = {}
        contas = {}
        datas = {}

        # ====== Empresas e Papéis ======
        self.stdout.write("\n🔎 Verificando Empresas e Papéis...")
        empresas_df = df.dropna(
            subset=["Empresa", "Codigo", "Ticker"]
        )  # Só valida Empresa, Código e Ticker

        for _, row in empresas_df.iterrows():
            nome_empresa = str(row["Empresa"]).strip()
            codigo = str(row["Codigo"]).strip()
            ticker = str(row["Ticker"]).strip()

            # Empresa
            empresa, created = Empresa.objects.get_or_create(nome=nome_empresa)
            empresas[nome_empresa] = empresa
            if created:
                self.stdout.write(self.style.SUCCESS(f"Empresa criada: {nome_empresa}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Empresa já existia: {nome_empresa}")
                )

            # Papel
            papel, created = Papel.objects.get_or_create(
                codigo=codigo,
                defaults={"empresa": empresa, "ticker": ticker},
            )
            papeis[codigo] = papel
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Papel criado: {codigo} - {ticker}")
                )
            else:
                self.stdout.write(self.style.WARNING(f"Papel já existia: {codigo}"))

        self.stdout.write(self.style.SUCCESS(f"🏢 Total de empresas: {len(empresas)}"))
        self.stdout.write(self.style.SUCCESS(f"📝 Total de papéis: {len(papeis)}"))

        # ====== Contas Financeiras ======
        self.stdout.write("\n🔎 Verificando Contas Financeiras...")
        contas_df = df.dropna(subset=["Conta Financeira"])  # Só valida Conta Financeira

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

        # ====== Datas ======
        self.stdout.write("\n📅 Registrando Datas únicas...")
        datas_df = df.dropna(subset=["Data"])  # Só valida Data

        for data_valor in datas_df["Data"].unique():
            try:
                # Tentar converter para o formato correto (yyyy-mm-dd)
                data_formatada = pd.to_datetime(data_valor, dayfirst=True).date()
                data_obj, created = DataRegistro.objects.get_or_create(
                    data=data_formatada
                )
                datas[data_formatada] = data_obj
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Data criada: {data_obj.data.strftime('%d/%m/%Y')}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Data já existia: {data_obj.data.strftime('%d/%m/%Y')}"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Data inválida '{data_valor}'. Erro: {e}")
                )

        self.stdout.write(self.style.SUCCESS(f"📆 Total de datas: {len(datas)}"))

        # Salva em memória para usar depois
        self.empresas = empresas
        self.papeis = papeis
        self.contas = contas
        self.datas = datas

        self.stdout.write(self.style.SUCCESS("\n✅ Estrutura validada!"))
        self.criar_dados_financeiros_vazios()

    @transaction.atomic
    def criar_dados_financeiros_vazios(self):
        self.stdout.write(
            "\n🛠️ Preenchendo dados financeiros com valor 0 (caso não existam)..."
        )

        # Buscar todos os registros existentes uma única vez
        registros_existentes = set(
            DadoFinanceiro.objects.values_list(
                "papel_id", "conta_id", "data_id"
            )
        )

        total = len(self.papeis) * len(self.contas) * len(self.datas)
        atual = 0
        dados_financeiros = []

        for papel in self.papeis.values():
            self.stdout.write(
                self.style.WARNING(f"Preenchendo papel: {papel.codigo}...")
            )
            for conta in self.contas.values():
                for data_obj in self.datas.values():
                    chave = (papel.id, conta.id, data_obj.id)

                    if chave not in registros_existentes:
                        dados_financeiros.append(
                            DadoFinanceiro(
                                papel=papel,
                                conta=conta,
                                data=data_obj,
                                valor=0
                            )
                        )

                        if len(dados_financeiros) >= 1000:
                            DadoFinanceiro.objects.bulk_create(dados_financeiros)
                            atual += len(dados_financeiros)
                            dados_financeiros = []

        if dados_financeiros:
            DadoFinanceiro.objects.bulk_create(dados_financeiros)
            atual += len(dados_financeiros)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Dados financeiros preenchidos com valor 0 ({atual} registros novos)."
            )
        )


    @transaction.atomic
    def importar_dados_financeiros(self):
        self.stdout.write("\n📂 Importando dados financeiros reais...")
        pasta = os.path.join(settings.BASE_DIR, "media", "uploads_bal")
        arquivos = [f for f in os.listdir(pasta) if f.endswith(".xlsx")]

        for nome_arquivo in arquivos:
            caminho = os.path.join(pasta, nome_arquivo)
            df = pd.read_excel(caminho, header=None)

            papel_codigo = str(df.iloc[0, 0]).strip()
            try:
                papel = Papel.objects.get(codigo=papel_codigo)
            except Papel.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Papel '{papel_codigo}' não encontrado. Pulando arquivo."))
                continue

            # Carrega todos os dados existentes do papel de uma vez
            dados_existentes = DadoFinanceiro.objects.filter(papel=papel)
            mapa_existentes = {(dado.conta_id, dado.data_id): dado for dado in dados_existentes}

            datas_excel = df.iloc[0, 1:].tolist()
            contas_excel = df.iloc[1:, 0].tolist()
            valores = df.iloc[1:, 1:]

            self.stdout.write(self.style.WARNING(f"Atualizando valores para Papel: {papel.codigo}"))

            novos_dados = []
            atualizacoes = []

            for i, conta_nome in enumerate(contas_excel):
                if pd.isna(conta_nome):
                    continue

                conta_nome = str(conta_nome).strip()
                conta = ContaFinanceira.objects.filter(nome=conta_nome).first()
                if not conta:
                    self.stdout.write(self.style.WARNING(f"Conta '{conta_nome}' não encontrada. Pulando..."))
                    continue

                for j, data_excel in enumerate(datas_excel):
                    if pd.isna(data_excel):
                        continue
                    try:
                        data_formatada = pd.to_datetime(data_excel, dayfirst=True).date()
                    except Exception:
                        continue

                    data_obj = DataRegistro.objects.filter(data=data_formatada).first()
                    if not data_obj:
                        self.stdout.write(self.style.WARNING(f"Data '{data_formatada}' não encontrada. Pulando..."))
                        continue

                    valor = valores.iat[i, j]
                    try:
                        valor = float(valor) if not pd.isna(valor) else 0
                    except (ValueError, TypeError):
                        valor = 0

                    chave = (conta.id, data_obj.id)
                    dado_existente = mapa_existentes.get(chave)

                    if dado_existente:
                        if dado_existente.valor == 0 and valor != 0:
                            dado_existente.valor = valor
                            atualizacoes.append(dado_existente)
                    else:
                        novos_dados.append(
                            DadoFinanceiro(papel=papel, conta=conta, data=data_obj, valor=valor)
                        )

            if novos_dados:
                DadoFinanceiro.objects.bulk_create(novos_dados, batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"✅ {len(novos_dados)} novos dados inseridos."))

            if atualizacoes:
                DadoFinanceiro.objects.bulk_update(atualizacoes, ["valor"], batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"✅ {len(atualizacoes)} dados atualizados."))

        self.stdout.write(self.style.SUCCESS("\n✅ Todos os arquivos processados!"))
