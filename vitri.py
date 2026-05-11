import streamlit as st
import easyocr
import pandas as pd
import json
import numpy as np
from PIL import Image

# --- HẰNG SỐ HIỆU (QUY ƯỚC CHUẨN) ---
HIEU_CHART = {0: [0,11,22,33,44,55,66,77,88,99], 1: [9,10,21,32,43,54,65,76,87,98],
              2: [8,19,20,31,42,53,64,75,86,97], 3: [7,18,29,30,41,52,63,74,85,96],
              4: [6,17,28,39,40,51,62,73,84,95], 5: [5,16,27,38,49,50,61,72,83,94],
              6: [4,15,26,37,48,59,60,71,82,93], 7: [3,14,25,36,47,58,69,70,81,92],
              8: [2,13,24,35,46,57,68,79,80,91], 9: [1,12,23,34,45,56,67,78,89,90]}

st.set_page_config(page_title="Hệ thống Thống kê Lô học", layout="wide")
st.title("📊 App Thống kê Vị trí & Thuộc tính")

# --- KHỞI TẠO DỮ LIỆU ---
if 'db' not in st.session_state:
    st.session_state.db = {"bang_a": [], "current_raw": []}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

def analyze_number(num):
    s = f"{num:02d}"
    x, y = int(s[0]), int(s[1])
    h_val = next((h for h, nums in HIEU_CHART.items() if num in nums), 0)
    return {"dau": x, "duoi": y, "tong": (x + y) % 10, "hieu": h_val, "cham": [x, y] if x != y else [x]}

# --- SIDEBAR ---
with st.sidebar:
    st.header("Cấu hình dữ liệu")
    uploaded_file = st.file_uploader("1. Tải ảnh kết quả", type=["png", "jpg", "jpeg"])
    gdb_input = st.number_input("2. Nhập GĐB hôm nay (2 số cuối)", min_value=0, max_value=99, value=0)
    
    uploaded_json = st.file_uploader("Nạp dữ liệu cũ (JSON)", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
        st.success("Đã nạp dữ liệu thành công!")

    run_button = st.button("Phân tích & Cập nhật điểm")

# --- XỬ LÝ KHI ẤN NÚT ---
if uploaded_file and run_button:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    with st.spinner('Đang đọc số từ ảnh...'):
        results = reader.readtext(img_array, detail=0)
        raw_text = "".join([res for res in results if res.isdigit()])
        raw = [int(d) for d in raw_text]
        st.session_state.db["current_raw"] = raw

    # Phân tích mục tiêu
    target = analyze_number(gdb_input)
    
    # KIỂM TRA VÀ KHỞI TẠO BANG_A NẾU CẦN (Sửa lỗi KeyError tại đây)
    if not st.session_state.db["bang_a"] or len(st.session_state.db["bang_a"]) != len(raw):
        st.session_state.db["bang_a"] = [{"points": {"dau":0,"duoi":0,"tong":0,"hieu":0,"cham":0}} for _ in range(len(raw))]

    # Nhảy điểm
    for i in range(len(raw)):
        val = raw[i]
        p = st.session_state.db["bang_a"][i]["points"]
        p["dau"] = 0 if val == target["dau"] else p["dau"] + 1
        p["duoi"] = 0 if val == target["duoi"] else p["duoi"] + 1
        p["tong"] = 0 if val == target["tong"] else p["tong"] + 1
        p["hieu"] = 0 if val == target["hieu"] else p["hieu"] + 1
        p["cham"] = 0 if val in target["cham"] else p["cham"] + 1
    
    st.success(f"Đã cập nhật điểm cho {len(raw)} vị trí!")

# --- HIỂN THỊ 3 TAB KẾT QUẢ ---
raw = st.session_state.db.get("current_raw", [])
if raw and st.session_state.db["bang_a"]:
    tab1, tab2, tab3 = st.tabs(["📌 Bảng A (Vị trí)", "🗂️ Bảng B (Thuộc tính)", "🎯 Bảng C (100 số)"])

    with tab1:
        st.subheader("Điểm tích lũy chi tiết tại từng vị trí")
        data_a = []
        for i in range(len(raw)):
            row = {"Vị trí": i+1, "Số": raw[i]}
            row.update(st.session_state.db["bang_a"][i]["points"])
            data_a.append(row)
        st.dataframe(pd.DataFrame(data_a), use_container_width=True, height=400)

    with tab2:
        st.subheader("Tổng hợp điểm theo dạng số (0-9)")
        # Gom điểm cho Bảng B
        bang_b = {k: [0]*10 for k in ["dau", "duoi", "tong", "hieu", "cham"]}
        for i, val in enumerate(raw):
            if val < 10: # Chỉ lấy các số từ 0-9
                for k in bang_b.keys():
                    bang_b[k][val] += st.session_state.db["bang_a"][i]["points"][k]
        
        df_b = pd.DataFrame(bang_b)
        df_b.index.name = "Số"
        st.table(df_b)

    with tab3:
        st.subheader("Điểm tổng hợp cho 100 con số (00-99)")
        bang_c = []
        for i in range(100):
            t = analyze_number(i)
            x, y = t["dau"], t["duoi"]
            # Công thức tính điểm của bạn
            if x != y: # Số thường
                score = (bang_b["dau"][x] + bang_b["duoi"][y] + bang_b["tong"][t["tong"]] + 
                         bang_b["hieu"][t["hieu"]] + bang_b["cham"][x] + bang_b["cham"][y])
            else: # Số kép bằng
                score = (bang_b["dau"][x] + bang_b["duoi"][x] + bang_b["tong"][t["tong"]] + 
                         bang_b["hieu"][0] + (2 * bang_b["cham"][x]))
            bang_c.append({"Con số": f"{i:02d}", "Tổng điểm": score})
        
        df_c = pd.DataFrame(bang_c).sort_values(by="Tổng điểm", ascending=False)
        st.dataframe(df_c, use_container_width=True, height=500)

    # Nút tải dữ liệu
    st.divider()
    json_data = json.dumps(st.session_state.db)
    st.download_button("📥 Tải file dữ liệu (.json) về máy", json_data, "du_lieu_loto.json", "application/json")
else:
    st.info("Vui lòng tải ảnh lên và nhấn 'Phân tích' để xem kết quả 3 bảng.")
