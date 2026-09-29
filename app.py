import streamlit as st
from urllib.parse import quote
from PIL import Image
from pyzbar.pyzbar import decode

st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍"
)

st.title("🔍 せどりリサーチAI")

# -------------------------
# JANコード保存
# -------------------------

if "jan" not in st.session_state:
    st.session_state.jan = ""

# -------------------------
# バーコード撮影
# -------------------------

st.header("📦 商品検索")

st.subheader("📷 バーコード撮影")

st.write(
    "商品のJANバーコードをカメラで撮影すると、"
    "JANコードを自動で読み取ります。"
)

camera_image = st.camera_input(
    "バーコードを撮影"
)

if camera_image is not None:

    image = Image.open(camera_image)

    barcodes = decode(image)

    if barcodes:

        barcode = barcodes[0].data.decode("utf-8")

        st.session_state.jan = barcode

        st.success(
            f"✅ JANコードを読み取りました：{barcode}"
        )

    else:

        st.warning(
            "⚠️ バーコードを読み取れませんでした。"
            "バーコードを大きく、正面から撮影してください。"
        )

# -------------------------
# JAN入力
# -------------------------

jan = st.text_input(
    "JANコード",
    value=st.session_state.jan,
    placeholder="例：4902430912526"
)

if jan:

    jan = jan.strip()

    if jan.isdigit() and len(jan) in (8, 12, 13):

        st.success("✅ JANコードを認識しました")

        amazon_url = (
            "https://www.amazon.co.jp/s?k="
            + quote(jan)
        )

        mercari_url = (
            "https://jp.mercari.com/search?keyword="
            + quote(jan)
        )

        google_url = (
            "https://www.google.com/search?q="
            + quote(jan)
        )

        st.link_button(
            "🛒 Amazonで検索",
            amazon_url
        )

        st.link_button(
            "🔴 メルカリで検索",
            mercari_url
        )

        st.link_button(
            "🔎 Googleで検索",
            google_url
        )

    else:

        st.warning(
            "⚠️ JANコードを8桁・12桁・13桁の数字で入力してください"
        )

st.divider()

# -------------------------
# 利益計算
# -------------------------

st.header("💰 利益計算")

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

    profit = (
        sell_price
        - buy_price
        - fee
        - shipping
    )

    if buy_price > 0:
        roi = profit / buy_price * 100
    else:
        roi = 0

    st.subheader("📊 計算結果")

    st.write(
        f"販売手数料：{fee:,}円"
    )

    st.write(
        f"送料：{shipping:,}円"
    )

    st.metric(
        "💰 想定利益",
        f"{profit:,}円"
    )

    st.metric(
        "📈 ROI",
        f"{roi:.1f}%"
    )

    if profit >= 1500 and roi >= 20:

        st.success(
            "🔥 仕入れ候補"
        )

    else:

        st.warning(
            "⚠️ 今回はスルー候補"
        )
