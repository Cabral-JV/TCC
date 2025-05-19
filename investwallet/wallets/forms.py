from django import forms
from .models import CarteiraRecomendada, CarteiraUsuario


class UploadArquivoForm(forms.Form):
    arquivo = forms.FileField()


class CarteiraForm(forms.Form):
    papeis_lista = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Digite os códigos das ações separados por vírgula.",
        label="Lista de Papéis"
    )

    def clean_papeis_lista(self):
        data = self.cleaned_data["papeis_lista"]
        codigos = [codigo.strip().upper() for codigo in data.split(",") if codigo.strip()]
        if not codigos:
            raise forms.ValidationError("Você precisa informar pelo menos um código de ação.")
        return codigos



class CarteiraUsuarioForm(forms.ModelForm):
    papeis_lista = forms.CharField(
        label="Papéis (um por linha)",
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Digite um código por linha. Exemplo:\nPETR4\nVALE3\nITUB4",
        required=False,
    )

    class Meta:
        model = CarteiraUsuario
        fields = ["nome"]

    def clean_papeis_lista(self):
        data = self.cleaned_data.get("papeis_lista", "")
        codigos = [codigo.strip().upper() for codigo in data.splitlines() if codigo.strip()]
        return codigos
