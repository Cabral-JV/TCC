# Usa a imagem oficial do Python
FROM python:3.13-alpine3.21

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY requirements.txt ./

# Instala as dependências
RUN apk add --no-cache build-base libpq postgresql-dev

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Expõe a porta padrão do Django
EXPOSE 8000

# Comando padrão para iniciar o servidor
CMD ["gunicorn", "investwallet.wsgi:application", "--bind", "0.0.0.0:8000"]