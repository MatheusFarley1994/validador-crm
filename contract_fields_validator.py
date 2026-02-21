"""
contract_fields_validator.py
Validação determinística dos campos extraídos de contratos escolares.
Não utiliza IA — apenas regras e lógica de negócio.
"""

from typing import Optional


# --------------------------------------------------------------------------- #
# Configuração de campos por modelo                                            #
# --------------------------------------------------------------------------- #

CAMPOS_OBRIGATORIOS: dict[str, list[str]] = {
    "novo": [
        "nome_escola",
        "razao_social",
        "cnpj",
        "email_login",
        "email_financeiro",
        "whatsapp",
        "alunos_totais",
        "alunos_gamificados",
        "implantacao",
        "assinatura",
        "inicio_implantacao",
        "inicio_cobranca",
        "cards_enviados",
    ],
    "antigo_v13": [
        "nome_escola",
        "razao_social",
        "cnpj",
        "email_login",
        "email_financeiro",
        "whatsapp",
        "alunos_totais",
        "alunos_gamificados",
        "implantacao",
        "assinatura",
        "inicio_implantacao",
        "inicio_cobranca",
        "cards_enviados",
    ],
}

CAMPOS_NUMERICOS = {"alunos_totais", "alunos_gamificados", "implantacao"}

PLACEHOLDERS = {"{{", "}}", "____", "xxxxx"}

LIMIAR_ALUNOS_BAIXO  = 5
LIMIAR_IMPLANTACAO_ZERO = 0


# --------------------------------------------------------------------------- #
# Helpers internos                                                             #
# --------------------------------------------------------------------------- #

def _e_vazio(valor) -> bool:
    """Retorna True se o valor for None, string vazia ou apenas espaços."""
    if valor is None:
        return True
    if isinstance(valor, str) and valor.strip() == "":
        return True
    return False


def _contem_placeholder(valor) -> bool:
    """Retorna True se o valor contiver algum dos placeholders conhecidos."""
    if not isinstance(valor, str):
        return False
    valor_lower = valor.lower()
    return any(ph.lower() in valor_lower for ph in PLACEHOLDERS)


def _validar_presenca(
    dados: dict,
    campos_obrigatorios: list[str],
    erros: list[str],
) -> None:
    """Verifica campos obrigatórios: ausência, vazio, espaços e placeholders."""
    for campo in campos_obrigatorios:
        valor = dados.get(campo)

        if _e_vazio(valor):
            erros.append(
                f"Campo obrigatório ausente ou vazio: '{campo}'."
            )
            continue  # Não verifica placeholder em campo já vazio

        if _contem_placeholder(valor):
            erros.append(
                f"Campo '{campo}' contém placeholder inválido: {valor!r}."
            )


def _validar_numericos(
    dados: dict,
    erros: list[str],
    warnings: list[str],
) -> None:
    """
    Valida campos numéricos:
    - Negativos → erro crítico
    - alunos_gamificados > alunos_totais → erro crítico
    - alunos_totais <= LIMIAR_ALUNOS_BAIXO → warning
    - implantacao == 0 → warning
    """
    valores: dict[str, Optional[float]] = {}

    for campo in CAMPOS_NUMERICOS:
        valor = dados.get(campo)
        if valor is None:
            valores[campo] = None
            continue
        if not isinstance(valor, (int, float)):
            # Tipo inválido já deveria ser capturado pelo contract_parser,
            # mas validamos defensivamente.
            erros.append(
                f"Campo '{campo}' deveria ser numérico, mas recebeu "
                f"{type(valor).__name__}: {valor!r}."
            )
            valores[campo] = None
            continue

        if valor < 0:
            erros.append(
                f"Campo '{campo}' não pode ser negativo (recebido: {valor})."
            )
            valores[campo] = None  # Exclui do uso em comparações subsequentes
        else:
            valores[campo] = float(valor)

    # Comparação alunos_gamificados × alunos_totais
    gamificados = valores.get("alunos_gamificados")
    totais      = valores.get("alunos_totais")

    if gamificados is not None and totais is not None:
        if gamificados > totais:
            erros.append(
                f"'alunos_gamificados' ({gamificados}) não pode ser maior "
                f"que 'alunos_totais' ({totais})."
            )

    # Warnings
    if totais is not None and totais <= LIMIAR_ALUNOS_BAIXO:
        warnings.append(
            f"'alunos_totais' está muito baixo ({int(totais)}). "
            "Verifique se o valor está correto."
        )

    implantacao = valores.get("implantacao")
    if implantacao is not None and implantacao == LIMIAR_IMPLANTACAO_ZERO:
        warnings.append(
            "'implantacao' está zerada. "
            "Verifique se a implantação é realmente gratuita."
        )


# --------------------------------------------------------------------------- #
# Função principal                                                             #
# --------------------------------------------------------------------------- #

def validar_campos_contrato(resultado_parser: dict) -> dict:
    """
    Valida de forma determinística os campos extraídos de um contrato escolar.

    Parâmetros:
        resultado_parser (dict): Saída do contract_parser.py no formato:
            {
                "modelo": "antigo_v13" | "novo",
                "dados": { ...campos extraídos... }
            }

    Retorna:
        dict com:
            - valido (bool): True se nenhum erro crítico for encontrado.
            - erros_criticos (list[str]): Erros que invalidam o contrato.
            - warnings (list[str]): Alertas que não invalidam o contrato.

    Lança:
        ValueError: Se a estrutura de entrada for inválida.
    """
    # Validação da entrada
    modelo = resultado_parser.get("modelo")
    dados  = resultado_parser.get("dados")

    if not modelo or not isinstance(modelo, str):
        raise ValueError("Campo 'modelo' ausente ou inválido na entrada.")
    if not isinstance(dados, dict):
        raise ValueError("Campo 'dados' ausente ou não é um dicionário.")
    if modelo not in CAMPOS_OBRIGATORIOS:
        raise ValueError(
            f"Modelo '{modelo}' não reconhecido. "
            f"Esperado: {list(CAMPOS_OBRIGATORIOS.keys())}."
        )

    erros:    list[str] = []
    warnings: list[str] = []

    campos_obrigatorios = CAMPOS_OBRIGATORIOS[modelo]

    # 1. Presença, vazio, espaços e placeholders
    _validar_presenca(dados, campos_obrigatorios, erros)

    # 2. Regras numéricas e comparações
    _validar_numericos(dados, erros, warnings)

    return {
        "valido":          len(erros) == 0,
        "erros_criticos":  erros,
        "warnings":        warnings,
    }


# --------------------------------------------------------------------------- #
# Exemplos de uso                                                              #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import json

    exemplos = [
        (
            "Contrato NOVO — válido",
            {
                "modelo": "novo",
                "dados": {
                    "nome_escola":           "Colégio Inovação",
                    "razao_social":          "Instituto Educacional Ltda.",
                    "cnpj":                  "12.345.678/0001-90",
                    "email_login":           "admin@colegio.com.br",
                    "email_financeiro":      "fin@colegio.com.br",
                    "whatsapp":              "(31) 99999-8888",
                    "alunos_totais":         420,
                    "alunos_gamificados":    210,
                    "implantacao":           3500.0,
                    "assinatura":            "R$ 890,00/mês",
                    "inicio_implantacao":    "01/03/2025",
                    "inicio_cobranca":       "01/04/2025",
                    "cards_enviados":        "Sim",
                    "desconto_primeiro_ano": "10%",
                    "saldo_loja":            None,
                    "ia":                    "Sim",
                },
            },
        ),
        (
            "Contrato com erros críticos",
            {
                "modelo": "novo",
                "dados": {
                    "nome_escola":           "",                 # vazio
                    "razao_social":          "   ",             # só espaços
                    "cnpj":                  "{{cnpj}}",        # placeholder
                    "email_login":           None,              # ausente
                    "email_financeiro":      "fin@escola.com",
                    "whatsapp":              "(31) 99999-0000",
                    "alunos_totais":         100,
                    "alunos_gamificados":    150,               # maior que totais
                    "implantacao":           -500.0,            # negativo
                    "assinatura":            "R$ 700,00/mês",
                    "inicio_implantacao":    "01/03/2025",
                    "inicio_cobranca":       "01/04/2025",
                    "cards_enviados":        "____",            # placeholder
                    "desconto_primeiro_ano": None,
                    "saldo_loja":            None,
                    "ia":                    None,
                },
            },
        ),
        (
            "Contrato com warnings",
            {
                "modelo": "antigo_v13",
                "dados": {
                    "nome_escola":           "Escola Pequena",
                    "razao_social":          "Escola Pequena Ltda.",
                    "cnpj":                  "98.765.432/0001-10",
                    "email_login":           "admin@pequena.com",
                    "email_financeiro":      "fin@pequena.com",
                    "whatsapp":              "(11) 91111-2222",
                    "alunos_totais":         3,                 # muito baixo → warning
                    "alunos_gamificados":    2,
                    "implantacao":           0,                 # zero → warning
                    "assinatura":            "R$ 300,00/mês",
                    "inicio_implantacao":    "15/02/2025",
                    "inicio_cobranca":       "15/03/2025",
                    "cards_enviados":        "Não",
                    "desconto_primeiro_ano": None,
                    "saldo_loja":            None,
                    "ia":                    None,
                },
            },
        ),
    ]

    for titulo, entrada in exemplos:
        resultado = validar_campos_contrato(entrada)
        simbolo   = "✔" if resultado["valido"] else "✘"
        print(f"\n── {simbolo}  {titulo}")
        print(f"   Válido  : {resultado['valido']}")

        if resultado["erros_criticos"]:
            print(f"   Erros   :")
            for e in resultado["erros_criticos"]:
                print(f"     • {e}")

        if resultado["warnings"]:
            print(f"   Warnings:")
            for w in resultado["warnings"]:
                print(f"     ⚠ {w}")
