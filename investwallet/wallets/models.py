from django.db import models
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from django.utils import timezone

User = get_user_model()


class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    setor = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.setor})"


class Papel(models.Model):
    codigo = models.CharField(max_length=10, unique=True)  # Ex: PETR4
    ticker = models.CharField(max_length=15, unique=True)  # Ex: PETR4.SA
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="papeis"
    )

    def __str__(self):
        return f"{self.codigo} ({self.empresa.nome})"


class ContaFinanceira(models.Model):
    nome = models.CharField(max_length=200, unique=True, db_index=True)

    def __str__(self):
        return self.nome


class Periodo(models.Model):
    data = models.DateField(unique=True)

    def __str__(self):
        return self.data.strftime("%d/%m/%Y")


class DadoFinanceiro(models.Model):
    papel = models.ForeignKey(
        Papel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="dados_financeiros",
    )
    conta = models.ForeignKey(ContaFinanceira, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ("papel", "conta", "periodo")

    def __str__(self):
        return f"{self.papel} - {self.conta} ({self.periodo}): {self.valor}"


class Cotacao(models.Model):
    papel = models.ForeignKey(
        Papel, on_delete=models.CASCADE, related_name="cotacoes", null=True, blank=True
    )
    data = models.DateField()
    preco_fechamento = models.DecimalField(max_digits=10, decimal_places=2)
    preco_abertura = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.DecimalField(max_digits=15, decimal_places=2)
    numero_total_acoes = models.DecimalField(
        max_digits=15, decimal_places=2, default=0.00
    )

    class Meta:
        unique_together = ("papel", "data")

    def __str__(self):
        return f"{self.papel.ticker} - {self.data}: {self.preco_fechamento}"


class CarteiraRecomendada(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    data_criacao = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nome

    def valor_total(self):
        return sum(pcr.valor_total() for pcr in self.papeis.all())

    def save(self, *args, **kwargs):
        if not self.pk and CarteiraRecomendada.objects.exists():
            raise ValueError("Já existe uma carteira recomendada cadastrada.")
        self.nome = "Carteira Recomendada"
        super().save(*args, **kwargs)


class PapelCarteiraRecomendada(models.Model):
    carteira = models.ForeignKey(
        CarteiraRecomendada, on_delete=models.CASCADE, related_name="papeis"
    )
    papel = models.ForeignKey("Papel", on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(
        default=1
    )  # Sempre 1, como regra de negócio

    class Meta:
        unique_together = ("carteira", "papel")

    def preco_atual(self):
        cotacao = Cotacao.objects.filter(papel=self.papel).order_by("-data").first()
        return cotacao.preco_fechamento if cotacao else 0

    def valor_total(self):
        return self.quantidade * self.preco_atual()


class CarteiraUsuario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carteiras")
    nome = models.CharField(max_length=255)
    data_criacao = models.DateField(auto_now_add=True)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # NOVO

    class Meta:
        unique_together = ("usuario", "nome")

    def __str__(self):
        return f"{self.nome} ({self.usuario.username})"

    def valor_total(self):
        return sum(p.valor_total() for p in self.papeis.all())

    def saldo_disponivel(self):
        return self.saldo  # Agora retorna direto o campo saldo


class PapelCarteiraUsuario(models.Model):
    carteira = models.ForeignKey(
        CarteiraUsuario, on_delete=models.CASCADE, related_name="papeis"
    )
    papel = models.ForeignKey(Papel, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()

    class Meta:
        unique_together = ("carteira", "papel")

    def preco_atual(self):
        agora = timezone.localtime()
        cotacao = Cotacao.objects.filter(papel=self.papel).order_by("-data").first()
        if not cotacao:
            return 0
        return (
            cotacao.preco_abertura
            if 10 <= agora.hour < 18
            else cotacao.preco_fechamento
        )

    def valor_total(self):
        return self.quantidade * self.preco_atual()


class Movimentacao(models.Model):
    TIPOS = [("COMPRA", "Compra"), ("VENDA", "Venda")]

    carteira_usuario = models.ForeignKey(
        CarteiraUsuario, on_delete=models.CASCADE, related_name="movimentacoes", null=True, blank=True
    )
    carteira_recomendada = models.ForeignKey(
        CarteiraRecomendada, on_delete=models.CASCADE, related_name="movimentacoes", null=True, blank=True
    )
    papel = models.ForeignKey(Papel, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=6, choices=TIPOS)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"

    def __str__(self):
        return f"{self.tipo} - {self.papel.codigo} ({self.quantidade})"

    def valor_total(self):
        return self.quantidade * self.preco_unitario

    def preco_atual(self):
        agora = timezone.localtime()
        cotacao = Cotacao.objects.filter(papel=self.papel).order_by("-data").first()
        if not cotacao:
            return 0
        return cotacao.preco_abertura if 10 <= agora.hour < 18 else cotacao.preco_fechamento

    def variacao(self):
        return self.preco_atual() - self.preco_unitario
