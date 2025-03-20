from django.db import models


class Empresa(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nome} ({self.ticker})"


class Papel(models.Model):
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="papeis"
    )
    codigo = models.CharField(max_length=10, unique=True, db_index=True)  # Ex: "BIDI11"
    ticker = models.CharField(max_length=15, unique=True, db_index=True)

    def __str__(self):
        return f"{self.codigo} ({self.empresa.nome})"


class ContaFinanceira(models.Model):
    nome = models.CharField(max_length=200, unique=True, db_index=True)

    def __str__(self):
        return self.nome


class Periodo(models.Model):
    TIPO_CHOICES = (
        ("TR", "Trimestral"),
        ("AN", "Anual"),
    )
    nome = models.CharField(
        max_length=50, help_text="Exemplo: 'Q1 2021' ou '2021'", unique=True
    )
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES)
    inicio = models.DateField(help_text="Data de início do período", db_index=True)
    fim = models.DateField(help_text="Data de término do período")

    def __str__(self):
        return self.nome


class DadoFinanceiro(models.Model):
    papel = models.ForeignKey(
        Papel, on_delete=models.CASCADE, related_name="dados_financeiros"
    )
    conta = models.ForeignKey(
        ContaFinanceira, on_delete=models.CASCADE, related_name="dados_financeiros"
    )
    periodo = models.ForeignKey(
        Periodo, on_delete=models.CASCADE, related_name="dados_financeiros"
    )
    valor = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("papel", "conta", "periodo")
        ordering = ["periodo__inicio"]

    def __str__(self):
        return f"{self.papel.codigo} - {self.conta.nome} ({self.periodo.nome}): {self.valor}"
