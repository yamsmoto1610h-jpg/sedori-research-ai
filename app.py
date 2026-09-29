import streamlit as st
from urllib.parse import quote
from PIL import Image, ImageEnhance, ImageOps
from pyzbar.pyzbar import decode

st.set_page_config(
    page_title="せどりリサーチAI",
    page_icon="🔍"
)

st.title("🔍 せどりリサーチAI")
st.header("📦 商品検索")

# JANコード保存
if "jan" not in st.session_state:
    st.session_state.jan = ""

st.subheader("📷 バーコード撮影")

st.write(
    "商品のJANバーコードを撮影してください。"
    "読み取れない場合は、下のJANコード欄に直接入力できます。"
)

camera_image = st.camera_input("バーコードを撮影")


def read_barcode(image):
    """複数の画像処理を試してバーコードを読み取る"""

    # RGBに統一
    image = image.convert("RGB")

    # 元画像
    images_to_try = [image]

    # 2倍・3倍に拡大
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

    # グレースケール
    gray = ImageOps.grayscale(image)

    images_to_try.append(gray)

    # コントラスト強化
    contrast = ImageEnhance.Contrast(gray).enhance(2.0)
    images_to_try.append(contrast)

    # さらに強く
    contrast2 = ImageEnhance.Contrast(gray).enhance(3.0)
    images_to_try.append(contrast2)

    # 各画像で読み取り
    for img in images_to_try:

        results = decode(img)

        if results:

            for result in results:

                try:
                    code = result.data.decode("utf-8")
                except:
                    continue

                # JAN-8 / JAN-13のみ採用
                if code.isdigit() and len(code) in (8, 13):
                    return code

    return None


if camera_image is not None:

    image = Image.open(camera_image)

    with st.spinner("🔍 バーコードを解析しています..."):

        barcode = read_barcode(image)

    if barcode:

        st.session_state.jan = barcode

        st.success(
            f"✅ JANコードを読み取りました：{barcode}"
        )

    else:

        st.warning(
            "⚠️ バーコードを自動認識できませんでした。\n\n"
            "バーコード全体が画面に入り、数字と縦線が"
            "はっきり見える距離で撮影してください。"
        )


st.subheader("🔢 JANコード")

jan = st.text_input(
    "JANコードを入力",
    value=st.session_state.jan,
    placeholder="例：4902430912526"
)


if jan:

    jan = jan.strip()

    if jan.isdigit() and len(jan) in (8, 13):

        st.success("✅ JANコードを確認しました")

        amazon_url = (
            "https://www.amazon.co.jp/s?k="
            + quote(jan)
        )

        mercari_url = (
            "https://jp.mercari.com/search?keyword="
            + quote(jan)
        )

        yahoo_url = (
            "https://auctions.yahoo.co.jp/search/search?p="
            + quote(jan)
        )

        st.subheader("🔎 商品を調べる")

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
            "🟣 Yahoo!オークションで検索",
            yahoo_url,
            use_container_width=True
        )

        st.info(
            f"検索中のJANコード：{jan}"
        )

    else:

        st.error(
            "JANコードは8桁または13桁の数字で入力してください。"
        )
