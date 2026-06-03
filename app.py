
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="WM MAP Dashboard v5 FULL BI",
    layout="wide"
)

YEARS = [2022, 2023, 2024, 2025]

GIANTS = {
    "7705034202",
    "7701215046",
    "4725001168",
    "7729101200"
}

def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).replace("\xa0", "").strip()

def clean_num(x):

    if pd.isna(x):
        return 0.0

    s = (
        str(x)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    if s in ["", "-", "nan"]:
        return 0.0

    try:
        return float(s)
    except:
        return 0.0

def compact(v):

    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M$"

    if v >= 1_000:
        return f"{v/1_000:.1f}K$"

    return f"{v:.0f}$"

@st.cache_data
def load_data(file):

    if file.name.endswith(".csv"):
        df = pd.read_csv(file, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file)

    df.columns = [clean_text(c) for c in df.columns]

    df["ИНН"] = df["ИНН"].apply(clean_text)
    df["Наименование"] = df["Наименование"].apply(clean_text)

    manager_cols = [
        c for c in df.columns
        if "менедж" in c.lower()
    ]

    if manager_cols:
        df["Менеджер"] = df[manager_cols[0]].apply(clean_text)
    else:
        df["Менеджер"] = ""

    potential_col = [
        c for c in df.columns
        if "Потенциал по ароме 2022" in c
    ][0]

    for y in YEARS:

        turnover_col = [
            c for c in df.columns
            if f"Оборот {y}" in c and "долл" in c
        ][0]

        sales_col = [
            c for c in df.columns
            if str(y) in c and "без НДС" in c
        ][0]

        df[f"turnover_{y}"] = df[turnover_col].apply(clean_num)
        df[f"sales_{y}"] = df[sales_col].apply(clean_num)

        df["potential_2022"] = df[potential_col].apply(clean_num)

        df[f"kup_{y}"] = np.where(
            df["potential_2022"] > 0,
            (df[f"sales_{y}"] / df["potential_2022"]) * 100,
            0
        )

    current_year = 2025

    df["category"] = ""

    df.loc[df["ИНН"].isin(GIANTS), "category"] = "Гигант"

    regular = df[~df["ИНН"].isin(GIANTS)].copy()

    regular = regular.sort_values(
        f"turnover_{current_year}",
        ascending=False
    )

    total = regular[f"turnover_{current_year}"].sum()

    regular["cum_share"] = (
        regular[f"turnover_{current_year}"].cumsum() / total
    )

    regular["category"] = np.select(
        [
            regular["cum_share"] <= 0.80,
            regular["cum_share"] <= 0.95
        ],
        ["A", "Б"],
        default="В"
    )

    df.loc[regular.index, "category"] = regular["category"]

    ranked = df[df[f"sales_{current_year}"] > 0].copy()

    ranked["rank"] = (
        ranked[f"sales_{current_year}"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df["rank"] = None
    df.loc[ranked.index, "rank"] = ranked["rank"]

    def status(row):

        if row[f"sales_{current_year}"] > 0:
            return "Активный"

        if row[f"turnover_{current_year}"] > 0:
            return "Потенциал"

        return "Неактивный"

    df["status"] = df.apply(status, axis=1)

    return df

st.markdown("""
<style>

.stApp {
    background-color: #f5f7fb;
    color: #0f172a;
}

section[data-testid="stSidebar"] {
    background-color: white;
    border-right: 1px solid #dbe4f0;
}

.block-container {
    padding-top: 1rem;
}

[data-testid="metric-container"] {
    background-color: white;
    border: 1px solid #dbe4f0;
    padding: 14px;
    border-radius: 14px;
}

.kpi-card {
    background: white;
    border: 1px solid #dbe4f0;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 14px;
}

.kup-card {
    background: linear-gradient(135deg,#7c3aed,#9333ea);
    color: white;
    border-radius: 18px;
    padding: 24px;
    text-align: center;
    margin-top: 10px;
}

.kup-value {
    font-size: 46px;
    font-weight: 700;
}

.small-label {
    color: #64748b;
    font-size: 13px;
}

.big-value {
    font-size: 34px;
    font-weight: 700;
}

.table-wrap {
    background: white;
    border-radius: 16px;
    padding: 14px;
    border: 1px solid #dbe4f0;
}

</style>
""", unsafe_allow_html=True)

st.title("Дашборд клиентов")

uploaded = st.sidebar.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv","xlsx","xls"]
)

if uploaded:

    df = load_data(uploaded)

    st.sidebar.subheader("Фильтры")

    categories = st.sidebar.multiselect(
        "Категория",
        ["Гигант","A","Б","В"],
        default=["Гигант","A","Б","В"]
    )

    statuses = st.sidebar.multiselect(
        "Статус",
        ["Активный","Потенциал","Неактивный"],
        default=["Активный","Потенциал","Неактивный"]
    )

    managers = sorted(df["Менеджер"].dropna().unique())

    selected_managers = st.sidebar.multiselect(
        "Менеджер",
        managers,
        default=managers
    )

    mode = st.selectbox(
        "Отображение",
        ["Все клиенты","Один клиент"]
    )

    filtered = df[
        (df["category"].isin(categories))
        &
        (df["status"].isin(statuses))
        &
        (df["Менеджер"].isin(selected_managers))
    ]

    if mode == "Один клиент":

        selected = st.selectbox(
            "Выберите клиента",
            filtered["Наименование"].tolist()
        )

        filtered = filtered[
            filtered["Наименование"] == selected
        ]

    row = filtered.iloc[0]

    top1, top2, top3, top4 = st.columns(4)

    top1.metric(
        "Оборот 2025",
        compact(filtered["turnover_2025"].sum())
    )

    top2.metric(
        "Продажи 2025",
        compact(filtered["sales_2025"].sum())
    )

    top3.metric(
        "Средний КУП",
        f"{filtered['kup_2025'].mean():.1f}%"
    )

    top4.metric(
        "Клиентов",
        len(filtered)
    )

    left, right = st.columns([5,2])

    turnover_values = []
    sales_values = []
    kup_values = []

    turnover_growth = []
    sales_growth = []

    prev_t = None
    prev_s = None

    for y in YEARS:

        t = filtered[f"turnover_{y}"].sum() / 1000
        s = filtered[f"sales_{y}"].sum() / 1000
        k = filtered[f"kup_{y}"].mean()

        turnover_values.append(t)
        sales_values.append(s)
        kup_values.append(k)

        if prev_t and prev_t > 0:
            turnover_growth.append(
                ((t-prev_t)/prev_t)*100
            )
        else:
            turnover_growth.append(None)

        if prev_s and prev_s > 0:
            sales_growth.append(
                ((s-prev_s)/prev_s)*100
            )
        else:
            sales_growth.append(None)

        prev_t = t
        prev_s = s

    with right:

        place = (
            f"ТОП-{int(row['rank'])}"
            if pd.notna(row["rank"])
            else "нет"
        )

        st.markdown(f"""
        <div class="kpi-card">
            <div class="small-label">Категория</div>
            <div class="big-value">{row['category']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="kpi-card">
            <div class="small-label">Место</div>
            <div class="big-value">{place}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="kpi-card">
            <div class="small-label">Статус</div>
            <div class="big-value">{row['status']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="kup-card">
            <div>КУП 2025</div>
            <div class="kup-value">
                {filtered['kup_2025'].mean():.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    with left:

        c1, c2 = st.columns(2)

        with c1:

            fig1 = go.Figure()

            fig1.add_bar(
                x=YEARS,
                y=turnover_values,
                marker_color="#2563eb",
                text=[compact(v*1000) for v in turnover_values],
                textposition="outside",
                name="Оборот"
            )

            fig1.add_trace(
                go.Scatter(
                    x=YEARS,
                    y=turnover_growth,
                    mode="lines+markers+text",
                    text=[
                        f"{v:.1f}%"
                        if v is not None else ""
                        for v in turnover_growth
                    ],
                    textposition="top center",
                    line=dict(color="#1d4ed8", width=3),
                    name="Прирост"
                )
            )

            fig1.update_layout(
                title="ДИНАМИКА ОБОРОТА",
                height=420,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font_color="#0f172a",
                yaxis_title="тыс.$",
                xaxis=dict(
                    tickmode="array",
                    tickvals=YEARS
                )
            )

            st.plotly_chart(
                fig1,
                use_container_width=True
            )

        with c2:

            fig2 = go.Figure()

            fig2.add_bar(
                x=YEARS,
                y=sales_values,
                marker_color="#16a34a",
                text=[compact(v*1000) for v in sales_values],
                textposition="outside",
                name="Продажи"
            )

            fig2.add_trace(
                go.Scatter(
                    x=YEARS,
                    y=sales_growth,
                    mode="lines+markers+text",
                    text=[
                        f"{v:.1f}%"
                        if v is not None else ""
                        for v in sales_growth
                    ],
                    textposition="top center",
                    line=dict(color="#15803d", width=3),
                    name="Прирост"
                )
            )

            fig2.update_layout(
                title="ДИНАМИКА ПРОДАЖ",
                height=420,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font_color="#0f172a",
                yaxis_title="тыс.$",
                xaxis=dict(
                    tickmode="array",
                    tickvals=YEARS
                )
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

        fig3 = go.Figure()

        fig3.add_trace(
            go.Scatter(
                x=YEARS,
                y=kup_values,
                mode="lines+markers+text",
                line=dict(
                    color="#9333ea",
                    width=5
                ),
                marker=dict(size=14),
                text=[
                    f"{v:.1f}%"
                    for v in kup_values
                ],
                textfont=dict(size=22),
                textposition="top center"
            )
        )

        fig3.update_layout(
            title="ДИНАМИКА КУП (%)",
            height=350,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font_color="#0f172a",
            yaxis_title="КУП %",
            xaxis=dict(
                tickmode="array",
                tickvals=YEARS
            )
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )

    st.subheader("Рейтинг клиентов")

    table = filtered.copy()

    table["Место"] = table["rank"].apply(
        lambda x: f"ТОП-{int(x)}"
        if pd.notna(x)
        else "нет"
    )

    out = table[[
        "Наименование",
        "Менеджер",
        "category",
        "status",
        "Место"
    ]].rename(columns={
        "category":"Категория",
        "status":"Статус"
    })

    st.dataframe(
        out,
        use_container_width=True,
        height=350
    )

else:

    st.info("Загрузите файл через sidebar.")
