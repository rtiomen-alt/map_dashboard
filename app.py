
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="WM MAP BI v6.1", layout="wide")

YEARS_RANGE = range(2020, 2035)

GIANTS = {
    "7705034202",
    "7701215046",
    "4725001168",
    "7729101200"
}

st.markdown("""
<style>
.stApp {
    background:#f4f7fb;
    color:#111827;
}

.metric-card {
    background:white;
    border-radius:16px;
    padding:16px;
    border:1px solid #dbe4f0;
}

.year-card {
    background:white;
    border-radius:16px;
    padding:12px;
    border:1px solid #dbe4f0;
}

.kup-box {
    background:#7c3aed;
    color:white;
    border-radius:12px;
    padding:14px;
    text-align:center;
    font-size:26px;
    font-weight:700;
    margin-top:10px;
}

.badge-pos {
    background:#dcfce7;
    color:#166534;
    padding:6px 10px;
    border-radius:8px;
    margin-top:8px;
    font-weight:700;
}

.badge-neg {
    background:#fee2e2;
    color:#991b1b;
    padding:6px 10px;
    border-radius:8px;
    margin-top:8px;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

def clean_num(x):

    if pd.isna(x):
        return 0.0

    s = (
        str(x)
        .replace("\xa0","")
        .replace(" ","")
        .replace(",",".")
        .strip()
    )

    if s in ["", "-", "nan"]:
        return 0.0

    try:
        return float(s)
    except:
        return 0.0

def format_turnover(v):

    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B$"

    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M$"

    if v >= 1_000:
        return f"{v/1_000:.1f}K$"

    return f"{v:.0f}$"

def format_sales(v):

    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M$"

    if v >= 1_000:
        return f"{v/1_000:.1f}K$"

    return f"{v:.0f}$"

def detect_years(columns):

    years = set()

    for c in columns:
        for y in YEARS_RANGE:
            if str(y) in str(c):
                years.add(y)

    return sorted(list(years))

st.title("WM MAP BI v6.1")

uploaded = st.sidebar.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv","xlsx","xls"]
)

if uploaded:

    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded, encoding="utf-8-sig")
    else:
        df = pd.read_excel(uploaded)

    df.columns = [str(c).strip() for c in df.columns]

    years = detect_years(df.columns)

    current_year = max(years)

    st.sidebar.success(f"Годы: {years}")

    inn_col = [c for c in df.columns if "ИНН" in c][0]
    name_col = [c for c in df.columns if "Наименование" in c][0]

    manager_cols = [c for c in df.columns if "менедж" in c.lower()]

    manager_col = manager_cols[0] if manager_cols else None

    df["ИНН"] = df[inn_col].astype(str)
    df["Клиент"] = df[name_col].astype(str)

    if manager_col:
        df["Менеджер"] = df[manager_col].astype(str)
    else:
        df["Менеджер"] = ""

    for y in years:

        turnover_cols = [
            c for c in df.columns
            if f"Оборот {y}" in c
        ]

        sales_cols = [
            c for c in df.columns
            if f"Продажи {y}" in c and "без НДС" in c
        ]

        potential_cols = [
            c for c in df.columns
            if "Потенциал" in c and str(y) in c
        ]

        df[f"turnover_{y}"] = (
            df[turnover_cols[0]].apply(clean_num)
            if turnover_cols else 0
        )

        df[f"sales_{y}"] = (
            df[sales_cols[0]].apply(clean_num)
            if sales_cols else 0
        )

        df[f"potential_{y}"] = (
            df[potential_cols[0]].apply(clean_num)
            if potential_cols else 0
        )

        df[f"kup_{y}"] = np.where(
            df[f"potential_{y}"] > 0,
            (df[f"sales_{y}"] / df[f"potential_{y}"]) * 100,
            0
        )

    df["Категория"] = ""

    df.loc[df["ИНН"].isin(GIANTS), "Категория"] = "ГИГАНТ"

    regular = df[~df["ИНН"].isin(GIANTS)].copy()

    regular = regular.sort_values(
        f"turnover_{current_year}",
        ascending=False
    )

    total = regular[f"turnover_{current_year}"].sum()

    regular["cum"] = (
        regular[f"turnover_{current_year}"].cumsum() / total
    )

    regular["Категория"] = np.select(
        [
            regular["cum"] <= 0.80,
            regular["cum"] <= 0.95
        ],
        ["A","Б"],
        default="В"
    )

    df.loc[regular.index, "Категория"] = regular["Категория"]

    ranked = df[df[f"sales_{current_year}"] > 0].copy()

    ranked["Место"] = (
        ranked[f"sales_{current_year}"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df["Место"] = None
    df.loc[ranked.index, "Место"] = ranked["Место"]

    categories = sorted(df["Категория"].unique())

    selected_categories = st.sidebar.multiselect(
        "Категории",
        categories,
        default=categories
    )

    managers = sorted(df["Менеджер"].dropna().unique())

    selected_managers = st.sidebar.multiselect(
        "Менеджеры",
        managers,
        default=managers
    )

    mode = st.sidebar.radio(
        "Режим",
        ["Один клиент", "Сводный"]
    )

    filtered = df[
        (df["Категория"].isin(selected_categories))
        &
        (df["Менеджер"].isin(selected_managers))
    ]

    if mode == "Один клиент":

        selected_client = st.selectbox(
            "Клиент",
            filtered["Клиент"].tolist()
        )

        filtered = filtered[
            filtered["Клиент"] == selected_client
        ]

    row = filtered.iloc[0]

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Оборот",
        format_turnover(
            filtered[f"turnover_{current_year}"].sum()
        )
    )

    m2.metric(
        "Продажи",
        format_sales(
            filtered[f"sales_{current_year}"].sum()
        )
    )

    m3.metric(
        "КУП",
        f"{filtered[f'kup_{current_year}'].mean():.1f}%"
    )

    m4.metric(
        "Клиентов",
        len(filtered)
    )

    st.divider()

    h1, h2, h3, h4 = st.columns(4)

    place = (
        f"ТОП-{int(row['Место'])}"
        if pd.notna(row["Место"])
        else "нет"
    )

    h1.markdown(f"### {row['Клиент']}")
    h2.markdown(f"**Менеджер:** {row['Менеджер']}")
    h3.markdown(f"**Категория:** {row['Категория']}")
    h4.markdown(f"**Место:** {place}")

    st.divider()

    cols = st.columns(len(years))

    prev_sales = None
    prev_turnover = None

    for idx, y in enumerate(years):

        sales = filtered[f"sales_{y}"].sum()
        turnover = filtered[f"turnover_{y}"].sum()
        kup = filtered[f"kup_{y}"].mean()

        sales_growth = None
        turnover_growth = None

        if prev_sales and prev_sales > 0:
            sales_growth = ((sales-prev_sales)/prev_sales)*100

        if prev_turnover and prev_turnover > 0:
            turnover_growth = ((turnover-prev_turnover)/prev_turnover)*100

        prev_sales = sales
        prev_turnover = turnover

        with cols[idx]:

            st.markdown(f"## {y}")

            fig = go.Figure()

            fig.add_bar(
                x=["Продажи"],
                y=[sales],
                marker_color="#16a34a",
                text=[format_sales(sales)],
                textposition="outside",
                hovertemplate="%{y:,.0f}$<extra></extra>"
            )

            fig.add_bar(
                x=["Оборот"],
                y=[turnover],
                marker_color="#2563eb",
                text=[format_turnover(turnover)],
                textposition="outside",
                hovertemplate="%{y:,.0f}$<extra></extra>"
            )

            fig.update_layout(
                height=340,
                margin=dict(l=10,r=10,t=10,b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                yaxis=dict(
                    tickformat=",.2s"
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            if sales_growth is not None:

                css = (
                    "badge-pos"
                    if sales_growth >= 0
                    else "badge-neg"
                )

                st.markdown(
                    f'<div class="{css}">Продажи: {sales_growth:.1f}%</div>',
                    unsafe_allow_html=True
                )

            if turnover_growth is not None:

                css = (
                    "badge-pos"
                    if turnover_growth >= 0
                    else "badge-neg"
                )

                st.markdown(
                    f'<div class="{css}">Оборот: {turnover_growth:.1f}%</div>',
                    unsafe_allow_html=True
                )

            st.markdown(
                f'''
                <div class="kup-box">
                    {kup:.1f}%<br>
                    <span style="font-size:14px;">КУП</span>
                </div>
                ''',
                unsafe_allow_html=True
            )

    st.divider()

    st.subheader("Таблица клиентов")

    table = filtered[[
        "Клиент",
        "Менеджер",
        "Категория",
        "Место"
    ]].copy()

    table["Место"] = table["Место"].apply(
        lambda x: f"ТОП-{int(x)}"
        if pd.notna(x)
        else "нет"
    )

    st.dataframe(
        table,
        use_container_width=True,
        height=400
    )

else:

    st.info("Загрузите файл.")
