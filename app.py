
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="WM MAP Dashboard v3.1",
    layout="wide"
)

st.title("WM MAP Dashboard v3.1")

uploaded = st.file_uploader(
    "Загрузить CSV/XLSX",
    type=["csv", "xlsx", "xls"]
)

if uploaded:

    st.success(f"Файл загружен: {uploaded.name}")

    try:

        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        st.subheader("Предпросмотр данных")

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

        st.metric(
            "Количество строк",
            len(df)
        )

        st.metric(
            "Количество колонок",
            len(df.columns)
        )

    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")

else:
    st.info("Загрузите CSV или XLSX файл.")
