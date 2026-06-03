
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="WM MAP Dashboard v4 FULL BI",
    layout="wide"
)

GIANTS = {
    "7705034202",
    "7701215046",
    "4725001168",
    "7729101200"
}

YEARS = [2022, 2023, 2024, 2025]

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

    manager_cols = [c for c in df.columns if "менедж" in c.lower()]
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
        df[f"potential_2022"] = df[potential_col].apply(clean_num)

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

    total_turnover = regular[f"turnover_{current_year}"].sum()

    regular["cum_share"] = (
        regular[f"turnover_{current_year}"].cumsum()
        / total_turnover
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
    background-color: #07111f;
    color: white;
}

[data-testid="metric-container"] {
    background-color: #0d1b2d;
    border: 1px solid #1f3b5b;
    padding: 10px;
    border-radius: 12px;
}

.kup-box {
    background: linear-gradient(135deg,#35104f,#581c87);
    border-radius: 12px;
    padding: 16px;
    text-align:center;
    border:1px solid #9333ea;
}

.kup-big {
    font-size:42px;
    font-weight:700;
    color:#d946ef;
}

.badge-pos {
    background:#14532d;
    color:#4ade80;
    padding:4px 8px;
    border-radius:8px;
    font-weight:700;
}

.badge-neg {
    background:#450a0a;
    color:#f87171;
    padding:4px 8px;
    border-radius:8px;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

st.title("WM MAP Dashboard v4 FULL BI")

uploaded = st.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv","xlsx","xls"]
)

if uploaded:

    df = load_data(uploaded)

    st.sidebar.header("Фильтры")

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

    search = st.sidebar.text_input("Поиск клиента")

    filtered = df[
        (df["category"].isin(categories))
        &
        (df["status"].isin(statuses))
        &
        (df["Менеджер"].isin(selected_managers))
    ]

    if search:
        filtered = filtered[
            filtered["Наименование"]
            .str.contains(search, case=False, na=False)
        ]

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

    st.subheader("Клиенты")

    tbl = filtered[[
        "Наименование",
        "Менеджер",
        "category",
        "status",
        "rank"
    ]].copy()

    tbl["Место"] = tbl["rank"].apply(
        lambda x: f"ТОП-{int(x)}"
        if pd.notna(x)
        else "нет"
    )

    st.dataframe(
        tbl.drop(columns=["rank"]),
        use_container_width=True,
        height=280
    )

    selected = st.selectbox(
        "Карточка клиента",
        filtered["Наименование"].tolist()
    )

    if selected:

        client = filtered[
            filtered["Наименование"] == selected
        ].iloc[0]

        left, right = st.columns([5,2])

        with right:

            place = (
                f"ТОП-{int(client['rank'])}"
                if pd.notna(client["rank"])
                else "нет"
            )

            st.metric("Категория", client["category"])
            st.metric("Место", place)
            st.metric("Статус", client["status"])

            st.markdown(f"""
            <div class="kup-box">
                <div>КУП 2025</div>
                <div class="kup-big">
                    {client['kup_2025']:.1f}%
                </div>
            </div>
            """, unsafe_allow_html=True)

        with left:

            turnover = []
            sales = []
            kup = []

            turnover_growth = []
            sales_growth = []

            prev_t = None
            prev_s = None

            for y in YEARS:

                t = client[f"turnover_{y}"] / 1000
                s = client[f"sales_{y}"] / 1000
                k = client[f"kup_{y}"]

                turnover.append(t)
                sales.append(s)
                kup.append(k)

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

            fig = go.Figure()

            fig.add_bar(
                x=YEARS,
                y=turnover,
                name="Оборот, тыс.$",
                marker_color="#2563eb",
                width=0.35,
                offset=-0.2
            )

            fig.add_bar(
                x=YEARS,
                y=sales,
                name="Продажи, тыс.$",
                marker_color="#16a34a",
                width=0.35,
                offset=0.2,
                yaxis="y2"
            )

            for i, year in enumerate(YEARS):

                tg = turnover_growth[i]
                sg = sales_growth[i]

                if tg is not None:

                    fig.add_annotation(
                        x=year-0.15,
                        y=turnover[i],
                        text=f"{tg:.0f}%",
                        showarrow=False,
                        bgcolor="#14532d" if tg > 0 else "#7f1d1d",
                        bordercolor="white",
                        font=dict(color="white", size=12)
                    )

                if sg is not None:

                    fig.add_annotation(
                        x=year+0.15,
                        y=sales[i],
                        text=f"{sg:.0f}%",
                        showarrow=False,
                        bgcolor="#14532d" if sg > 0 else "#7f1d1d",
                        bordercolor="white",
                        font=dict(color="white", size=12)
                    )

                fig.add_annotation(
                    x=year,
                    y=max(turnover[i], sales[i]) * 1.12,
                    text=f"<b>KUP {kup[i]:.1f}%</b>",
                    showarrow=False,
                    font=dict(
                        size=18,
                        color="#d946ef"
                    )
                )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#07111f",
                plot_bgcolor="#07111f",
                height=700,
                barmode="group",
                title=selected,
                legend=dict(
                    orientation="h"
                ),
                xaxis=dict(
                    tickmode="array",
                    tickvals=YEARS
                ),
                yaxis=dict(
                    title="Оборот, тыс.$",
                    side="left",
                    gridcolor="#1e293b"
                ),
                yaxis2=dict(
                    title="Продажи, тыс.$",
                    overlaying="y",
                    side="right",
                    gridcolor="#1e293b"
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

else:
    st.info("Загрузите CSV/XLSX файл.")
