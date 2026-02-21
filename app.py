"""
app.py
Validador de CRM - Gamefik
Interface Streamlit para extração e validação de dados via PDF/imagem.
"""

import os
import tempfile
import streamlit as st
from pathlib import Path

from crm_pipeline import executar_pipeline


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
# Helpers de renderização                                                      #
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
        st.markdown(
            f'<p style="color:rgba(240,238,255,0.35);font-size:0.75rem;margin:0.5rem 0 1rem">'
            f'{len(uploaded_files)} arquivo(s) selecionado(s)</p>',
            unsafe_allow_html=True,
        )

    btn_validar = st.button("▶ &nbsp;Validar", disabled=not uploaded_files)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:rgba(240,238,255,0.2);font-size:0.72rem;line-height:1.6">'
        'Formatos aceitos: <strong style="color:rgba(240,238,255,0.4)">PDF, JPG, PNG</strong><br>'
        'Os arquivos são processados localmente e enviados à API da Anthropic para extração.<br><br>'
        'Certifique-se que a variável <code style="color:#6339ff">ANTHROPIC_API_KEY</code> está configurada.'
        '</p>',
        unsafe_allow_html=True,
    )


with col_result:

    if btn_validar and uploaded_files:

        # Salva arquivos em diretório temporário
        with tempfile.TemporaryDirectory() as tmpdir:
            caminhos = []
            for uf in uploaded_files:
                destino = os.path.join(tmpdir, uf.name)
                with open(destino, "wb") as f:
                    f.write(uf.getbuffer())
                caminhos.append(destino)

            with st.spinner("Processando arquivos com IA..."):
                try:
                    saida = executar_pipeline(caminhos)

                except ValueError as e:
                    st.markdown(
                        f'<div class="card"><div class="card-title">⚠ Erro</div>'
                        f'<div class="error-item"><span class="error-dot">●</span>{e}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.stop()

                except RuntimeError as e:
                    st.markdown(
                        f'<div class="card"><div class="card-title">⚠ Falha no pipeline</div>'
                        f'<div class="error-item"><span class="error-dot">●</span>{e}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.stop()

            # ── Arquivos processados ─────────────────────────────────────── #
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📂 &nbsp;Arquivos processados</div>', unsafe_allow_html=True)
            _render_arquivos(saida["sucessos"], saida["falhas"])
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Texto consolidado ────────────────────────────────────────── #
            with st.expander("🔍  Ver texto extraído", expanded=False):
                st.markdown(
                    f'<div class="text-preview">{saida["texto"][:1200]}'
                    f'{"…" if len(saida["texto"]) > 1200 else ""}</div>',
                    unsafe_allow_html=True,
                )

            # ── Dados extraídos e Resultado lado a lado ──────────────────── #
            c1, c2 = st.columns([1.3, 1])

            with c1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">🗂 &nbsp;Dados extraídos</div>', unsafe_allow_html=True)
                _render_dados(saida["dados"])
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">✅ &nbsp;Validação</div>', unsafe_allow_html=True)
                _render_resultado(saida["resultado"])
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
            <div style="font-size:0.72rem;max-width:220px;line-height:1.6">
                Faça upload de um ou mais arquivos para iniciar a validação
            </div>
        </div>
        """, unsafe_allow_html=True)
