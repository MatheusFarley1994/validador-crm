"""
contract_pipeline.py
Orquestrador do fluxo de validação contratual — dados comerciais.

O pipeline opera sobre qualquer texto de contrato, independentemente de
estrutura, formato ou modelo. Nenhuma detecção de template é realizada.

Fluxo:
    texto_contrato
        → contract_parser           (extrai dados comerciais via IA)
        → contract_fields_validator (valida campos obrigatórios)
        → comparar_crm_contrato     (warnings de divergência CRM × contrato)
        → resultado consolidado
"""

from typing import Optional

from contract_parser           import extrair_dados_contrato
from contract_fields_validator import validar_campos_contrato


# --------------------------------------------------------------------------- #
# Comparação CRM × Contrato                                                   #
# --------------------------------------------------------------------------- #

def _to_number(valor) -> float | None:
    """
    Converte um valor numérico de qualquer formato para float.

    Aceita:
        - int ou float  → converte diretamente
        - str           → remove "R$", espaços, pontos de milhar;
                          substitui vírgula decimal por ponto

    Retorna:
        float se a conversão for bem-sucedida, None caso contrário.

    Exemplos:
        "R$ 3.500,00" → 3500.0
        "3.500"       → 3500.0  (ponto de milhar)
        "3500,00"     → 3500.0
        420           → 420.0
        "450"         → 450.0
        "abc"         → None
    """
    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    if not isinstance(valor, str):
        return None

    texto = valor.strip()
    texto = texto.replace("R$", "").strip()
    texto = texto.replace(" ", "")

    # Formato brasileiro: vírgula indica decimal → ponto é milhar
    if "," in texto:
        texto = texto.replace(".", "")   # remove pontos de milhar
        texto = texto.replace(",", ".")  # vírgula decimal vira ponto
    # Sem vírgula: ponto com exatamente 3 dígitos após = milhar
    elif "." in texto:
        partes = texto.split(".")
        if all(len(p) == 3 for p in partes[1:]):
            texto = texto.replace(".", "")

    try:
        return float(texto)
    except ValueError:
        return None


def comparar_crm_contrato(
    dados_crm:      dict,
    dados_contrato: dict,
) -> list[str]:
    """
    Compara campos comerciais entre os dados do CRM e os dados do contrato.

    Divergências geram warnings — nunca erros críticos. O status_final
    resultante de divergências é "revisao_manual", não "invalido".

    Utiliza _to_number() para normalizar os valores antes de comparar,
    garantindo robustez contra diferentes formatos numéricos.

    Comparações realizadas:
        - numero_alunos (CRM) vs alunos_totais (Contrato)
        - valor_implantacao (CRM) vs implantacao (Contrato)

    Parâmetros:
        dados_crm (dict): Campos extraídos pelo crm_parser.
        dados_contrato (dict): Campos extraídos pelo contract_parser.

    Retorna:
        list[str]: Lista de warnings de divergência. Vazia se tudo consistente.
    """
    warnings: list[str] = []

    comparacoes = [
        (
            "numero_alunos",     dados_crm,
            "alunos_totais",     dados_contrato,
            "Número de alunos",
        ),
        (
            "valor_implantacao", dados_crm,
            "implantacao",       dados_contrato,
            "Valor de implantação",
        ),
    ]

    for campo_crm, fonte_crm, campo_contrato, fonte_contrato, label in comparacoes:
        val_crm      = fonte_crm.get(campo_crm)
        val_contrato = fonte_contrato.get(campo_contrato)

        num_crm      = _to_number(val_crm)
        num_contrato = _to_number(val_contrato)

        # Só compara se ambas as conversões foram bem-sucedidas
        if num_crm is None or num_contrato is None:
            continue

        if num_crm != num_contrato:
            warnings.append(
                f"{label} divergente: CRM={val_crm}, Contrato={val_contrato}."
            )

    return warnings


# --------------------------------------------------------------------------- #
# Status final                                                                 #
# --------------------------------------------------------------------------- #

def _determinar_status_final(
    validacao_campos:      dict,
    warnings_crm_contrato: list[str],
) -> str:
    """
    Determina o status_final do pipeline contratual.

    Regras (em ordem de prioridade):
        1. Erro crítico de campo         → "invalido"
        2. Divergência CRM × contrato    → "revisao_manual"
        3. Tudo consistente              → "valido"
    """
    if not validacao_campos["valido"]:
        return "invalido"

    if warnings_crm_contrato:
        return "revisao_manual"

    return "valido"


# --------------------------------------------------------------------------- #
# Função principal                                                             #
# --------------------------------------------------------------------------- #

def executar_pipeline_contrato(
    texto_contrato: str,
    dados_crm:      Optional[dict] = None,
    api_key:        Optional[str]  = None,
) -> dict:
    """
    Executa o pipeline de validação contratual baseado em dados comerciais.

    Aceita qualquer texto de contrato, independentemente de estrutura ou
    formato. Nunca lança exceção por conteúdo não reconhecido — campos
    ausentes resultam em status "invalido" via validacao_campos.

    Parâmetros:
        texto_contrato (str): Texto bruto extraído do contrato via OCR ou PDF.
        dados_crm (dict, opcional): Campos do CRM para comparação cruzada.
            Se fornecido, ativa a detecção de divergências CRM × contrato.
        api_key (str, opcional): Chave da API Anthropic. Se None, usa a
            variável de ambiente ANTHROPIC_API_KEY.

    Retorna:
        dict com:
            - dados_extraidos (dict): Campos extraídos pelo contract_parser.
            - validacao_campos (dict): Resultado de validar_campos_contrato
              com chaves: valido (bool), erros_criticos (list), warnings (list).
            - warnings_crm_contrato (list[str]): Divergências entre CRM e contrato.
            - status_final (str): "valido", "invalido" ou "revisao_manual".

    Lança:
        ValueError: Se o texto estiver vazio ou a resposta da IA for inválida.
        RuntimeError: Em caso de falha na chamada à API da Anthropic.
    """
    if not texto_contrato or not texto_contrato.strip():
        raise ValueError("O texto do contrato está vazio.")

    # ── Etapa 1: Extração de dados via IA ────────────────────────────────────
    resultado_parser = extrair_dados_contrato(
        texto_bruto = texto_contrato,
        api_key     = api_key,
    )
    dados_extraidos = resultado_parser.get("dados", {})

    # ── Etapa 2: Validação de campos ─────────────────────────────────────────
    # Injeta "comercial" como modelo para acionar o conjunto de regras genérico
    # definido em contract_fields_validator.
    resultado_para_validacao = {**resultado_parser, "modelo": "comercial"}
    validacao_campos = validar_campos_contrato(resultado_para_validacao)

    # ── Etapa 3: Comparação CRM × Contrato ───────────────────────────────────
    warnings_crm_contrato = comparar_crm_contrato(
        dados_crm      = dados_crm or {},
        dados_contrato = dados_extraidos,
    )

    # ── Etapa 4: Consolidação ─────────────────────────────────────────────────
    status_final = _determinar_status_final(validacao_campos, warnings_crm_contrato)

    return {
        "dados_extraidos":       dados_extraidos,
        "validacao_campos":      validacao_campos,
        "warnings_crm_contrato": warnings_crm_contrato,
        "status_final":          status_final,
    }


# --------------------------------------------------------------------------- #
# Exibição formatada                                                           #
# --------------------------------------------------------------------------- #

def _exibir_resultado(resultado: dict) -> None:
    """Exibe o resultado do pipeline de forma legível no terminal."""
    STATUS_SIMBOLO = {
        "valido":         "✔",
        "invalido":       "✘",
        "revisao_manual": "⚠",
    }

    status  = resultado["status_final"]
    simbolo = STATUS_SIMBOLO.get(status, "?")

    print("\n" + "═" * 50)
    print("  RESULTADO DO PIPELINE CONTRATUAL")
    print("═" * 50)
    print(f"  Status final      : {simbolo}  {status.upper()}")

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

    w_crm = resultado["warnings_crm_contrato"]
    if w_crm:
        print("\n  ── Divergências CRM × Contrato")
        for w in w_crm:
            print(f"       ⚠ {w}")

    print("═" * 50)


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                               #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    TEXTO_CONTRATO = """\
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
"""

    # CRM com divergência proposital no número de alunos
    DADOS_CRM_EXEMPLO = {
        "numero_alunos":     350,   # diverge do contrato (420)
        "valor_implantacao": 3500,  # igual ao contrato
    }

    try:
        resultado = executar_pipeline_contrato(
            texto_contrato = TEXTO_CONTRATO,
            dados_crm      = DADOS_CRM_EXEMPLO,
        )
        _exibir_resultado(resultado)

    except ValueError as e:
        print(f"\n[ERRO DE VALIDAÇÃO] {e}")
    except RuntimeError as e:
        print(f"\n[ERRO DE API] {e}")
