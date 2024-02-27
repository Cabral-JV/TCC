# Fundamentus Scraper

Este é um script em Python desenvolvido para automatizar o processo de download e extração de informações financeiras de empresas listadas no site Fundamentus. O script utiliza o Selenium para interagir com a interface do site, baixar arquivos ZIP contendo informações financeiras e extrair os dados relevantes.

## Autor

- **Nome:** [João Victor Cordeiro Cabral]
- **GitHub** [Cabral-JV]

## Coautor

- **Nome:** [Gabriel de Oliveira Castro]
- **GitHub** [gabrielocastro]

## Funcionalidades

- **Download Automático:** O script realiza o download automático dos dados financeiros de empresas específicas, utilizando o Selenium para interagir com o site Fundamentus.

- **Extração e Renomeação:** Os arquivos ZIP baixados são automaticamente extraídos e renomeados para facilitar a organização dos dados. Os arquivos são movidos para uma pasta específica.

- **Gestão de Erros:** O script gerencia erros durante o processo, registrando os papeis que apresentaram problemas em um arquivo de log.

## Requisitos

- Python 3.x
- Selenium
- ChromeDriver (o caminho do executável deve ser configurado no script)

## Configuração

1. Instale as dependências necessárias executando `pip install -r requirements.txt`.
2. Certifique-se de ter o ChromeDriver instalado e atualizado. O caminho do executável deve ser configurado no script.

## Utilização

### Passo 1: Preparação

Certifique-se de que você tenha os seguintes arquivos no diretório atual:

- `fundamentus_scraper.py`
- `lista_papeis.txt`

### Passo 2: Preparação dos Papeis

Edite o arquivo `lista_papeis.txt` e insira os papeis que deseja processar. Cada papel deve ser colocado em uma nova linha. Exemplo:

```txt
AALR3
ABCB3
ABCB4
ABEV3
```

Salve o arquivo após inserir os papeis.

### Passo 3: Execução do Script

Execute o seguinte comando no terminal:

```bash
python fundamentus_scraper.py
```

O script será executado e irá extrair os dados do site Fundamentus para os papeis especificados no arquivo `lista_papeis.txt`. Os dados serão baixados em formato ZIP, extraídos e renomeados para a pasta `balancos`. Os papeis que falharem no processo de extração serão armazenados no arquivo `lista_papeis_error.txt`.

### Passo 4: Verificação dos Resultados

Após a execução do script, verifique a pasta `balancos` para encontrar os arquivos extraídos e renomeados corretamente. Verifique também o arquivo `lista_papeis_error.txt` para identificar os papeis que falharam no processo de extração.

## Testes Automatizados

Este projeto inclui testes automatizados para verificar o correto funcionamento das funções. Para executar os testes, utilize o seguinte comando no terminal:

```bash
python fundamentus_scraper.py --test
```

Os testes serão executados, e os resultados serão exibidos no terminal.
