"""
crm_parser.py
Módulo para extração estruturada de dados de CRM a partir de texto bruto,
utilizando a API da Anthropic (Claude) com resposta forçada em JSON.
"""

import json
import os
import re
from typing import Optional

import anthropic

# --------------------------------------------------------------------------- #
# Configuração                                                                  #
# --------------------------------------------------------------------------- #

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
TEMPERATURE = 0.0  # Máxima determinismo para extração estruturada

CAMPOS_ESPERADOS = [
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

SYSTEM_PROMPT = """\
Você é um assistente especializado em extração de dados de CRM.

Sua única tarefa é analisar o texto fornecido pelo usuário e extrair as
informações solicitadas, retornando EXCLUSIVAMENTE um objeto JSON válido —
sem explicações, sem markdown, sem texto adicional.

Regras de formato:
- Retorne apenas o objeto JSON, começando com { e terminando com }.
- Números devem ser retornados como number (não string): ex. 1500.00, não "1500.00".
- Exceção: "numero_alunos" pode ser retornado como string se vier como faixa textual
  (ex: "Até 50 alunos", "51–100 alunos", "Mais de 1001 alunos"). Nesse caso, retorne
  a faixa exatamente como está no texto.

Regras de extração — leia com atenção:
- Extraia APENAS o que estiver claramente e literalmente presente no texto.
- Se houver qualquer dúvida sobre um valor, retorne null.
- Se um campo não estiver no texto, retorne null.
- Nunca estime valores.
- Nunca deduza valores implícitos.
- Nunca infira informações a partir de contexto ou conhecimento externo.
- Nunca calcule nada — nenhum campo deve ser resultado de operação matemática.
- Nunca derive "arr" a partir de "mrr" ou qualquer outro campo.
- Em caso de ambiguidade, prefira sempre null a arriscar um valor incorreto.

Mapeamento de seções — CRÍTICO, siga à risca:

O texto do CRM possui duas seções distintas. Você DEVE identificá-las e
extrair cada campo exclusivamente da seção correta.

SEÇÃO "Negociação" (ou equivalente — cabeçalho da oportunidade):
  → "nome"              = nome da negociação/oportunidade (NÃO é o nome de uma pessoa)
  → "nome_escola"       = nome da escola ou instituição
  → "vendedor"          = vendedor responsável pela negociação
  → "perfil_escola"     = perfil ou descrição da escola
  → "numero_alunos"     = número ou faixa de alunos
  → "nivel_prioridade"  = nível de prioridade (ex: "GRUPO A", "GRUPO B")
  → "mrr"               = MRR acordado
  → "arr"               = ARR (nunca derive de mrr)
  → "dor_escola"        = principais dores ou problemas da escola
  → "valor_implantacao" = valor de implantação
  → "link_contrato"     = link do contrato
  → "forma_implantacao" = forma de implantação (ex: "Remota", "Presencial")

SEÇÃO "Contatos" (ou equivalente — lista de contatos da negociação):
  → "contato_nome"      = nome do contato listado nesta seção
  → "contato_telefone"  = telefone do contato listado nesta seção
  → "contato_email"     = e-mail do contato listado nesta seção

Regras específicas para campos de contato:
- "contato_nome" deve vir EXCLUSIVAMENTE da seção "Contatos".
  Nunca use o nome da negociação nem qualquer nome da seção "Negociação".
- Se houver múltiplos contatos, extraia apenas o primeiro.
- Se a seção "Contatos" não existir ou estiver vazia, retorne null para
  contato_nome, contato_telefone e contato_email.

Estrutura esperada:
{
  "nome": string | null,
  "nome_escola": string | null,
  "vendedor": string | null,
  "perfil_escola": string | null,
  "numero_alunos": number | null,
  "nivel_prioridade": string | null,
  "mrr": number | null,
  "arr": number | null,
  "dor_escola": string | null,
  "valor_implantacao": number | null,
  "link_contrato": string | null,
  "forma_implantacao": string | null,
  "contato_nome": string | null,
  "contato_telefone": string | null,
  "contato_email": string | null
}
"""


# --------------------------------------------------------------------------- #
# Funções auxiliares                                                            #
# --------------------------------------------------------------------------- #

def _build_user_message(texto_bruto: str) -> str:
    return f"Extraia os dados do seguinte texto de CRM:\n\n{texto_bruto}"


def _converter_faixa_alunos(valor) -> Optional[int]:
    """
    Converte o campo numero_alunos para inteiro, aceitando tanto números
    simples quanto faixas textuais vindas do CRM.

    Exemplos:
        "Até 50 alunos"        → 50
        "51–100 alunos"        → 100
        "101–200 alunos"       → 200
        "201–300 alunos"       → 300
        "301–500 alunos"       → 500
        "501–1000 alunos"      → 1000
        "Mais de 1001 alunos"  → 1001
        450                    → 450
        "450"                  → 450
        valor não reconhecido  → None
    """
    if valor is None:
        return None

    # Já é número inteiro ou float
    if isinstance(valor, (int, float)):
        return int(valor)

    texto = str(valor).strip()

    # Número simples em string (ex: "450")
    if texto.isdigit():
        return int(texto)

    # Extrai todos os números do texto
    numeros = re.findall(r"\d+", texto)
    if not numeros:
        return None

    texto_lower = texto.lower()

    # "Até X" ou "até X" → retorna o único número encontrado
    if texto_lower.startswith("até") or texto_lower.startswith("ate"):
        return int(numeros[0])

    # "Mais de X" → retorna o único número encontrado
    if "mais de" in texto_lower:
        return int(numeros[0])

    # Faixa "X–Y" ou "X-Y" → retorna o limite superior (último número)
    if len(numeros) >= 2:
        return int(numeros[-1])

    # Fallback: único número encontrado no texto
    return int(numeros[0])


def _parse_json_response(content: str) -> dict:
    """
    Extrai e interpreta o primeiro bloco JSON válido da resposta do modelo.

    Estratégia:
        1. Usa regex com re.DOTALL para localizar o primeiro trecho
           delimitado por { ... } na resposta, ignorando texto ao redor.
        2. Tenta interpretar o trecho encontrado como JSON.
        3. Lança ValueError com mensagem clara em caso de falha.
    """
    match = re.search(r"\{.*\}", content, re.DOTALL)

    if not match:
        raise ValueError(
            "Nenhum bloco JSON encontrado na resposta do modelo.\n"
            f"Conteúdo recebido:\n{content}"
        )

    json_bruto = match.group()

    try:
        return json.loads(json_bruto)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Bloco JSON encontrado, mas inválido.\n"
            f"Trecho extraído:\n{json_bruto}\n"
            f"Erro de parsing: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Função principal                                                              #
# --------------------------------------------------------------------------- #

def extrair_dados_crm(
    texto_bruto: str,
    api_key: Optional[str] = None,
) -> dict:
    """
    Extrai dados estruturados de um texto bruto de CRM usando Claude.

    Parâmetros:
        texto_bruto (str): Texto livre extraído do CRM.
        api_key (str, opcional): Chave da API Anthropic. Se não informada,
            utiliza a variável de ambiente ANTHROPIC_API_KEY.

    Retorna:
        dict com os campos extraídos. Campos não encontrados terão valor None.

    Lança:
        ValueError: Se a resposta do modelo não for um JSON válido.
        anthropic.APIError: Em caso de erros na chamada da API.
    """
    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_user_message(texto_bruto),
            }
        ],
    )

    resposta_texto = message.content[0].text
    dados = _parse_json_response(resposta_texto)

    # Garante que todos os campos esperados estejam presentes no retorno
    for campo in CAMPOS_ESPERADOS:
        dados.setdefault(campo, None)

    # Normaliza numero_alunos para inteiro antes de enviar ao validador
    dados["numero_alunos"] = _converter_faixa_alunos(dados.get("numero_alunos"))

    return dados


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                                #
# --------------------------------------------------------------------------- #

TEXTO_EXEMPLO = """
Oportunidade: João Silva
Escola: Colégio Modelo
Vendedor responsável: Maria Costa
Perfil: Escola privada de médio porte
Total de alunos: 450
Prioridade: GRUPO B
MRR acordado: R$ 650,00
Principais dores: Gestão financeira deficiente e falta de controle de inadimplência.
Valor de implantação: R$ 4.500,00
Contrato: https://contratos.empresa.com/colegio-modelo
Forma de implantação: Remota

Contato responsável: Ana Lima
Telefone: (31) 99999-8888
E-mail: ana.lima@colegio.com.br
"""

if __name__ == "__main__":
    print("=== CRM Parser — Exemplo de Extração ===\n")

    try:
        dados = extrair_dados_crm(TEXTO_EXEMPLO)

        print("Dados extraídos:")
        for campo, valor in dados.items():
            print(f"  {campo:<20} : {valor}")

    except ValueError as e:
        print(f"[ERRO DE PARSING] {e}")
    except anthropic.APIError as e:
        print(f"[ERRO DE API] {e}")
