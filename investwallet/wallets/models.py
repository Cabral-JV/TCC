from django.db import models

from django.db import models

class Empresa(models.Model):
    nome = models.CharField(max_length=100)
    ticker = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.nome} ({self.ticker})"

class ContaFinanceira(models.Model):
    nome = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nome

class Periodo(models.Model):
    TIPO_CHOICES = (
        ('TR', 'Trimestral'),
        ('AN', 'Anual'),
    )
    # Por exemplo: "Q1 2021", "2021"
    nome = models.CharField(max_length=50, help_text="Identificação do período, ex: 'Q1 2021' ou '2021'")
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES)
    inicio = models.DateField(help_text="Data de início do período")
    fim = models.DateField(help_text="Data de término do período")

    def __str__(self):
        return self.nome

class DadoFinanceiro(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    conta = models.ForeignKey(ContaFinanceira, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        unique_together = ('empresa', 'conta', 'periodo')
        ordering = ['periodo__inicio']

    def __str__(self):
        return f"{self.empresa.ticker} - {self.conta.nome} ({self.periodo.nome}): {self.valor}"

