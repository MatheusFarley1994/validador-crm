"""
contract_clause_validator.py
Validação de integridade de cláusulas contratuais comparando o contrato
recebido com o modelo oficial correspondente.

Dependências: apenas biblioteca padrão do Python (difflib, re, pathlib).
"""

import re
import difflib
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
# Configuração                                                                 #
# --------------------------------------------------------------------------- #

ARQUIVOS_BASE: dict[str, str] = {
    "novo":        "modelo_novo_base.txt",
    "antigo_v13":  "modelo_antigo_base.txt",
}

SIMILARIDADE_MINIMA: float = 0.97

PALAVRAS_CRITICAS: set[str] = {
    "multa", "prazo", "rescisão", "rescisao", "reajuste",
}

# Padrão de cláusula: "1.", "1.1", "1.1.2", "III.", "IV.", "A.", etc.
PADRAO_CLAUSULA = re.compile(
    r"(?:^|\n)"                          # início de linha
    r"("
    r"(?:[IVXLCDM]+\.)"                  # romano: III., IV.
    r"|(?:[A-Z]\.)"                      # letra maiúscula: A., B.
    r"|(?:\d+(?:\.\d+)*\.?)"             # numérico: 1. | 1.1 | 1.1.2
    r")"
    r"\s",                               # seguido de espaço
    re.MULTILINE,
)


# --------------------------------------------------------------------------- #
# Funções auxiliares públicas                                                  #
# --------------------------------------------------------------------------- #

def normalizar_texto(texto: str) -> str:
    """
    Normaliza o texto para comparação:
    - Converte para minúsculas.
    - Colapsa múltiplos espaços e quebras de linha em espaço único.
    - Remove espaços nas bordas.
    """
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def separar_clausulas(texto: str) -> dict[str, str]:
    """
    Divide o texto em cláusulas numeradas.

    Cada cláusula é identificada por seu marcador (ex: "1.", "1.1", "III.")
    e mapeada para seu conteúdo normalizado.

    Retorna:
        dict {marcador: conteudo_normalizado}
    """
    matches = list(PADRAO_CLAUSULA.finditer(texto))
    clausulas: dict[str, str] = {}

    for i, match in enumerate(matches):
        marcador = match.group(1).rstrip(".")
        inicio   = match.end()
        fim      = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        conteudo = texto[inicio:fim]
        clausulas[marcador] = normalizar_texto(conteudo)

    return clausulas


def calcular_similaridade(texto_a: str, texto_b: str) -> float:
    """
    Calcula a similaridade entre dois textos normalizados usando
    difflib.SequenceMatcher.

    Retorna:
        float entre 0.0 (completamente diferente) e 1.0 (idêntico).
    """
    return difflib.SequenceMatcher(
        None,
        normalizar_texto(texto_a),
        normalizar_texto(texto_b),
    ).ratio()


# --------------------------------------------------------------------------- #
# Helpers internos                                                             #
# --------------------------------------------------------------------------- #

def _carregar_modelo_base(modelo: str, diretorio_base: Optional[str] = None) -> str:
    """
    Carrega o arquivo de modelo base correspondente ao tipo de contrato.

    Parâmetros:
        modelo: "novo" ou "antigo_v13".
        diretorio_base: diretório onde os arquivos base estão. Se None, usa
            o mesmo diretório do módulo.

    Lança:
        ValueError: Se o modelo não for reconhecido.
        FileNotFoundError: Se o arquivo base não for encontrado.
    """
    if modelo not in ARQUIVOS_BASE:
        raise ValueError(
            f"Modelo '{modelo}' não reconhecido. "
            f"Esperado: {list(ARQUIVOS_BASE.keys())}."
        )

    nome_arquivo = ARQUIVOS_BASE[modelo]
    diretorio    = Path(diretorio_base) if diretorio_base else Path(__file__).parent
    caminho      = diretorio / nome_arquivo

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo de modelo base não encontrado: '{caminho}'. "
            f"Certifique-se de que '{nome_arquivo}' está no diretório '{diretorio}'."
        )

    return caminho.read_text(encoding="utf-8")


def _determinar_nivel_risco(
    clausulas_alteradas: list[str],
    clausulas_ausentes:  list[str],
    clausulas_extras:    list[str],
    clausulas_base:      dict[str, str],
    clausulas_contrato:  dict[str, str],
) -> str:
    """
    Determina o nível de risco com base nas cláusulas alteradas, ausentes e extras.

    Regras (em ordem de prioridade):
        1. Qualquer cláusula ausente                          → "alto"
        2. Qualquer cláusula extra (não prevista na base)     → "alto"
        3. Qualquer alteração com palavra crítica no conteúdo → "alto"
        4. Qualquer alteração sem palavra crítica              → "medio"
        5. Nenhuma alteração                                  → "baixo"
    """
    if clausulas_ausentes:
        return "alto"

    if clausulas_extras:
        return "alto"

    for marcador in clausulas_alteradas:
        conteudo_base     = clausulas_base.get(marcador, "")
        conteudo_contrato = clausulas_contrato.get(marcador, "")
        texto_combinado   = f"{conteudo_base} {conteudo_contrato}".lower()

        if any(palavra in texto_combinado for palavra in PALAVRAS_CRITICAS):
            return "alto"

    if clausulas_alteradas:
        return "medio"

    return "baixo"


# --------------------------------------------------------------------------- #
# Função principal                                                             #
# --------------------------------------------------------------------------- #

def validar_clausulas(
    modelo:          str,
    texto_contrato:  str,
    diretorio_base:  Optional[str] = None,
) -> dict:
    """
    Valida a integridade das cláusulas do contrato comparando com o modelo oficial.

    Parâmetros:
        modelo (str): Tipo de contrato — "novo" ou "antigo_v13".
        texto_contrato (str): Texto bruto extraído do contrato a validar.
        diretorio_base (str, opcional): Caminho do diretório com os arquivos base.
            Se None, usa o diretório do próprio módulo.

    Retorna:
        dict com:
            - valido (bool): False se houver cláusulas ausentes ou extras;
              cláusulas apenas alteradas não invalidam, apenas impactam o risco.
            - clausulas_alteradas (list[str]): Marcadores com similaridade < 0.97.
            - clausulas_ausentes (list[str]): Marcadores presentes na base mas
              ausentes no contrato.
            - clausulas_extras (list[str]): Marcadores presentes no contrato mas
              ausentes na base — risco jurídico de inserção não autorizada.
            - nivel_risco (str): "baixo", "medio" ou "alto".

    Lança:
        ValueError: Se o modelo não for reconhecido.
        FileNotFoundError: Se o arquivo de modelo base não for encontrado.
    """
    # 1. Carrega e separa cláusulas do modelo base
    texto_base          = _carregar_modelo_base(modelo, diretorio_base)
    clausulas_base      = separar_clausulas(texto_base)
    clausulas_contrato  = separar_clausulas(texto_contrato)

    clausulas_alteradas: list[str] = []
    clausulas_ausentes:  list[str] = []
    clausulas_extras:    list[str] = []

    # 2. Compara cada cláusula da base com o contrato recebido
    for marcador, conteudo_base in clausulas_base.items():
        if marcador not in clausulas_contrato:
            clausulas_ausentes.append(marcador)
            continue

        similaridade = calcular_similaridade(
            conteudo_base,
            clausulas_contrato[marcador],
        )

        if similaridade < SIMILARIDADE_MINIMA:
            clausulas_alteradas.append(marcador)

    # 3. Detecta cláusulas extras (presentes no contrato mas ausentes na base)
    marcadores_base = set(clausulas_base.keys())
    for marcador in clausulas_contrato:
        if marcador not in marcadores_base:
            clausulas_extras.append(marcador)

    # 4. Determina nível de risco
    nivel_risco = _determinar_nivel_risco(
        clausulas_alteradas,
        clausulas_ausentes,
        clausulas_extras,
        clausulas_base,
        clausulas_contrato,
    )

    # Inválido apenas por ausência ou adição de cláusulas — alterações impactam só o risco
    valido = not clausulas_ausentes and not clausulas_extras

    return {
        "valido":              valido,
        "clausulas_alteradas": clausulas_alteradas,
        "clausulas_ausentes":  clausulas_ausentes,
        "clausulas_extras":    clausulas_extras,
        "nivel_risco":         nivel_risco,
    }


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                               #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import tempfile
    import os

    # Modelo base simulado
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

    # Contrato com: cláusula 3 alterada, cláusula 4 ausente e cláusula 5 extra
    CONTRATO_RECEBIDO = """\
1. OBJETO DO CONTRATO
O presente contrato tem por objeto a prestação de serviços de software educacional.

1.1 O serviço será prestado de forma contínua durante o prazo de vigência.

2. PRAZO DE VIGÊNCIA
O contrato terá duração de 12 meses, renovável automaticamente.

3. VALOR E REAJUSTE
O valor mensal poderá ser reajustado a qualquer momento mediante notificação.

5. CLÁUSULA ADICIONAL NÃO PREVISTA
Esta cláusula foi inserida unilateralmente e não consta no modelo oficial.
"""

    # Salva arquivos temporários para simular o diretório de bases
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = os.path.join(tmpdir, "modelo_novo_base.txt")
        with open(base_path, "w", encoding="utf-8") as f:
            f.write(MODELO_BASE)

        resultado = validar_clausulas(
            modelo         = "novo",
            texto_contrato = CONTRATO_RECEBIDO,
            diretorio_base = tmpdir,
        )

    print("=== Validação de Cláusulas ===\n")
    simbolo = "✔" if resultado["valido"] else "✘"
    print(f"  Válido             : {simbolo} {resultado['valido']}")
    print(f"  Nível de risco     : {resultado['nivel_risco'].upper()}")
    print(f"  Cláusulas alteradas: {resultado['clausulas_alteradas'] or '—'}")
    print(f"  Cláusulas ausentes : {resultado['clausulas_ausentes'] or '—'}")
    print(f"  Cláusulas extras   : {resultado['clausulas_extras'] or '—'}")
