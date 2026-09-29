import streamlit as st
import requests
import re
import math
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps
from pyzbar.pyzbar import decode


# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍",
    layout="centered"
)

st.title("🔍 せどりリサーチAI")
st.caption("バーコードを読んで、その場で仕入れ判断")


# =========================
# 初期化
# =========================
for key, value in {
    "jan": "",
    "product_name": "",
    "candidates": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================
# 商品名を検索用に整理
# =========================
def clean_name(name):
    if not name:
        return ""

    for pattern in [
        r"《[^》]*》",
        r"\[[^\]]*\]",
        r"【[^】]*】",
        r"『[^』]*』"
    ]:
        name = re.sub(pattern, "", name)

    return re.sub(r"\s+", " ", name).strip()


# =========================
# バーコード読取
# =========================
def read_barcode(image):
    try:
        img = image.convert("RGB")
        gray = ImageOps.grayscale(img)

        targets = [
            img,
            img.resize((img.width * 2, img.height * 2)),
            gray,
            ImageEnhance.Contrast(gray).enhance(3)
        ]

        for target in targets:
            for result in decode(target):
                code = result.data.decode().strip()

                if code.isdigit() and len(code) in (8, 12, 13):
                    return code
    except Exception:
        pass

    return None


# =========================
# Yahoo API
# =========================
@st.cache_data(ttl=600)
def yahoo_search(jan):
    try:
        app_id = str(st.secrets["YAHOO_APP_ID"]).strip()

        r = requests.get(
            "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch",
            params={
                "appid": app_id,
                "jan_code": jan,
                "results": 10
            },
            timeout=15
        )

        if r.status_code != 200:
            return None, f"Yahoo API：HTTP {r.status_code}"

        hits = r.json().get("hits", [])

        if not hits:
            return None, "Yahooで商品が見つかりませんでした。"

        hits.sort(key=lambda x: x.get("price", 999999999))
        hit = hits[0]

        image = (
            (hit.get("exImage") or {}).get("url")
            or (hit.get("image") or {}).get("medium")
            or ""
        )

        return {
            "name": hit.get("name", ""),
            "brand": (hit.get("brand") or {}).get("name", ""),
            "price": hit.get("price", 0),
            "shop": (hit.get("seller") or {}).get("name", ""),
            "image": image,
            "url": hit.get("url", ""),
            "hits": hits
        }, None

    except Exception as e:
        return None, f"Yahoo検索エラー：{e}"


# =========================
# 楽天API
# =========================
@st.cache_data(ttl=600)
def rakuten_search(keyword):
    try:
        app_id = str(st.secrets["RAKUTEN_APP_ID"]).strip()
        access_key = str(st.secrets["RAKUTEN_ACCESS_KEY"]).strip()

        app_url = (
            "https://sedori-research-ai-"
            "j5x65mktg58sbwrcvwackx.streamlit.app"
        )

        r = requests.get(
            "https://openapi.rakuten.co.jp/"
            "ichibams/api/IchibaItem/Search/20260701",
            params={
                "format": "json",
                "formatVersion": 2,
                "keyword": keyword,
                "applicationId": app_id,
                "accessKey": access_key,
                "hits": 10,
                "sort": "+itemPrice",
                "availability": 1
            },
            headers={
                "Referer": app_url + "/",
                "Origin": app_url
            },
            timeout=15
        )

        if r.status_code != 200:
            return [], f"楽天API：HTTP {r.status_code}"

        entries = r.json().get("Items", []) or r.json().get("items", [])
        items = []

        for entry in entries:
            item = entry.get("Item") or entry.get("item") or entry

            try:
                price = int(item.get("itemPrice", 0))
            except (ValueError, TypeError):
                continue

            if price > 0:
                items.append({
                    "name": item.get("itemName", ""),
                    "price": price,
                    "shop": item.get("shopName", ""),
                    "url": item.get("itemUrl", "")
                })

        items.sort(key=lambda x: x["price"])

        return items, None

    except Exception as e:
        return [], f"楽天検索エラー：{e}"


# =========================
# ① バーコード
# =========================
st.subheader("① バーコード")

camera = st.camera_input("JANバーコードを撮影")

if camera:
    code = read_barcode(Image.open(camera))

    if code:
        if code != st.session_state.jan:
            st.session_state.jan = code
            st.session_state.product_name = ""

        st.success(f"JAN：{code}")
    else:
        st.warning("バーコードを読み取れませんでした。")


jan = st.text_input(
    "JANコード",
    value=st.session_state.jan,
    placeholder="例：4573102693020"
).strip()

if jan != st.session_state.jan:
    st.session_state.jan = jan
    st.session_state.product_name = ""


# =========================
# ② 商品特定
# =========================
product = None

if jan and jan.isdigit() and len(jan) in (8, 12, 13):

    with st.spinner("商品を検索中..."):
        product, yahoo_error = yahoo_search(jan)

    if product:
        if not st.session_state.product_name:
            st.session_state.product_name = clean_name(product["name"])

        st.subheader("② 商品")

        if product["image"]:
            st.image(product["image"], width=180)

        st.markdown(f"### {product['name']}")

        if product["brand"]:
            st.caption(f"ブランド：{product['brand']}")

        st.caption(f"JAN：{jan}")

    else:
        st.warning(yahoo_error)


# =========================
# 検索ワード
# =========================
search_word = st.text_input(
    "検索用商品名",
    value=st.session_state.product_name
).strip()

st.session_state.product_name = search_word


# =========================
# ③ 相場
# =========================
if search_word:

    st.subheader("③ 相場チェック")

    yahoo_price = product["price"] if product else 0

    with st.spinner("楽天価格を取得中..."):
        rakuten_items, rakuten_error = rakuten_search(search_word)

    rakuten_price = (
        rakuten_items[0]["price"]
        if rakuten_items else 0
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Yahoo最安",
        f"¥{yahoo_price:,}" if yahoo_price else "―"
    )

    c2.metric(
        "楽天最安",
        f"¥{rakuten_price:,}" if rakuten_price else "―"
    )

    if rakuten_error:
        st.warning(rakuten_error)

    elif rakuten_items:
        with st.expander(f"楽天価格一覧（{len(rakuten_items)}件）"):
            for item in rakuten_items:
                st.write(
                    f"**¥{item['price']:,}** "
                    f"｜{item['shop']}"
                )
                st.caption(item["name"])

    encoded = quote(search_word)

    st.link_button(
        "🔴 メルカリ売り切れ相場を確認",
        f"https://jp.mercari.com/search?keyword={encoded}",
        use_container_width=True
    )

    st.caption(
        "メルカリを開いたら「販売状況 → 売り切れ」で"
        "最近の成約価格を確認してください。"
    )

    with st.expander("その他の市場を見る"):

        st.link_button(
            "Amazon",
            f"https://www.amazon.co.jp/s?k={encoded}",
            use_container_width=True
        )

        st.link_button(
            "Yahoo!ショッピング",
            f"https://shopping.yahoo.co.jp/search?p={encoded}",
            use_container_width=True
        )

        st.link_button(
            "楽天市場",
            f"https://search.rakuten.co.jp/search/mall/{encoded}/",
            use_container_width=True
        )


# =========================
# ④ 仕入れ判断
# =========================
st.divider()
st.subheader("④ 仕入れ判断")

selling_price = st.number_input(
    "メルカリ想定売価",
    min_value=0,
    value=5000,
    step=100
)

purchase_price = st.number_input(
    "店頭の仕入価格",
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
    "宅急便 60": 750,
    "宅急便 80": 850,
    "宅急便 100": 1050,
    "宅急便 120": 1200,
    "宅急便 140": 1450,
    "宅急便 160": 1700
}

shipping_method = st.selectbox(
    "配送方法",
    list(shipping_options),
    index=6
)

shipping = shipping_options[shipping_method]

materials = st.number_input(
    "梱包資材",
    min_value=0,
    value=0,
    step=10
)

fee_rate = st.number_input(
    "販売手数料 %",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=0.5
)

minimum_profit = st.number_input(
    "最低利益",
    min_value=0,
    value=1500,
    step=100
)

minimum_roi = st.number_input(
    "最低ROI %",
    min_value=0.0,
    value=30.0,
    step=5.0
)


# =========================
# 計算
# =========================
fee = selling_price * fee_rate / 100

before_purchase = (
    selling_price
    - fee
    - shipping
    - materials
)

profit = before_purchase - purchase_price

roi = (
    profit / purchase_price * 100
    if purchase_price > 0 else 0
)

profit_limit = before_purchase - minimum_profit

roi_limit = (
    before_purchase / (1 + minimum_roi / 100)
)

max_purchase = math.floor(
    max(0, min(profit_limit, roi_limit))
)


# =========================
# 結果
# =========================
st.markdown("### 📊 判定結果")

a, b, c = st.columns(3)

a.metric("利益", f"¥{profit:,.0f}")
b.metric("ROI", f"{roi:.1f}%")
c.metric("仕入上限", f"¥{max_purchase:,}")


if (
    profit >= minimum_profit
    and roi >= minimum_roi
):
    st.success("🟢 仕入れ候補")

elif profit > 0:
    st.warning("🟡 利益は出ますが基準未満")

else:
    st.error("🔴 見送り")


if purchase_price <= max_purchase and purchase_price > 0:

    st.success(
        f"仕入上限より "
        f"¥{max_purchase - purchase_price:,} 安いです"
    )

elif purchase_price > max_purchase:

    st.warning(
        f"仕入上限を "
        f"¥{purchase_price - max_purchase:,} 超えています"
    )


# =========================
# ⑤ 候補保存
# =========================
if st.button(
    "⭐ 仕入れ候補に保存",
    use_container_width=True
):

    st.session_state.candidates.append({
        "JAN": jan,
        "商品名": search_word,
        "仕入": purchase_price,
        "売価": selling_price,
        "利益": round(profit),
        "ROI": round(roi, 1),
        "仕入上限": max_purchase
    })

    st.success("保存しました")


if st.session_state.candidates:

    with st.expander(
        f"⭐ 保存した候補（{len(st.session_state.candidates)}件）"
    ):
        st.dataframe(
            st.session_state.candidates,
            use_container_width=True
    )
