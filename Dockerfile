# Usa uma imagem base leve e segura
FROM python:3.13-alpine3.21

# Evita problemas de cache e define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema antes de copiar o código
RUN apk add --no-cache \
    build-base \
    libpq \
    postgresql-dev \
    && python3 -m ensurepip \
    && pip install --upgrade pip

# Copia apenas o necessário para instalar as dependências
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Expõe a porta padrão do Django
EXPOSE 8000

# Comando para iniciar o Gunicorn (ajuste para seu projeto)
CMD ["gunicorn", "investwallet.wsgi:application", "--bind", "0.0.0.0:8000"]
