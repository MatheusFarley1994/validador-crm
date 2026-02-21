"""
contract_parser.py
Extração estruturada de dados de contratos (antigo_v13 ou novo) a partir de
texto bruto via OCR, utilizando a API da Anthropic (Claude).
"""

import json
import os
import re
from typing import Optional

import anthropic



# --------------------------------------------------------------------------- #
# Configuração                                                                 #
# --------------------------------------------------------------------------- #

MODEL       = "claude-sonnet-4-6"
MAX_TOKENS  = 2048
TEMPERATURE = 0.0

CAMPOS_DADOS = [
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
    "desconto_primeiro_ano",
    "saldo_loja",
    "ia",
]

SYSTEM_PROMPT = """\
Você é um assistente especializado em extração de dados de contratos escolares.

Sua única tarefa é analisar o texto do contrato fornecido e extrair os campos
solicitados, retornando EXCLUSIVAMENTE um objeto JSON válido.

Regras absolutas — sem exceções:
- Retorne apenas o objeto JSON, começando com { e terminando com }.
- Não use markdown, não use blocos de código, não adicione explicações.
- Nunca invente ou estime dados que não estejam literalmente no texto.
- Use null para qualquer campo ausente ou ambíguo.
- Números (implantacao, alunos_totais, alunos_gamificados) devem ser retornados
  como number, não como string. Ex: 1500.00 e não "1500.00".
- Datas, textos e identificadores devem ser retornados como string.
- Em caso de qualquer dúvida sobre um valor, prefira null.

Estrutura exigida:
{
  "dados": {
    "nome_escola": string | null,
    "razao_social": string | null,
    "cnpj": string | null,
    "email_login": string | null,
    "email_financeiro": string | null,
    "whatsapp": string | null,
    "alunos_totais": number | null,
    "alunos_gamificados": number | null,
    "implantacao": number | null,
    "assinatura": string | null,
    "inicio_implantacao": string | null,
    "inicio_cobranca": string | null,
    "cards_enviados": string | null,
    "desconto_primeiro_ano": string | null,
    "saldo_loja": string | null,
    "ia": string | null
  }
}

Não inclua o campo "modelo" — ele é gerenciado exclusivamente pelo backend.
"""


# --------------------------------------------------------------------------- #
# Helpers internos                                                             #
# --------------------------------------------------------------------------- #

def _build_user_message(texto_bruto: str, modelo: str) -> str:
    return (
        f"Modelo de contrato identificado: {modelo}\n\n"
        f"Extraia os dados do seguinte contrato:\n\n{texto_bruto}"
    )


def _parse_json_response(content: str) -> dict:
    """
    Extrai e interpreta o primeiro objeto JSON estruturalmente válido da resposta.

    Estratégia:
        Em vez de regex simples (que não entende aninhamento), a função varre o
        texto caractere a caractere rastreando a profundidade de chaves { }.
        Isso garante que apenas um bloco completo e balanceado seja candidato ao
        parsing — tolerando texto livre antes e depois do JSON, múltiplos blocos
        na resposta, e objetos profundamente aninhados.

    Fluxo:
        1. Localiza o primeiro '{' no texto.
        2. Avança rastreando abertura/fechamento de chaves (ignora chaves dentro
           de strings para evitar falsos positivos).
        3. Ao atingir profundidade 0 pela primeira vez, delimita o candidato.
        4. Tenta json.loads() no candidato — se falhar, busca o próximo '{'.
        5. Se nenhum candidato for parseável, lança ValueError detalhado.

    Lança:
        ValueError: Se nenhum JSON válido for encontrado na resposta.
    """
    candidatos_tentados: list[str] = []
    pos = 0

    while pos < len(content):
        inicio = content.find("{", pos)
        if inicio == -1:
            break

        profundidade = 0
        dentro_de_string = False
        escape = False

        for i, char in enumerate(content[inicio:], start=inicio):
            if escape:
                escape = False
                continue
            if char == "\\" and dentro_de_string:
                escape = True
                continue
            if char == '"' and not escape:
                dentro_de_string = not dentro_de_string
                continue
            if dentro_de_string:
                continue
            if char == "{":
                profundidade += 1
            elif char == "}":
                profundidade -= 1
                if profundidade == 0:
                    candidato = content[inicio: i + 1]
                    candidatos_tentados.append(candidato)
                    try:
                        return json.loads(candidato)
                    except json.JSONDecodeError:
                        # Bloco balanceado mas inválido; tenta a partir do próximo '{'
                        pos = inicio + 1
                        break
            else:
                continue
        else:
            # Chegou ao fim sem fechar todas as chaves — bloco incompleto
            pos = inicio + 1

    # Nenhum candidato parseável encontrado
    if candidatos_tentados:
        raise ValueError(
            f"{len(candidatos_tentados)} bloco(s) JSON encontrado(s), mas nenhum é válido.\n"
            f"Último candidato tentado:\n{candidatos_tentados[-1]}\n"
            f"Verifique se a resposta do modelo está malformada."
        )

    raise ValueError(
        "Nenhum bloco JSON encontrado na resposta do modelo.\n"
        f"Conteúdo recebido:\n{content}"
    )


def _garantir_campos(resultado: dict, modelo: str) -> dict:
    """
    Garante que o retorno contenha a estrutura completa esperada,
    preenchendo campos ausentes com None.

    O campo "modelo" é sempre sobrescrito com o valor detectado pelo backend,
    ignorando qualquer valor que a IA possa ter retornado.
    """
    resultado["modelo"] = modelo  # sempre injetado pelo backend, nunca pela IA
    resultado.setdefault("dados", {})

    for campo in CAMPOS_DADOS:
        resultado["dados"].setdefault(campo, None)

    return resultado


# --------------------------------------------------------------------------- #
# Validação estrutural                                                         #
# --------------------------------------------------------------------------- #

CAMPOS_NUMERICOS = {"implantacao", "alunos_totais", "alunos_gamificados"}


def _validar_estrutura(resultado: dict) -> None:
    """
    Valida a estrutura e os tipos do dicionário retornado pela IA.

    Verificações realizadas:
        1. Chave "dados" existe no resultado.
        2. "dados" é um dicionário.
        3. Todos os campos de CAMPOS_DADOS estão presentes em "dados".
        4. Campos numéricos (implantacao, alunos_totais, alunos_gamificados)
           são int, float ou None — nunca string, lista ou dict.
        5. Nenhum campo simples contém tipos complexos (lista ou dict).

    Lança:
        ValueError: Com descrição precisa da violação encontrada.
    """
    # 1 + 2. Chave "dados" existe e é dict
    if "dados" not in resultado:
        raise ValueError(
            "Resposta da IA não contém a chave obrigatória \'dados\'."
        )

    dados = resultado["dados"]

    if not isinstance(dados, dict):
        raise ValueError(
            f"O campo \'dados\' deve ser um dicionário, "
            f"mas recebeu: {type(dados).__name__}."
        )

    # 3. Todos os campos obrigatórios presentes
    ausentes = [c for c in CAMPOS_DADOS if c not in dados]
    if ausentes:
        raise ValueError(
            f"Campo(s) obrigatório(s) ausente(s) em \'dados\': {ausentes}."
        )

    # 4 + 5. Validação de tipo por campo
    erros_tipo: list[str] = []

    for campo, valor in dados.items():
        if valor is None:
            continue  # None é sempre permitido

        if campo in CAMPOS_NUMERICOS:
            if not isinstance(valor, (int, float)):
                erros_tipo.append(
                    f"\'{campo}\' deve ser numérico ou null, "
                    f"mas recebeu {type(valor).__name__}: {valor!r}."
                )
        elif isinstance(valor, (list, dict)):
            erros_tipo.append(
                f"\'{campo}\' não pode ser {type(valor).__name__} — "
                f"apenas string, número ou null são permitidos."
            )

    if erros_tipo:
        raise ValueError(
            "Tipo(s) inválido(s) na resposta da IA:\n"
            + "\n".join(f"  • {e}" for e in erros_tipo)
        )


# --------------------------------------------------------------------------- #
# Função principal                                                             #
# --------------------------------------------------------------------------- #

def extrair_dados_contrato(
    texto_bruto:      str,
    modelo_detectado: str,
    api_key:          Optional[str] = None,
) -> dict:
    """
    Extrai dados estruturados de um contrato escolar a partir de texto bruto.

    O modelo do contrato deve ser detectado externamente (ex: pelo pipeline)
    e passado via modelo_detectado. O parser confia exclusivamente nesse valor,
    sem realizar nenhuma detecção própria.

    Parâmetros:
        texto_bruto (str): Texto extraído do contrato via OCR ou PDF parser.
        modelo_detectado (str): Modelo já identificado — "novo" ou "antigo_v13".
            Deve ser fornecido pelo chamador; nunca é inferido internamente.
        api_key (str, opcional): Chave da API Anthropic. Se omitida, usa a
            variável de ambiente ANTHROPIC_API_KEY.

    Retorna:
        dict no formato:
            {
                "modelo": "antigo_v13" | "novo",
                "dados": { ...campos extraídos... }
            }

    Lança:
        ValueError: Se o texto estiver vazio, o modelo for inválido, o JSON
            retornado for inválido, a estrutura estiver incompleta ou algum campo
            contiver tipo incompatível.
        RuntimeError: Em caso de falha na chamada à API da Anthropic.
    """
    if not texto_bruto or not texto_bruto.strip():
        raise ValueError("O texto do contrato está vazio.")

    modelo = modelo_detectado

    # 1. Chamada à API
    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _build_user_message(texto_bruto, modelo),
                }
            ],
        )
    except anthropic.APIError as exc:
        raise RuntimeError(f"Erro na chamada à API da Anthropic: {exc}") from exc

    # 3. Parsing da resposta
    resposta_texto = message.content[0].text
    resultado = _parse_json_response(resposta_texto)

    # 4. Validação estrutural e de tipos
    _validar_estrutura(resultado)

    # 5. Normalização: injeta modelo e garante todos os campos
    resultado = _garantir_campos(resultado, modelo)

    return resultado


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                               #
# --------------------------------------------------------------------------- #

TEXTO_EXEMPLO_NOVO = """
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
Desconto 1º Ano: 10%
IA Incluída: Sim
"""

if __name__ == "__main__":
    print("=== Contract Parser — Exemplo de Extração ===\n")

    try:
        resultado = extrair_dados_contrato(
            texto_bruto      = TEXTO_EXEMPLO_NOVO,
            modelo_detectado = "novo",
        )

        print(f"Modelo detectado : {resultado['modelo']}\n")
        print("Dados extraídos:")
        for campo, valor in resultado["dados"].items():
            print(f"  {campo:<25} : {valor}")

    except ValueError as e:
        print(f"[ERRO DE VALIDAÇÃO] {e}")
    except RuntimeError as e:
        print(f"[ERRO DE API] {e}")
