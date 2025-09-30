import os
import math
import pandas as pd
import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone

# ------------ الإعدادات العامة ------------
st.set_page_config(page_title="أسعار الصرف المباشرة", page_icon="💱", layout="wide")
st.title("💱 أسعار الصرف المباشرة")

load_dotenv(override=True)

MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB   = os.getenv("MONGO_DB", "fxdb")
MONGO_COLL = os.getenv("MONGO_COLL", "rates")

BASE_CURRENCY = (os.getenv("BASE_CURRENCY", "USD") or "USD").strip().upper()
# تأكد من تحويل SYMBOLS إلى قائمة عليا
SYMBOLS = [
    s.strip().upper()
    for s in (os.getenv("SYMBOLS", "") or "").split(",")
    if s.strip()
]

# ------------ اتصال Mongo ------------
client = MongoClient(MONGO_URI)
coll = client[MONGO_DB][MONGO_COLL]

# ------------ مؤشّر وتحديث تلقائي كل 30 ثانية ------------
st_autorefresh(interval=30 * 1000, key="fxrefresh")
st.markdown(
    "<div style='background:#fff7e6; border-left:6px solid #faad14; padding:8px 12px;'>"
    "⏳ يتم تحديث العرض تلقائيًا كل <b>30 ثانية</b>. المصدر: أحدث مستند محفوظ في MongoDB."
    "</div>",
    unsafe_allow_html=True,
)

# ------------ قراءة أحدث مستند ------------
doc = coll.find_one(sort=[("ts", -1)])
if not doc:
    st.warning("⚠️ لا توجد بيانات بعد في MongoDB. شغّل `ingest_fx.py` أولاً.")
    st.stop()

# نتوقع بنية مثل:
# { base: 'USD', rates: {'USD':1.0,'YER':..., 'SAR':..., 'EUR':...}, ts: <ISODate> }
rates_map = (doc.get("rates") or doc)  # توافقًا مع نسخ سابقة
# تحصين: تحويل المفاتيح إلى upper
rates_map = {k.upper(): v for k, v in rates_map.items() if isinstance(v, (int, float))}

last_ts = doc.get("ts")
# طباعة وقت التحديث
if isinstance(last_ts, datetime):
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    last_ts_txt = last_ts.astimezone(timezone.utc).strftime("%H:%M:%S %d-%m-%Y UTC")
else:
    last_ts_txt = "None"

st.caption(f"🕒 آخر تحديث: {last_ts_txt} — Base: {BASE_CURRENCY}")

# ------------ دوال تحويل بين العملات ------------
def safe_div(a: float, b: float):
    try:
        if b == 0 or b is None or a is None:
            return None
        return a / b
    except Exception:
        return None

def convert(amount: float, from_ccy: str, to_ccy: str, base: str, rmap: dict):
    """
    يعتمد على وجود أسعار مقابل base فقط (USD مثلاً).
    إذا أردت from→to:
      from→base = 1 / rate[from]
      base→to   = rate[to]
      إذن from→to = (1 / rate[from]) * rate[to]
    والحالات الخاصة:
      إذا from==base: return amount * rate[to]
      إذا to==base  : return amount / rate[from]
    """
    from_ccy = from_ccy.upper()
    to_ccy   = to_ccy.upper()
    base     = base.upper()

    if amount is None or not isinstance(amount, (int, float)):
        return None
    if from_ccy == to_ccy:
        return float(amount)

    # لا بد من توفر أسعار هذه الرموز
    if to_ccy not in rmap and to_ccy != base:
        return None
    if from_ccy not in rmap and from_ccy != base:
        return None

    # حالات خاصة مع الـ base
    if from_ccy == base and to_ccy in rmap:
        return amount * rmap[to_ccy]
    if to_ccy == base and from_ccy in rmap:
        return safe_div(amount, rmap[from_ccy])

    # التحويل العام عبر الـ base
    if from_ccy in rmap and to_ccy in rmap:
        return amount * safe_div(rmap[to_ccy], rmap[from_ccy])

    return None

# ------------ جدول أسعار مختصرة (آخر قيم متوفّرة) ------------
def fmt(v):
    return "—" if (v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))) else f"{v:,.4f}"

rows = []
pairs = [
    ("USD", "YER"),
    ("SAR", "YER"),
    ("USD", "SAR"),
    ("YER", "USD"),
    ("YER", "SAR"),
    ("SAR", "USD"),
]
for src, dst in pairs:
    val_vs_usd = convert(1.0, src, "USD", BASE_CURRENCY, rates_map)
    val_vs_sar = convert(1.0, src, "SAR", BASE_CURRENCY, rates_map)
    val_vs_yer = convert(1.0, src, "YER", BASE_CURRENCY, rates_map)
    rows.append({
        "من": src, "إلى": dst,
        "السعر (1 USD)": fmt(val_vs_usd),
        "السعر (1 SAR)": fmt(val_vs_sar),
        "السعر (1 YER)": fmt(val_vs_yer),
    })

st.subheader("⭐ أسعار مختصرة (أحدث قيم متوفّرة)")
st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ------------ محوّل العملات ------------
st.subheader("💱 محوّل العملات")

# العملات المعروفة من الخريطة + BASE + SYMBOLS من .env
known_set = set(rates_map.keys())
known_set.add(BASE_CURRENCY)
for s in SYMBOLS:
    known_set.add(s)
known = sorted(list(known_set))

col_amt, col_from, col_to = st.columns([2, 2, 2])

with col_amt:
    amount = st.number_input("المبلغ", value=100.0, min_value=0.0, step=1.0)

with col_from:
    from_ccy = st.selectbox("من", options=known, index=known.index(BASE_CURRENCY) if BASE_CURRENCY in known else 0)

with col_to:
    # اختَر عملة مختلفة افتراضيًا إن وجدت
    default_to = 0
    for i, c in enumerate(known):
        if c != from_ccy:
            default_to = i
            break
    to_ccy = st.selectbox("إلى", options=known, index=default_to)

result = convert(amount, from_ccy, to_ccy, BASE_CURRENCY, rates_map)
if result is None:
    st.error("لا يمكن حساب التحويل لهذه العملتين بالبيانات الحالية.")
else:
    st.success(f"{amount:,.2f} {from_ccy} = {result:,.2f} {to_ccy}  (السعر المستخدم محسوب من {BASE_CURRENCY})")

# ------------ قسم اختياري: عرض جميع الأسعار مقابل الـ Base ------------
with st.expander("📊 عرض جميع الأسعار مقابل الـ Base الحالية"):
    df_all = (
        pd.DataFrame(
            [{"base": BASE_CURRENCY, "symbol": k, "rate": v, "ts": last_ts} for k, v in rates_map.items()]
        )
        .sort_values("symbol")
        .reset_index(drop=True)
    )
    st.dataframe(df_all, use_container_width=True)

    st.caption(
        "ملاحظة: إذا كانت العملة غير موجودة مباشرة مقابل الـ Base، نحسبها عبر نسب الأسعار (مثال: SAR→YER = YER/SAR). "
        "ثبات SAR طبيعي لأنه مربوط بالدولار."
    )
