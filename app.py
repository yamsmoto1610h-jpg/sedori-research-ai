import streamlit as st
import requests
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from pyzbar.pyzbar import decode


# ==================================================
# 基本設定
# ==================================================

st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍",
    layout="centered"
)

st.title("🔍 せどりリサーチAI")
st.caption("バーコード → 相場検索 → 利益計算 → 仕入れ判断")


# ==================================================
# セッション
# ==================================================

if "jan" not in st.session_state:
    st.session_state.jan = ""

if "candidates" not in st.session_state:
    st.session_state.candidates = []


# ==================================================
# バーコード読み取り
# ==================================================

def read_barcode(image):

    image = image.convert("RGB")

    images_to_try = []

    # 元画像
    images_to_try.append(image)

    # 2倍
    images_to_try.append(
        image.resize(
            (
                image.width * 2,
                image.height * 2
            )
        )
    )

    # 3倍
    images_to_try.append(
        image.resize(
            (
                image.width * 3,
                image.height * 3
            )
        )
    )

    # グレースケール
    gray = ImageOps.grayscale(image)

    images_to_try.append(gray)

    # コントラスト強化
    contrast2 = ImageEnhance.Contrast(
        gray
    ).enhance(2.0)

    images_to_try.append(contrast2)

    contrast3 = ImageEnhance.Contrast(
        gray
    ).enhance(3.0)

    images_to_try.append(contrast3)

    # シャープ化
    sharp = gray.filter(
        ImageFilter.SHARPEN
    )

    images_to_try.append(sharp)

    # 白黒強調
    threshold = gray.point(
        lambda x: 0 if x < 140 else 255
    )

    images_to_try.append(threshold)

    # 読み取り
    for img in images_to_try:

        try:

            results = decode(img)

        except Exception:

            continue

        if not results:
            continue

        for result in results:

            try:

                code = result.data.decode(
                    "utf-8"
                ).strip()

            except Exception:

                continue

            if (
                code.isdigit()
                and len(code) in (8, 12, 13)
            ):

                return code

    return None


# ==================================================
# 商品情報取得
# ==================================================

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

        product = data.get(
            "product",
            {}
        )

        name = (
            product.get("product_name_ja")
            or product.get("product_name")
            or ""
        )

        brand = (
            product.get("brands")
            or ""
        )

        image_url = (
            product.get("image_front_url")
            or product.get("image_url")
            or ""
        )

        return {
            "name": name,
            "brand": brand,
            "image": image_url
        }

    except Exception:

        return None


# ==================================================
# 商品検索
# ==================================================

st.header("📦 商品検索")


# ==================================================
# バーコード撮影
# ==================================================

st.subheader("📷 バーコード撮影")

st.write(
    "バーコード全体が画面に入るように撮影してください。"
)

camera_image = st.camera_input(
    "バーコードを撮影"
)


if camera_image is not None:

    try:

        image = Image.open(
            camera_image
        )

        barcode = read_barcode(
            image
        )

        if barcode:

            st.session_state.jan = barcode

            st.success(
                f"✅ 読み取り成功：{barcode}"
            )

        else:

            st.warning(
                "⚠️ バーコードを読み取れませんでした。\n\n"
                "・バーコード全体を写す\n"
                "・少し離して撮る\n"
                "・光の反射を避ける\n"
                "・カメラを水平にする\n\n"
                "この4点を確認してもう一度撮影してください。"
            )

    except Exception:

        st.error(
            "画像の読み込みに失敗しました。"
        )


# ==================================================
# JAN入力
# ==================================================

st.subheader("🔢 JANコード")

jan = st.text_input(
    "JANコード",
    value=st.session_state.jan,
    placeholder="例：4902430912526"
)

jan = jan.strip()


# ==================================================
# JANチェック
# ==================================================

valid_jan = False

if jan:

    if (
        jan.isdigit()
        and len(jan) in (8, 12, 13)
    ):

        valid_jan = True

        st.success(
            "✅ JANコード確認OK"
        )

    else:

        st.error(
            "JANコードは8桁・12桁・13桁の数字で入力してください。"
        )


# ==================================================
# 商品情報
# ==================================================

product_name = ""
brand = ""
image_url = ""


if valid_jan:

    product = get_product_info(
        jan
    )

    if product:

        product_name = (
            product.get("name", "")
        )

        brand = (
            product.get("brand", "")
        )

        image_url = (
            product.get("image", "")
        )


# ==================================================
# 商品名
# ==================================================

st.subheader("🏷️ 商品名・型番")

search_name = st.text_input(
    "商品名・型番",
    value=product_name,
    placeholder="例：EPSON KAM-6CL-L"
)

search_name = search_name.strip()


if image_url:

    st.image(
        image_url,
        width=220
    )


if brand:

    st.write(
        f"ブランド：**{brand}**"
    )


if valid_jan and not product_name:

    st.info(
        "このJANの商品名は自動取得できませんでした。\n\n"
        "メルカリ検索を正確にするため、"
        "商品名や型番が分かる場合は上の欄に入力してください。"
    )


# ==================================================
# 検索ワード
# ==================================================

if search_name:

    search_word = search_name

elif jan:

    search_word = jan

else:

    search_word = ""


# ==================================================
# 相場検索
# ==================================================

if search_word:

    st.subheader("🛒 相場を調べる")

    st.write(
        f"検索ワード：**{search_word}**"
    )


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


    if not search_name:

        st.warning(
            "💡 メルカリはJANコードだけでは"
            "商品がヒットしないことがあります。\n\n"
            "商品名・型番を入力すると、"
            "その文字でメルカリ検索できます。"
        )


# ==================================================
# 利益計算
# ==================================================

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


# ==================================================
# 配送方法
# ==================================================

st.subheader("🚚 配送方法")


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

    "その他・手入力": 0
}


shipping_method = st.selectbox(
    "配送方法",
    list(
        shipping_options.keys()
    )
)


if shipping_method == "その他・手入力":

    shipping_cost = st.number_input(
        "送料（円）",
        min_value=0,
        value=0,
        step=10
    )

else:

    shipping_cost = (
        shipping_options[
            shipping_method
        ]
    )


# ==================================================
# 資材代
# ==================================================

if shipping_method == "宅急便コンパクト":

    default_material = 70

elif shipping_method == "ゆうパケットプラス":

    default_material = 65

else:

    default_material = 0


material_cost = st.number_input(
    "梱包・専用資材代（円）",
    min_value=0,
    value=default_material,
    step=5
)


total_shipping = (
    shipping_cost
    + material_cost
)


st.write(
    f"送料：**{shipping_cost:,}円**"
)

st.write(
    f"資材代：**{material_cost:,}円**"
)

st.write(
    f"配送関連費：**{total_shipping:,}円**"
)


# ==================================================
# 仕入れ基準
# ==================================================

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


# ==================================================
# 計算
# ==================================================

if selling_price > 0:

    fee = int(
        selling_price
        * fee_rate
        / 100
    )


    money_before_purchase = (
        selling_price
        - fee
        - total_shipping
    )


    profit = (
        money_before_purchase
        - purchase_price
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


    # ==============================================
    # 仕入上限
    # ==============================================

    max_by_profit = (
        money_before_purchase
        - target_profit
    )


    if target_roi > 0:

        max_by_roi = (
            money_before_purchase
            / (
                1
                + target_roi / 100
            )
        )

    else:

        max_by_roi = (
            money_before_purchase
        )


    max_purchase = max(
        0,
        int(
            min(
                max_by_profit,
                max_by_roi
            )
        )
    )


    # ==============================================
    # 結果
    # ==============================================

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
        f"配送関連費：{total_shipping:,}円"
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


    # ==============================================
    # 仕入上限
    # ==============================================

    st.subheader("🏷️ 仕入上限価格")


    st.metric(
        "この価格以下なら基準クリア",
        f"{max_purchase:,}円"
    )


    st.caption(
        f"最低利益 {target_profit:,}円 ＋ "
        f"最低ROI {target_roi:.1f}% を"
        "両方満たす仕入上限です。"
    )


    # ==============================================
    # 判定
    # ==============================================

    st.subheader("🚦 仕入れ判定")


    qualified = False


    if purchase_price == 0:

        st.info(
            "仕入価格を入力すると判定します。"
        )


    elif (
        profit >= target_profit
        and roi >= target_roi
    ):

        qualified = True

        st.success(
            "🟢 仕入れ候補"
        )

        difference = (
            max_purchase
            - purchase_price
        )

        st.write(
            f"仕入上限より "
            f"**{difference:,}円安く** "
            "仕入れできます。"
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
                "安ければ基準を満たします。"
            )


    # ==============================================
    # 候補保存
    # ==============================================

    if purchase_price > 0:

        if st.button(
            "⭐ この商品を候補に保存",
            use_container_width=True
        ):

            candidate = {

                "商品名":
                    search_name
                    if search_name
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
                    round(
                        roi,
                        1
                    ),

                "仕入上限":
                    max_purchase,

                "判定":
                    "🟢 仕入れ候補"
                    if qualified
                    else "🔴 見送り"
            }


            st.session_state.candidates.append(
                candidate
            )


            st.success(
                "✅ 候補リストに保存しました"
            )


# ==================================================
# 候補リスト
# ==================================================

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
            f"仕入価格：{item['仕入価格']:,}円"
        )

        st.write(
            f"販売価格：{item['販売価格']:,}円"
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
            f"判定：{item['判定']}"
        )

        st.divider()


    if st.button(
        "🗑️ 候補リストをすべて削除",
        use_container_width=True
    ):

        st.session_state.candidates = []

        st.rerun()


else:

    st.info(
        "まだ仕入れ候補は保存されていません。"
    )
