"""
iPos Fabi - Auto Crawler (time)
=======================================
- Tự động login lấy token mới mỗi ngày
- Crawl thời gian chế biến của ngày hôm qua
- Lưu ra file Excel theo ngày
"""

# -*- coding: utf-8 -*-
import base64
import pandas as pd
import json
import logging
import os
import requests
import smtplib
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ============================================================
# CẤU HÌNH
# ============================================================

IPOS_EMAIL    = "Email"
IPOS_PASSWORD = "password"


COMPANY_ID = "COMPANY_ID"
BRAND_ID   = "BRAND_ID"
STORE_ID   = "STORE_ID"
 
ACCESS_TOKEN     = "ACCESS_TOKEN"
OUTPUT_DIR       = r"D:\BanRau_IPos_Data\time_service"
TOKEN_CACHE_FILE = r".token_cache.json"
 
LOGIN_URL  = "https://posapi.ipos.vn/api/accounts/v1/user/login"
DETAIL_URL = "https://posapi.ipos.vn/api/v3/forward/dw/report/fabi/controller/item/detail"
TZ_VN      = timezone(timedelta(hours=7))

MAX_WORKERS = 3   # số request song song (giảm xuống tránh bị rate limit)
TIMEOUT     = 60  # giây, tăng lên vì IPOS đôi khi response chậm
MAX_RETRIES = 3   # số lần retry khi timeout

# ============================================================
# GMAIL CONFIG
# ============================================================
 
GMAIL_FROM     = "GMAIL_FROM"       # email gui
GMAIL_PASSWORD = "GMAIL_PASSWORD"       # <-- App Password 16 ky tu tu Google
GMAIL_TO       = "GMAIL_TO"       # email nhan
 
# ============================================================
# LOGGING
# ============================================================
 
os.makedirs(OUTPUT_DIR, exist_ok=True)
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(OUTPUT_DIR, "crawler.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)
 
# ============================================================
# GMAIL
# ============================================================
 
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From']    = GMAIL_FROM
        msg['To']      = GMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
 
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_FROM, GMAIL_PASSWORD)
            server.send_message(msg)
 
        log.info(f"Đã gửi email: {subject}")
    except Exception as e:
        log.warning(f"Không gửi được email: {e}")
 
# ============================================================
# TOKEN
# ============================================================
 
def load_cached_token():
    try:
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache = json.load(f)
        if cache.get("exp", 0) - datetime.now().timestamp() > 7200:
            log.info("Token cache con han")
            return cache["token"]
    except Exception:
        pass
    return None
 
def save_token(token, exp):
    os.makedirs(os.path.dirname(TOKEN_CACHE_FILE), exist_ok=True)
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump({"token": token, "exp": exp}, f)
 
def login():
    log.info("Đang login iPos...")
    resp = requests.post(
        LOGIN_URL,
        json={"email": IPOS_EMAIL, "password": IPOS_PASSWORD},
        headers={
            "Accept":            "application/json, text/plain, */*",
            "Accept-Language":   "vi",
            "access_token":      ACCESS_TOKEN,
            "Authorization":     "",
            "Content-Type":      "application/json;charset=UTF-8",
            "fabi_type":         "pos-cms",
            "Origin":            "https://fabi.ipos.vn",
            "Referer":           "https://fabi.ipos.vn/",
            "x-client-timezone": "25200000",
            "User-Agent":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        timeout=15
    )
    if not resp.ok:
        raise Exception(f"Login thất bại: HTTP {resp.status_code} - {resp.text[:300]}")
 
    data = resp.json()
    token = (
        data.get("token") or data.get("access_token") or
        (data.get("data") or {}).get("token") or
        (data.get("data") or {}).get("access_token")
    )
    if not token:
        raise Exception(f"Không tìm thấy token: {str(data)[:300]}")
 
    try:
        pad = token.split(".")[1]
        pad += "=" * (4 - len(pad) % 4)
        exp = json.loads(base64.b64decode(pad)).get("exp", int(datetime.now().timestamp()) + 86400)
    except Exception:
        exp = int(datetime.now().timestamp()) + 86400
 
    save_token(token, exp)
    log.info(f"Login OK!")
    return token
 
def get_token():
    return load_cached_token() or login()
 
def make_headers(token):
    return {
        "Accept":            "application/json, text/plain, */*",
        "Accept-Language":   "vi",
        "access_token":      ACCESS_TOKEN,
        "Authorization":     token,
        "fabi_type":         "pos-cms",
        "Origin":            "https://fabi.ipos.vn",
        "Referer":           "https://fabi.ipos.vn/",
        "x-client-timezone": "25200000",
        "User-Agent":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
 
# ============================================================
# HELPERS
# ============================================================
 
def get_timestamps(d):
    start = datetime(d.year, d.month, d.day,  0,  0,  0, tzinfo=TZ_VN)
    end   = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=TZ_VN)
    return int(start.timestamp()), int(end.timestamp())
 
def ts_to_str(ts):
    if not ts: return ""
    if ts > 1e12: ts = ts / 1000
    return datetime.fromtimestamp(ts, tz=TZ_VN).strftime("%Y-%m-%d %H:%M:%S")
 
def ms_to_min(ms):
    return round(ms / 60000, 2) if ms else 0
 
def clean_row(row):
    return {
        "sale_id":        row.get("sale_id", ""),
        "sale_detail_id": row.get("sale_detail_id", ""),
        "tran_no":        row.get("tran_no", ""),
        "tran_date":      ts_to_str(row.get("tran_date")),
        "item_id":        row.get("item_id", ""),
        "item_name":      row.get("item_name", ""),
        "quantity":       row.get("quantity", 0),
        "table_id":       row.get("table_id", ""),
        "table_name":     row.get("table_name", ""),
        "start_time":     ts_to_str(row.get("start_time")),
        "end_time":       ts_to_str(row.get("end_time")),
        "duration_ms":    row.get("duration", 0),
        "duration_min":   ms_to_min(row.get("duration", 0)),
        "store_id":       row.get("store_id", ""),
        "brand_id":       row.get("brand_id", ""),
    }
 
# ============================================================
# FETCH 1 PAGE (co retry)
# ============================================================
 
def fetch_page(page, from_ts, to_ts, token):
    params = {
        "company_id":     COMPANY_ID,
        "brand_id":       BRAND_ID,
        "store_id":       STORE_ID,
        "from_timestamp": from_ts,
        "to_timestamp":   to_ts,
        "page":           page,
        "order_by":       '{"duration": "desc"}',
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(DETAIL_URL, headers=make_headers(token), params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            log.warning(f"  [Timeout] page {page}, lan {attempt}/{MAX_RETRIES} — thử lại...")
            time.sleep(3 * attempt)
        except requests.HTTPError:
            raise
    raise Exception(f"Page {page} timeout sau {MAX_RETRIES} lần thử")
 
# ============================================================
# CRAWLER
# ============================================================
 
def crawl_one_day(d, token):
    from_ts, to_ts = get_timestamps(d)
    log.info(f"Crawl ngày {d}  ({from_ts} -> {to_ts})")
 
    try:
        first = fetch_page(1, from_ts, to_ts, token)
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            log.warning("Token het han -> login lai...")
            token = login()
            first = fetch_page(1, from_ts, to_ts, token)
        else:
            raise
 
    total_pages = first.get("total_pages", 1)
    num_results = first.get("num_results", "?")
    all_rows    = first.get("data", [])
 
    log.info(f"  Page 1/{total_pages}: {len(all_rows)} dong  (total_pages={total_pages}, num_results={num_results})")
 
    if total_pages <= 1:
        return all_rows, token
 
    # Crawl song song cac page con lai
    def fetch_safe(page):
        try:
            data = fetch_page(page, from_ts, to_ts, token)
            return page, data.get("data", []), None
        except Exception as e:
            return page, [], str(e)
 
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_safe, p): p for p in range(2, total_pages + 1)}
        for future in as_completed(futures):
            page, rows, err = future.result()
            if err:
                log.warning(f"  [Loi] page {page}: {err}")
            else:
                results[page] = rows
                log.info(f"  Page {page}/{total_pages}: {len(rows)} dòng")
 
    for page in sorted(results.keys()):
        all_rows.extend(results[page])
 
    return all_rows, token
 
# ============================================================
# EXPORT
# ============================================================
 
def export(rows, d):
    date_str = str(d)
    cleaned  = [clean_row(r) for r in rows]
    df = pd.DataFrame(cleaned)
 
    for col in ["tran_date", "start_time", "end_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
 
    xlsx_file = os.path.join(OUTPUT_DIR, f"cooking_time_detail_{date_str}.xlsx")
    with pd.ExcelWriter(xlsx_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        ws = writer.sheets["Data"]
        for col_cells in ws.columns:
            max_len = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in col_cells
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 40)
 
    log.info(f"Saved: {xlsx_file} ({len(df)} dong)")
    return xlsx_file, len(df)
 
# ============================================================
# NETWORK CHECK
# ============================================================
 
def wait_for_network(max_wait=60):
    log.info("Kiểm tra kết nối mạng...")
    for i in range(max_wait):
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            log.info(f"Mạng OK (sau {i}s)")
            return True
        except Exception:
            time.sleep(1)
    log.error("Không có mạng sau 60 giây!")
    return False
 
# ============================================================
# MAIN
# ============================================================
 
if __name__ == "__main__":
    target = (
        date.fromisoformat(sys.argv[1])
        if len(sys.argv) > 1
        else (datetime.now(tz=TZ_VN) - timedelta(days=1)).date()
    )
 
    log.info(f"IPOS Cooking Time Crawler - ngày {target}")
 
    try:
        if not wait_for_network():
            sys.exit(1)
 
        token = get_token()
        raw_rows, token = crawl_one_day(target, token)
 
        if not raw_rows:
            log.warning(f"Không có dữ liệu ngày {target}")
            send_email(
                subject=f"[BanRau] Crawl {target} - Không có data",
                body=f"Crawler chạy thành công nhưng không có dữ liệu cho ngày {target}."
            )
            sys.exit(0)
 
        log.info(f"Tổng: {len(raw_rows)} dòng")
        xlsx_file, row_count = export(raw_rows, target)
        log.info("XONG!")
 
        # Gửi email thành công
        send_email(
            subject=f"[BanRau] Crawl {target} thành công - {row_count} dòng",
            body=(
                f"Crawl Thời gian chế biến ngày {target} hoàn thất!\n\n"
                f"Số dòng: {row_count}\n"
                f"File: {xlsx_file}\n\n"
                f"Log: {os.path.join(OUTPUT_DIR, 'crawler.log')}"
            )
        )
 
    except Exception as e:
        log.error(f"Loi: {e}")
 
        # Gửi email báo lỗi
        send_email(
            subject=f"[BanRau] Crawl {target} THẤT BẠI",
            body=(
                f"Crawler gặp lỗi khi chạy ngày {target}!\n\n"
                f"Lỗi: {str(e)}\n\n"
                f"Kiểm trra log: {os.path.join(OUTPUT_DIR, 'crawler.log')}"
            )
        )
        sys.exit(1)
 
