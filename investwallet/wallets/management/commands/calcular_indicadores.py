from django.core.management.base import BaseCommand
from django.db.models import Q
from decimal import Decimal, InvalidOperation, DivisionByZero
from math import sqrt
from wallets.models import Papel, DadoFinanceiro, ContaFinanceira, Periodo, Cotacao


class Command(BaseCommand):
    help = "Calcula e salva Valor de Mercado,  VPA, LPA, P/L, P/VP, Graham e ROE para cada papel"

    def handle(self, *args, **options):
        # Contas base
        conta_patrimonio = ContaFinanceira.objects.filter(
            nome="Patrimônio Líquido"
        ).first()
        conta_lucro = ContaFinanceira.objects.filter(
            nome="Lucro/Prejuízo do Período"
        ).first()

        if not conta_patrimonio or not conta_lucro:
            self.stderr.write("Contas Patrimônio Líquido ou Lucro não encontradas.")
            return

        # Contas para indicadores
        contas_indicadores = {}
        for nome in ["Valor de Mercado", "VPA", "LPA", "P/L", "P/VP", "Graham", "ROE"]:
            conta, _ = ContaFinanceira.objects.get_or_create(nome=nome)
            contas_indicadores[nome] = conta

        for papel in Papel.objects.all():
            # Últimos 4 períodos com lucro
            dados_lucro = (
                DadoFinanceiro.objects.filter(papel=papel, conta=conta_lucro)
                .select_related("periodo")
                .order_by("-periodo__data")[:4]
            )

            if len(dados_lucro) < 1:
                continue

            ultimo_lucro = dados_lucro[0]
            data_referencia = ultimo_lucro.periodo.data
            periodo_referencia = ultimo_lucro.periodo

            # Patrimônio do mesmo período
            patrimonio = DadoFinanceiro.objects.filter(
                papel=papel, conta=conta_patrimonio, periodo=periodo_referencia
            ).first()

            if not patrimonio:
                self.stderr.write(
                    f"[SKIP] {papel.codigo} sem patrimônio em {data_referencia}"
                )
                continue

            # Cotação antes do período
            cotacao = (
                Cotacao.objects.filter(papel=papel, data__lt=data_referencia)
                .order_by("-data")
                .first()
            )

            if not cotacao:
                self.stderr.write(
                    f"[SKIP] {papel.codigo} sem cotação antes de {data_referencia}"
                )
                continue
            # Verificar se cotação tem os campos necessários
            if cotacao.numero_total_acoes is None or cotacao.preco_fechamento is None:
                self.stderr.write(f"[SKIP] {papel.codigo} com dados incompletos na cotação.")
                continue

            try:
                numero_acoes = Decimal(cotacao.numero_total_acoes)
                preco = Decimal(cotacao.preco_fechamento)
                patrimonio_valor = Decimal(patrimonio.valor)
                lucro_valor = Decimal(ultimo_lucro.valor)
                

                valor_mercado = numero_acoes * preco
                vpa = patrimonio_valor / numero_acoes if numero_acoes else Decimal(0)
                lpa = lucro_valor / numero_acoes if numero_acoes else Decimal(0)
                pl = preco / lpa if lpa else Decimal(0)
                pvp = preco / vpa if vpa else Decimal(0)
                graham_valor = Decimal("22.5") * lpa * vpa
                graham = Decimal(sqrt(graham_valor)) if graham_valor > 0 else Decimal(0)

                # ROE com 4 períodos
                lucro_acumulado = sum([Decimal(df.valor) for df in dados_lucro])
                roe = (
                    (lucro_acumulado / patrimonio_valor) * Decimal(100)
                    if patrimonio_valor
                    else Decimal(0)
                )

                # Dicionário de valores calculados
                indicadores = {
                    "VPA": vpa,
                    "LPA": lpa,
                    "P/L": pl,
                    "P/VP": pvp,
                    "Graham": graham,
                    "ROE": roe,
                    "Valor de Mercado": valor_mercado,
                }

                for nome, valor in indicadores.items():
                    conta = contas_indicadores[nome]
                    dado, created = DadoFinanceiro.objects.update_or_create(
                        papel=papel,
                        conta=conta,
                        periodo=periodo_referencia,
                        defaults={"valor": valor},
                    )

                self.stdout.write(
                self.style.SUCCESS(
                    f"{papel.codigo} [{data_referencia}]: "
                    f"VPA={vpa:.2f}, LPA={lpa:.2f}, P/L={pl:.2f}, "
                    f"P/VP={pvp:.2f}, Graham={graham:.2f}, ROE={roe:.2f}% | "
                    f"Preço/ações de {cotacao.data}"
                )
            )

            except (InvalidOperation, DivisionByZero) as e:
                self.stderr.write(f"[ERRO] {papel.codigo} falha: {e}")
