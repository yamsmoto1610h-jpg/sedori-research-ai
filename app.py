import streamlit as st
import requests
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps
from pyzbar.pyzbar import decode

st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍"
)

st.title("🔍 せどりリサーチAI")
st.header("📦 商品検索")

# -------------------------
# JANコード保存
# -------------------------

if "jan" not in st.session_state:
    st.session_state.jan = ""

# -------------------------
# バーコード読み取り関数
# -------------------------

def read_barcode(image):

    image = image.convert("RGB")

    images_to_try = [image]

    # 2倍
    images_to_try.append(
        image.resize(
            (image.width * 2, image.height * 2)
        )
    )

    # 3倍
    images_to_try.append(
        image.resize(
            (image.width * 3, image.height * 3)
        )
    )

    # グレースケール
    gray = ImageOps.grayscale(image)
    images_to_try.append(gray)

    # コントラスト強化
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
                except:
                    continue

                if code.isdigit() and len(code) in (8, 12, 13):
                    return code

    return None


# -------------------------
# 商品情報取得
# -------------------------

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

    except:
        return None


# -------------------------
# バーコード撮影
# -------------------------

st.subheader("📷 バーコード撮影")

st.write(
    "商品のJANバーコードを撮影してください。"
)

camera_image = st.camera_input(
    "バーコードを撮影"
)

if camera_image is not None:

    image = Image.open(camera_image)

    barcode = read_barcode(image)

    if barcode:

        st.session_state.jan = barcode

        st.success(
            f"✅ JANコードを読み取りました：{barcode}"
        )

    else:

        st.warning(
            "⚠️ バーコードを読み取れませんでした。"
        )


# -------------------------
# JAN入力
# -------------------------

st.subheader("🔢 JANコード")

jan = st.text_input(
    "JANコードを入力",
    value=st.session_state.jan,
    placeholder="例：4902430912526"
)

jan = jan.strip()


# -------------------------
# 商品検索
# -------------------------

if jan:

    if jan.isdigit() and len(jan) in (8, 12, 13):

        st.success("✅ JANコードを確認しました")

        st.subheader("🔎 商品情報")

        product = get_product_info(jan)

        search_word = jan

        if product:

            name = product["name"]
            brand = product["brand"]
            image_url = product["image"]

            if image_url:

                st.image(
                    image_url,
                    width=250
                )

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
                "この商品は無料の商品データベースでは"
                "見つかりませんでした。"
                "JANコードで各サイトを検索できます。"
            )

        # -------------------------
        # 各サイト検索
        # -------------------------

        st.subheader("🛒 相場を調べる")

        amazon_url = (
            "https://www.amazon.co.jp/s?k="
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

        mercari_url = (
            "https://jp.mercari.com/search?keyword="
            + quote(search_word)
        )

        st.link_button(
            "🟠 Amazonで検索",
            amazon_url
        )

        st.link_button(
            "🔴 楽天市場で検索",
            rakuten_url
        )

        st.link_button(
            "🟣 Yahoo!ショッピングで検索",
            yahoo_url
        )

        st.link_button(
            "🔴 メルカリで検索",
            mercari_url
        )

    else:

        st.error(
            "JANコードは8桁・12桁・13桁の数字で入力してください。"
        )
# -------------------------
# 利益計算
# -------------------------

st.divider()
st.header("💰 利益計算")

purchase_price = st.number_input(
    "仕入価格（円）",
    min_value=0,
    value=0,
    step=100
)

selling_price = st.number_input(
    "想定販売価格（円）",
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

shipping_cost = st.number_input(
    "送料（円）",
    min_value=0,
    value=750,
    step=50
)

if selling_price > 0:

    fee = int(selling_price * fee_rate / 100)

    profit = (
        selling_price
        - purchase_price
        - fee
        - shipping_cost
    )

    if purchase_price > 0:
        roi = profit / purchase_price * 100
    else:
        roi = 0

    if selling_price > 0:
        profit_margin = profit / selling_price * 100
    else:
        profit_margin = 0

    st.subheader("📊 計算結果")

    st.write(f"販売価格：{selling_price:,}円")
    st.write(f"仕入価格：{purchase_price:,}円")
    st.write(f"販売手数料：{fee:,}円")
    st.write(f"送料：{shipping_cost:,}円")

    st.metric(
        "想定利益",
        f"{profit:,}円"
    )

    st.metric(
        "ROI（仕入額に対する利益率）",
        f"{roi:.1f}%"
    )

    st.metric(
        "売上利益率",
        f"{profit_margin:.1f}%"
    )

    st.subheader("🚦 仕入れ判定")

    if profit >= 1500 and roi >= 30:

        st.success(
            "🟢 仕入れ候補：利益1,500円以上・ROI30%以上"
        )

    elif profit >= 1000 and roi >= 20:

        st.warning(
            "🟡 要検討：利益は出ていますが慎重に確認"
        )

    else:

        st.error(
            "🔴 見送り候補：利益またはROIが基準未満"
        )
