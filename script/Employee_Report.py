# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import ast, re, os, sys, json, logging, warnings
from datetime import datetime, timedelta

import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# ============================================================
# CAU HINH
# ============================================================

BASE_DIR         = r"D:\BanRau_IPos_Data"
CREDENTIALS_FILE = r"C:\Users\PC\credentials.json"
SHEET_URL        = "https://docs.google.com/spreadsheets/d/1zaQ9iLPum6z369f3ukNbh3myrnJjNhJzQViv3TFd0ys/edit?usp=sharing"

# ============================================================
# LOGGING
# ============================================================

os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "analysis.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ============================================================
# GOOGLE SHEETS
# ============================================================

def connect_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    return gspread.authorize(creds)

def append_to_sheet(spreadsheet, worksheet_index, new_data):
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    old_data  = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how='all')
    final     = pd.concat([old_data, new_data], ignore_index=True)
    final     = final.replace([np.inf, -np.inf], 0).fillna(0)
    set_with_dataframe(worksheet, final)
    log.info(f"   Sheet {worksheet_index}: +{len(new_data)} dong moi (tong: {len(final)})")

# ============================================================
# DOC FILE
# ============================================================

def read_latest_file(folder, prefix, suffix=".xlsx"):
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    filepath  = os.path.join(folder, f"{prefix}{yesterday}{suffix}")
    if os.path.exists(filepath):
        df = pd.read_excel(filepath)
        log.info(f"Doc {len(df)} rows tu {os.path.basename(filepath)}")
        return df
    files = sorted([f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(suffix)])
    if files:
        filepath = os.path.join(folder, files[-1])
        df = pd.read_excel(filepath)
        log.info(f"Doc file moi nhat: {files[-1]} ({len(df)} rows)")
        return df
    raise FileNotFoundError(f"Khong co file nao trong {folder} voi prefix '{prefix}'")

# ============================================================
# I. LOAD DATA
# ============================================================

def load_data():
    log.info("Doc data...")

    Hoadontheothoigian = read_latest_file(os.path.join(BASE_DIR, "Hoa_don"), "hoa_don_")
    Hoadontheothoigian = Hoadontheothoigian[[
        '_store_uid','tran_id','origin_tran_id','tran_no','created_at',
        'start_hour','start_minute','end_hour','end_minute','table_name',
        'discount_extra_amount','extra_data','total_amount'
    ]]

    Chitiethoadon = read_latest_file(os.path.join(BASE_DIR, "sale_detail"), "sale_detail_")
    Chitiethoadon = Chitiethoadon[[
        'tran_id','tran_no','table_name','store_uid','peo_count',
        'item_name','item_type_name','quantity','price','unit_id',
        'amount_origin','store_name'
    ]]

    Nhatkyorder = read_latest_file(os.path.join(BASE_DIR, "sale_change_log"), "sale_change_log_")
    Nhatkyorder = Nhatkyorder[['created_at','tran_id','log_type','table_name','change_data']]

    Thoigiangiaomon = read_latest_file(os.path.join(BASE_DIR, "time_service"), "cooking_time_detail_")

    return Hoadontheothoigian, Chitiethoadon, Nhatkyorder, Thoigiangiaomon

# ============================================================
# II. PROCESS HOA DON
# ============================================================

def process_hoadon(Hoadontheothoigian, Chitiethoadon):
    log.info("Xu ly Hoa don...")

    def extract_fields(x):
        try:
            data = ast.literal_eval(x)
            return pd.Series({
                'customer_phone': data.get('customer_phone'),
                'customer_name': data.get('customer_name'),
                'Membership_Type_Name': data.get('Membership_Type_Name')
            })
        except:
            return pd.Series([None, None, None])

    Hoadontheothoigian[['customer_phone','customer_name','Membership_Type_Name']] = \
        Hoadontheothoigian['extra_data'].apply(extract_fields)

    Hoadontheothoigian['Gio vao'] = (
        Hoadontheothoigian['start_hour'].astype(str).str.zfill(2) + ':' +
        Hoadontheothoigian['start_minute'].astype(str).str.zfill(2)
    )
    Hoadontheothoigian['Gio ra'] = (
        Hoadontheothoigian['end_hour'].astype(str).str.zfill(2) + ':' +
        Hoadontheothoigian['end_minute'].astype(str).str.zfill(2)
    )
    Hoadontheothoigian = Hoadontheothoigian.rename(columns={
        '_store_uid':'Ma cua hang','tran_id':'Ma hoa don','origin_tran_id':'Ma hoa don goc',
        'tran_no':'So hoa don','created_at':'Ngay','table_name':'Ban',
        'discount_extra_amount':'Giam gia','total_amount':'Tong hoa don',
        'customer_phone':'SDT','customer_name':'Ten Khach',
        'Membership_Type_Name':'Loai thanh vien',
        'Gio vao':'Gio vao','Gio ra':'Gio ra'
    })
    Hoadontheothoigian = Hoadontheothoigian.drop(
        columns=['extra_data','start_hour','start_minute','end_hour','end_minute']
    )
    Hoadontheothoigian['Ngay'] = pd.to_datetime(Hoadontheothoigian['Ngay']).dt.strftime('%d/%m/%Y')

    Hoadontheothoigian = Hoadontheothoigian.rename(columns={
        'Ma cua hang':'Mã cửa hàng','Ma hoa don':'Mã hóa đơn','Ma hoa don goc':'Mã hóa đơn gốc',
        'So hoa don':'Số hóa đơn','Ngay':'Ngày','Ban':'Bàn',
        'Giam gia':'Giảm giá','Tong hoa don':'Tổng hóa đơn',
        'SDT':'SĐT','Ten Khach':'Tên Khách','Loai thanh vien':'Loại thành viên',
        'Gio vao':'Giờ vào','Gio ra':'Giờ ra'
    })

    # Loai khach hang
    mask = Hoadontheothoigian.index.notnull()
    Hoadontheothoigian['Loại khách hàng'] = np.select(
        condlist=[
            (Hoadontheothoigian.loc[mask,'SĐT'].isna() | (Hoadontheothoigian.loc[mask,'SĐT'] == '')) &
            (Hoadontheothoigian.loc[mask,'Loại thành viên'].isna() | (Hoadontheothoigian.loc[mask,'Loại thành viên'] == '')),
            (Hoadontheothoigian.loc[mask,'SĐT'].notna() & (Hoadontheothoigian.loc[mask,'SĐT'] != '')) &
            (Hoadontheothoigian.loc[mask,'Loại thành viên'].isna() |
             (Hoadontheothoigian.loc[mask,'Loại thành viên'] == '') |
             (Hoadontheothoigian.loc[mask,'Loại thành viên'] == 'Thành viên mặc định'))
        ],
        choicelist=['Khách lẻ','Khách mới'],
        default='Khách quay lại'
    )


    # Chi tiet hoa don
    Chitiethoadon = Chitiethoadon.rename(columns={
        'tran_id':'Mã hóa đơn','tran_no':'Số hóa đơn','table_name':'Bàn',
        'store_uid':'Mã cửa hàng','peo_count':'Số khách','item_name':'Tên hàng',
        'item_type_name':'Nhóm hàng','quantity':'Số lượng','price':'Đơn giá',
        'unit_id':'Đơn vị tính','amount_origin':'Thành tiền','store_name':'Cửa hàng',
    })

    # Merge
    merged_df_1 = pd.merge(
        Chitiethoadon, Hoadontheothoigian,
        on=['Mã hóa đơn','Mã cửa hàng','Bàn','Số hóa đơn'], how='right'
    )
    merged_df_1 = merged_df_1.sort_values(by=['Số hóa đơn','Ngày','Tên hàng'])
    merged_df_1['Mark'] = merged_df_1.groupby(['Số hóa đơn','Tên hàng','Số lượng']).cumcount() + 1

    merged_df_1.loc[merged_df_1['Mã hóa đơn gốc'].notna(),'Mã hóa đơn'] = merged_df_1['Mã hóa đơn gốc']

    return merged_df_1

# ============================================================
# III. PROCESS NHAT KY ORDER
# ============================================================

def process_nhatky(Nhatkyorder_raw):
    log.info("Xu ly Nhat ky order...")

    def process_row(row):
        try:
            data = ast.literal_eval(row['change_data'])
            created_at = row['created_at']
            log_type = row['log_type']
            table_name = row['table_name']
            employee_name = data.get('employee_name')
            store_uid = data.get('store_uid')
            tran_id = data.get('tran_id')
            origin_tran_id = data.get('origin_tran_id')
            tran_no = data.get('tran_no')
            extra_data = data.get('extra_data', {})
            message_modify_table = extra_data.get('message_modify_table')
            items = data.get('sale_detail', [])
            rows = []
            for item in items:
                rows.append({
                    'created_at': created_at, 'log_type': log_type, 'table_name': table_name,
                    'employee_name': employee_name, 'store_uid': store_uid,
                    'tran_id': tran_id, 'origin_tran_id': origin_tran_id, 'tran_no': tran_no,
                    'message_modify_table': message_modify_table,
                    'item_type': 'MAIN', 'item_name': item.get('item_name'), 'parent_item': None,
                    'price': item.get('price'), 'quantity': item.get('quantity'), 'unit_id': item.get('unit_id')
                })
                for tp in (item.get('toppings') or []):
                    rows.append({
                        'created_at': created_at, 'log_type': log_type, 'table_name': table_name,
                        'employee_name': employee_name, 'store_uid': store_uid,
                        'tran_id': tran_id, 'origin_tran_id': origin_tran_id, 'tran_no': tran_no,
                        'message_modify_table': message_modify_table,
                        'item_type': 'TOPPING', 'item_name': tp.get('item_name'), 'parent_item': item.get('item_name'),
                        'price': tp.get('price'), 'quantity': tp.get('quantity', item.get('quantity')), 'unit_id': tp.get('unit_id')
                    })
            return rows
        except:
            return []

    result = Nhatkyorder_raw.apply(process_row, axis=1).explode()
    result = result[result.apply(lambda x: isinstance(x, dict))]
    result_df = pd.DataFrame(result.tolist()).reset_index(drop=True)
    result_df['line_revenue'] = result_df['price'] * result_df['quantity']
    result_df = result_df.rename(columns={
        'created_at':'Thời gian','log_type':'Loại log','table_name':'Bàn',
        'employee_name':'Nhân viên','store_uid':'Mã cửa hàng','tran_id':'Mã hóa đơn',
        'origin_tran_id':'Mã hóa đơn gốc','tran_no':'Số hóa đơn',
        'message_modify_table':'Ghi chú','item_name':'Tên hàng',
        'price':'Đơn giá','quantity':'Số lượng','unit_id':'Đơn vị tính','line_revenue':'Thành tiền'
    })
    result_df = result_df.drop(columns=['item_type','parent_item'], errors='ignore')
    Nhatkyorder = result_df

    Nhatkyorder = Nhatkyorder[Nhatkyorder['Loại log'].isin(['SALE_MERGE_ORDER','SALE_CHANGE','SALE_SPLIT_ORDER'])]

    # ===== NHOM 1: GOP / TACH DON =====
    target_hoadon_list = Nhatkyorder[
        Nhatkyorder['Loại log'].str.contains('SALE_MERGE_ORDER|SALE_SPLIT_ORDER', case=False, na=False)
    ][['Mã hóa đơn']].drop_duplicates()

    Nhatkyorder_gop_tach = Nhatkyorder.merge(target_hoadon_list, on='Mã hóa đơn', how='inner')
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.sort_values(['Mã hóa đơn','Thời gian']).reset_index(drop=True)

    # Xu ly gop don
    Nhatkyorder_gop_tach['Mã hóa đơn sau khi gộp bàn'] = None
    mask_gop = Nhatkyorder_gop_tach['Ghi chú'].str.contains('gộp vào', case=False, na=False)

    def extract_new_invoice_gop(text):
        if pd.isna(text): return None
        try:
            after = text.split("gộp vào")[-1].strip()
            return after.split("-")[0].strip()
        except:
            return None

    Nhatkyorder_gop_tach.loc[mask_gop, 'Mã hóa đơn sau khi gộp bàn'] = \
        Nhatkyorder_gop_tach.loc[mask_gop, 'Ghi chú'].apply(extract_new_invoice_gop)
    Nhatkyorder_gop_tach['Mã hóa đơn sau khi gộp bàn'] = \
        Nhatkyorder_gop_tach['Mã hóa đơn sau khi gộp bàn'].replace('', None)
    Nhatkyorder_gop_tach['Mã hóa đơn sau khi gộp bàn'] = (
        Nhatkyorder_gop_tach.groupby('Số hóa đơn')['Mã hóa đơn sau khi gộp bàn']
        .transform(lambda x: x.ffill().bfill())
    )
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach[
        ~Nhatkyorder_gop_tach['Ghi chú'].str.contains('[SALE_MERGE_ORDER]', na=False, regex=False)
    ]

    mapping_gop = dict(zip(Nhatkyorder_gop_tach['Mã hóa đơn'], Nhatkyorder_gop_tach['Mã hóa đơn sau khi gộp bàn']))

    def find_final_code(code):
        visited = set()
        while pd.notna(code) and code in mapping_gop and mapping_gop[code] not in visited:
            visited.add(code)
            next_code = mapping_gop.get(code)
            if pd.isna(next_code): break
            code = next_code
        return code

    Nhatkyorder_gop_tach['Mã hóa đơn cuối cùng'] = Nhatkyorder_gop_tach['Mã hóa đơn'].apply(find_final_code)
    sohd_map = (Nhatkyorder_gop_tach.drop_duplicates(subset=['Mã hóa đơn'], keep='first')
                .set_index('Mã hóa đơn')['Số hóa đơn'])
    Nhatkyorder_gop_tach['Số hóa đơn cuối'] = Nhatkyorder_gop_tach['Mã hóa đơn cuối cùng'].map(sohd_map)
    Nhatkyorder_gop_tach['Số hóa đơn cuối'] = Nhatkyorder_gop_tach['Số hóa đơn cuối'].fillna(
        Nhatkyorder_gop_tach['Số hóa đơn']
    )
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.drop(columns=['Số hóa đơn'], errors='ignore')
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.rename(columns={'Số hóa đơn cuối':'Số hóa đơn'})
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.drop(columns=['Mã hóa đơn','Mã hóa đơn sau khi gộp bàn'], errors='ignore')
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.rename(columns={'Mã hóa đơn cuối cùng':'Mã hóa đơn'})
    cols_order = ['Mã hóa đơn','Số hóa đơn','Thời gian','Bàn','Nhân viên','Loại log','Ghi chú','Tên hàng','Số lượng']
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.reindex(columns=cols_order)
    Nhatkyorder_gop_tach = Nhatkyorder_gop_tach.sort_values(['Số hóa đơn','Thời gian']).reset_index(drop=True)

    # Xu ly tach don
    Nhatkyorder_tachdon = Nhatkyorder_gop_tach.copy()
    Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'] = None

    mask_tach = (
        Nhatkyorder_tachdon['Ghi chú'].str.contains('[Tách đơn]', case=False, na=False) &
        Nhatkyorder_tachdon['Ghi chú'].str.contains('tạo thành hóa đơn', case=False, na=False)
    )

    def extract_invoice_tach(text):
        if pd.isna(text): return None
        text_lower = text.lower()
        keyword = "tạo thành hóa đơn"
        if keyword in text_lower:
            start_index = text_lower.find(keyword) + len(keyword)
            after_phrase = text[start_index:].strip()
            return after_phrase.split("-")[0].strip()
        return None

    Nhatkyorder_tachdon.loc[mask_tach, 'Mã hóa đơn sau khi tách bàn'] = \
        Nhatkyorder_tachdon.loc[mask_tach, 'Ghi chú'].apply(extract_invoice_tach)
    Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'] = \
        Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'].replace('', None)

    mask_tach2 = Nhatkyorder_tachdon['Loại log'] == 'SALE_SPLIT_ORDER'
    Nhatkyorder_tachdon.loc[mask_tach2, 'Mã hóa đơn sau khi tách bàn'] = (
        Nhatkyorder_tachdon.groupby('Mã hóa đơn')['Mã hóa đơn sau khi tách bàn']
        .transform(lambda x: x.ffill().bfill())
    )
    Nhatkyorder_tachdon.loc[~mask_tach2, 'Mã hóa đơn sau khi tách bàn'] = None

    mapping_df = Nhatkyorder_tachdon[Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'].notna()][
        ['Mã hóa đơn','Mã hóa đơn sau khi tách bàn']
    ].drop_duplicates()
    child_to_parent_map = dict(zip(mapping_df['Mã hóa đơn sau khi tách bàn'], mapping_df['Mã hóa đơn']))

    def find_ultimate_root(invoice_code, p_map):
        current = invoice_code
        while current in p_map:
            parent = p_map[current]
            if parent == current: break
            current = parent
        return current

    Nhatkyorder_tachdon['Group_ID_Goc'] = Nhatkyorder_tachdon['Mã hóa đơn'].apply(
        lambda x: find_ultimate_root(x, child_to_parent_map)
    )
    Nhatkyorder_tachdon = Nhatkyorder_tachdon.sort_values(
        by=['Thời gian','Group_ID_Goc']
    ).reset_index(drop=True)

    lookup_dict = dict(zip(Nhatkyorder_tachdon['Mã hóa đơn'], Nhatkyorder_tachdon['Số hóa đơn']))

    def map_full_invoice(row):
        if row['Loại log'] == 'SALE_SPLIT_ORDER':
            return lookup_dict.get(row['Mã hóa đơn sau khi tách bàn'], None)
        return None

    Nhatkyorder_tachdon['Số hóa đơn tách bàn'] = Nhatkyorder_tachdon.apply(map_full_invoice, axis=1)

    # Xoa dong co Ma ko NaN nhung So hoa don NaN
    Nhatkyorder_tachdon = Nhatkyorder_tachdon[
        ~(Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'].notna() &
          Nhatkyorder_tachdon['Số hóa đơn tách bàn'].isna())
    ]
    Nhatkyorder_tachdon = Nhatkyorder_tachdon[
        ~Nhatkyorder_tachdon['Ghi chú'].str.contains(r'hóa đơn được tạo mới', case=False, na=False)
    ]
    Nhatkyorder_tachdon['Ma_Sort_Phu'] = Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'].astype(str).str[-4:]
    Nhatkyorder_tachdon = Nhatkyorder_tachdon.sort_values(
        by=['Group_ID_Goc','Thời gian','Ma_Sort_Phu']
    ).reset_index(drop=True).drop(columns=['Ma_Sort_Phu'])

    if Nhatkyorder_tachdon.empty:
        Nhatkyorder_nhom_1 = pd.DataFrame(columns=Nhatkyorder_tachdon.columns)
    else:
        Nhatkyorder_tachdon['Số lượng'] = pd.to_numeric(Nhatkyorder_tachdon['Số lượng'], errors='coerce').fillna(0)
        Nhatkyorder_tachdon = Nhatkyorder_tachdon.sort_values(['Group_ID_Goc','Thời gian']).reset_index(drop=True)

        final_rows = []
        for group_id, df_group in Nhatkyorder_tachdon.groupby('Group_ID_Goc'):
            root_id  = df_group.iloc[0]['Mã hóa đơn']
            root_shd = df_group.iloc[0]['Số hóa đơn']
            current_inventory = []
            processed_indices = set()

            for idx, row in df_group.iterrows():
                if idx in processed_indices: continue

                if row['Loại log'] == 'SALE_CHANGE':
                    if row['Số lượng'] > 0:
                        current_inventory.append(row.to_dict())
                    else:
                        qty_to_remove = abs(row['Số lượng'])
                        for i in range(len(current_inventory)-1, -1, -1):
                            if current_inventory[i]['Tên hàng'] == row['Tên hàng']:
                                removable = min(current_inventory[i]['Số lượng'], qty_to_remove)
                                current_inventory[i]['Số lượng'] -= removable
                                qty_to_remove -= removable
                                if current_inventory[i]['Số lượng'] <= 0:
                                    current_inventory.pop(i)
                            if qty_to_remove <= 0: break

                elif row['Loại log'] == 'SALE_SPLIT_ORDER' and pd.notna(row['Mã hóa đơn sau khi tách bàn']):
                    new_id  = row['Mã hóa đơn sau khi tách bàn']
                    new_shd = row['Số hóa đơn tách bàn']
                    thoi_gian_tach = row['Thời gian']
                    df_block_tach = df_group[
                        (df_group['Loại log'] == 'SALE_SPLIT_ORDER') &
                        (df_group['Thời gian'] == thoi_gian_tach)
                    ]
                    processed_indices.update(df_block_tach.index.tolist())
                    items_to_stay = df_block_tach.groupby('Tên hàng')['Số lượng'].sum().abs().to_dict()
                    updated_inventory = []
                    for item in current_inventory:
                        name = item['Tên hàng']
                        qty  = item['Số lượng']
                        stay_qty = items_to_stay.get(name, 0)
                        if stay_qty >= qty:
                            updated_inventory.append(item)
                            items_to_stay[name] -= qty
                        elif stay_qty > 0:
                            stay_item = item.copy(); stay_item['Số lượng'] = stay_qty
                            updated_inventory.append(stay_item)
                            move_item = item.copy(); move_item['Số lượng'] = qty - stay_qty
                            move_item['Mã hóa đơn'] = new_id; move_item['Số hóa đơn'] = new_shd
                            final_rows.append(pd.Series(move_item))
                            items_to_stay[name] = 0
                        else:
                            item['Mã hóa đơn'] = new_id; item['Số hóa đơn'] = new_shd
                            final_rows.append(pd.Series(item))
                    current_inventory = updated_inventory

            for item in current_inventory:
                final_rows.append(pd.Series(item))

        Nhatkyorder_tachdon = pd.DataFrame(final_rows).reset_index(drop=True)
        Nhatkyorder_tachdon = Nhatkyorder_tachdon.sort_values(['Group_ID_Goc','Thời gian']).reset_index(drop=True)

        mask_not_nan = Nhatkyorder_tachdon['Mã hóa đơn sau khi tách bàn'].notna()
        Nhatkyorder_tachdon.loc[mask_not_nan, 'Số hóa đơn'] = \
            Nhatkyorder_tachdon.loc[mask_not_nan, 'Số hóa đơn tách bàn']
        Nhatkyorder_tachdon = Nhatkyorder_tachdon.drop(
            columns=['Group_ID_Goc','Mã hóa đơn sau khi tách bàn','Số hóa đơn tách bàn'], errors='ignore'
        ).reset_index(drop=True)

        Nhatkyorder_nhom_1 = Nhatkyorder_tachdon

    # ===== NHOM 2: CHI SUA DON =====
    mask_hop_le = Nhatkyorder['Loại log'].str.contains('SALE_CHANGE', case=False, na=False)
    hoa_don_co_hanh_dong_khac = Nhatkyorder.loc[~mask_hop_le, 'Số hóa đơn'].unique()
    Nhatkyorder_nhom_2 = (
        Nhatkyorder[~Nhatkyorder['Số hóa đơn'].isin(hoa_don_co_hanh_dong_khac)]
        .sort_values(['Số hóa đơn','Thời gian']).reset_index(drop=True)
    )

    Nhatkyorder = pd.concat([Nhatkyorder_nhom_1, Nhatkyorder_nhom_2], ignore_index=True)
    Nhatkyorder = Nhatkyorder.sort_values(by=['Mã hóa đơn','Thời gian'], ascending=True)

    Nhatkyorder['Thời gian'] = pd.to_datetime(Nhatkyorder['Thời gian'], format='%d/%m/%Y %H:%M', errors='coerce')
    Nhatkyorder['Thời gian'] = Nhatkyorder['Thời gian'].dt.strftime('%d/%m/%Y %H:%M:00')
    Nhatkyorder['Thời gian'] = pd.to_datetime(Nhatkyorder['Thời gian'], format='%d/%m/%Y %H:%M:%S')
    Nhatkyorder['Ngày']  = Nhatkyorder['Thời gian'].dt.strftime('%d/%m/%Y')
    Nhatkyorder['Năm']   = Nhatkyorder['Thời gian'].dt.year
    Nhatkyorder['Tháng'] = Nhatkyorder['Thời gian'].dt.strftime('%m-%Y')
    iso = Nhatkyorder['Thời gian'].dt.isocalendar()
    Nhatkyorder['Tuần'] = iso.week.astype(str).str.zfill(2) + '-' + iso.year.astype(str)

    # FIFO
    Nhatkyorder['Số lượng'] = pd.to_numeric(Nhatkyorder['Số lượng'], errors='coerce').fillna(0)
    pos_df = Nhatkyorder[Nhatkyorder['Số lượng'] > 0].copy()
    neg_df = Nhatkyorder[Nhatkyorder['Số lượng'] < 0].copy()
    for _, neg_row in neg_df.iterrows():
        amount_to_deduct = abs(neg_row['Số lượng'])
        bill_id = neg_row['Mã hóa đơn']
        item_name = neg_row['Tên hàng']
        mask2 = (pos_df['Mã hóa đơn'] == bill_id) & (pos_df['Tên hàng'] == item_name)
        for idx in reversed(pos_df[mask2].index.tolist()):
            if amount_to_deduct <= 0: break
            current_val = pos_df.at[idx, 'Số lượng']
            if current_val <= amount_to_deduct:
                amount_to_deduct -= current_val
                pos_df.at[idx, 'Số lượng'] = 0
            else:
                pos_df.at[idx, 'Số lượng'] = current_val - amount_to_deduct
                amount_to_deduct = 0
    Nhatkyorder = pos_df[pos_df['Số lượng'] > 0]
    Nhatkyorder['Thời gian'] = pd.to_datetime(Nhatkyorder['Thời gian'])
    Nhatkyorder = Nhatkyorder.sort_values(by=['Mã hóa đơn','Tên hàng','Thời gian'])
    Nhatkyorder['Mark'] = Nhatkyorder.groupby(['Mã hóa đơn','Tên hàng','Số lượng']).cumcount() + 1

    return Nhatkyorder

# ============================================================
# IV. PROCESS THOI GIAN GIAO MON
# ============================================================

def process_thoigian(Thoigiangiaomon):
    log.info("Xu ly Thoi gian giao mon...")

    Thoigiangiaomon = Thoigiangiaomon.rename(columns={
        'sale_id':'Mã hóa đơn','table_name':'Bàn','tran_no':'Số hóa đơn',
        'item_name':'Tên hàng','quantity':'Số lượng','tran_date':'Ngày',
        'duration_min':'Thời gian phục vụ (phút)',
        'start_time':'Thời gian bắt đầu','end_time':'Thời gian kết thúc',
        'store_id':'Mã cửa hàng'
    })
    drop_cols = [c for c in ['sale_detail_id','table_id','item_id','duration_ms','brand_id','duration_str'] if c in Thoigiangiaomon.columns]
    Thoigiangiaomon = Thoigiangiaomon.drop(columns=drop_cols)
    Thoigiangiaomon['Ngày'] = pd.to_datetime(Thoigiangiaomon['Ngày'], unit='s', errors='coerce').dt.strftime('%d/%m/%Y')

    return Thoigiangiaomon

# ============================================================
# V. MERGE & TINH KPI
# ============================================================

def merge_and_compute(HoadontheothoigianFn, Nhatkyorder, Thoigiangiaomon):
    log.info("Merge va tinh KPI...")

    # Merge Nhatky vao Hoadon
    Nhatky_subset = Nhatkyorder[["Mã hóa đơn","Số hóa đơn","Số lượng","Tên hàng","Thời gian","Nhân viên","Mark"]]
    merged_2 = pd.merge(
        HoadontheothoigianFn, Nhatky_subset,
        on=["Mã hóa đơn","Số hóa đơn","Số lượng","Tên hàng","Mark"], how="left"
    )
    
    cols = ['Thời gian', 'Nhân viên']
 
    # Buoc 1: fill trong tung hoa don
    merged_2[cols] = (
        merged_2.groupby('Mã hóa đơn')[cols]
        .transform(lambda x: x.ffill().bfill())
        .infer_objects(copy=False)
    )
 
    # Buoc 2: tao lookup chuan tu Hoadontheothoigian
    lookup = (
        Nhatkyorder.groupby('Mã hóa đơn').agg({
            'Nhân viên': 'first', 'Thời gian': 'first'
        })
    )
 
    # Buoc 3: fill NaN tu lookup
    for col in cols:
        merged_2[col] = merged_2[col].fillna(
            merged_2['Mã hóa đơn'].map(lookup[col])
        )
 
    # Buoc 4: xoa dong khong co So hoa don
    merged_2.dropna(subset=['Số hóa đơn'], inplace=True)	

    # Merge Thoi gian giao mon
    ThoigiangiaomonFn_subset = Thoigiangiaomon[["Mã hóa đơn","Số lượng","Tên hàng","Thời gian phục vụ (phút)"]]
    DataNhanSuBanRau = pd.merge(
        merged_2, ThoigiangiaomonFn_subset,
        on=["Mã hóa đơn","Số lượng","Tên hàng"], how="left"
    )

    return DataNhanSuBanRau

# ============================================================
# VI. TINH TOAN VA XUAT
# ============================================================

def compute_outputs(DataNhanSuBanRau):
    log.info("Tinh toan outputs...")

    col_time = "Thời gian phục vụ (phút)"
    nuoc_lau_items = [
        "NƯỚC LẨU (2 ĐẾN 4 KHÁCH)",
        "NƯỚC LẨU (5 ĐẾN 8 KHÁCH)",
        "NƯỚC LẨU (1 KHÁCH)"
    ]

    # Fill thoi gian nuoc lau cho cung nhom
    mask_lau_item = DataNhanSuBanRau["Tên hàng"].isin(nuoc_lau_items)
    time_map = (
        DataNhanSuBanRau[mask_lau_item]
        .dropna(subset=[col_time])
        .groupby("Mã hóa đơn")[col_time].first()
    )
    mask_fill = (
        (DataNhanSuBanRau["Nhóm hàng"] == "NƯỚC LẨU") &
        (DataNhanSuBanRau[col_time].isna())
    )
    DataNhanSuBanRau.loc[mask_fill, col_time] = \
        DataNhanSuBanRau.loc[mask_fill, "Mã hóa đơn"].map(time_map)

    DataNhanSuBanRau = DataNhanSuBanRau[~DataNhanSuBanRau["Tên hàng"].isin(nuoc_lau_items)]
    df = DataNhanSuBanRau.dropna(subset=[col_time])

    # ===== DataThoiGian =====
    df_tg = df.rename(columns={
        'Số hóa đơn':'Số hoá đơn','Ngày':'Ngày vào',
        'Tên hàng':'Tên món','Nhóm hàng':'Tên nhóm',
        'Thời gian phục vụ (phút)':'Thời gian hoàn thành đơn (phút)',
        'Mã hóa đơn':'ID'
    })
    DataThoiGian = df_tg[[
        "Cửa hàng","Số hoá đơn","Ngày vào","Tên món","Số lượng",
        "Tên nhóm","Thời gian hoàn thành đơn (phút)","Nhân viên","ID"
    ]]

    # ===== DataKHTT =====
    DataNhanSuBanRau['Thời gian'] = pd.to_datetime(DataNhanSuBanRau['Thời gian'])
    DataNhanSuBanRau_sorted = DataNhanSuBanRau.sort_values(by=['Mã hóa đơn','Thời gian'])
    DataNhanSuBanRau_first  = DataNhanSuBanRau_sorted.groupby('Mã hóa đơn', as_index=False).first()
    DataNhanSuBanRau_first  = DataNhanSuBanRau_first.rename(columns={
        'Số hóa đơn':'Số hoá đơn','Ngày':'Ngày vào','Tên Khách':'Tên',
        'Loại khách hàng':'Loại khách','Thời gian':'Thời gian order','Mã hóa đơn':'ID'
    })
    DataKHTTtheoNS = DataNhanSuBanRau_first[[
        'Cửa hàng','Số khách','Loại thành viên','Tên','SĐT','ID',
        'Số hoá đơn','Loại khách','Ngày vào','Thời gian order','Nhân viên'
    ]]

    # ===== DataNSKinhdoanh =====
    cols_kd = ['Cửa hàng','Ngày','Số hóa đơn','Thời gian','Tên hàng',
               'Đơn vị tính','Mã hóa đơn','Số lượng','Đơn giá','Nhóm hàng','Nhân viên']
    cols_kd_exist = [c for c in cols_kd if c in DataNhanSuBanRau.columns]
    DataNSKinhdoanh = DataNhanSuBanRau[cols_kd_exist].dropna(subset=['Nhân viên'])
    DataNSKinhdoanh = DataNSKinhdoanh.rename(columns={'Ngày':'Ngày vào'})

    # Tinh KPI kinh doanh
    df_kd = DataNSKinhdoanh.copy()
    anxanh_items = ["VÉ ĂN XANH","VÉ DÂN NHỎ ĂN XANH","COMBO VÉ ĂN XANH - UỐNG LÀNH","COMBO VÉ DÂN NHỎ"]
    combo_items  = ["COMBO VÉ ĂN XANH - UỐNG LÀNH","COMBO VÉ DÂN NHỎ"]
    alc_items    = ["ALACARTE","NƯỚC NGỌT"]

    df_combo = (
        df_kd[df_kd['Tên hàng'].isin(combo_items)]
        .groupby(['Ngày vào','Cửa hàng','Nhân viên'], as_index=False)['Số lượng']
        .sum().rename(columns={'Số lượng':'SL Vé Combo'})
    )
    df_anxanh = (
        df_kd[df_kd['Tên hàng'].isin(anxanh_items)]
        .groupby(['Ngày vào','Cửa hàng','Nhân viên'], as_index=False)['Số lượng']
        .sum().rename(columns={'Số lượng':'SL Vé Ăn Xanh'})
    )
    df_anxanh_total = (
        df_kd[df_kd['Tên hàng'].isin(anxanh_items)]
        .groupby(['Ngày vào','Cửa hàng'], as_index=False)['Số lượng']
        .sum().rename(columns={'Số lượng':'SL Vé Tổng trong ngày'})
    )
    df_alc = (
        df_kd[df_kd['Nhóm hàng'].isin(alc_items)]
        .groupby(['Ngày vào','Cửa hàng','Nhân viên'], as_index=False)['Đơn giá']
        .sum().rename(columns={'Đơn giá':'Giá trị ALC'})
    )
    df_alc_total = (
        df_kd[df_kd['Nhóm hàng'].isin(alc_items)]
        .groupby(['Ngày vào','Cửa hàng'], as_index=False)['Đơn giá']
        .sum().rename(columns={'Đơn giá':'Giá trị tổng ALC'})
    )

    dataTimeKD = (
        df_kd[['Cửa hàng','Ngày vào','Nhân viên']].drop_duplicates()
        .merge(df_combo,       on=['Ngày vào','Cửa hàng','Nhân viên'], how='left')
        .merge(df_anxanh,      on=['Ngày vào','Cửa hàng','Nhân viên'], how='left')
        .merge(df_anxanh_total,on=['Ngày vào','Cửa hàng'],             how='left')
        .merge(df_alc,         on=['Ngày vào','Cửa hàng','Nhân viên'], how='left')
        .merge(df_alc_total,   on=['Ngày vào','Cửa hàng'],             how='left')
        .fillna(0)
    )
    dataTimeKD = dataTimeKD[dataTimeKD['SL Vé Ăn Xanh'] != 0]

    return DataThoiGian, DataKHTTtheoNS, dataTimeKD

# ============================================================
# VII. DAY LEN GOOGLE SHEETS
# ============================================================

def push_to_sheets(DataThoiGian, DataKHTTtheoNS, dataTimeKD):
    log.info("Day data len Google Sheets...")
    gc = connect_gsheet()
    spreadsheet = gc.open_by_url(SHEET_URL)

    append_to_sheet(spreadsheet, 0, DataThoiGian)
    append_to_sheet(spreadsheet, 1, DataKHTTtheoNS)
    append_to_sheet(spreadsheet, 2, dataTimeKD)

    log.info("Day len Sheets thanh cong!")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    log.info("Bat dau phan tich BanRau...")
    try:
        Hoadontheothoigian, Chitiethoadon, Nhatkyorder_raw, Thoigiangiaomon_raw = load_data()

        HoadontheothoigianFn = process_hoadon(Hoadontheothoigian, Chitiethoadon)
        Nhatkyorder          = process_nhatky(Nhatkyorder_raw)
        Thoigiangiaomon      = process_thoigian(Thoigiangiaomon_raw)

        DataNhanSuBanRau = merge_and_compute(HoadontheothoigianFn, Nhatkyorder, Thoigiangiaomon)

        DataThoiGian, DataKHTTtheoNS, dataTimeKD = compute_outputs(DataNhanSuBanRau)

        push_to_sheets(DataThoiGian, DataKHTTtheoNS, dataTimeKD)

        log.info("Hoan tat!")
        print('{"status": "success"}')

    except Exception as e:
        log.error(f"Loi: {e}", exc_info=True)
        print(f'{{"status": "error", "message": "{str(e)}"}}')
        sys.exit(1)
