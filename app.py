import math
import re
from urllib.parse import quote

import requests
import streamlit as st
from PIL import Image, ImageEnhance, ImageOps

try:
    from pyzbar.pyzbar import decode
    BARCODE_AVAILABLE = True
except (ImportError, OSError):
    BARCODE_AVAILABLE = False

st.set_page_config(page_title="せどりリサーチAI Ver.2", page_icon="🔍", layout="centered")
st.title("🔍 せどりリサーチAI Ver.2")
st.caption("JAN検索 → 国内・海外の利益試算 → 仕入れ判定")

for key, value in {"jan": "", "product_name": "", "candidates": []}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clean_name(name):
    if not name:
        return ""
    for pattern in [r"《[^》]*》", r"\[[^\]]*\]", r"【[^】]*】", r"『[^』]*』"]:
        name = re.sub(pattern, "", name)
    return re.sub(r"\s+", " ", name).strip()


def read_barcode(image):
    if not BARCODE_AVAILABLE:
        return None
    try:
        img = image.convert("RGB")
        gray = ImageOps.grayscale(img)
        targets = [img, img.resize((img.width * 2, img.height * 2)), gray,
                   ImageEnhance.Contrast(gray).enhance(3)]
        for target in targets:
            for result in decode(target):
                code = result.data.decode().strip()
                if code.isdigit() and len(code) in (8, 12, 13):
                    return code
    except Exception:
        return None
    return None


@st.cache_data(ttl=600)
def yahoo_search(jan):
    app_id = st.secrets.get("YAHOO_APP_ID", "")
    if not app_id:
        return None, "YAHOO_APP_IDが未設定です。"
    try:
        r = requests.get("https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch",
                         params={"appid": app_id, "jan_code": jan, "results": 10}, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return None, "Yahooで商品が見つかりませんでした。"
        hits.sort(key=lambda x: float(x.get("price") or 999999999))
        hit = hits[0]
        return {"name": hit.get("name", ""), "brand": (hit.get("brand") or {}).get("name", ""),
                "price": int(float(hit.get("price") or 0)),
                "image": (hit.get("exImage") or {}).get("url") or (hit.get("image") or {}).get("medium") or ""}, None
    except Exception as e:
        return None, f"Yahoo検索に失敗しました: {type(e).__name__}"


@st.cache_data(ttl=600)
def rakuten_search(keyword):
    app_id = st.secrets.get("RAKUTEN_APP_ID", "")
    access_key = st.secrets.get("RAKUTEN_ACCESS_KEY", "")
    if not app_id or not access_key:
        return [], "楽天APIの認証情報が未設定です。"
    app_url = "https://sedori-research-ai-j5x65mktg58sbwrcvwackx.streamlit.app"
    try:
        r = requests.get("https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701",
                         params={"format": "json", "formatVersion": 2, "keyword": keyword,
                                 "applicationId": app_id, "accessKey": access_key,
                                 "hits": 10, "sort": "+itemPrice", "availability": 1},
                         headers={"Referer": app_url + "/", "Origin": app_url}, timeout=15)
        r.raise_for_status()
        entries = r.json().get("Items", []) or r.json().get("items", [])
        items = []
        for entry in entries:
            item = entry.get("Item") or entry.get("item") or entry
            try:
                price = int(item.get("itemPrice", 0))
            except (ValueError, TypeError):
                continue
            if price > 0:
                items.append({"name": item.get("itemName", ""), "price": price,
                              "shop": item.get("shopName", ""), "url": item.get("itemUrl", "")})
        return sorted(items, key=lambda x: x["price"]), None
    except Exception as e:
        return [], f"楽天検索に失敗しました: {type(e).__name__}"


st.subheader("① 商品を特定")
if not BARCODE_AVAILABLE:
    st.info("バーコード解析ライブラリが利用できません。JANコードの手入力は利用できます。")
camera = st.camera_input("バーコードを撮影")
if camera:
    code = read_barcode(Image.open(camera))
    if code:
        if code != st.session_state.jan:
            st.session_state.jan = code
            st.session_state.product_name = ""
        st.success(f"読取成功: {code}")
    else:
        st.warning("読み取れませんでした。明るい場所でバーコードを大きく撮影するか、手入力してください。")

jan = st.text_input("JAN / EAN / UPC", key="jan", placeholder="例: 4904810079620").strip()
product = None
if jan and jan.isdigit() and len(jan) in (8, 12, 13):
    product, err = yahoo_search(jan)
    if product:
        if st.session_state.get("last_product_jan") != jan:
            st.session_state.product_name = clean_name(product["name"])
            st.session_state.last_product_jan = jan
        if product["image"]:
            st.image(product["image"], width=180)
        st.write("**" + product["name"] + "**")
        if product["brand"]:
            st.caption("ブランド: " + product["brand"])
    elif err:
        st.warning(err)

search_word = st.text_input("検索用商品名（必要に応じて編集）", key="product_name")
if search_word:
    st.subheader("② 国内相場とeBay検索")
    rakuten_items, rakuten_error = rakuten_search(search_word)
    c1, c2 = st.columns(2)
    c1.metric("Yahoo最安候補", f"¥{product['price']:,}" if product else "未取得")
    c2.metric("楽天最安候補", f"¥{rakuten_items[0]['price']:,}" if rakuten_items else "未取得")
    if rakuten_error:
        st.caption(rakuten_error)
    if rakuten_items:
        with st.expander("楽天価格一覧"):
            for item in rakuten_items:
                st.write(f"¥{item['price']:,} | {item['shop']} | {item['name']}")
    encoded = quote(search_word)
    st.link_button("メルカリで売り切れ相場を確認", f"https://jp.mercari.com/search?keyword={encoded}", use_container_width=True)
    st.link_button("eBayで販売中の商品を確認", f"https://www.ebay.com/sch/i.html?_nkw={encoded}", use_container_width=True)
    st.link_button("eBayで売れた商品を確認", f"https://www.ebay.com/sch/i.html?_nkw={encoded}&LH_Sold=1&LH_Complete=1", use_container_width=True)
    st.caption("検索結果は手動で確認してください。eBay成約相場の自動取得は未実装です。")

st.divider()
mode = st.radio("③ 販売先", ["メルカリ（国内）", "eBay（海外）"], horizontal=True)
purchase_price = st.number_input("仕入れ価格（円）", min_value=0, value=1000, step=100)
materials = st.number_input("梱包資材費（円）", min_value=0, value=100, step=10)
minimum_profit = st.number_input("最低目標利益（円）", min_value=0, value=2000, step=100)
minimum_roi = st.number_input("最低ROI（%・仕入れ価格に対する利益率）", min_value=0.0, value=30.0, step=5.0)

if mode.startswith("メルカリ"):
    selling_price = st.number_input("メルカリ想定売価（円）", min_value=0, value=5000, step=100)
    domestic_shipping = {"ゆうパケットポストmini": 160, "ネコポス": 210,
                         "ゆうパケットポスト": 215, "ゆうパケット": 230,
                         "宅急便コンパクト": 450, "ゆうパケットプラス": 455,
                         "宅急便 60": 750, "宅急便 80": 850,
                         "宅急便 100": 1050, "宅急便 120": 1200,
                         "宅急便 140": 1450, "宅急便 160": 1700}
    shipping_method = st.selectbox("配送方法（料金は参考値・要確認）", list(domestic_shipping), index=6)
    shipping = domestic_shipping[shipping_method]
    fee_rate = st.number_input("販売手数料（%）", min_value=0.0, max_value=100.0, value=10.0, step=0.5)
    revenue = float(selling_price)
    expenses_ex_purchase = revenue * fee_rate / 100 + shipping + materials
    confirmed = True
    breakdown = {"売上": revenue, "販売手数料": revenue * fee_rate / 100,
                 "国内送料": shipping, "梱包資材": materials}
else:
    st.info("eBayの成約相場・送料・関税は自動取得していません。各公式見積もりを確認して入力してください。")
    destination = st.selectbox("発送先", ["アメリカ", "カナダ", "イギリス", "ドイツ", "フランス", "オーストラリア", "その他"])
    origin = st.text_input("原産国（製造国。日本から発送＝日本製とは限りません）", placeholder="例: China")
    hs_code = st.text_input("HSコード（分かる場合）", placeholder="例: 該当する税番")
    shipping_term = st.selectbox("輸入費用の負担方式", ["DDP（原則売り手負担）", "DAP（原則買い手負担）", "不明"])
    usd_price = st.number_input("eBay商品価格（USD）", min_value=0.0, value=149.99, step=1.0)
    usd_shipping_charged = st.number_input("購入者から受け取る送料（USD）", min_value=0.0, value=39.99, step=1.0)
    exchange = st.number_input("計算用為替レート（1 USD＝何円）", min_value=1.0, value=150.0, step=1.0)
    st.caption("為替は自動取得していません。実際の受取時の換算レートとは異なる場合があります。")
    weight = st.number_input("梱包後重量（kg）", min_value=0.0, value=1.0, step=0.1)
    a, b, c = st.columns(3)
    length = a.number_input("縦（cm）", min_value=0.0, value=40.0)
    width = b.number_input("横（cm）", min_value=0.0, value=30.0)
    height = c.number_input("高さ（cm）", min_value=0.0, value=20.0)
    st.caption(f"梱包サイズ: {length:g}×{width:g}×{height:g}cm / 実重量: {weight:g}kg。容積重量の計算方法は配送会社ごとに異なります。")
    shipping_verified = st.checkbox("国際送料は配送会社の見積もりで確認済み")
    shipping = st.number_input("国際送料（円・売り手が配送会社に支払う額）", min_value=0, value=6500, step=100)
    st.markdown("**輸入費用（売り手負担額のみ）**")
    customs_verified = st.checkbox("関税・輸入税・通関手数料の負担と金額を確認済み")
    duty = st.number_input("売り手負担の関税（円）", min_value=0, value=0, step=100)
    import_tax = st.number_input("売り手負担の輸入税・輸入消費税等（円）", min_value=0, value=0, step=100)
    brokerage = st.number_input("売り手負担の通関・立替手数料（円）", min_value=0, value=0, step=100)
    st.caption("買い手が負担する金額は売り手経費に加えません。DDP/DAPだけで負担が確定するわけではありません。")
    ebay_fee_rate = st.number_input("eBay落札手数料率（%・実際のカテゴリーに合わせて変更）", min_value=0.0, max_value=100.0, value=13.6, step=0.1)
    international_fee_rate = st.number_input("eBay海外取引追加手数料率（%・適用条件を確認）", min_value=0.0, max_value=100.0, value=1.35, step=0.05)
    fixed_fee_usd = st.number_input("注文ごとの固定手数料（USD）", min_value=0.0, value=0.40, step=0.05)
    buyer_tax_usd = st.number_input("eBayが徴収する買い手側の税金（USD・手数料算定用、判明時のみ）", min_value=0.0, value=0.0, step=1.0)
    ad_rate = st.number_input("広告費率（%・使わないなら0）", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
    payout_rate = st.number_input("為替換算・出金等の費用率（%・実際の条件を確認）", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
    extra = st.number_input("その他の費用・返品リスク予備費（円）", min_value=0, value=1000, step=100)
    revenue = (usd_price + usd_shipping_charged) * exchange
    fee_base = (usd_price + usd_shipping_charged + buyer_tax_usd) * exchange
    ebay_fee = fee_base * (ebay_fee_rate + international_fee_rate) / 100 + fixed_fee_usd * exchange
    ad_fee = revenue * ad_rate / 100
    payout_fee = revenue * payout_rate / 100
    expenses_ex_purchase = (ebay_fee + ad_fee + payout_fee + shipping + duty + import_tax +
                            brokerage + materials + extra)
    confirmed = shipping_verified and customs_verified and shipping_term != "不明" and bool(origin.strip()) and bool(hs_code.strip())
    breakdown = {"売上（商品＋購入者負担送料）": revenue, "eBay手数料（概算）": ebay_fee,
                 "広告費（概算）": ad_fee, "為替・出金費用（概算）": payout_fee,
                 "国際送料": shipping, "関税（売り手負担）": duty,
                 "輸入税（売り手負担）": import_tax, "通関手数料": brokerage,
                 "梱包資材": materials, "その他・予備費": extra}

profit = revenue - expenses_ex_purchase - purchase_price
roi = profit / purchase_price * 100 if purchase_price > 0 else None
profit_limit = revenue - expenses_ex_purchase - minimum_profit
roi_limit = (revenue - expenses_ex_purchase) / (1 + minimum_roi / 100)
max_purchase = math.floor(max(0, min(profit_limit, roi_limit)))

st.divider()
st.subheader("④ 利益・仕入れ判定")
a, b, c = st.columns(3)
a.metric("予想利益", f"¥{profit:,.0f}")
b.metric("ROI", f"{roi:.1f}%" if roi is not None else "算定不可")
c.metric("仕入れ上限", f"¥{max_purchase:,}")

if not confirmed:
    st.warning("🟠 要確認：送料・関税・原産国・HSコード等が未確認です。利益は仮計算で、仕入れOK判定は出せません。")
elif purchase_price <= 0:
    st.info("仕入れ価格を入力してください。")
elif profit >= minimum_profit and roi is not None and roi >= minimum_roi:
    st.success("🟢 設定した利益基準を満たしています（相場・商品状態は別途確認）。")
elif profit > 0:
    st.warning("🟡 利益はプラスですが目標基準未満です。")
else:
    st.error("🔴 赤字見込み：見送り推奨。")

with st.expander("費用内訳を確認", expanded=True):
    for k, v in breakdown.items():
        st.write(f"{k}: ¥{v:,.0f}")
    st.write(f"仕入れ価格: ¥{purchase_price:,}")
    st.write(f"**最終予想利益: ¥{profit:,.0f}**")
    st.caption("eBay手数料・税金の計算対象や適用条件は商品・アカウント・配送条件により変動します。")

if st.button("⭐ 仕入れ候補に保存", use_container_width=True):
    st.session_state.candidates.append({"JAN": jan, "商品名": search_word,
        "販売先": mode, "仕入": purchase_price, "売上（円）": round(revenue),
        "利益（円）": round(profit), "ROI（%）": round(roi, 1) if roi is not None else None,
        "仕入上限": max_purchase, "費用確認済み": confirmed})
    st.success("このセッション内に保存しました。")
if st.session_state.candidates:
    with st.expander(f"保存した候補（{len(st.session_state.candidates)}件）"):
        st.dataframe(st.session_state.candidates, use_container_width=True)
        st.caption("セッションを終了すると消える場合があります。永続保存機能は未実装です。")
