"""
extractor.py
Módulo de extração de texto a partir de arquivos PDF e imagens.

Dependências:
    pip install pdfminer.six pytesseract Pillow
    sudo apt install tesseract-ocr  # ou equivalente no seu sistema
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Constantes                                                                   #
# --------------------------------------------------------------------------- #

EXTENSOES_PDF = {".pdf"}
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png"}
EXTENSOES_SUPORTADAS = EXTENSOES_PDF | EXTENSOES_IMAGEM


# --------------------------------------------------------------------------- #
# Extratores internos                                                          #
# --------------------------------------------------------------------------- #

def _extrair_de_pdf(caminho: str) -> str:
    """Extrai texto de um arquivo PDF usando pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text
    except ImportError as exc:
        raise ImportError(
            "pdfminer.six não está instalado. Execute: pip install pdfminer.six"
        ) from exc

    try:
        texto = extract_text(caminho)
    except Exception as exc:
        raise RuntimeError(f"Erro ao extrair texto do PDF '{caminho}': {exc}") from exc

    if not texto or not texto.strip():
        raise ValueError(f"O PDF '{caminho}' não contém texto legível ou está vazio.")

    return texto.strip()


def _extrair_de_imagem(caminho: str) -> str:
    """Extrai texto de uma imagem usando pytesseract (OCR)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "pytesseract ou Pillow não estão instalados. "
            "Execute: pip install pytesseract Pillow"
        ) from exc

    try:
        imagem = Image.open(caminho)
        texto = pytesseract.image_to_string(imagem, lang="por+eng")
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo de imagem não encontrado: '{caminho}'")
    except Exception as exc:
        raise RuntimeError(f"Erro ao extrair texto da imagem '{caminho}': {exc}") from exc

    if not texto or not texto.strip():
        raise ValueError(f"Nenhum texto detectado na imagem '{caminho}'.")

    return texto.strip()


# --------------------------------------------------------------------------- #
# Função pública                                                               #
# --------------------------------------------------------------------------- #

def extrair_texto_arquivo(caminho_arquivo: str) -> str:
    """
    Extrai texto de um arquivo PDF ou imagem (jpg, jpeg, png).

    A detecção do tipo é feita automaticamente pelo sufixo do arquivo.

    Parâmetros:
        caminho_arquivo (str): Caminho para o arquivo de entrada.

    Retorna:
        str: Texto extraído do arquivo.

    Lança:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se a extensão não for suportada ou o arquivo estiver vazio.
        RuntimeError: Em caso de falha durante a extração.
        ImportError: Se a dependência necessária não estiver instalada.
    """
    caminho = Path(caminho_arquivo)

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: '{caminho_arquivo}'")

    if not caminho.is_file():
        raise ValueError(f"O caminho fornecido não é um arquivo: '{caminho_arquivo}'")

    extensao = caminho.suffix.lower()

    if extensao not in EXTENSOES_SUPORTADAS:
        raise ValueError(
            f"Tipo de arquivo não suportado: '{extensao}'. "
            f"Extensões aceitas: {', '.join(sorted(EXTENSOES_SUPORTADAS))}"
        )

    if extensao in EXTENSOES_PDF:
        return _extrair_de_pdf(caminho_arquivo)

    if extensao in EXTENSOES_IMAGEM:
        return _extrair_de_imagem(caminho_arquivo)


# Mantém compatibilidade com crm_pipeline.py que importa extrair_texto_pdf
def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Atalho para extração de PDFs. Use extrair_texto_arquivo() para suporte completo."""
    return extrair_texto_arquivo(caminho_pdf)


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                               #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python extractor.py <caminho_do_arquivo>")
        print("Exemplo: python extractor.py documento.pdf")
        print("         python extractor.py formulario.png")
        sys.exit(1)

    arquivo = sys.argv[1]

    try:
        texto = extrair_texto_arquivo(arquivo)
        print(f"✔ Texto extraído com sucesso ({len(texto)} caracteres):\n")
        print(texto[:500] + ("..." if len(texto) > 500 else ""))
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERRO] {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"[ERRO DE EXTRAÇÃO] {e}")
        sys.exit(1)
    except ImportError as e:
        print(f"[ERRO DE DEPENDÊNCIA] {e}")
        sys.exit(1)
