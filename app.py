import streamlit as st

st.set_page_config(
    page_title="せどり利益計算",
    page_icon="🔍"
)

st.title("🔍 せどり利益計算")

st.write("商品の仕入価格と販売価格を入力してください。")

buy_price = st.number_input(
    "仕入価格（円）",
    min_value=0,
    value=3000,
    step=100
)

sell_price = st.number_input(
    "販売予定価格（円）",
    min_value=0,
    value=6000,
    step=100
)

fee_rate = st.number_input(
    "販売手数料（%）",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=0.1
)

shipping = st.number_input(
    "送料（円）",
    min_value=0,
    value=750,
    step=50
)

if st.button("利益を計算する"):
    fee = int(sell_price * fee_rate / 100)
    profit = sell_price - buy_price - fee - shipping

    if buy_price > 0:
        roi = profit / buy_price * 100
    else:
        roi = 0

    st.subheader("📊 計算結果")
    st.write(f"販売手数料：{fee:,}円")
    st.write(f"送料：{shipping:,}円")

    st.metric("💰 想定利益", f"{profit:,}円")
    st.metric("📈 ROI", f"{roi:.1f}%")

    if profit >= 1500 and roi >= 20:
        st
