from contract_pipeline import executar_pipeline_contrato

TEXTO_CONTRATO = """
CONTRATO DE ASSINATURA DE SOFTWARE (SaaS)
ANEXO 1 - TABELA RESUMO COMERCIAL

Total de Alunos: 420
Valor de Implantação: R$ 3.500,00
"""

DADOS_CRM = {
    "numero_alunos": 350,          # diferente de 420
    "valor_implantacao": 3500      # igual
}

resultado = executar_pipeline_contrato(
    texto_contrato=TEXTO_CONTRATO,
    dados_crm=DADOS_CRM
)

print("\nRESULTADO FINAL:")
print(resultado)