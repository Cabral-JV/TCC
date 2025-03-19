from django import forms
from .models import File


class UploadArquivoForm(forms.ModelForm):
    class Meta:
        model = File
        arquivo = forms.FileField()
