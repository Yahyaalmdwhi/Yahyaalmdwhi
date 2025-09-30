# # ingest_fx.py
# import time
# import requests
# from datetime import datetime, timezone
# from pymongo import MongoClient, ASCENDING
# from pymongo.errors import DuplicateKeyError
# from config import (
#     MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION,
#     EXCHANGE_API_KEY, BASE_CURRENCY, SYMBOLS, POLL_SECONDS
# )

# def get_rates():
#     # مثال على API مجانية: exchangerate-api/fastforex مثلًا
#     # هنا نستخدم api.exchangerate-api.com v6 (endpoint latest)
#     url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/{BASE_CURRENCY}"
#     r = requests.get(url, timeout=20)
#     r.raise_for_status()
#     data = r.json()
#     if data.get("result") != "success":
#         raise RuntimeError(f"API error: {data}")
#     all_rates = data["conversion_rates"]
#     wanted = [s.strip().upper() for s in SYMBOLS.split(",") if s.strip()]
#     ts = datetime.now(timezone.utc)
#     docs = []
#     for sym in wanted:
#         if sym in all_rates:
#             docs.append({
#                 "base": BASE_CURRENCY,
#                 "symbol": sym,
#                 "rate": float(all_rates[sym]),
#                 "ts": ts
#             })
#     return docs

# def main():
#     client = MongoClient(MONGO_URI)
#     coll = client[MONGO_DB_NAME][MONGO_COLLECTION]

#     # فهرس فريد لمنع التكرار لنفس الوقت/الرمز
#     coll.create_index([("symbol", ASCENDING), ("ts", ASCENDING)], unique=True)

#     print(f"[ingest] Writing into {MONGO_DB_NAME}.{MONGO_COLLECTION} every {POLL_SECONDS}s ...")
#     while True:
#         try:
#             docs = get_rates()
#             if docs:
#                 for d in docs:
#                     try:
#                         coll.insert_one(d)
#                     except DuplicateKeyError:
#                         pass
#                 print(f"[ingest] inserted {len(docs)} docs at {docs[0]['ts']}")
#             else:
#                 print("[ingest] no docs")
#         except Exception as e:
#             print("[ingest] error:", e)
#         time.sleep(POLL_SECONDS)

# if __name__ == "__main__":
#     main()


# ingest_fx.py
import os, time, requests, datetime
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB   = os.getenv("MONGO_DB", "fxdb")
MONGO_COLL = os.getenv("MONGO_COLL", "rates")

API_KEY    = os.getenv("EXCHANGE_API_KEY")
BASE       = os.getenv("BASE_CURRENCY", "USD").upper()
SYMBOLS    = [s.strip().upper() for s in os.getenv("SYMBOLS","USD,YER,SAR").split(",")]

assert API_KEY, "EXCHANGE_API_KEY مفقود في .env"

client = MongoClient(MONGO_URI)
coll   = client[MONGO_DB][MONGO_COLL]

# فهرس زمني
coll.create_index([("ts", ASCENDING)])

def fetch_rates():
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{BASE}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("result") != "success":
        raise RuntimeError(f"API error: {data}")
    all_rates = data["conversion_rates"]
    # نحتفظ فقط بالعملات المطلوبة
    rates = {k: all_rates[k] for k in SYMBOLS if k in all_rates}
    # تأكد أن USD = 1 لو موجود
    if BASE == "USD":
        rates["USD"] = 1.0
    doc = {
        "base": BASE,
        "symbols": SYMBOLS,
        "rates": rates,
        "ts": datetime.datetime.utcnow()
    }
    return doc

def main(loop=False, every_seconds=300):
    if loop:
        print(f"[ingest] loop: every {every_seconds}s")
    while True:
        doc = fetch_rates()
        coll.insert_one(doc)
        print(f"[ingest] inserted: {doc['ts']}  rates={doc['rates']}")
        if not loop:
            break
        time.sleep(every_seconds)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--loop", action="store_true", help="يجلب كل فترة")
    p.add_argument("--seconds", type=int, default=300)
    args = p.parse_args()
    main(loop=args.loop, every_seconds=args.seconds)

# ... أعلى الملف كما هو

def fetch_rates():
    # ...
    now = datetime.datetime.utcnow()
    doc = {
        "base": BASE,
        "symbols": symbols_list,
        "rates": rates_dict,
        "ts": now,          # وقت الإدخال (هذا الذي عليه الفهرس)
}

    return doc
