"""
crm_validator.py
Módulo para validação de dados de CRM antes de inserção ou processamento.
"""

from typing import Any


CAMPOS_OBRIGATORIOS = [
    "nome",
    "nome_escola",
    "vendedor",
    "perfil_escola",
    "numero_alunos",
    "nivel_prioridade",
    "mrr",
    "arr",
    "dor_escola",
    "valor_implantacao",
    "link_contrato",
    "forma_implantacao",
    "contato_nome",
    "contato_telefone",
    "contato_email",
]


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _digits_only(value: str) -> str:
    return "".join(c for c in str(value) if c.isdigit())


def _grupo_esperado(mrr: float) -> str:
    """Retorna o grupo de prioridade esperado com base no valor de MRR."""
    if mrr > 700:
        return "GRUPO A"
    if mrr >= 401:
        return "GRUPO B"
    if mrr >= 300:
        return "GRUPO C"
    if mrr >= 100:
        return "GRUPO D"
    return "GRUPO E"


def validar_crm(dados: dict) -> dict:
    """
    Valida um dicionário com dados de CRM.

    Parâmetros:
        dados (dict): Dicionário contendo os campos do CRM.

    Retorna:
        dict com:
            - status (str): "valido" ou "invalido"
            - erros (list[str]): Lista de mensagens de erro encontradas.
    """
    erros = []

    # ------------------------------------------------------------------ #
    # 1. Campos obrigatórios presentes e não vazios                        #
    # ------------------------------------------------------------------ #
    for campo in CAMPOS_OBRIGATORIOS:
        valor = dados.get(campo)
        if valor is None or str(valor).strip() == "":
            erros.append(f"Campo obrigatório ausente ou vazio: '{campo}'.")

    # ------------------------------------------------------------------ #
    # 2. numero_alunos — inteiro > 0                                       #
    # ------------------------------------------------------------------ #
    numero_alunos = dados.get("numero_alunos")
    if numero_alunos is not None and str(numero_alunos).strip() != "":
        try:
            numero_alunos_int = int(numero_alunos)
            if numero_alunos_int <= 0:
                erros.append("'numero_alunos' deve ser um inteiro maior que zero.")
            elif numero_alunos_int != float(numero_alunos):
                # Rejeita valores como 2.5
                erros.append("'numero_alunos' deve ser um número inteiro (sem decimais).")
        except (TypeError, ValueError):
            erros.append("'numero_alunos' deve ser um número inteiro válido.")

    # ------------------------------------------------------------------ #
    # 3. mrr — numérico > 0                                               #
    # ------------------------------------------------------------------ #
    mrr = dados.get("mrr")
    mrr_valido = False
    if mrr is not None and str(mrr).strip() != "":
        if not _is_numeric(mrr):
            erros.append("'mrr' deve ser um valor numérico.")
        elif float(mrr) <= 0:
            erros.append("'mrr' deve ser maior que zero.")
        else:
            mrr_valido = True

    # ------------------------------------------------------------------ #
    # 4. nivel_prioridade - deve ser coerente com mrr                     #
    # ------------------------------------------------------------------ #
    nivel = dados.get("nivel_prioridade")
    if mrr_valido and nivel is not None and str(nivel).strip() != "":
        grupo = _grupo_esperado(float(mrr))
        if str(nivel).strip().upper() != grupo:
            erros.append(
                f"Nivel de prioridade inconsistente com MRR. Esperado: {grupo}."
            )

    # ------------------------------------------------------------------ #
    # 6. arr == 12 * mrr                                                  #
    # ------------------------------------------------------------------ #
    arr = dados.get("arr")
    if arr is not None and str(arr).strip() != "":
        if not _is_numeric(arr):
            erros.append("'arr' deve ser um valor numérico.")
        elif mrr_valido:
            esperado = round(float(mrr) * 12, 10)
            if round(float(arr), 10) != esperado:
                erros.append(
                    f"'arr' deve ser exatamente 12 × mrr "
                    f"(esperado: {esperado}, recebido: {float(arr)})."
                )

    # ------------------------------------------------------------------ #
    # 7. contato_telefone — mínimo 10 dígitos                             #
    # ------------------------------------------------------------------ #
    telefone = dados.get("contato_telefone")
    if telefone is not None and str(telefone).strip() != "":
        digitos = _digits_only(telefone)
        if len(digitos) < 10:
            erros.append(
                f"'contato_telefone' deve conter pelo menos 10 dígitos "
                f"(encontrados: {len(digitos)})."
            )

    # ------------------------------------------------------------------ #
    # 8. contato_email — deve conter "@"                                  #
    # ------------------------------------------------------------------ #
    email = dados.get("contato_email")
    if email is not None and str(email).strip() != "":
        if "@" not in str(email):
            erros.append("'contato_email' deve conter '@'.")

    # ------------------------------------------------------------------ #
    # 9. link_contrato — deve começar com "http"                          #
    # ------------------------------------------------------------------ #
    link = dados.get("link_contrato")
    if link is not None and str(link).strip() != "":
        if not str(link).strip().lower().startswith("http"):
            erros.append("'link_contrato' deve começar com 'http'.")

    # ------------------------------------------------------------------ #
    # Resultado final                                                      #
    # ------------------------------------------------------------------ #
    return {
        "status": "valido" if not erros else "invalido",
        "erros": erros,
    }


# ---------------------------------------------------------------------- #
# Exemplo de uso                                                           #
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    exemplo = {
        "nome": "João Silva",
        "nome_escola": "Escola Modelo",
        "vendedor": "Maria Costa",
        "perfil_escola": "Privada",
        "numero_alunos": 300,
        "nivel_prioridade": "GRUPO A",  # mrr 1500 > 700 → GRUPO A
        "mrr": 1500.00,
        "arr": 18000.00,          # 12 * 1500
        "dor_escola": "Gestão financeira deficiente",
        "valor_implantacao": 5000,
        "link_contrato": "https://contratos.empresa.com/joao-silva",
        "forma_implantacao": "Remota",
        "contato_nome": "Ana Lima",
        "contato_telefone": "(31) 99999-8888",
        "contato_email": "ana.lima@escolamodelo.com.br",
    }

    resultado = validar_crm(exemplo)
    print(f"Status : {resultado['status']}")
    if resultado["erros"]:
        print("Erros encontrados:")
        for erro in resultado["erros"]:
            print(f"  • {erro}")
    else:
        print("Nenhum erro encontrado. Dados válidos!")
