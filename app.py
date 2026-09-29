import streamlit as st
import requests
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps
from pyzbar.pyzbar import decode


# =========================
# 基本設定
# =========================

st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍"
)

st.title("🔍 せどりリサーチAI")
st.caption("バーコード → 相場確認 → 利益計算 → 仕入れ判断")


# =========================
# JANコード保存
# =========================

if "jan" not in st.session_state:
    st.session_state.jan = ""


# =========================
# バーコード読み取り
# =========================

def read_barcode(image):

    image = image.convert("RGB")

    images_to_try = [image]

    images_to_try.append(
        image.resize(
            (image.width * 2, image.height * 2)
        )
    )

    images_to_try.append(
        image.resize(
            (image.width * 3, image.height * 3)
        )
    )

    gray = ImageOps.grayscale(image)

    images_to_try.append(gray)

    images_to_try.append(
        ImageEnhance.Contrast(gray).enhance(2.0)
    )

    images_to_try.append(
        ImageEnhance.Contrast(gray).enhance(3.0)
    )

    for img in images_to_try:

        results = decode(img)

        if results:

            for result in results:

                try:
                    code = result.data.decode("utf-8")
                except Exception:
                    continue

                if code.isdigit() and len(code) in (8, 12, 13):
                    return code

    return None


# =========================
# 商品情報取得
# =========================

@st.cache_data(ttl=3600)
def get_product_info(jan):

    url = (
        "https://world.openfoodfacts.org/"
        f"api/v2/product/{jan}.json"
    )

    try:

        response = requests.get(
            url,
            timeout=10
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if data.get("status") != 1:
            return None

        product = data.get("product", {})

        name = (
            product.get("product_name_ja")
            or product.get("product_name")
            or ""
        )

        brand = product.get("brands", "")

        image_url = (
            product.get("image_front_url")
            or product.get("image_url")
        )

        return {
            "name": name,
            "brand": brand,
            "image": image_url
        }

    except Exception:
        return None


# =========================
# 商品検索
# =========================

st.header("📦 商品検索")

st.subheader("📷 バーコード撮影")

camera_image = st.camera_input(
    "商品のJANバーコードを撮影"
)

if camera_image is not None:

    image = Image.open(camera_image)

    barcode = read_barcode(image)

    if barcode:

        st.session_state.jan = barcode

        st.success(
            f"✅ JANコード：{barcode}"
        )

    else:

        st.warning(
            "⚠️ バーコードを読み取れませんでした。"
        )


# =========================
# JAN入力
# =========================

st.subheader("🔢 JANコード")

jan = st.text_input(
    "JANコードを入力",
    value=st.session_state.jan,
    placeholder="例：4902430912526"
)

jan = jan.strip()


# =========================
# JAN検索
# =========================

if jan:

    if jan.isdigit() and len(jan) in (8, 12, 13):

        st.success("✅ JANコード確認OK")

        product = get_product_info(jan)

        search_word = jan

        st.subheader("🔎 商品情報")

        if product:

            name = product["name"]
            brand = product["brand"]
            image_url = product["image"]

            if image_url:
                st.image(image_url, width=250)

            if name:

                st.write(
                    f"**商品名：** {name}"
                )

                search_word = name

            if brand:

                st.write(
                    f"**ブランド：** {brand}"
                )

        else:

            st.info(
                "商品情報を自動取得できませんでした。"
                "JANコードで各サイトを検索します。"
            )


        # =========================
        # 相場検索
        # =========================

        st.subheader("🛒 相場を調べる")

        amazon_url = (
            "https://www.amazon.co.jp/s?k="
            + quote(search_word)
        )

        mercari_url = (
            "https://jp.mercari.com/search?keyword="
            + quote(search_word)
        )

        rakuten_url = (
            "https://search.rakuten.co.jp/search/mall/"
            + quote(search_word)
        )

        yahoo_url = (
            "https://shopping.yahoo.co.jp/search?p="
            + quote(search_word)
        )

        st.link_button(
            "🟠 Amazonで検索",
            amazon_url,
            use_container_width=True
        )

        st.link_button(
            "🔴 メルカリで検索",
            mercari_url,
            use_container_width=True
        )

        st.link_button(
            "🔴 楽天市場で検索",
            rakuten_url,
            use_container_width=True
        )

        st.link_button(
            "🟣 Yahoo!ショッピングで検索",
            yahoo_url,
            use_container_width=True
        )

    else:

        st.error(
            "JANコードは8桁・12桁・13桁の数字で入力してください。"
        )


# =========================
# 利益計算
# =========================

st.divider()

st.header("💰 仕入れ・利益計算")


selling_price = st.number_input(
    "想定販売価格（円）",
    min_value=0,
    value=0,
    step=100
)


purchase_price = st.number_input(
    "実際の仕入価格（円）",
    min_value=0,
    value=0,
    step=100
)


fee_rate = st.number_input(
    "販売手数料（％）",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=0.5
)


# =========================
# 配送方法
# =========================

st.subheader("🚚 配送方法")


shipping_options = {

    "ゆうパケットポストmini": {
        "shipping": 160,
        "material": 0
    },

    "ネコポス": {
        "shipping": 210,
        "material": 0
    },

    "ゆうパケットポスト": {
        "shipping": 215,
        "material": 0
    },

    "ゆうパケット": {
        "shipping": 230,
        "material": 0
    },

    "宅急便コンパクト": {
        "shipping": 450,
        "material": 70
    },

    "ゆうパケットプラス": {
        "shipping": 455,
        "material": 65
    },

    "宅急便 60サイズ": {
        "shipping": 750,
        "material": 0
    },

    "宅急便 80サイズ": {
        "shipping": 850,
        "material": 0
    },

    "宅急便 100サイズ": {
        "shipping": 1050,
        "material": 0
    },

    "宅急便 120サイズ": {
        "shipping": 1200,
        "material": 0
    },

    "宅急便 140サイズ": {
        "shipping": 1450,
        "material": 0
    },

    "宅急便 160サイズ": {
        "shipping": 1700,
        "material": 0
    },

    "その他・手入力": {
        "shipping": 0,
        "material": 0
    }
}


shipping_method = st.selectbox(
    "配送方法を選択",
    list(shipping_options.keys())
)


if shipping_method == "その他・手入力":

    shipping_cost = st.number_input(
        "送料（円）",
        min_value=0,
        value=0,
        step=10
    )

    material_cost = st.number_input(
        "梱包資材代（円）",
        min_value=0,
        value=0,
        step=10
    )

else:

    shipping_cost = (
        shipping_options[shipping_method]["shipping"]
    )

    material_cost = (
        shipping_options[shipping_method]["material"]
    )


total_shipping_cost = (
    shipping_cost
    + material_cost
)


st.write(
    f"送料：**{shipping_cost:,}円**"
)

st.write(
    f"専用資材等：**{material_cost:,}円**"
)

st.write(
    f"配送関連合計：**{total_shipping_cost:,}円**"
)


# =========================
# 仕入れ基準
# =========================

st.subheader("🎯 仕入れ基準")


target_profit = st.number_input(
    "最低欲しい利益（円）",
    min_value=0,
    value=1500,
    step=100
)


target_roi = st.number_input(
    "最低ROI（％）",
    min_value=0.0,
    value=30.0,
    step=5.0
)


# =========================
# 仕入上限価格
# =========================

if selling_price > 0:

    fee = int(
        selling_price
        * fee_rate
        / 100
    )


    # -------------------------
    # 利益基準から計算
    # -------------------------

    max_purchase_profit = (
        selling_price
        - fee
        - total_shipping_cost
        - target_profit
    )


    # -------------------------
    # ROI基準から計算
    #
    # ROI =
    # 利益 ÷ 仕入価格 × 100
    # -------------------------

    available_before_purchase = (
        selling_price
        - fee
        - total_shipping_cost
    )


    if target_roi > 0:

        max_purchase_roi = (
            available_before_purchase
            / (1 + target_roi / 100)
        )

    else:

        max_purchase_roi = (
            available_before_purchase
        )


    # 両方の条件を満たす安い方
    max_purchase_price = min(
        max_purchase_profit,
        max_purchase_roi
    )


    max_purchase_price = max(
        0,
        int(max_purchase_price)
    )


    st.subheader("🏷️ 仕入上限価格")


    st.metric(
        "この金額以下なら仕入れ基準クリア",
        f"{max_purchase_price:,}円"
    )


    st.caption(
        f"最低利益 {target_profit:,}円・"
        f"最低ROI {target_roi:.1f}% の"
        "両方を満たす目安です。"
    )


    # =========================
    # 実際の利益
    # =========================

    profit = (
        selling_price
        - purchase_price
        - fee
        - total_shipping_cost
    )


    if purchase_price > 0:

        roi = (
            profit
            / purchase_price
            * 100
        )

    else:

        roi = 0


    profit_margin = (
        profit
        / selling_price
        * 100
    )


    st.subheader("📊 計算結果")


    st.write(
        f"販売価格：{selling_price:,}円"
    )

    st.write(
        f"仕入価格：{purchase_price:,}円"
    )

    st.write(
        f"販売手数料：{fee:,}円"
    )

    st.write(
        f"配送関連費：{total_shipping_cost:,}円"
    )


    st.metric(
        "💰 想定利益",
        f"{profit:,}円"
    )


    st.metric(
        "📈 ROI",
        f"{roi:.1f}%"
    )


    st.metric(
        "📊 売上利益率",
        f"{profit_margin:.1f}%"
    )


    # =========================
    # 仕入れ判定
    # =========================

    st.subheader("🚦 仕入れ判定")


    if purchase_price == 0:

        st.info(
            "仕入価格を入力すると"
            "仕入れ判定が表示されます。"
        )


    elif (
        profit >= target_profit
        and roi >= target_roi
    ):

        st.success(
            "🟢 仕入れ基準クリア"
        )

        difference = (
            max_purchase_price
            - purchase_price
        )

        st.write(
            f"仕入上限より **{difference:,}円安く** "
            "仕入れできます。"
        )


    else:

        st.error(
            "🔴 見送り候補"
        )

        over_price = (
            purchase_price
            - max_purchase_price
        )

        if over_price > 0:

            st.write(
                f"仕入基準を満たすには、"
                f"あと **{over_price:,}円** "
                "安く仕入れる必要があります。"
            )
