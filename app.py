import streamlit as st
import requests
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from pyzbar.pyzbar import decode
import math
import re


# ==================================================
# 基本設定
# ==================================================
st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍",
    layout="centered"
)

st.title("🔍 せどりリサーチAI")
st.caption("バーコード → 商品特定 → 複数市場の価格確認 → 仕入れ判断")


# ==================================================
# セッション
# ==================================================
if "jan" not in st.session_state:
    st.session_state.jan = ""

if "product_name" not in st.session_state:
    st.session_state.product_name = ""

if "candidates" not in st.session_state:
    st.session_state.candidates = []


# ==================================================
# 商品名を検索しやすくする
# ==================================================
def clean_product_name(name):

    if not name:
        return ""

    cleaned = name

    cleaned = re.sub(r"《[^》]*》", "", cleaned)
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"【[^】]*】", "", cleaned)
    cleaned = re.sub(r"『[^』]*』", "", cleaned)

    unnecessary_words = [
        "送料無料",
        "新品",
        "在庫あり",
        "在庫切れ",
        "即納",
    ]

    for word in unnecessary_words:
        cleaned = cleaned.replace(word, "")

    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


# ==================================================
# バーコード読み取り
# ==================================================
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


# ==================================================
# Yahoo! API
# JAN → 商品特定
# ==================================================
def search_yahoo_by_jan(jan):

    try:
        app_id = st.secrets["YAHOO_APP_ID"]

    except Exception:
        return None, "Yahoo! Client IDがSecretsにありません。"

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
            return None, "Yahoo!では商品が見つかりませんでした。"

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

            "shop": (
                hit.get("seller") or {}
            ).get("name", ""),

            "results": hits,
        }

        return product, None

    except requests.exceptions.Timeout:
        return None, "Yahoo! APIがタイムアウトしました。"

    except Exception as e:
        return None, f"Yahoo!検索エラー：{e}"


# ==================================================
# 楽天市場API
# 商品名 → 楽天価格
# ==================================================
def search_rakuten(keyword):

    try:
        app_id = st.secrets["RAKUTEN_APP_ID"]
        access_key = st.secrets["RAKUTEN_ACCESS_KEY"]

    except Exception:
        return None, "楽天のApplication ID / Access KeyがSecretsにありません。"

    url = (
        "https://openapi.rakuten.co.jp/"
        "ichibams/api/IchibaItem/Search/20260701"
    )

    # Application IDはこちら
    params = {
        "applicationId": app_id,
        "keyword": keyword,
        "format": "json",
        "formatVersion": 2,
        "hits": 10,
        "sort": "+itemPrice",
        "availability": 1,
        "imageFlag": 1,
    }

    # Access Keyはこちら
    headers = {
        "accessKey": access_key
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:

            try:
                error_data = response.json()

                detail = (
                    error_data.get("error_description")
                    or error_data.get("error")
                    or ""
                )

            except Exception:
                detail = response.text[:200]

            return (
                None,
                f"楽天APIエラー：HTTP {response.status_code} {detail}"
            )

        data = response.json()

        # formatVersion=2
        items = data.get("Items") or data.get("items") or []

        if not items:
            return None, "楽天市場では該当商品が見つかりませんでした。"

        cleaned_items = []

        for entry in items:

            # Version 1 / Version 2の両方に対応
            item = (
                entry.get("Item")
                or entry.get("item")
                or entry
            )

            try:
                price = int(item.get("itemPrice", 0))
            except Exception:
                price = 0

            cleaned_items.append({
                "name": item.get("itemName", ""),
                "price": price,
                "url": item.get("itemUrl", ""),
                "shop": item.get("shopName", ""),
                "review_count": item.get("reviewCount", 0),
                "review_average": item.get("reviewAverage", 0),
            })

        cleaned_items = [
            item
            for item in cleaned_items
            if item["price"] > 0
        ]

        cleaned_items.sort(
            key=lambda x: x["price"]
        )

        if not cleaned_items:
            return None, "楽天市場で有効な価格情報を取得できませんでした。"

        return cleaned_items, None

    except requests.exceptions.Timeout:
        return None, "楽天APIがタイムアウトしました。"

    except Exception as e:
        return None, f"楽天検索エラー：{e}"


# ==================================================
# 1. バーコード
# ==================================================
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

        st.success(f"JAN：{detected_jan}")

    else:

        st.warning(
            "読み取れませんでした。"
            "バーコード全体を大きく撮影してください。"
        )


# ==================================================
# JAN手入力
# ==================================================
jan = st.text_input(
    "JANコード",
    value=st.session_state.jan,
    placeholder="例：4573102693020"
)

jan = jan.strip()

if jan != st.session_state.jan:
    st.session_state.jan = jan
    st.session_state.product_name = ""


# ==================================================
# 2. Yahoo!商品情報
# ==================================================
product = None

if jan:

    if not jan.isdigit():

        st.error("JANコードは数字で入力してください。")

    elif len(jan) not in [8, 12, 13]:

        st.warning("JANコードの桁数を確認してください。")

    else:

        with st.spinner("Yahoo!から商品を特定中..."):

            product, yahoo_error = search_yahoo_by_jan(jan)

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

            st.metric(
                "Yahoo!新品参考価格",
                f"¥{product['price']:,}"
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

                st.session_state.product_name = clean_product_name(
                    product["name"]
                )

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

            st.warning(yahoo_error)


# ==================================================
# 検索用商品名
# ==================================================
product_name = st.text_input(
    "検索に使う商品名・型番",
    value=st.session_state.product_name
)

st.session_state.product_name = product_name

search_word = product_name.strip() or jan


# ==================================================
# 3. 楽天市場
# ==================================================
if search_word:

    st.subheader("🛍️ 3. 楽天市場の価格")

    with st.spinner("楽天市場を検索中..."):

        rakuten_items, rakuten_error = search_rakuten(
            search_word
        )

    if rakuten_items:

        prices = [
            item["price"]
            for item in rakuten_items
        ]

        rakuten_min = min(prices)

        st.success("楽天API接続成功")

        st.metric(
            "楽天 最安参考価格",
            f"¥{rakuten_min:,}"
        )

        st.caption(
            f"楽天市場から{len(rakuten_items)}件取得"
        )

        with st.expander("楽天の価格一覧を見る"):

            for item in rakuten_items:

                st.markdown(
                    f"### ¥{item['price']:,}"
                )

                st.write(
                    item["name"]
                )

                if item["shop"]:
                    st.caption(
                        f"ショップ：{item['shop']}"
                    )

                if item["review_count"]:

                    st.caption(
                        f"レビュー："
                        f"{item['review_average']} "
                        f"({item['review_count']}件)"
                    )

                if item["url"]:

                    st.link_button(
                        "楽天の商品を見る",
                        item["url"]
                    )

                st.divider()

    else:

        st.warning(rakuten_error)


# ==================================================
# 4. 他市場へのリンク
# ==================================================
if search_word:

    st.subheader("🔎 4. 他の相場を確認")

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
        "メルカリでは「絞り込み → 販売状況 → 売り切れ」"
        "で実際に売れた価格を確認してください。"
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


# ==================================================
# 5. 利益計算
# ==================================================
st.divider()

st.subheader("💰 5. メルカリ利益計算")

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


fee_rate = st.number_input(
    "販売手数料（％）",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=0.5
)


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


# ==================================================
# 計算
# ==================================================
fee = selling_price * fee_rate / 100

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
        * 100
    )

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


# ==================================================
# 6. 仕入れ判定
# ==================================================
st.subheader("📊 6. 仕入れ判定")


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
    f"販売価格 ¥{selling_price:,}"
    f" − 手数料 ¥{fee:,.0f}"
    f" − 送料 ¥{shipping:,}"
    f" − 資材 ¥{materials:,}"
    f" − 仕入 ¥{purchase_price:,}"
)


profit_ok = profit >= minimum_profit
roi_ok = roi >= minimum_roi


if profit_ok and roi_ok:

    st.success(
        "🟢 仕入れ候補です"
    )

elif profit > 0:

    st.warning(
        "🟡 利益は出ますが、仕入れ基準未満です"
    )

else:

    st.error(
        "🔴 この価格では赤字です"
    )


if (
    purchase_price > 0
    and purchase_price <= max_purchase
):

    difference = (
        max_purchase
        - purchase_price
    )

    st.success(
        f"仕入上限より ¥{difference:,} 安く仕入れられます。"
    )

elif purchase_price > max_purchase:

    difference = (
        purchase_price
        - max_purchase
    )

    st.warning(
        f"仕入上限を ¥{difference:,} オーバーしています。"
    )


# ==================================================
# 仕入れ候補保存
# ==================================================
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


if st.session_state.candidates:

    st.divider()

    st.subheader("⭐ 仕入れ候補")

    st.dataframe(
        st.session_state.candidates,
        use_container_width=True
)
