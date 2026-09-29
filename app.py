import streamlit as st
import requests
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from pyzbar.pyzbar import decode
import math


# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍",
    layout="centered"
)

st.title("🔍 せどりリサーチAI")
st.caption("バーコード → 商品特定 → 相場検索 → 利益計算")


# =========================
# セッション
# =========================
if "jan" not in st.session_state:
    st.session_state.jan = ""

if "product_name" not in st.session_state:
    st.session_state.product_name = ""

if "candidates" not in st.session_state:
    st.session_state.candidates = []


# =========================
# バーコード読み取り
# =========================
def read_barcode(image):
    try:
        img = image.convert("RGB")

        images = [
            img,
            img.resize((img.width * 2, img.height * 2)),
            img.resize((img.width * 3, img.height * 3)),
        ]

        gray = ImageOps.grayscale(img)

        images.extend([
            gray,
            ImageEnhance.Contrast(gray).enhance(2),
            ImageEnhance.Contrast(gray).enhance(3),
            gray.filter(ImageFilter.SHARPEN),
            gray.point(lambda x: 0 if x < 128 else 255),
        ])

        for target in images:
            results = decode(target)

            for result in results:
                code = result.data.decode("utf-8").strip()

                if code.isdigit() and len(code) in [8, 12, 13]:
                    return code

    except Exception:
        pass

    return None


# =========================
# Yahoo!ショッピングAPI
# =========================
def search_yahoo_by_jan(jan):
    try:
        app_id = st.secrets["YAHOO_APP_ID"]
    except Exception:
        return None, "Yahoo! Client IDがSecretsに設定されていません。"

    url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

    params = {
        "appid": app_id,
        "jan_code": jan,
        "results": 10,
        "image_size": 300,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None, f"Yahoo! APIエラー：HTTP {response.status_code}"

        data = response.json()
        hits = data.get("hits", [])

        if not hits:
            return None, "Yahoo!ショッピングでは商品が見つかりませんでした。"

        # 同じJANでも複数ショップがあるため、
        # 最安価格の商品を基準にする
        hits = sorted(
            hits,
            key=lambda x: x.get("price", 999999999)
        )

        hit = hits[0]

        brand = hit.get("brand") or {}
        image = hit.get("exImage") or {}
        normal_image = hit.get("image") or {}

        product = {
            "name": hit.get("name", ""),
            "price": hit.get("price", 0),
            "brand": brand.get("name", ""),
            "jan": hit.get("janCode", jan),
            "image": (
                image.get("url")
                or normal_image.get("medium")
                or normal_image.get("small")
                or ""
            ),
            "url": hit.get("url", ""),
            "shop": (hit.get("seller") or {}).get("name", ""),
            "results": hits,
        }

        return product, None

    except requests.exceptions.Timeout:
        return None, "Yahoo! APIへの接続がタイムアウトしました。"

    except Exception as e:
        return None, f"商品検索中にエラーが発生しました：{e}"


# =========================
# バーコード撮影
# =========================
st.subheader("📷 バーコード撮影")

camera = st.camera_input(
    "商品のJANバーコードを撮影してください"
)

if camera is not None:
    image = Image.open(camera)

    detected_jan = read_barcode(image)

    if detected_jan:
        if detected_jan != st.session_state.jan:
            st.session_state.jan = detected_jan
            st.session_state.product_name = ""

        st.success(
            f"バーコードを読み取りました：{detected_jan}"
        )

    else:
        st.warning(
            "バーコードを読み取れませんでした。"
            "バーコード全体が大きく写るように撮影してください。"
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

if jan != st.session_state.jan:
    st.session_state.jan = jan
    st.session_state.product_name = ""


# =========================
# 商品検索
# =========================
product = None

if jan:

    if not jan.isdigit():
        st.error("JANコードは数字で入力してください。")

    elif len(jan) not in [8, 12, 13]:
        st.warning("JANコードの桁数を確認してください。")

    else:
        with st.spinner("Yahoo!の商品データを検索中..."):
            product, error = search_yahoo_by_jan(jan)

        if product:

            st.success("商品が見つかりました！")

            st.subheader("🏷️ 商品情報")

            if product["image"]:
                st.image(
                    product["image"],
                    width=220
                )

            st.markdown(
                f"### {product['name']}"
            )

            if product["brand"]:
                st.write(
                    f"**ブランド：** {product['brand']}"
                )

            st.write(
                f"**JAN：** {product['jan']}"
            )

            st.write(
                f"**Yahoo!最安参考価格：** "
                f"¥{product['price']:,}"
            )

            if product["shop"]:
                st.write(
                    f"**ショップ：** {product['shop']}"
                )

            if product["url"]:
                st.link_button(
                    "Yahoo!の商品ページを見る",
                    product["url"]
                )

            if not st.session_state.product_name:
                st.session_state.product_name = product["name"]

            # Yahoo!価格一覧
            with st.expander("Yahoo!の価格一覧を見る"):

                for hit in product["results"][:10]:

                    name = hit.get("name", "")
                    price = hit.get("price", 0)
                    shop = (
                        hit.get("seller") or {}
                    ).get("name", "")
                    item_url = hit.get("url", "")

                    st.write(
                        f"¥{price:,}｜{shop}"
                    )

                    if item_url:
                        st.link_button(
                            f"商品を見る：{name[:25]}",
                            item_url
                        )

                    st.divider()

        else:
            st.warning(error)


# =========================
# 商品名
# =========================
st.subheader("✏️ 検索する商品名")

product_name = st.text_input(
    "商品名・型番",
    value=st.session_state.product_name,
    placeholder="例：バンダイ 超合金 ○○"
)

st.session_state.product_name = product_name

search_word = product_name.strip()

if not search_word:
    search_word = jan


# =========================
# 各市場検索
# =========================
if search_word:

    st.subheader("🛒 相場を調べる")

    encoded = quote(search_word)

    mercari_url = (
        "https://jp.mercari.com/search"
        f"?keyword={encoded}"
    )

    amazon_url = (
        "https://www.amazon.co.jp/s"
        f"?k={encoded}"
    )

    yahoo_url = (
        "https://shopping.yahoo.co.jp/search"
        f"?p={encoded}"
    )

    rakuten_url = (
        "https://search.rakuten.co.jp/search/mall/"
        f"{encoded}/"
    )

    st.link_button(
        "🔴 メルカリで検索",
        mercari_url,
        use_container_width=True
    )

    st.link_button(
        "🟠 Amazonで検索",
        amazon_url,
        use_container_width=True
    )

    st.link_button(
        "🔵 Yahoo!ショッピングで検索",
        yahoo_url,
        use_container_width=True
    )

    st.link_button(
        "🟣 楽天市場で検索",
        rakuten_url,
        use_container_width=True
    )


# =========================
# 利益計算
# =========================
st.divider()
st.subheader("💰 利益計算")

purchase_price = st.number_input(
    "仕入価格（円）",
    min_value=0,
    value=1000,
    step=100
)

selling_price = st.number_input(
    "想定販売価格（円）",
    min_value=0,
    value=3000,
    step=100
)

fee_rate = st.number_input(
    "販売手数料（％）",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=0.5
)

shipping = st.number_input(
    "送料（円）",
    min_value=0,
    value=750,
    step=10
)

materials = st.number_input(
    "梱包資材（円）",
    min_value=0,
    value=0,
    step=10
)

minimum_profit = st.number_input(
    "最低ほしい利益（円）",
    min_value=0,
    value=1000,
    step=100
)

minimum_roi = st.number_input(
    "最低ROI（％）",
    min_value=0.0,
    value=30.0,
    step=5.0
)


# =========================
# 計算
# =========================
fee = selling_price * (fee_rate / 100)

profit = (
    selling_price
    - purchase_price
    - fee
    - shipping
    - materials
)

if purchase_price > 0:
    roi = (profit / purchase_price) * 100
else:
    roi = 0


net_before_purchase = (
    selling_price
    - fee
    - shipping
    - materials
)

profit_limit = (
    net_before_purchase
    - minimum_profit
)

roi_limit = (
    net_before_purchase
    / (1 + minimum_roi / 100)
)

max_purchase = math.floor(
    max(
        0,
        min(
            profit_limit,
            roi_limit
        )
    )
)


# =========================
# 結果
# =========================
st.subheader("📊 計算結果")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "想定利益",
        f"¥{profit:,.0f}"
    )

with col2:
    st.metric(
        "ROI",
        f"{roi:.1f}%"
    )

st.metric(
    "この条件での仕入上限",
    f"¥{max_purchase:,}"
)


# =========================
# 仕入れ判定
# =========================
profit_ok = profit >= minimum_profit
roi_ok = roi >= minimum_roi

if profit_ok and roi_ok:
    st.success(
        "🟢 仕入れ候補"
    )

elif profit > 0:
    st.warning(
        "🟡 利益は出ますが、設定した基準未満です。"
    )

else:
    st.error(
        "🔴 赤字になる可能性があります。"
    )


# =========================
# 候補保存
# =========================
if st.button(
    "⭐ 仕入れ候補に保存",
    use_container_width=True
):

    candidate = {
        "JAN": jan,
        "商品名": product_name,
        "仕入価格": purchase_price,
        "販売価格": selling_price,
        "利益": round(profit),
        "ROI": round(roi, 1),
    }

    st.session_state.candidates.append(
        candidate
    )

    st.success(
        "仕入れ候補に保存しました。"
    )


# =========================
# 保存一覧
# =========================
if st.session_state.candidates:

    st.divider()
    st.subheader("⭐ 保存した仕入れ候補")

    st.dataframe(
        st.session_state.candidates,
        use_container_width=True
    )
