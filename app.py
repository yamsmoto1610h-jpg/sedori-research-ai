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
st.caption("店舗せどり用 商品リサーチ・利益計算")


# =========================
# セッション保存
# =========================

if "jan" not in st.session_state:
    st.session_state.jan = ""

if "product_name" not in st.session_state:
    st.session_state.product_name = ""

if "camera_open" not in st.session_state:
    st.session_state.camera_open = False

if "candidates" not in st.session_state:
    st.session_state.candidates = []


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


# =========================
# カメラON/OFF
# =========================

if not st.session_state.camera_open:

    if st.button(
        "📷 バーコードを撮影する",
        use_container_width=True
    ):

        st.session_state.camera_open = True
        st.rerun()

else:

    st.subheader("📷 バーコード撮影")

    camera_image = st.camera_input(
        "JANバーコードを撮影"
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

    if st.button(
        "❌ カメラを閉じる",
        use_container_width=True
    ):

        st.session_state.camera_open = False
        st.rerun()


# =========================
# JAN入力
# =========================

st.subheader("🔢 JANコード")

jan = st.text_input(
    "JANコード",
    value=st.session_state.jan,
    placeholder="例：4902430912526"
)

jan = jan.strip()

st.session_state.jan = jan


# =========================
# 商品情報
# =========================

product = None
auto_name = ""
brand = ""
image_url = ""

if jan and jan.isdigit() and len(jan) in (8, 12, 13):

    product = get_product_info(jan)

    if product:

        auto_name = product["name"]
        brand = product["brand"]
        image_url = product["image"]

        if (
            auto_name
            and not st.session_state.product_name
        ):

            st.session_state.product_name = auto_name


# =========================
# 商品名
# =========================

st.subheader("🏷️ 商品名")

product_name = st.text_input(
    "商品名・型番",
    value=st.session_state.product_name,
    placeholder="例：EPSON KAM-6CL-L"
)

product_name = product_name.strip()

st.session_state.product_name = product_name


if image_url:

    st.image(
        image_url,
        width=220
    )

if brand:

    st.write(
        f"ブランド：**{brand}**"
    )


# =========================
# 検索ワード
# =========================

if product_name:

    search_word = product_name

elif jan:

    search_word = jan

else:

    search_word = ""


# =========================
# 相場検索
# =========================

if search_word:

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

    st.write(
        f"検索ワード：**{search_word}**"
    )

    st.link_button(
        "🟠 Amazonで商品を確認",
        amazon_url,
        use_container_width=True
    )

    st.link_button(
        "🔴 メルカリで相場を確認",
        mercari_url,
        use_container_width=True
    )

    st.link_button(
        "🔴 楽天市場で確認",
        rakuten_url,
        use_container_width=True
    )

    st.link_button(
        "🟣 Yahoo!ショッピングで確認",
        yahoo_url,
        use_container_width=True
    )

    st.caption(
        "メルカリでJAN検索がヒットしない場合は、"
        "上の商品名・型番を入力すると商品名で検索できます。"
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
    "店頭の仕入価格（円）",
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

    "ゆうパケットポストmini": (160, 0),

    "ネコポス": (210, 0),

    "ゆうパケットポスト": (215, 0),

    "ゆうパケット": (230, 0),

    "宅急便コンパクト": (450, 70),

    "ゆうパケットプラス": (455, 65),

    "宅急便 60サイズ": (750, 0),

    "宅急便 80サイズ": (850, 0),

    "宅急便 100サイズ": (1050, 0),

    "宅急便 120サイズ": (1200, 0),

    "宅急便 140サイズ": (1450, 0),

    "宅急便 160サイズ": (1700, 0),

    "その他": (0, 0)
}


shipping_method = st.selectbox(
    "配送方法",
    list(shipping_options.keys())
)


shipping_cost, material_cost = (
    shipping_options[shipping_method]
)


if shipping_method == "その他":

    shipping_cost = st.number_input(
        "送料（円）",
        min_value=0,
        value=0,
        step=10
    )

    material_cost = st.number_input(
        "資材代（円）",
        min_value=0,
        value=0,
        step=10
    )


total_shipping = (
    shipping_cost
    + material_cost
)


st.write(
    f"配送関連費：**{total_shipping:,}円**"
)


# =========================
# 仕入れ基準
# =========================

st.subheader("🎯 仕入れ基準")


target_profit = st.number_input(
    "最低利益（円）",
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
# 計算
# =========================

if selling_price > 0:

    fee = int(
        selling_price
        * fee_rate
        / 100
    )

    money_after_cost = (
        selling_price
        - fee
        - total_shipping
    )

    max_by_profit = (
        money_after_cost
        - target_profit
    )

    if target_roi > 0:

        max_by_roi = (
            money_after_cost
            / (1 + target_roi / 100)
        )

    else:

        max_by_roi = money_after_cost


    max_purchase = max(
        0,
        int(
            min(
                max_by_profit,
                max_by_roi
            )
        )
    )


    profit = (
        selling_price
        - purchase_price
        - fee
        - total_shipping
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


    # =========================
    # 結果
    # =========================

    st.subheader("🏷️ 仕入上限")

    st.metric(
        "この価格以下が仕入れ目安",
        f"{max_purchase:,}円"
    )


    st.subheader("📊 利益")

    st.metric(
        "想定利益",
        f"{profit:,}円"
    )

    st.metric(
        "ROI",
        f"{roi:.1f}%"
    )

    st.metric(
        "売上利益率",
        f"{profit_margin:.1f}%"
    )


    # =========================
    # 判定
    # =========================

    st.subheader("🚦 仕入れ判定")

    qualified = False

    if purchase_price == 0:

        st.info(
            "店頭の仕入価格を入力してください。"
        )

    elif (
        profit >= target_profit
        and roi >= target_roi
    ):

        qualified = True

        st.success(
            "🟢 仕入れ基準クリア"
        )

        difference = (
            max_purchase
            - purchase_price
        )

        st.write(
            f"仕入上限より **{difference:,}円安い**"
        )

    else:

        st.error(
            "🔴 見送り候補"
        )

        over = (
            purchase_price
            - max_purchase
        )

        if over > 0:

            st.write(
                f"あと **{over:,}円** "
                "安ければ仕入れ基準を満たします。"
            )


    # =========================
    # 候補保存
    # =========================

    if purchase_price > 0:

        if st.button(
            "⭐ この商品を候補に保存",
            use_container_width=True
        ):

            candidate = {

                "商品名":
                    product_name
                    if product_name
                    else "商品名未入力",

                "JAN":
                    jan
                    if jan
                    else "未入力",

                "仕入価格":
                    purchase_price,

                "販売価格":
                    selling_price,

                "利益":
                    profit,

                "ROI":
                    round(roi, 1),

                "仕入上限":
                    max_purchase,

                "判定":
                    "仕入れ候補"
                    if qualified
                    else "見送り"
            }

            st.session_state.candidates.append(
                candidate
            )

            st.success(
                "⭐ 候補リストに保存しました"
            )


# =========================
# 候補一覧
# =========================

st.divider()

st.header("⭐ 仕入れ候補リスト")


if st.session_state.candidates:

    for number, item in enumerate(
        st.session_state.candidates,
        start=1
    ):

        st.write(
            f"### {number}. {item['商品名']}"
        )

        st.write(
            f"JAN：{item['JAN']}"
        )

        st.write(
            f"仕入：{item['仕入価格']:,}円"
        )

        st.write(
            f"販売想定：{item['販売価格']:,}円"
        )

        st.write(
            f"利益：**{item['利益']:,}円**"
        )

        st.write(
            f"ROI：**{item['ROI']:.1f}%**"
        )

        st.write(
            f"仕入上限：{item['仕入上限']:,}円"
        )

        st.write(
            f"判定：**{item['判定']}**"
        )

        st.divider()


    if st.button(
        "🗑️ 候補リストを全削除"
    ):

        st.session_state.candidates = []

        st.rerun()

else:

    st.info(
        "まだ商品は保存されていません。"
)
