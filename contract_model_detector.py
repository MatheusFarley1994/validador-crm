"""
contract_model_detector.py
Detecção automática do modelo de contrato com base em marcadores textuais.
Não utiliza IA — apenas lógica de busca por strings com regras definidas.
"""

from typing import Optional


# --------------------------------------------------------------------------- #
# Marcadores por modelo                                                        #
# --------------------------------------------------------------------------- #

MARCADORES: dict[str, list[str]] = {
    "novo": [
        "ANEXO 1 - TABELA RESUMO COMERCIAL",
        "CONTRATO DE ASSINATURA DE SOFTWARE (SaaS)",
    ],
    "antigo_v13": [
        "saldo em loja",
        "Contrato Escolas v13",
    ],
}

# Valores de confiança
CONFIANCA_ENCONTRADO  = 0.95
CONFIANCA_AMBIGUO     = 0.50
CONFIANCA_DESCONHECIDO = 0.0


# --------------------------------------------------------------------------- #
# Função principal                                                             #
# --------------------------------------------------------------------------- #

def detectar_modelo_contrato(texto: str) -> dict:
    """
    Detecta o modelo de contrato presente em um texto extraído via OCR.

    A detecção é baseada exclusivamente em marcadores textuais predefinidos,
    sem uso de inteligência artificial.

    Parâmetros:
        texto (str): Texto bruto extraído do contrato (ex: via OCR ou PDF).

    Retorna:
        dict com as chaves:
            - modelo (str): "novo", "antigo_v13" ou "desconhecido".
            - confianca (float): 0.95 (certeza), 0.5 (ambíguo) ou 0.0 (não identificado).
            - marcadores_encontrados (list[str]): Lista dos marcadores detectados no texto.
    """
    texto_lower = texto.lower()
    encontrados_por_modelo: dict[str, list[str]] = {}

    # Busca case-insensitive por cada marcador de cada modelo
    for modelo, marcadores in MARCADORES.items():
        achados = [
            marcador
            for marcador in marcadores
            if marcador.lower() in texto_lower
        ]
        if achados:
            encontrados_por_modelo[modelo] = achados

    marcadores_encontrados: list[str] = [
        marcador
        for achados in encontrados_por_modelo.values()
        for marcador in achados
    ]

    modelos_detectados = list(encontrados_por_modelo.keys())

    # Determinação do modelo e confiança
    if len(modelos_detectados) == 1:
        modelo    = modelos_detectados[0]
        confianca = CONFIANCA_ENCONTRADO

    elif len(modelos_detectados) > 1:
        modelo    = "desconhecido"
        confianca = CONFIANCA_AMBIGUO

    else:
        modelo    = "desconhecido"
        confianca = CONFIANCA_DESCONHECIDO

    return {
        "modelo":                modelo,
        "confianca":             confianca,
        "marcadores_encontrados": marcadores_encontrados,
    }


# --------------------------------------------------------------------------- #
# Exemplo de uso                                                               #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    exemplos = [
        (
            "Contrato de Assinatura de Software (SaaS)\n"
            "ANEXO 1 - Tabela Resumo Comercial\n"
            "Valor mensal: R$ 1.500,00",
        ),
        (
            "Contrato Escolas v13\n"
            "Saldo em Loja disponível: R$ 200,00\n"
            "Vigência: 12 meses",
        ),
        (
            "Este documento não contém marcadores reconhecidos.\n"
            "Apenas texto genérico.",
        ),
        (
            # Caso ambíguo: marcadores de ambos os modelos
            "ANEXO 1 - TABELA RESUMO COMERCIAL\n"
            "Contrato Escolas v13",
        ),
    ]

    rotulos = ["Modelo novo", "Modelo antigo_v13", "Desconhecido", "Ambíguo"]

    for rotulo, texto in zip(rotulos, exemplos):
        resultado = detectar_modelo_contrato(texto)
        print(f"── {rotulo} {'─' * (35 - len(rotulo))}")
        print(f"   modelo    : {resultado['modelo']}")
        print(f"   confiança : {resultado['confianca']}")
        print(f"   marcadores: {resultado['marcadores_encontrados']}")
        print()
