import html
import io
import re
import unicodedata
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Dashboard de Estudos", layout="wide")


THEMES = {
    "Escuro": {
        "bg": "#0E1117",
        "sidebar_bg": "#111827",
        "panel": "#161B22",
        "panel_soft": "rgba(255,255,255,0.04)",
        "text": "#F9FAFB",
        "muted": "#9CA3AF",
        "border": "rgba(250,250,250,0.12)",
        "input_bg": "#111827",
        "grid_bg": "#0F172A",
        "grid_header": "#1F2937",
        "mark_bg": "#5B4B00",
        "mark_text": "#FFF4B2",
        "plotly_template": "plotly_dark",
    },
    "Claro": {
        "bg": "#FFFFFF",
        "sidebar_bg": "#F8FAFC",
        "panel": "#F6F8FA",
        "panel_soft": "rgba(0,0,0,0.035)",
        "text": "#111827",
        "muted": "#4B5563",
        "border": "rgba(17,24,39,0.10)",
        "input_bg": "#FFFFFF",
        "grid_bg": "#FFFFFF",
        "grid_header": "#EEF2F7",
        "mark_bg": "#FFF2A8",
        "mark_text": "#1F2937",
        "plotly_template": "plotly_white",
    },
}


@st.cache_data(show_spinner=False)
def load_csv_from_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    df["source_file"] = file_name
    return df


@st.cache_data(show_spinner=False)
def combine_dataframes(dataframes: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frames = [df.copy() for df in dataframes if df is not None and not df.empty]
    if not frames:
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True, sort=False)
    if "source_file" not in merged.columns:
        merged["source_file"] = "desconhecido"

    merged = normalize_columns(merged)
    merged["_doi_norm"] = merged["DOI"].map(normalize_doi) if "DOI" in merged.columns else ""
    merged["_title_norm"] = merged["Title"].map(normalize_text) if "Title" in merged.columns else ""
    merged["_dedupe_key"] = merged["_doi_norm"]
    empty_key = merged["_dedupe_key"].astype(str).str.strip().eq("")
    merged.loc[empty_key, "_dedupe_key"] = merged.loc[empty_key, "_title_norm"]
    return merged


def classify_citations_bucket(value: object) -> str:
    try:
        if pd.isna(value):
            return "unknown"
    except Exception:
        pass

    try:
        citations = float(value)
    except (TypeError, ValueError):
        return "unknown"

    if citations < 0:
        return "unknown"
    if citations == 0:
        return "0"
    if citations <= 9:
        return "1-9"
    if citations <= 49:
        return "10-49"
    if citations <= 99:
        return "50-99"
    return "100+"




def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["Year", "Citations"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Citations" in df.columns:
        df["citations_bucket"] = df["Citations"].apply(classify_citations_bucket)
    elif "citations_bucket" not in df.columns:
        df["citations_bucket"] = "unknown"

    return df


def available(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


def categorical_options(df: pd.DataFrame, col: str):
    if not available(df, col):
        return []
    return sorted([x for x in df[col].dropna().astype(str).unique().tolist() if x.strip()])


def safe_text(value) -> str:
    if value is None:
        return "Não disponível."
    try:
        if pd.isna(value):
            return "Não disponível."
    except Exception:
        pass
    value = str(value).strip()
    return value if value else "Não disponível."


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_doi(value: object) -> str:
    doi = normalize_text(value)
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.replace("doi:", "").strip()
    return doi


def doi_url(value: object) -> str:
    normalized = normalize_doi(value)
    return f"https://doi.org/{normalized}" if normalized else ""


def deduplicate_studies(df: pd.DataFrame, strategy: str) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0

    working = df.copy()
    valid_key = working["_dedupe_key"].astype(str).str.strip().ne("")

    if strategy == "Manter maior número de citações" and "Citations" in working.columns:
        working = working.sort_values("Citations", ascending=False, na_position="last")
    elif strategy == "Manter artigo mais recente" and "Year" in working.columns:
        working = working.sort_values("Year", ascending=False, na_position="last")

    with_key = working[valid_key].drop_duplicates(subset=["_dedupe_key"], keep="first")
    without_key = working[~valid_key]
    deduped = pd.concat([with_key, without_key], ignore_index=True, sort=False)
    removed = len(working) - len(deduped)
    return deduped, removed


def highlight_text(text: str, query: str, theme_name: str, exact_match: bool = False) -> str:
    safe = html.escape(safe_text(text))
    query = (query or "").strip()
    if not query:
        return safe

    if exact_match:
        terms = [re.escape(query)]
    else:
        terms = [re.escape(term) for term in query.split() if term.strip()]
    if not terms:
        return safe

    theme = THEMES[theme_name]
    pattern = re.compile(r"(" + "|".join(terms) + r")", re.IGNORECASE)
    return pattern.sub(
        rf"<mark style='background:{theme['mark_bg']}; color:{theme['mark_text']}; padding:0 0.15rem; border-radius:0.2rem;'>\1</mark>",
        safe,
    )


def style_plotly(fig, theme_name: str):
    theme = THEMES[theme_name]
    fig.update_layout(
        template=theme["plotly_template"],
        paper_bgcolor=theme["panel"],
        plot_bgcolor=theme["panel"],
        font=dict(color=theme["text"]),
        title=dict(font=dict(color=theme["text"])),
        legend=dict(font=dict(color=theme["text"]), title=dict(font=dict(color=theme["text"]))),
        hoverlabel=dict(font=dict(color=theme["text"])),
        margin=dict(l=20, r=20, t=55, b=20),
    )
    fig.update_xaxes(
        gridcolor=theme["border"],
        zerolinecolor=theme["border"],
        linecolor=theme["border"],
        tickfont=dict(color=theme["text"]),
        title_font=dict(color=theme["text"]),
    )
    fig.update_yaxes(
        gridcolor=theme["border"],
        zerolinecolor=theme["border"],
        linecolor=theme["border"],
        tickfont=dict(color=theme["text"]),
        title_font=dict(color=theme["text"]),
    )
    fig.update_traces(
        textfont_color=theme["text"],
        insidetextfont=dict(color=theme["text"]),
        outsidetextfont=dict(color=theme["text"]),
        hoverlabel=dict(font=dict(color=theme["text"])),
    )
    return fig


def apply_theme(theme_name: str):
    theme = THEMES[theme_name]
    st.markdown(
        f"""
        <style>
            html, body, [data-testid="stAppViewContainer"], .stApp {{
                background: {theme['bg']} !important;
                color: {theme['text']} !important;
            }}
            [data-testid="stHeader"] {{
                background: {theme['bg']} !important;
            }}
            [data-testid="stSidebar"] {{
                background: {theme['sidebar_bg']} !important;
            }}
            [data-testid="stSidebar"] * {{
                color: {theme['text']} !important;
            }}
            .block-container {{
                background: {theme['bg']} !important;
                color: {theme['text']} !important;
            }}
            h1, h2, h3, h4, h5, h6, p, label, span, div {{
                color: inherit;
            }}
            div[data-baseweb="select"] > div,
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div,
            .stTextInput > div > div > input,
            .stNumberInput input,
            .stSelectbox div[data-baseweb="select"] > div,
            .stMultiSelect div[data-baseweb="select"] > div,
            .stDateInput input,
            .stFileUploader section,
            .stSlider > div[data-baseweb="slider"],
            textarea {{
                background: {theme['input_bg']} !important;
                color: {theme['text']} !important;
                border-color: {theme['border']} !important;
            }}
            div[data-baseweb="select"] span,
            div[data-baseweb="select"] input,
            .stTextInput input,
            textarea {{
                color: {theme['text']} !important;
            }}
            div[role="listbox"] {{
                background: {theme['input_bg']} !important;
                color: {theme['text']} !important;
                border: 1px solid {theme['border']} !important;
            }}
            div[role="option"] {{
                background: {theme['input_bg']} !important;
                color: {theme['text']} !important;
            }}
            div[data-testid="stMetric"] {{
                background: {theme['panel_soft']} !important;
                border: 1px solid {theme['border']} !important;
                padding: 0.6rem 0.8rem;
                border-radius: 0.8rem;
            }}
            div[data-testid="stMetric"] * {{
                color: {theme['text']} !important;
            }}
            div[data-testid="stExpander"] {{
                border: 1px solid {theme['border']} !important;
                border-radius: 0.8rem;
                overflow: hidden;
                background: {theme['panel']} !important;
            }}
            div[data-testid="stDataFrame"],
            div[data-testid="stTable"] {{
                border: 1px solid {theme['border']} !important;
                border-radius: 0.8rem;
                overflow: hidden;
                background: {theme['grid_bg']} !important;
            }}
            [data-testid="stDataFrameResizable"] {{
                background: {theme['grid_bg']} !important;
            }}
            [data-testid="stDataFrameResizable"] * {{
                color: {theme['text']} !important;
            }}
            [data-testid="stDataFrame"] [role="grid"],
            [data-testid="stDataFrame"] canvas {{
                background: {theme['grid_bg']} !important;
            }}
            div.stDownloadButton > button,
            div.stButton > button,
            button[kind="secondary"] {{
                background: {theme['panel']} !important;
                color: {theme['text']} !important;
                border: 1px solid {theme['border']} !important;
            }}
            .paper-card {{
                padding: 0.9rem 1rem;
                border-radius: 0.7rem;
                background: {theme['panel']} !important;
                border: 1px solid {theme['border']} !important;
                color: {theme['text']} !important;
            }}
            .mini-muted {{
                color: {theme['muted']} !important;
                font-size: 0.92rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


st.title("Dashboard Interativa de Mapeamento Bibliográfico")
st.caption(
    "Carregue um ou mais CSVs para explorar distribuição temporal, tipo de publicação, domínio, "
    "publisher, impacto, filtros avançados e uma seção específica de deduplicação automática."
)

st.sidebar.header("Entrada de dados")
theme_name = st.sidebar.radio("Tema visual", options=["Escuro", "Claro"], index=0)
apply_theme(theme_name)

with st.sidebar.expander("Carregamento de arquivos", expanded=False):
    uploaded_files = st.file_uploader(
        "Selecione um ou mais CSVs",
        type=["csv"],
        accept_multiple_files=True,
    )

frames: list[pd.DataFrame] = []
load_errors: list[str] = []

for uploaded in uploaded_files or []:
    try:
        frames.append(load_csv_from_bytes(uploaded.getvalue(), uploaded.name))
    except Exception as exc:
        load_errors.append(f"{uploaded.name}: {exc}")

if load_errors:
    with st.sidebar.expander("Arquivos com problema", expanded=False):
        for err in load_errors:
            st.write(f"- {err}")

if not frames:
    st.info("Faça upload de um ou mais CSVs para começar.")
    st.stop()

raw_df = combine_dataframes(frames)
if raw_df.empty:
    st.warning("Nenhum dado pôde ser carregado a partir dos arquivos enviados.")
    st.stop()

with st.sidebar.expander("Deduplicação", expanded=False):
    dedupe_enabled = st.toggle("Ativar deduplicação automática", value=True)
    dedupe_strategy = st.selectbox(
        "Critério para manter duplicatas",
        ["Manter primeiro registro encontrado", "Manter maior número de citações", "Manter artigo mais recente"],
        index=1,
    )

    if dedupe_enabled:
        df, removed_duplicates = deduplicate_studies(raw_df, dedupe_strategy)
    else:
        df, removed_duplicates = raw_df.copy(), 0

    st.markdown(
        f"<div class='mini-muted'>Arquivos lidos: <b>{len(frames)}</b><br>"
        f"Registros antes da deduplicação: <b>{len(raw_df):,}</b><br>"
        f"Duplicatas removidas: <b>{removed_duplicates:,}</b><br>"
        f"Registros atuais: <b>{len(df):,}</b></div>".replace(",", "."),
        unsafe_allow_html=True,
    )
    st.caption("A deduplicação utiliza DOI normalizado e, quando DOI não está disponível, título normalizado.")

st.sidebar.header("Filtros")
search = st.sidebar.text_input("Buscar em título, resumo ou takeaway")
search_exact = st.sidebar.checkbox("Procurar termos exatos", value=False)
exclude_terms = st.sidebar.text_input("Excluir termos dos resultados")

search_value = (search or "").strip()
exclude_value = (exclude_terms or "").strip()
search_terms = [search_value] if search_exact and search_value else [term for term in re.split(r"\s+", search_value) if term]
exclude_search_terms = [exclude_value] if search_exact and exclude_value else [term for term in re.split(r"\s+", exclude_value) if term]

source_file_opts = categorical_options(df, "source_file")
selected_source_files = st.sidebar.multiselect("Arquivos de origem", source_file_opts)

if available(df, "Year"):
    valid_years = df["Year"].dropna()
    if not valid_years.empty:
        min_year = int(valid_years.min())
        max_year = int(valid_years.max())
        year_range = st.sidebar.slider("Ano", min_year, max_year, (min_year, max_year))
    else:
        year_range = None
else:
    year_range = None

filter_columns = [
    ("publication_group_detailed", "Tipo de publicação"),
    ("Study Type", "Study Type"),
    ("publisher_group", "Publisher"),
    ("domain_guess", "Domínio"),
    ("recent_6y", "Últimos 6 anos"),
    ("source_group", "Escopo de origem"),
    ("citations_bucket", "Faixa de citações"),
    ("Journal SJR Quartile", "Quartil SJR"),
]

selected_filters = {}
for col, label in filter_columns:
    opts = categorical_options(df, col)
    if opts:
        selected_filters[col] = st.sidebar.multiselect(label, opts)

filtered = df.copy()

if selected_source_files and available(filtered, "source_file"):
    filtered = filtered[filtered["source_file"].astype(str).isin(selected_source_files)]

if year_range is not None and available(filtered, "Year"):
    filtered = filtered[(filtered["Year"] >= year_range[0]) & (filtered["Year"] <= year_range[1])]

for col, vals in selected_filters.items():
    if vals:
        filtered = filtered[filtered[col].astype(str).isin(vals)]

if search_terms or exclude_search_terms:
    text_cols = [c for c in ["Title", "Abstract", "Takeaway"] if available(filtered, c)]
    if text_cols:
        combined_text = filtered[text_cols].fillna("").astype(str).agg(" ".join, axis=1)

        if search_terms:
            include_mask = pd.Series(True, index=filtered.index)
            for term in search_terms:
                current = combined_text.str.contains(re.escape(term), case=False, na=False, regex=True)
                include_mask = include_mask & current
            filtered = filtered[include_mask]
            combined_text = combined_text.loc[filtered.index]

        if exclude_search_terms:
            exclude_mask = pd.Series(False, index=filtered.index)
            for term in exclude_search_terms:
                current = combined_text.str.contains(re.escape(term), case=False, na=False, regex=True)
                exclude_mask = exclude_mask | current
            filtered = filtered[~exclude_mask]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros filtrados", f"{len(filtered):,}".replace(",", "."))
col2.metric("Registros totais", f"{len(df):,}".replace(",", "."))

if "Citations" in filtered.columns:
    citations_mean = filtered["Citations"].dropna().mean()
    col3.metric("Citações médias", f"{citations_mean:.1f}" if pd.notna(citations_mean) else "0")
else:
    col3.metric("Citações médias", "N/D")

col4.metric("% do corpus", f"{(len(filtered) / len(df) * 100):.1f}%" if len(df) else "0%")

st.divider()

r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    if "Year" in filtered.columns and not filtered["Year"].dropna().empty:
        yearly = filtered.groupby("Year", dropna=True).size().reset_index(name="Amount of studies")
        yearly["Year"] = yearly["Year"].astype(int)
        fig = px.bar(yearly, x="Year", y="Amount of studies", title="Distribution by year")
        st.plotly_chart(style_plotly(fig, theme_name), use_container_width=True)
    else:
        st.warning("Coluna 'Year' não disponível para gráfico temporal.")

# with r1c2:
#     if "publication_group_detailed" in filtered.columns:
#         pub = filtered["publication_group_detailed"].fillna("unknown").value_counts().reset_index()
#         pub.columns = ["Tipo", "Quantidade"]
#         fig = px.pie(pub, names="Tipo", values="Quantidade", title="Tipos de publicação")
#         st.plotly_chart(style_plotly(fig, theme_name), use_container_width=True)
#     else:
#         st.warning("Coluna 'publication_group_detailed' não disponível.")

with r1c2:
    if "citations_bucket" in filtered.columns:
        cb = filtered["citations_bucket"].fillna("unknown").astype(str).value_counts().reset_index()
        cb.columns = ["Range", "Amount of studies"]
        order = ["0", "1-9", "10-49", "50-99", "100+", "unknown"]
        cb["ord"] = cb["Range"].apply(lambda x: order.index(x) if x in order else 999)
        cb = cb.sort_values("ord")
        fig = px.bar(cb, x="Range", y="Amount of studies", title="Citations range")
        st.plotly_chart(style_plotly(fig, theme_name), use_container_width=True)
    else:
        st.warning("Coluna 'citations_bucket' não disponível.")

with r1c3:
    if "Journal SJR Quartile" in filtered.columns and not filtered["Journal SJR Quartile"].dropna().empty:
        yearly = filtered.groupby("Journal SJR Quartile", dropna=True).size().reset_index(name="Amount of studies")
        yearly["Journal SJR Quartile"] = yearly["Journal SJR Quartile"].astype(int)
        fig = px.bar(yearly, x="Journal SJR Quartile", y="Amount of studies", title="Distribution by quartile")
        st.plotly_chart(style_plotly(fig, theme_name), use_container_width=True)
    else:
        st.warning("Coluna 'Year' não disponível para gráfico temporal.")

st.subheader("Tabela exploratória")
st.caption("Clique em uma linha para exibir os detalhes do estudo.")

show_cols = [
    c
    for c in [
        "Title",
        "Authors",
        "Year",
        "Citations",
        "Journal",
        "Journal SJR Quartile",
        "Study Type",
        "publication_group_detailed",
        "publisher_group",
        "domain_guess",
        "recent_6y",
        "source",
        "source_file",
        "DOI",
    ]
    if c in filtered.columns
]

filtered_table = filtered.reset_index(drop=True).copy()
filtered_table.index = filtered_table.index + 1
filtered_table.index.name = "Linha"

event = st.dataframe(
    filtered_table[show_cols],
    use_container_width=True,
    height=520,
    on_select="rerun",
    selection_mode="single-row",
    key="exploratory_table",
)

export_csv = filtered.drop(columns=[c for c in ["_doi_norm", "_title_norm", "_dedupe_key"] if c in filtered.columns]).to_csv(index=False).encode("utf-8")
st.download_button(
    label="Baixar dados filtrados (CSV)",
    data=export_csv,
    file_name="estudos_filtrados_dashboard.csv",
    mime="text/csv",
)

selected_rows = event.selection.rows if event and hasattr(event, "selection") else []

if selected_rows:
    selected_pos = selected_rows[0]
    selected_idx = filtered_table.index[selected_pos]
    selected_study = filtered_table.loc[selected_idx]

    st.divider()
    st.markdown(
        f"<h3>{highlight_text(selected_study.get('Title'), search, theme_name, search_exact)}</h3>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='mini-muted'><b>Journal/Event:</b> {html.escape(safe_text(selected_study.get('Journal')))}"
        f" &nbsp;&nbsp; <b>Arquivo de origem:</b> {html.escape(safe_text(selected_study.get('source_file')))}</div>",
        unsafe_allow_html=True,
    )

    meta_cols = st.columns(3)
    if "Year" in selected_study.index:
        meta_cols[0].metric("Ano", safe_text(selected_study.get("Year")))
    if "Citations" in selected_study.index:
        meta_cols[1].metric("Citações", safe_text(selected_study.get("Citations")))
    if "Journal SJR Quartile" in selected_study.index:
        meta_cols[2].metric("Quartil SJR", safe_text(selected_study.get("Journal SJR Quartile")))

    if "Study Type" in selected_study.index:
        st.caption(f"**Study Type:** {safe_text(selected_study.get('Study Type'))}")
    if "DOI" in selected_study.index and safe_text(selected_study.get("DOI")) != "Não disponível.":
        doi_value = safe_text(selected_study.get("DOI"))
        doi_link = doi_url(doi_value)
        doi_cols = st.columns([6, 1.4])
        doi_cols[0].caption(f"**DOI:** {doi_value}")
        if doi_link:
            doi_cols[1].link_button("Baixar / abrir", doi_link, use_container_width=True)

    takeaway_value = selected_study.get("Takeaway") if "Takeaway" in selected_study.index else None
    abstract_value = selected_study.get("Abstract") if "Abstract" in selected_study.index else None

    st.markdown("### 🧠 Takeaway")
    takeaway_html = highlight_text(takeaway_value, search, theme_name, search_exact)
    st.markdown(f"<div class='paper-card'>{takeaway_html}</div>", unsafe_allow_html=True)

    with st.expander("📄 Ver Abstract completo", expanded=True):
        abstract_html = highlight_text(abstract_value, search, theme_name, search_exact)
        st.markdown(
            f"""
            <div class='paper-card' style="max-height: 420px; overflow-y: auto; text-align: justify; line-height: 1.65;">
                {abstract_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    row_to_copy = filtered_table.iloc[[selected_idx - 1]].drop(
        columns=[c for c in ["_doi_norm", "_title_norm", "_dedupe_key"] if c in filtered_table.columns],
        errors="ignore",
    )
    st.markdown("**Linha selecionada para cópia**")
    st.code(row_to_copy.to_csv(index=False, header=False, sep="	"), language="text")
else:
    st.info("Selecione uma linha na tabela exploratória para visualizar os dados do artigo.")
