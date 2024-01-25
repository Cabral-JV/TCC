import os
import shutil
import zipfile
import time
import unittest
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL base do site que contém os links para download
URL_BASE = "https://www.fundamentus.com.br/balancos.php?papel={papel}&interface=mobile"


def criar_pasta_se_nao_existir(caminho_pasta):
    """
    Cria uma pasta se ela não existir.

    Args:
        caminho_pasta (str): Caminho da pasta a ser criada.
    """
    if not os.path.exists(caminho_pasta):
        os.makedirs(caminho_pasta)


def ler_papeis_de_arquivo(caminho_arquivo_papeis):
    """
    Lê os papeis de um arquivo de texto.

    Args:
        caminho_arquivo (str): Caminho do arquivo de texto contendo os papeis.

    Returns:
        list: Lista de papeis lidos do arquivo.
    """
    with open(caminho_arquivo_papeis, "r") as arquivo:
        papeis = [linha.strip() for linha in arquivo if linha.strip()]
    return papeis


def extrair_dados_fundamentus(papeis):
    """
    Extrai os dados do site Fundamentus para os papeis especificados.

    Args:
        papeis (list): Lista de papeis a serem extraídos.

    Returns:
        list: Lista de papeis que falharam no processo de extração.
    """
    papeis_error = []

    # Cria as pastas se não existirem
    pasta_destino_baixados = os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados")
    criar_pasta_se_nao_existir(pasta_destino_baixados)

    # Configuração do Selenium
    chrome_options = webdriver.ChromeOptions()

    # Define o diretório de downloads personalizado
    prefs = {
        "download.default_directory": os.path.abspath(pasta_destino_baixados),
        "download.prompt_for_download": False,
        "download.extensions_to_open": "",
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Configuração do caminho do ChromeDriver
    chrome_options.add_argument("webdriver.chrome.driver=chromedriver.exe")

    # Inicializa o driver do Selenium
    with webdriver.Chrome(options=chrome_options) as driver:
        for papel in papeis:
            papel_url = URL_BASE.format(papel=papel)
            driver.get(papel_url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "a.bt-baixar"))
                )

                botao_download = driver.find_element(By.CSS_SELECTOR, "a.bt-baixar")

                arquivo_destino = os.path.join(pasta_destino_baixados, f"{papel}.zip")
                botao_download.click()

                time.sleep(10)

                arquivo_baixado = max(
                    [os.path.join(pasta_destino_baixados, f) for f in os.listdir(pasta_destino_baixados)],
                    key=os.path.getctime,
                )
                novo_nome_arquivo = f"{papel}.zip"
                caminho_destino = os.path.join(pasta_destino_baixados, novo_nome_arquivo)
                os.rename(arquivo_baixado, caminho_destino)

                # Tempo de espera adicional para garantir que a renomeação seja concluída
                time.sleep(10)

                print(f"Arquivo {novo_nome_arquivo} baixado e renomeado com sucesso!")
            except Exception as e:
                papeis_error.append(papel)
                print(f"Erro ao baixar o arquivo do papel {papel}: {str(e)}")
                continue

    # Após o loop, adiciona os papeis com erro ao arquivo lista_papeis_error.txt
    armazenar_papeis_com_erros(papeis_error)

    return papeis_error


def extrair_e_renomear_arquivos_zip(pasta_origem, pasta_destino):
    """
    Extrai e renomeia os arquivos ZIP para a pasta de destino.

    Args:
        pasta_origem (str): Caminho da pasta de origem dos arquivos ZIP.
        pasta_destino (str): Caminho da pasta de destino dos arquivos extraídos.

    Raises:
        zipfile.BadZipFile: Se ocorrer um erro ao extrair um arquivo ZIP inválido.
    """
    for nome_arquivo in os.listdir(pasta_origem):
        caminho_arquivo_zip = os.path.join(pasta_origem, nome_arquivo)

        if nome_arquivo.endswith(".zip"):
            try:
                with zipfile.ZipFile(caminho_arquivo_zip, "r") as zip_ref:
                    zip_ref.extractall(pasta_destino)

                nome_papel = os.path.splitext(nome_arquivo)[0]

                caminho_arquivo_xls = os.path.join(pasta_destino, "balanco.xls")
                novo_nome_arquivo = os.path.join(pasta_destino, f"{nome_papel}.xls")
                os.rename(caminho_arquivo_xls, novo_nome_arquivo)

                print(f"Arquivo {novo_nome_arquivo} extraído e renomeado com sucesso!")
            except zipfile.BadZipFile:
                print(f'O arquivo "{caminho_arquivo_zip}" não é um arquivo zip válido.')


def mover_arquivos_renomeados(pasta_origem, pasta_destino):
    """
    Move os arquivos renomeados para a pasta de destino.

    Args:
        pasta_origem (str): Caminho da pasta de origem dos arquivos renomeados.
        pasta_destino (str): Caminho da pasta de destino dos arquivos renomeados.
    """
    for nome_arquivo in os.listdir(pasta_origem):
        if nome_arquivo.endswith(".xls"):
            caminho_arquivo = os.path.join(pasta_origem, nome_arquivo)
            novo_nome_arquivo = os.path.join(pasta_destino, nome_arquivo)
            try:
                shutil.move(caminho_arquivo, novo_nome_arquivo)
                print(f"Arquivo {novo_nome_arquivo} movido para a pasta balancos")
            except FileNotFoundError:
                print(f"Arquivo {caminho_arquivo} não encontrado.")
            except Exception as e:
                print(f"Erro ao mover o arquivo {caminho_arquivo}: {str(e)}")


def armazenar_papeis_com_erros(papeis_error):
    """
    Armazena os papeis com erros em um arquivo.

    Args:
        papeis_error (list): Lista de papeis com erros.
    """
    caminho_arquivo_papeis_error = "lista_papeis_error.txt"
    with open(caminho_arquivo_papeis_error, "w") as arquivo:
        for papel in papeis_error:
            arquivo.write(f"{papel}\n")


def processar_lote_de_papeis(papeis):
    """
    Processa um lote de papeis.

    Args:
        papeis (list): Lista de papeis a serem processados.
    """
    # Cria as pastas se não existirem
    criar_pasta_se_nao_existir(os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados"))
    criar_pasta_se_nao_existir(os.path.join(os.getcwd(), "Fundamentus_Scraper", "balancos"))

    pasta_baixados = os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados")
    papeis_error = extrair_dados_fundamentus(papeis)

    if papeis_error:
        extrair_e_renomear_arquivos_zip(pasta_baixados, pasta_baixados)
        pasta_balancos = os.path.join(os.getcwd(), "Fundamentus_Scraper", "balancos")
        mover_arquivos_renomeados(pasta_baixados, pasta_balancos)

    if papeis_error:
        armazenar_papeis_com_erros(papeis_error)
    print("Processamento concluído!")


class TestFundamentusScraper(unittest.TestCase):
    def test_extrair_dados_fundamentus(self):
        papeis = ["AALR3", "ABCB3", "ABCB4", "ABEV3"]
        papeis_error = extrair_dados_fundamentus(papeis)
        self.assertEqual(len(papeis_error), 0)

    def test_extrair_e_renomear_arquivos_zip(self):
        pasta_origem = os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados")
        pasta_destino = os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados")
        extrair_e_renomear_arquivos_zip(pasta_origem, pasta_destino)
        arquivos_renomeados = os.listdir(pasta_destino)
        self.assertGreater(len(arquivos_renomeados), 0)

    def test_mover_arquivos_renomeados(self):
        pasta_origem = os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados")
        pasta_destino = os.path.join(os.getcwd(), "Fundamentus_Scraper", "balancos")
        extrair_e_renomear_arquivos_zip(pasta_origem, pasta_origem)
        mover_arquivos_renomeados(pasta_origem, pasta_destino)
        arquivos_movidos = os.listdir(pasta_destino)
        self.assertGreater(len(arquivos_movidos), 0)

    def test_processar_lote_de_papeis(self):
        papeis = ["AALR3", "ABCB3", "ABCB4", "ABEV3"]
        processar_lote_de_papeis(papeis)
        pasta_balancos = os.path.join(os.getcwd(), "Fundamentus_Scraper", "balancos")
        arquivos_movidos = os.listdir(pasta_balancos)
        self.assertGreater(len(arquivos_movidos), 0)
        self.assertTrue(os.path.exists("lista_papeis_error.txt"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        unittest.main(argv=sys.argv[:1])
    else:
        processar_lote_de_papeis(
            ler_papeis_de_arquivo("Fundamentus_Scraper\lista_papeis.txt")
        )
