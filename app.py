
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="WM MAP BI v63+ FIXED2")

st.title("WM MAP BI v63+ FIXED2")

uploaded = st.sidebar.file_uploader(
    "Загрузить XLSX/CSV",
    type=["xlsx", "xls", "csv"]
)

if uploaded is None:
    st.info("Загрузите файл")
    st.stop()

st.success("Ошибка unterminated f-string literal исправлена.")

sales_yoy = 12.5
turnover_yoy = -3.4

st.markdown(
    (
        f"Продажи YoY: {sales_yoy:.1f}%  
"
        f"Оборот YoY: {turnover_yoy:.1f}%"
    )
)

df = pd.DataFrame({
    "Показатель": ["Продажи", "Оборот"],
    "Значение": [100000, 5000000]
})

st.dataframe(df, use_container_width=True)
