"""
crm_pipeline.py
Pipeline completo de processamento de CRM a partir de um ou mais arquivos.

Fluxo:
    Arquivos (PDF / imagem) → extractor.py → texto consolidado
        → crm_parser.py → crm_validator.py → terminal
"""

import sys

from extractor import extrair_texto_arquivo
from crm_parser import extrair_dados_crm
from crm_validator import validar_crm


# --------------------------------------------------------------------------- #
# Exibição                                                                     #
# --------------------------------------------------------------------------- #

LINHA = "─" * 43

def _exibir_arquivos(sucessos: list[str], falhas: list[tuple[str, str]]) -> None:
    print(f"\n┌{LINHA}┐")
    print("│           ARQUIVOS PROCESSADOS            │")
    print(f"└{LINHA}┘")
    for caminho in sucessos:
        print(f"  ✔  {caminho}")
    for caminho, motivo in falhas:
        print(f"  ✘  {caminho}  →  {motivo}")


def _exibir_texto_consolidado(texto: str, limite: int = 400) -> None:
    print(f"\n┌{LINHA}┐")
    print("│         TEXTO CONSOLIDADO (resumo)        │")
    print(f"└{LINHA}┘")
    print(f"  Total de caracteres: {len(texto)}\n")
    resumo = texto[:limite].replace("\n", " ")
    sufixo = "..." if len(texto) > limite else ""
    print(f"  {resumo}{sufixo}")


def _exibir_dados(dados: dict) -> None:
    print(f"\n┌{LINHA}┐")
    print("│             DADOS EXTRAÍDOS               │")
    print(f"└{LINHA}┘")
    for campo, valor in dados.items():
        print(f"  {campo:<22} : {valor}")


def _exibir_resultado(resultado: dict) -> None:
    status = resultado["status"]
    erros  = resultado["erros"]
    simbolo = "✔" if status == "valido" else "✘"

    print(f"\n┌{LINHA}┐")
    print("│          RESULTADO DA VALIDAÇÃO           │")
    print(f"└{LINHA}┘")
    print(f"  Status : {simbolo}  {status.upper()}")

    if erros:
        print(f"\n  Erros encontrados ({len(erros)}):")
        for erro in erros:
            print(f"    • {erro}")
    else:
        print("\n  Nenhum erro encontrado. Dados prontos para uso.")


# --------------------------------------------------------------------------- #
# Extração de múltiplos arquivos                                               #
# --------------------------------------------------------------------------- #

def _extrair_textos(caminhos: list[str]) -> tuple[str, list[str], list[tuple[str, str]]]:
    """
    Tenta extrair texto de cada arquivo da lista.

    Retorna:
        texto_consolidado (str): Todos os textos extraídos concatenados.
        sucessos (list[str]): Caminhos processados com êxito.
        falhas (list[tuple[str, str]]): Pares (caminho, mensagem de erro).
    """
    partes: list[str] = []
    sucessos: list[str] = []
    falhas: list[tuple[str, str]] = []

    for caminho in caminhos:
        try:
            texto = extrair_texto_arquivo(caminho)
            partes.append(texto)
            sucessos.append(caminho)
            print(f"  ✔ Extraído: {caminho}  ({len(texto)} caracteres)")
        except FileNotFoundError:
            motivo = "arquivo não encontrado"
            falhas.append((caminho, motivo))
            print(f"  ✘ Ignorado: {caminho}  →  {motivo}")
        except (ValueError, RuntimeError, ImportError) as exc:
            motivo = str(exc)
            falhas.append((caminho, motivo))
            print(f"  ✘ Ignorado: {caminho}  →  {motivo}")

    texto_consolidado = "\n\n".join(partes)
    return texto_consolidado, sucessos, falhas


# --------------------------------------------------------------------------- #
# Pipeline                                                                     #
# --------------------------------------------------------------------------- #

def executar_pipeline(caminhos_arquivos: list[str]) -> dict:
    """
    Executa o pipeline completo para um ou mais arquivos.

    Parâmetros:
        caminhos_arquivos (list[str]): Lista de caminhos de arquivos (PDF ou imagem).

    Retorna:
        dict com:
            - sucessos  (list[str]): Arquivos processados com êxito.
            - falhas    (list[tuple]): Arquivos que falharam e motivo.
            - texto     (str): Texto consolidado de todos os arquivos.
            - dados     (dict): Campos extraídos pelo parser.
            - resultado (dict): Status e erros do validador.

    Lança:
        ValueError: Se nenhum arquivo puder ser processado ou texto estiver vazio.
        RuntimeError: Em caso de falha na IA ou na validação.
    """

    # 1. Extração de texto
    print(f"\n[1/3] Extraindo texto de {len(caminhos_arquivos)} arquivo(s)...")
    texto_consolidado, sucessos, falhas = _extrair_textos(caminhos_arquivos)

    if not sucessos:
        raise ValueError(
            "Nenhum arquivo pôde ser processado. "
            "Verifique os caminhos e formatos informados."
        )

    if not texto_consolidado.strip():
        raise ValueError("O texto consolidado está vazio. Nenhum conteúdo foi extraído.")

    # 2. Parsing via IA
    print("\n[2/3] Extraindo dados estruturados com IA (Claude)...")
    try:
        dados = extrair_dados_crm(texto_consolidado)
    except ValueError as exc:
        raise ValueError(f"Erro no parsing da resposta da IA: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Erro na chamada à API da Anthropic: {exc}") from exc

    # 3. Validação dos dados
    print("\n[3/3] Validando dados extraídos...")
    try:
        resultado = validar_crm(dados)
    except Exception as exc:
        raise RuntimeError(f"Erro inesperado na validação: {exc}") from exc

    return {
        "sucessos":  sucessos,
        "falhas":    falhas,
        "texto":     texto_consolidado,
        "dados":     dados,
        "resultado": resultado,
    }


# --------------------------------------------------------------------------- #
# Entrypoint                                                                   #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:     python crm_pipeline.py <arquivo1> [arquivo2] ...")
        print("Exemplo: python crm_pipeline.py proposta.pdf contato.png")
        sys.exit(1)

    arquivos = sys.argv[1:]

    try:
        saida = executar_pipeline(arquivos)
        _exibir_arquivos(saida["sucessos"], saida["falhas"])
        _exibir_texto_consolidado(saida["texto"])
        _exibir_dados(saida["dados"])
        _exibir_resultado(saida["resultado"])

    except ValueError as e:
        print(f"\n[ERRO] {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n[ERRO] Falha no pipeline: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nExecução interrompida pelo usuário.")
        sys.exit(0)
