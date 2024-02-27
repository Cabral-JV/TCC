import os
import shutil
import zipfile
import time
import unittest
import sys
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constantes
URL_BASE = "https://www.fundamentus.com.br/balancos.php?papel={papel}&interface=mobile"
DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "Fundamentus_Scraper", "baixados")
BALANCOS_FOLDER = os.path.join(os.getcwd(), "Fundamentus_Scraper", "balancos")
PAPEIS_SUCCESS_FILE = os.path.join(
    os.getcwd(), "Fundamentus_Scraper", "lista_papeis_success.txt"
)
PAPEIS_ERROR_FILE = os.path.join(
    os.getcwd(), "Fundamentus_Scraper", "lista_papeis_error.txt"
)
PAPEIS_FILE = os.path.join(os.getcwd(), "Fundamentus_Scraper", "lista_papeis.txt")


def criar_pasta_se_nao_existir(caminho_pasta):
    """
    Cria uma pasta se ela não existir.

    Args:
        caminho_pasta (str): O caminho da pasta a ser criada.
    """
    if not os.path.exists(caminho_pasta):
        os.makedirs(caminho_pasta)


def ler_papeis_de_arquivo(caminho_arquivo_papeis):
    """
    Lê os papéis de um arquivo de texto.

    Args:
        caminho_arquivo_papeis (str): O caminho do arquivo de texto contendo os papéis.

    Returns:
        list: Uma lista de papéis lidos do arquivo.
    """
    with open(caminho_arquivo_papeis, "r") as arquivo:
        papeis = [linha.strip() for linha in arquivo if linha.strip()]
    return papeis


def extrair_dados_fundamentus(papeis):
    """
    Extrai os dados do site Fundamentus para os papéis especificados.

    Args:
        papeis (list): Uma lista de papéis a serem extraídos.

    Returns:
        tuple: Uma tupla contendo duas listas, uma de papéis que falharam no processo de extração e outra de papéis com sucesso.
    """
    papeis_error = []
    papeis_success = []

    # Carrega a lista de papéis de sucesso
    if os.path.exists(PAPEIS_SUCCESS_FILE):
        with open(PAPEIS_SUCCESS_FILE, "r") as arquivo:
            papeis_success = [linha.strip() for linha in arquivo if linha.strip()]

    # Carrega a lista de papéis com erro
    if os.path.exists(PAPEIS_ERROR_FILE):
        with open(PAPEIS_ERROR_FILE, "r") as arquivo:
            papeis_error = [linha.strip() for linha in arquivo if linha.strip()]

    # Configuração do Selenium
    chrome_options = webdriver.ChromeOptions()

    # Define o diretório de downloads personalizado
    prefs = {
        "download.default_directory": os.path.abspath(DOWNLOADS_FOLDER),
        "download.prompt_for_download": False,
        "download.extensions_to_open": "",
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Configuração do caminho do ChromeDriver
    chrome_options.add_argument("webdriver.chrome.driver=chromedriver.exe")

    # Inicializa o driver do Selenium
    with webdriver.Chrome(options=chrome_options) as driver:
        for papel in papeis:
            # Verifica se o papel está na lista de sucesso ou de erro
            if papel in papeis_success:
                print(f"O papel {papel} já foi baixado e está na lista de sucesso.")
                continue
            elif papel in papeis_error:
                print(
                    f"O papel {papel} está na lista de erro. Tentando baixar novamente..."
                )
            else:
                print(f"Baixando o papel {papel}...")

            papel_url = URL_BASE.format(papel=papel)
            driver.get(papel_url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "a.bt-baixar"))
                )

                botao_download = driver.find_element(By.CSS_SELECTOR, "a.bt-baixar")

                arquivo_destino = os.path.join(DOWNLOADS_FOLDER, f"{papel}.zip")
                botao_download.click()
                time.sleep(10)

                arquivo_baixado = max(
                    [
                        os.path.join(DOWNLOADS_FOLDER, f)
                        for f in os.listdir(DOWNLOADS_FOLDER)
                    ],
                    key=os.path.getctime,
                )
                novo_nome_arquivo = os.path.join(DOWNLOADS_FOLDER, f"{papel}.zip")
                os.rename(arquivo_baixado, novo_nome_arquivo)

                # Tempo de espera adicional para garantir que a renomeação seja concluída
                time.sleep(5)

                papeis_success.append(papel)
                print(f"Arquivo {novo_nome_arquivo} baixado e renomeado com sucesso!")
                armazenar_papeis_success(papeis_success)
            except:
                papeis_error.append(papel)
                print(f"Erro ao baixar o arquivo do papel {papel}")
                armazenar_papeis_com_erros(papeis_error)
                continue

    return papeis_error, papeis_success


def extrair_e_renomear_arquivos_zip(pasta_origem, pasta_destino):
    """
    Extrai e renomeia os arquivos ZIP para a pasta de destino.

    Args:
        pasta_origem (str): O caminho da pasta de origem dos arquivos ZIP.
        pasta_destino (str): O caminho da pasta de destino dos arquivos extraídos.

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
        pasta_origem (str): O caminho da pasta de origem dos arquivos renomeados.
        pasta_destino (str): O caminho da pasta de destino dos arquivos renomeados.
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
            except:
                print(f"Erro ao mover o arquivo {caminho_arquivo}")


def armazenar_papeis_com_erros(papeis_error):
    """
    Armazena os papéis com erros em um arquivo.

    Args:
        papeis_error (list): Uma lista de papéis com erros.
    """
    with open(PAPEIS_ERROR_FILE, "a") as arquivo:
        for papel in papeis_error:
            arquivo.write(f"{papel}\n")


def armazenar_papeis_success(papeis_success):
    """
    Armazena os papéis com sucesso em um arquivo.

    Args:
        papeis_success (list): Uma lista de papéis com sucesso.
    """
    with open(PAPEIS_SUCCESS_FILE, "a") as arquivo:
        for papel in papeis_success:
            arquivo.write(f"{papel}\n")


def processar_lote_de_papeis(papeis):
    """
    Processa um lote de papéis.

    Args:
        papeis (list): Uma lista de papéis a serem processados.
    """
    # Cria as pastas se não existirem
    criar_pasta_se_nao_existir(DOWNLOADS_FOLDER)
    criar_pasta_se_nao_existir(BALANCOS_FOLDER)

    pasta_baixados = DOWNLOADS_FOLDER
    papeis_error, papeis_success = extrair_dados_fundamentus(papeis)

    if papeis_error:
        extrair_e_renomear_arquivos_zip(DOWNLOADS_FOLDER, DOWNLOADS_FOLDER)
        pasta_balancos = BALANCOS_FOLDER
        mover_arquivos_renomeados(DOWNLOADS_FOLDER, BALANCOS_FOLDER)

        # Verifica se todos os papéis estão presentes na pasta balancos
        for papel in papeis_success:
            if not os.path.exists(os.path.join(pasta_balancos, f"{papel}.xls")):
                print(f"Baixando novamente o papel {papel}!")
                papeis_error.append(papel)
                papeis_success.remove(papel)
                break

    if papeis_error:
        # Atualiza os arquivos de lista de papéis com erro e sucesso
        armazenar_papeis_com_erros(papeis_error)
        armazenar_papeis_success(papeis_success)

        # Tenta baixar novamente os papéis com erro
        extrair_dados_fundamentus(papeis_error)

    print("Processamento concluído!")


class TestFundamentusScraper(unittest.TestCase):
    def test_extrair_dados_fundamentus(self):
        papeis = ["AALR3", "ABCB3", "ABCB4", "ABEV3"]
        papeis_error, papeis_success = extrair_dados_fundamentus(papeis)
        self.assertEqual(len(papeis_error), 0)

    def test_extrair_e_renomear_arquivos_zip(self):
        pasta_origem = DOWNLOADS_FOLDER
        pasta_destino = DOWNLOADS_FOLDER
        extrair_e_renomear_arquivos_zip(pasta_origem, pasta_destino)
        arquivos_renomeados = os.listdir(pasta_destino)
        self.assertGreater(len(arquivos_renomeados), 0)

    def test_mover_arquivos_renomeados(self):
        pasta_origem = DOWNLOADS_FOLDER
        pasta_destino = BALANCOS_FOLDER
        extrair_e_renomear_arquivos_zip(pasta_origem, pasta_origem)
        mover_arquivos_renomeados(pasta_origem, pasta_destino)
        arquivos_movidos = os.listdir(pasta_destino)
        self.assertGreater(len(arquivos_movidos), 0)

    def test_processar_lote_de_papeis(self):
        papeis = ["AALR3", "ABCB3", "ABCB4", "ABEV3"]
        processar_lote_de_papeis(papeis)
        pasta_balancos = BALANCOS_FOLDER
        arquivos_movidos = os.listdir(pasta_balancos)
        self.assertGreater(len(arquivos_movidos), 0)
        self.assertTrue(os.path.exists(PAPEIS_ERROR_FILE))
        self.assertTrue(os.path.exists(PAPEIS_SUCCESS_FILE))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        unittest.main(argv=sys.argv[:1])
    else:
        processar_lote_de_papeis(ler_papeis_de_arquivo(PAPEIS_FILE))
