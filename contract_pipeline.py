"""
contract_pipeline.py
Orquestrador do fluxo completo de validação contratual.

Fluxo:
    texto_contrato
        → contract_model_detector  (detecta o modelo)
        → contract_parser          (extrai dados estruturados via IA)
        → contract_fields_validator (valida campos obrigatórios)
        → contract_clause_validator (valida integridade das cláusulas)
        → resultado consolidado
"""

from typing import Optional

from contract_model_detector   import detectar_modelo_contrato
from contract_parser           import extrair_dados_contrato
from contract_fields_validator import validar_campos_contrato
from contract_clause_validator import validar_clausulas


# --------------------------------------------------------------------------- #
# Helpers internos                                                             #
# --------------------------------------------------------------------------- #

def _determinar_status_final(
    validacao_campos:    dict,
    validacao_clausulas: dict,
) -> str:
    """
    Determina o status_final consolidado do pipeline.

    Regras (em ordem de prioridade):
        1. Campos inválidos                           → "invalido"
        2. Cláusulas ausentes ou extras               → "invalido"
        3. Nível de risco "alto" ou "medio"           → "revisao_manual"
        4. Tudo válido e risco baixo                  → "valido"
    """
    if not validacao_campos["valido"]:
        return "invalido"

    if validacao_clausulas["clausulas_ausentes"] or validacao_clausulas["clausulas_extras"]:
        return "invalido"

    nivel_risco = validacao_clausulas["nivel_risco"]
    if nivel_risco in ("alto", "medio"):
        return "revisao_manual"

    return "valido"


# --------------------------------------------------------------------------- #
# Função principal                                                             #
# --------------------------------------------------------------------------- #

def executar_pipeline_contrato(
    texto_contrato:  str,
    api_key:         Optional[str] = None,
    diretorio_base:  Optional[str] = None,
) -> dict:
    """
    Executa o pipeline completo de validação contratual.

    Parâmetros:
        texto_contrato (str): Texto bruto extraído do contrato via OCR ou PDF.
        api_key (str, opcional): Chave da API Anthropic. Se None, usa
            a variável de ambiente ANTHROPIC_API_KEY.
        diretorio_base (str, opcional): Diretório com os arquivos de modelo base
            para validação de cláusulas. Se None, usa o diretório do módulo
            contract_clause_validator.

    Retorna:
        dict com:
            - modelo (str): Modelo detectado ("novo" ou "antigo_v13").
            - dados_extraidos (dict): Campos extraídos pelo contract_parser.
            - validacao_campos (dict): Resultado de validar_campos_contrato.
            - validacao_clausulas (dict): Resultado de validar_clausulas.
            - status_final (str): "valido", "invalido" ou "revisao_manual".
            - nivel_risco (str): Nível de risco das cláusulas ("baixo"/"medio"/"alto").

    Lança:
        ValueError: Se o texto estiver vazio, o modelo for desconhecido ou
            a resposta da IA for inválida.
        FileNotFoundError: Se o arquivo de modelo base de cláusulas não existir.
        RuntimeError: Em caso de falha na chamada à API da Anthropic.
    """
    if not texto_contrato or not texto_contrato.strip():
        raise ValueError("O texto do contrato está vazio.")

    # ── Etapa 1: Detecção de modelo ──────────────────────────────────────────
    deteccao = detectar_modelo_contrato(texto_contrato)
    modelo   = deteccao["modelo"]

    if modelo == "desconhecido":
        raise ValueError(
            "Modelo de contrato não identificado. "
            f"Marcadores encontrados: {deteccao['marcadores_encontrados']}. "
            "Verifique se o documento é um contrato válido (antigo_v13 ou novo)."
        )

    # ── Etapa 2: Extração de dados via IA ────────────────────────────────────
    resultado_parser = extrair_dados_contrato(
        texto_bruto      = texto_contrato,
        modelo_detectado = modelo,
        api_key          = api_key,
    )
    dados_extraidos = resultado_parser.get("dados", {})

    # ── Etapa 3: Validação de campos ─────────────────────────────────────────
    validacao_campos = validar_campos_contrato(resultado_parser)

    # ── Etapa 4: Validação de cláusulas ──────────────────────────────────────
    validacao_clausulas = validar_clausulas(
        modelo          = modelo,
        texto_contrato  = texto_contrato,
        diretorio_base  = diretorio_base,
    )

    # ── Etapa 5: Consolidação ─────────────────────────────────────────────────
    status_final = _determinar_status_final(validacao_campos, validacao_clausulas)
    nivel_risco  = validacao_clausulas["nivel_risco"]

    return {
        "modelo":               modelo,
        "dados_extraidos":      dados_extraidos,
        "validacao_campos":     validacao_campos,
        "validacao_clausulas":  validacao_clausulas,
        "status_final":         status_final,
        "nivel_risco":          nivel_risco,
    }


# --------------------------------------------------------------------------- #
# Exibição formatada                                                           #
# --------------------------------------------------------------------------- #

def _exibir_resultado(resultado: dict) -> None:
    """Exibe o resultado do pipeline de forma legível no terminal."""
    STATUS_SIMBOLO = {
        "valido":          "✔",
        "invalido":        "✘",
        "revisao_manual":  "⚠",
    }
    RISCO_SIMBOLO = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}

    status      = resultado["status_final"]
    risco       = resultado["nivel_risco"]
    simbolo     = STATUS_SIMBOLO.get(status, "?")
    simbolo_r   = RISCO_SIMBOLO.get(risco, "?")

    print("\n" + "═" * 50)
    print("  RESULTADO DO PIPELINE CONTRATUAL")
    print("═" * 50)
    print(f"  Modelo detectado  : {resultado['modelo']}")
    print(f"  Status final      : {simbolo}  {status.upper()}")
    print(f"  Nível de risco    : {simbolo_r}  {risco.upper()}")

    # Campos
    vc = resultado["validacao_campos"]
    print(f"\n  ── Validação de Campos {'✔' if vc['valido'] else '✘'}")
    if vc["erros_criticos"]:
        for e in vc["erros_criticos"]:
            print(f"       • {e}")
    if vc["warnings"]:
        for w in vc["warnings"]:
            print(f"       ⚠ {w}")
    if not vc["erros_criticos"] and not vc["warnings"]:
        print("       Nenhum problema encontrado.")

    # Cláusulas
    vl = resultado["validacao_clausulas"]
    print(f"\n  ── Validação de Cláusulas {'✔' if vl['valido'] else '✘'}")
    if vl["clausulas_ausentes"]:
        print(f"       Ausentes : {vl['clausulas_ausentes']}")
    if vl["clausulas_extras"]:
        print(f"       Extras   : {vl['clausulas_extras']}")
    if vl["clausulas_alteradas"]:
        print(f"       Alteradas: {vl['clausulas_alteradas']}")
    if not any([vl["clausulas_ausentes"], vl["clausulas_extras"], vl["clausulas_alteradas"]]):
        print("       Nenhum problema encontrado.")

    print("═" * 50)


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                               #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import tempfile
    import os

    MODELO_BASE = """\
1. OBJETO DO CONTRATO
O presente contrato tem por objeto a prestação de serviços de software educacional.

1.1 O serviço será prestado de forma contínua durante o prazo de vigência.

2. PRAZO DE VIGÊNCIA
O contrato terá duração de 12 meses, renovável automaticamente.

3. VALOR E REAJUSTE
O valor mensal é fixo, sujeito a reajuste anual pelo IPCA.

4. RESCISÃO
A rescisão antecipada implica multa de 30% sobre o valor restante.
"""

    TEXTO_CONTRATO = """\
CONTRATO DE ASSINATURA DE SOFTWARE (SaaS)
ANEXO 1 - TABELA RESUMO COMERCIAL

Nome da Escola: Colégio Inovação
Razão Social: Instituto Educacional Inovação Ltda.
CNPJ: 12.345.678/0001-90
E-mail de Login: admin@colegioinovacao.com.br
E-mail Financeiro: financeiro@colegioinovacao.com.br
WhatsApp: (31) 98888-7777
Total de Alunos: 420
Alunos Gamificados: 210
Valor de Implantação: R$ 3.500,00
Assinatura Mensal: R$ 890,00
Início da Implantação: 01/03/2025
Início da Cobrança: 01/04/2025
Cards Enviados: Sim

1. OBJETO DO CONTRATO
O presente contrato tem por objeto a prestação de serviços de software educacional.

1.1 O serviço será prestado de forma contínua durante o prazo de vigência.

2. PRAZO DE VIGÊNCIA
O contrato terá duração de 12 meses, renovável automaticamente.

3. VALOR E REAJUSTE
O valor mensal é fixo, sujeito a reajuste anual pelo IPCA.

4. RESCISÃO
A rescisão antecipada implica multa de 30% sobre o valor restante.
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = os.path.join(tmpdir, "modelo_novo_base.txt")
        with open(base_path, "w", encoding="utf-8") as f:
            f.write(MODELO_BASE)

        try:
            resultado = executar_pipeline_contrato(
                texto_contrato = TEXTO_CONTRATO,
                diretorio_base = tmpdir,
            )
            _exibir_resultado(resultado)

        except ValueError as e:
            print(f"\n[ERRO DE VALIDAÇÃO] {e}")
        except FileNotFoundError as e:
            print(f"\n[ERRO DE ARQUIVO] {e}")
        except RuntimeError as e:
            print(f"\n[ERRO DE API] {e}")
