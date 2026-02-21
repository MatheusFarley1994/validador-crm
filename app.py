"""
app.py
Validador de CRM + Contrato - Gamefik
Interface Streamlit para extração e validação de dados via PDF/imagem.
"""

import os
import tempfile
import streamlit as st
from pathlib import Path
from pdfminer.high_level import extract_text as extract_text_pdf

from crm_pipeline      import executar_pipeline
from contract_pipeline import executar_pipeline_contrato


# --------------------------------------------------------------------------- #
# Configuração da página                                                       #
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="Validador de CRM - Gamefik",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------- #
# CSS personalizado                                                            #
# --------------------------------------------------------------------------- #

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
}

/* Fundo */
.stApp {
    background-color: #0a0a0f;
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -10%, rgba(99, 57, 255, 0.18) 0%, transparent 60%),
        radial-gradient(ellipse 40% 30% at 90% 80%, rgba(255, 87, 51, 0.08) 0%, transparent 50%);
}

/* Títulos */
h1, h2, h3 {
    font-family: 'Syne', sans-serif !important;
}

/* Header principal */
.gamefik-header {
    text-align: center;
    padding: 3rem 0 2rem;
    border-bottom: 1px solid rgba(99, 57, 255, 0.3);
    margin-bottom: 2.5rem;
}

.gamefik-logo {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.35em;
    color: #6339ff;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.gamefik-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    color: #f0eeff;
    line-height: 1.1;
    margin: 0;
}

.gamefik-title span {
    color: #6339ff;
}

.gamefik-subtitle {
    color: rgba(240, 238, 255, 0.4);
    font-size: 0.8rem;
    margin-top: 0.75rem;
    letter-spacing: 0.05em;
}

/* Cards */
.card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(99, 57, 255, 0.2);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
}

.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: #6339ff;
    text-transform: uppercase;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Arquivo tag */
.file-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(99, 57, 255, 0.12);
    border: 1px solid rgba(99, 57, 255, 0.3);
    border-radius: 6px;
    padding: 0.3rem 0.7rem;
    font-size: 0.78rem;
    color: #c4b8ff;
    margin: 0.2rem;
}

.file-tag.error {
    background: rgba(255, 69, 58, 0.1);
    border-color: rgba(255, 69, 58, 0.3);
    color: #ff8b82;
}

/* Tabela de dados */
.data-table {
    width: 100%;
    border-collapse: collapse;
}

.data-table tr {
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.data-table tr:last-child {
    border-bottom: none;
}

.data-table td {
    padding: 0.55rem 0.5rem;
    font-size: 0.8rem;
    vertical-align: top;
}

.data-table td:first-child {
    color: rgba(240, 238, 255, 0.4);
    width: 38%;
    letter-spacing: 0.03em;
}

.data-table td:last-child {
    color: #f0eeff;
    font-weight: 400;
}

.data-table td.null-value {
    color: rgba(240, 238, 255, 0.2);
    font-style: italic;
}

/* Status badges */
.badge-valido {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(52, 199, 89, 0.12);
    border: 1px solid rgba(52, 199, 89, 0.4);
    color: #34c759;
    border-radius: 100px;
    padding: 0.4rem 1rem;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
}

.badge-invalido {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(255, 69, 58, 0.12);
    border: 1px solid rgba(255, 69, 58, 0.4);
    color: #ff453a;
    border-radius: 100px;
    padding: 0.4rem 1rem;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
}

.badge-revisao {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(255, 159, 10, 0.12);
    border: 1px solid rgba(255, 159, 10, 0.4);
    color: #ff9f0a;
    border-radius: 100px;
    padding: 0.4rem 1rem;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
}

/* Lista de erros */
.error-item {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.6rem 0.8rem;
    background: rgba(255, 69, 58, 0.07);
    border-left: 2px solid #ff453a;
    border-radius: 0 6px 6px 0;
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    color: #ff8b82;
}

.error-dot {
    color: #ff453a;
    font-size: 0.6rem;
    margin-top: 0.25rem;
    flex-shrink: 0;
}

/* Warning item */
.warning-item {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.6rem 0.8rem;
    background: rgba(255, 159, 10, 0.07);
    border-left: 2px solid #ff9f0a;
    border-radius: 0 6px 6px 0;
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    color: #ffcc60;
}

/* Info row para contrato */
.info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.45rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.8rem;
}

.info-row:last-child { border-bottom: none; }
.info-label { color: rgba(240,238,255,0.4); }
.info-value { color: #f0eeff; }

/* Risco badges */
.risco-baixo  { color: #34c759; }
.risco-medio  { color: #ff9f0a; }
.risco-alto   { color: #ff453a; }

/* Cláusula tag */
.clausula-tag {
    display: inline-block;
    background: rgba(255, 69, 58, 0.1);
    border: 1px solid rgba(255, 69, 58, 0.25);
    border-radius: 4px;
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
    color: #ff8b82;
    margin: 0.15rem;
}

.clausula-tag.extra {
    background: rgba(255, 159, 10, 0.1);
    border-color: rgba(255, 159, 10, 0.25);
    color: #ffcc60;
}

.clausula-tag.alterada {
    background: rgba(99, 57, 255, 0.1);
    border-color: rgba(99, 57, 255, 0.3);
    color: #c4b8ff;
}

/* Banner status geral */
.status-banner {
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: 0.06em;
}

.status-banner.valido {
    background: rgba(52, 199, 89, 0.08);
    border: 1px solid rgba(52, 199, 89, 0.3);
    color: #34c759;
}

.status-banner.invalido {
    background: rgba(255, 69, 58, 0.08);
    border: 1px solid rgba(255, 69, 58, 0.3);
    color: #ff453a;
}

.status-banner.revisao_manual {
    background: rgba(255, 159, 10, 0.08);
    border: 1px solid rgba(255, 159, 10, 0.3);
    color: #ff9f0a;
}

/* Texto consolidado */
.text-preview {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 1rem;
    font-size: 0.75rem;
    color: rgba(240, 238, 255, 0.5);
    line-height: 1.7;
    max-height: 180px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid rgba(99, 57, 255, 0.15);
    margin: 2rem 0;
}

/* Upload area override */
[data-testid="stFileUploader"] {
    background: rgba(99, 57, 255, 0.04) !important;
    border: 1px dashed rgba(99, 57, 255, 0.35) !important;
    border-radius: 12px !important;
    padding: 0.5rem !important;
}

/* Botão */
.stButton > button {
    background: #6339ff !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.06em !important;
    padding: 0.65rem 2rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}

.stButton > button:hover {
    background: #7a55ff !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(99, 57, 255, 0.35) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* Spinner */
.stSpinner > div {
    border-top-color: #6339ff !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99, 57, 255, 0.4); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Helpers de renderização — CRM (inalterados)                                  #
# --------------------------------------------------------------------------- #

LABELS = {
    "nome":             "Nome",
    "nome_escola":      "Escola",
    "vendedor":         "Vendedor",
    "perfil_escola":    "Perfil",
    "numero_alunos":    "Nº de alunos",
    "nivel_prioridade": "Prioridade",
    "mrr":              "MRR",
    "arr":              "ARR",
    "dor_escola":       "Dor da escola",
    "valor_implantacao":"Valor implantação",
    "link_contrato":    "Link contrato",
    "forma_implantacao":"Forma implantação",
    "contato_nome":     "Contato",
    "contato_telefone": "Telefone",
    "contato_email":    "E-mail",
}


def _render_dados(dados: dict) -> None:
    rows = ""
    for campo, label in LABELS.items():
        valor = dados.get(campo)
        if valor is None:
            rows += f'<tr><td>{label}</td><td class="null-value">—</td></tr>'
        else:
            rows += f"<tr><td>{label}</td><td>{valor}</td></tr>"
    st.markdown(
        f'<table class="data-table"><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_resultado(resultado: dict) -> None:
    status = resultado["status"]
    erros  = resultado["erros"]

    if status == "valido":
        st.markdown(
            '<div style="margin-bottom:1rem">'
            '<span class="badge-valido">✓ &nbsp;VÁLIDO</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="margin-bottom:1rem">'
            '<span class="badge-invalido">✗ &nbsp;INVÁLIDO</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        for erro in erros:
            st.markdown(
                f'<div class="error-item">'
                f'<span class="error-dot">●</span>{erro}'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_arquivos(sucessos: list, falhas: list) -> None:
    html = ""
    for f in sucessos:
        nome = Path(f).name
        html += f'<span class="file-tag">📄 {nome}</span>'
    for f, motivo in falhas:
        nome = Path(f).name
        html += f'<span class="file-tag error" title="{motivo}">⚠ {nome}</span>'
    st.markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Helpers de renderização — Contrato                                           #
# --------------------------------------------------------------------------- #

_RISCO_COR   = {"baixo": "risco-baixo", "medio": "risco-medio", "alto": "risco-alto"}
_RISCO_ICONE = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}
_STATUS_BADGE = {
    "valido":         '<span class="badge-valido">✓ &nbsp;VÁLIDO</span>',
    "invalido":       '<span class="badge-invalido">✗ &nbsp;INVÁLIDO</span>',
    "revisao_manual": '<span class="badge-revisao">⚠ &nbsp;REVISÃO MANUAL</span>',
}


def _render_contrato(saida_contrato: dict) -> None:
    """Renderiza o card de resultado do pipeline de contrato."""
    vc  = saida_contrato["validacao_campos"]
    vcl = saida_contrato["validacao_clausulas"]
    status  = saida_contrato["status_final"]
    risco   = saida_contrato["nivel_risco"]
    modelo  = saida_contrato["modelo"]

    risco_css  = _RISCO_COR.get(risco, "")
    risco_icon = _RISCO_ICONE.get(risco, "")
    badge      = _STATUS_BADGE.get(status, "")

    # Status + modelo + risco
    st.markdown(
        f'<div style="margin-bottom:0.75rem">{badge}</div>'
        f'<div class="info-row"><span class="info-label">Modelo</span>'
        f'<span class="info-value">{modelo}</span></div>'
        f'<div class="info-row"><span class="info-label">Nível de risco</span>'
        f'<span class="info-value {risco_css}">{risco_icon} {risco.upper()}</span></div>',
        unsafe_allow_html=True,
    )

    # Erros de campos
    if vc["erros_criticos"]:
        st.markdown('<div style="margin-top:0.75rem">', unsafe_allow_html=True)
        for e in vc["erros_criticos"]:
            st.markdown(
                f'<div class="error-item"><span class="error-dot">●</span>{e}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # Warnings de campos
    if vc["warnings"]:
        for w in vc["warnings"]:
            st.markdown(
                f'<div class="warning-item"><span style="color:#ff9f0a;font-size:0.6rem;margin-top:0.25rem">▲</span>{w}</div>',
                unsafe_allow_html=True,
            )

    # Cláusulas
    def _clausula_tags(marcadores: list, css_class: str) -> str:
        return "".join(
            f'<span class="clausula-tag {css_class}">{m}</span>'
            for m in marcadores
        )

    if vcl["clausulas_ausentes"]:
        st.markdown(
            f'<div style="margin-top:0.6rem;font-size:0.75rem;color:rgba(240,238,255,0.4);margin-bottom:0.25rem">Ausentes</div>'
            + _clausula_tags(vcl["clausulas_ausentes"], ""),
            unsafe_allow_html=True,
        )

    if vcl["clausulas_extras"]:
        st.markdown(
            f'<div style="margin-top:0.6rem;font-size:0.75rem;color:rgba(240,238,255,0.4);margin-bottom:0.25rem">Extras</div>'
            + _clausula_tags(vcl["clausulas_extras"], "extra"),
            unsafe_allow_html=True,
        )

    if vcl["clausulas_alteradas"]:
        st.markdown(
            f'<div style="margin-top:0.6rem;font-size:0.75rem;color:rgba(240,238,255,0.4);margin-bottom:0.25rem">Alteradas</div>'
            + _clausula_tags(vcl["clausulas_alteradas"], "alterada"),
            unsafe_allow_html=True,
        )

    if not any([vc["erros_criticos"], vcl["clausulas_ausentes"],
                vcl["clausulas_extras"], vcl["clausulas_alteradas"]]):
        st.markdown(
            '<p style="color:rgba(240,238,255,0.3);font-size:0.78rem;margin-top:0.5rem">'
            'Nenhum problema encontrado.</p>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Lógica de separação e consolidação                                           #
# --------------------------------------------------------------------------- #

def _separar_arquivos(uploaded_files) -> tuple[list, list]:
    """Retorna (imagens, pdfs) separados por extensão."""
    imagens, pdfs = [], []
    for uf in uploaded_files:
        ext = Path(uf.name).suffix.lower()
        if ext == ".pdf":
            pdfs.append(uf)
        else:
            imagens.append(uf)
    return imagens, pdfs


def _status_geral(status_crm: str, status_contrato: str) -> str:
    """
    Consolida os dois status em um único status_geral.

    Regras (ordem de prioridade):
        1. CRM inválido                 → "invalido"
        2. Contrato inválido            → "invalido"
        3. Contrato em revisão manual   → "revisao_manual"
        4. Caso contrário               → "valido"
    """
    if status_crm == "invalido":
        return "invalido"
    if status_contrato == "invalido":
        return "invalido"
    if status_contrato == "revisao_manual":
        return "revisao_manual"
    return "valido"


def _render_banner_status(status: str) -> None:
    """Exibe o banner de status geral no topo dos resultados."""
    config = {
        "valido":         ("✔", "APROVADO — CRM e contrato válidos"),
        "invalido":       ("✘", "REPROVADO — Foram encontrados erros críticos"),
        "revisao_manual": ("⚠", "REVISÃO MANUAL — Cláusulas alteradas ou risco elevado"),
    }
    icone, texto = config.get(status, ("?", status.upper()))
    st.markdown(
        f'<div class="status-banner {status}">'
        f'<span style="font-size:1.2rem">{icone}</span>'
        f'<span>{texto}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_erro_inline(titulo: str, mensagem: str) -> None:
    st.markdown(
        f'<div class="card"><div class="card-title">⚠ {titulo}</div>'
        f'<div class="error-item"><span class="error-dot">●</span>{mensagem}</div></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Interface principal                                                          #
# --------------------------------------------------------------------------- #

# Header
st.markdown("""
<div class="gamefik-header">
    <div class="gamefik-logo">🎮 Gamefik</div>
    <h1 class="gamefik-title">Validador de <span>CRM</span></h1>
    <p class="gamefik-subtitle">Extração e validação automática de dados via IA · PDF & Imagens</p>
</div>
""", unsafe_allow_html=True)

# Layout em colunas
col_upload, col_result = st.columns([1, 1.6], gap="large")

with col_upload:
    st.markdown('<div class="card-title">📁 &nbsp;Arquivos</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        label="Arraste ou selecione arquivos",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        imagens_preview, pdfs_preview = _separar_arquivos(uploaded_files)
        st.markdown(
            f'<p style="color:rgba(240,238,255,0.35);font-size:0.75rem;margin:0.5rem 0 0.25rem">'
            f'{len(uploaded_files)} arquivo(s) &nbsp;·&nbsp; '
            f'{len(imagens_preview)} imagem(ns) &nbsp;·&nbsp; '
            f'{len(pdfs_preview)} PDF(s)</p>',
            unsafe_allow_html=True,
        )

    btn_validar = st.button("▶ &nbsp;Validar", disabled=not uploaded_files)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:rgba(240,238,255,0.2);font-size:0.72rem;line-height:1.6">'
        '<strong style="color:rgba(240,238,255,0.4)">Imagens (JPG, PNG)</strong> → Pipeline CRM<br>'
        '<strong style="color:rgba(240,238,255,0.4)">PDF</strong> → Pipeline Contrato<br><br>'
        'Envie ao menos 1 imagem e exatamente 1 PDF.<br><br>'
        'Certifique-se que a variável <code style="color:#6339ff">ANTHROPIC_API_KEY</code> está configurada.'
        '</p>',
        unsafe_allow_html=True,
    )


with col_result:

    if btn_validar and uploaded_files:

        imagens, pdfs = _separar_arquivos(uploaded_files)

        # ── Validações de entrada ────────────────────────────────────────── #
        if not imagens:
            _render_erro_inline("Arquivos insuficientes", "Envie ao menos uma imagem (JPG ou PNG) com os prints do CRM.")
            st.stop()

        if not pdfs:
            _render_erro_inline("Arquivo ausente", "Envie o contrato em formato PDF.")
            st.stop()

        if len(pdfs) > 1:
            _render_erro_inline("PDFs em excesso", f"Apenas 1 PDF é permitido por validação. Foram enviados {len(pdfs)}.")
            st.stop()

        # ── Salva arquivos temporários ───────────────────────────────────── #
        with tempfile.TemporaryDirectory() as tmpdir:

            caminhos_imagens = []
            for uf in imagens:
                destino = os.path.join(tmpdir, uf.name)
                with open(destino, "wb") as f:
                    f.write(uf.getbuffer())
                caminhos_imagens.append(destino)

            caminho_pdf = os.path.join(tmpdir, pdfs[0].name)
            with open(caminho_pdf, "wb") as f:
                f.write(pdfs[0].getbuffer())

            # ── Pipeline CRM (imagens) ───────────────────────────────────── #
            with st.spinner("Processando CRM..."):
                try:
                    saida_crm = executar_pipeline(caminhos_imagens)
                except ValueError as e:
                    _render_erro_inline("Erro no pipeline CRM", str(e))
                    st.stop()
                except RuntimeError as e:
                    _render_erro_inline("Falha no pipeline CRM", str(e))
                    st.stop()

            # ── Pipeline Contrato (PDF) ──────────────────────────────────── #
            with st.spinner("Processando contrato..."):
                try:
                    texto_contrato = extract_text_pdf(caminho_pdf)
                    if not texto_contrato or not texto_contrato.strip():
                        raise ValueError("O PDF do contrato não contém texto legível.")
                    saida_contrato = executar_pipeline_contrato(
                        texto_contrato = texto_contrato,
                    )
                except ValueError as e:
                    _render_erro_inline("Erro no pipeline Contrato", str(e))
                    st.stop()
                except FileNotFoundError as e:
                    _render_erro_inline("Arquivo base não encontrado", str(e))
                    st.stop()
                except RuntimeError as e:
                    _render_erro_inline("Falha no pipeline Contrato", str(e))
                    st.stop()

            # ── Consolidação ─────────────────────────────────────────────── #
            status_crm = saida_crm["resultado"]["status"]
            status_geral = _status_geral(status_crm, saida_contrato["status_final"])

            # ── Banner de status geral ───────────────────────────────────── #
            _render_banner_status(status_geral)

            # ── Arquivos processados ─────────────────────────────────────── #
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📂 &nbsp;Arquivos processados</div>', unsafe_allow_html=True)
            _render_arquivos(saida_crm["sucessos"], saida_crm["falhas"])
            st.markdown(f'<span class="file-tag">📑 {pdfs[0].name}</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Texto CRM consolidado ────────────────────────────────────── #
            with st.expander("🔍  Ver texto extraído do CRM", expanded=False):
                st.markdown(
                    f'<div class="text-preview">{saida_crm["texto"][:1200]}'
                    f'{"…" if len(saida_crm["texto"]) > 1200 else ""}</div>',
                    unsafe_allow_html=True,
                )

            # ── Dados CRM + Validação CRM ────────────────────────────────── #
            c1, c2 = st.columns([1.3, 1])

            with c1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">🗂 &nbsp;Dados CRM extraídos</div>', unsafe_allow_html=True)
                _render_dados(saida_crm["dados"])
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">✅ &nbsp;Validação CRM</div>', unsafe_allow_html=True)
                _render_resultado(saida_crm["resultado"])
                st.markdown('</div>', unsafe_allow_html=True)

            # ── Card Contrato ────────────────────────────────────────────── #
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📜 &nbsp;Validação do Contrato</div>', unsafe_allow_html=True)
            _render_contrato(saida_contrato)
            st.markdown('</div>', unsafe_allow_html=True)

    elif not uploaded_files:
        st.markdown("""
        <div style="
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            height:320px;
            color:rgba(240,238,255,0.15);
            text-align:center;
            gap:0.75rem;
        ">
            <div style="font-size:2.5rem">📂</div>
            <div style="font-family:'Syne',sans-serif;font-size:0.85rem;letter-spacing:0.08em">
                NENHUM ARQUIVO ENVIADO
            </div>
            <div style="font-size:0.72rem;max-width:240px;line-height:1.6">
                Envie as imagens do CRM e o PDF do contrato para iniciar a validação
            </div>
        </div>
        """, unsafe_allow_html=True)
