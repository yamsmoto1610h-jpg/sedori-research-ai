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
st.caption("バーコード → 商品特定 → 相場確認 → 仕入れ判断")


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

        hits = sorted(
            hits,
            key=lambda x: x.get("price", 999999999)
        )

        hit = hits[0]

        brand = hit.get("brand") or {}
        ex_image = hit.get("exImage") or {}
        normal_image = hit.get("image") or {}

        product = {
            "name": hit.get("name", ""),
            "price": hit.get("price", 0),
            "brand": brand.get("name", ""),
            "jan": hit.get("janCode", jan),
            "image": (
                ex_image.get("url")
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
st.subheader("📷 1. バーコード")

camera = st.camera_input(
    "商品のJANバーコードを撮影"
)

if camera is not None:

    image = Image.open(camera)

    detected_jan = read_barcode(image)

    if detected_jan:

        if detected_jan != st.session_state.jan:
            st.session_state.jan = detected_jan
            st.session_state.product_name = ""

        st.success(
            f"JAN：{detected_jan}"
        )

    else:
        st.warning(
            "読み取れませんでした。バーコード全体を大きく撮影してください。"
        )


# =========================
# JAN入力
# =========================
jan = st.text_input(
    "JANコード",
    value=st.session_state.jan,
    placeholder="例：4573102693020"
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

        with st.spinner("商品を検索中..."):
            product, error = search_yahoo_by_jan(jan)

        if product:

            st.success("商品を特定しました")

            st.subheader("🏷️ 2. 商品情報")

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
                f"**Yahoo!新品参考価格：¥{product['price']:,}**"
            )

            if product["shop"]:
                st.caption(
                    f"Yahoo!ショップ：{product['shop']}"
                )

            if product["url"]:
                st.link_button(
                    "Yahoo!商品ページ",
                    product["url"],
                    use_container_width=True
                )

            if not st.session_state.product_name:
                st.session_state.product_name = product["name"]

            with st.expander("Yahoo!価格一覧"):

                for hit in product["results"][:10]:

                    price = hit.get("price", 0)

                    shop = (
                        hit.get("seller") or {}
                    ).get("name", "")

                    st.write(
                        f"¥{price:,}｜{shop}"
                    )

        else:

            st.warning(error)


# =========================
# 商品名
# =========================
product_name = st.text_input(
    "検索に使う商品名・型番",
    value=st.session_state.product_name
)

st.session_state.product_name = product_name

search_word = product_name.strip() or jan


# =========================
# 相場検索
# =========================
if search_word:

    st.subheader("🔎 3. 相場を確認")

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
        "🔴 メルカリ相場を見る",
        mercari_url,
        use_container_width=True
    )

    st.caption(
        "メルカリで「絞り込み → 販売状況 → 売り切れ」にすると成約相場を確認できます。"
    )

    st.link_button(
        "🟠 Amazonで見る",
        amazon_url,
        use_container_width=True
    )

    st.link_button(
        "🔵 Yahoo!で見る",
        yahoo_url,
        use_container_width=True
    )

    st.link_button(
        "🟣 楽天で見る",
        rakuten_url,
        use_container_width=True
    )


# =========================
# メルカリ利益計算
# =========================
st.divider()

st.subheader("💰 4. メルカリ利益計算")

st.info(
    "メルカリの売り切れ相場を確認して、想定販売価格を入力してください。"
)


selling_price = st.number_input(
    "メルカリ想定販売価格",
    min_value=0,
    value=5000,
    step=100
)


purchase_price = st.number_input(
    "店舗での仕入価格",
    min_value=0,
    value=1000,
    step=100
)


# =========================
# 配送方法
# =========================
shipping_options = {
    "ゆうパケットポストmini": 160,
    "ネコポス": 210,
    "ゆうパケットポスト": 215,
    "ゆうパケット": 230,
    "宅急便コンパクト": 450,
    "ゆうパケットプラス": 455,
    "宅急便 60サイズ": 750,
    "宅急便 80サイズ": 850,
    "宅急便 100サイズ": 1050,
    "宅急便 120サイズ": 1200,
    "宅急便 140サイズ": 1450,
    "宅急便 160サイズ": 1700,
    "その他・手入力": 0,
}


shipping_method = st.selectbox(
    "配送方法",
    list(shipping_options.keys()),
    index=6
)


if shipping_method == "その他・手入力":

    shipping = st.number_input(
        "送料",
        min_value=0,
        value=750,
        step=10
    )

else:

    shipping = shipping_options[shipping_method]

    st.write(
        f"送料：**¥{shipping:,}**"
    )


# =========================
# 専用箱・梱包代
# =========================
default_material = 0

if shipping_method == "宅急便コンパクト":
    default_material = 70

elif shipping_method == "ゆうパケットプラス":
    default_material = 65


materials = st.number_input(
    "梱包資材・専用箱代",
    min_value=0,
    value=default_material,
    step=10
)


# =========================
# 手数料
# =========================
fee_rate = st.number_input(
    "販売手数料（％）",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=0.5
)


# =========================
# 自分の仕入基準
# =========================
st.markdown("#### 🎯 仕入れ基準")

minimum_profit = st.number_input(
    "最低ほしい利益",
    min_value=0,
    value=1500,
    step=100
)

minimum_roi = st.number_input(
    "最低ROI（％）",
    min_value=0.0,
    value=30.0,
    step=5.0
)


# =========================
# 利益計算
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

    roi = (
        profit
        / purchase_price
    ) * 100

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


if minimum_roi >= 0:

    roi_limit = (
        net_before_purchase
        / (1 + minimum_roi / 100)
    )

else:

    roi_limit = 0


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
st.subheader("📊 5. 仕入れ判定")

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "利益",
        f"¥{profit:,.0f}"
    )


with col2:

    st.metric(
        "ROI",
        f"{roi:.1f}%"
    )


st.metric(
    "🔥 仕入上限額",
    f"¥{max_purchase:,}"
)


st.caption(
    f"販売価格 ¥{selling_price:,} − "
    f"手数料 ¥{fee:,.0f} − "
    f"送料 ¥{shipping:,} − "
    f"資材 ¥{materials:,} − "
    f"仕入 ¥{purchase_price:,}"
)


# =========================
# 判定
# =========================
profit_ok = profit >= minimum_profit
roi_ok = roi >= minimum_roi


if profit_ok and roi_ok:

    st.success(
        "🟢 仕入れ候補です"
    )

elif profit > 0:

    st.warning(
        "🟡 利益は出ますが、設定した仕入れ基準には届きません"
    )

else:

    st.error(
        "🔴 この価格では赤字です"
    )


if purchase_price <= max_purchase and purchase_price > 0:

    difference = max_purchase - purchase_price

    st.success(
        f"仕入上限より ¥{difference:,} 安く仕入れられます。"
    )

elif purchase_price > max_purchase:

    difference = purchase_price - max_purchase

    st.warning(
        f"仕入上限を ¥{difference:,} オーバーしています。"
    )


# =========================
# 保存
# =========================
if st.button(
    "⭐ この商品を仕入れ候補に保存",
    use_container_width=True
):

    candidate = {
        "JAN": jan,
        "商品名": product_name,
        "仕入": purchase_price,
        "想定売価": selling_price,
        "配送": shipping_method,
        "利益": round(profit),
        "ROI": round(roi, 1),
        "仕入上限": max_purchase,
    }

    st.session_state.candidates.append(
        candidate
    )

    st.success(
        "仕入れ候補に保存しました"
    )


# =========================
# 候補一覧
# =========================
if st.session_state.candidates:

    st.divider()

    st.subheader(
        "⭐ 仕入れ候補"
    )

    st.dataframe(
        st.session_state.candidates,
        use_container_width=True
)
