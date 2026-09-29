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
