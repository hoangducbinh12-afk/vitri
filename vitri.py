import streamlit as st
import easyocr
import pandas as pd
import json
import numpy as np
from PIL import Image

# --- HẰNG SỐ HIỆU QUY ƯỚC (Dành cho việc phân tích GĐB và Bảng D) ---
HIEU_CHART = {0: [0,11,22,33,44,55,66,77,88,99], 1: [9,10,21,32,43,54,65,76,87,98],
              2: [8,19,20,31,42,53,64,75,86,97], 3: [7,18,29,30,41,52,63,74,85,96],
              4: [6,17,28,39,40,51,62,73,84,95], 5: [5,16,27,38,49,50,61,72,83,94],
              6: [4,15,26,37,48,59,60,71,82,93], 7: [3,14,25,36,47,58,69,70,81,92],
              8: [2,13,24,35,46,57,68,79,80,91], 9: [1,12,23,34,45,56,67,78,89,90]}

st.set_page_config(page_title="Hệ thống Thống kê Lô học Pro", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = {"bang_b_points": [], "current_raw": []}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

def analyze_gdb_result(num):
    s = f"{num:02d}"
    x, y = int(s[0]), int(s[1])
    h_val = 0
    for h, nums in HIEU_CHART.items():
        if num in nums: h_val = h; break
    return {"dau": x, "duoi": y, "tong": (x + y) % 10, "hieu": h_val, "cham": [x, y]}

# --- SIDEBAR ---
with st.sidebar:
    st.header("Cấu hình dữ liệu")
    uploaded_file = st.file_uploader("1. Tải ảnh kết quả", type=["png", "jpg", "jpeg"])
    gdb_input = st.number_input("2. Nhập 2 số cuối GĐB hôm nay", 0, 99, 0)
    uploaded_json = st.file_uploader("Nạp dữ liệu cũ (JSON)", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
    num_dan = st.slider("Số lượng dàn số", 10, 100, 20)
    run_btn = st.button("Phân tích & Cập nhật điểm")

# --- XỬ LÝ LOGIC ---
if uploaded_file and run_btn:
    reader = load_ocr()
    image = Image.open(uploaded_file)
    results = reader.readtext(np.array(image), detail=0)
    # Lấy toàn bộ chữ số từ ảnh
    raw = [int(d) for d in "".join([res for res in results if res.isdigit()])]
    st.session_state.db["current_raw"] = raw
    
    target = analyze_gdb_result(gdb_input)
    
    # Khởi tạo điểm nếu chưa có hoặc số lượng vị trí thay đổi
    if not st.session_state.db.get("bang_b_points") or len(st.session_state.db["bang_b_points"]) != len(raw):
        st.session_state.db["bang_b_points"] = [{"dau":0,"duoi":0,"tong":0,"hieu":0,"cham":0} for _ in range(len(raw))]

    # Cập nhật điểm Bảng B (So sánh SO VE của Bảng A với các thuộc tính GĐB hôm nay)
    for i in range(len(raw)):
        val = raw[i]
        p = st.session_state.db["bang_b_points"][i]
        p["dau"] = 0 if val == target["dau"] else p["dau"] + 1
        p["duoi"] = 0 if val == target["duoi"] else p["duoi"] + 1
        p["tong"] = 0 if val == target["tong"] else p["tong"] + 1
        p["hieu"] = 0 if val == target["hieu"] else p["hieu"] + 1
        p["cham"] = 0 if val in target["cham"] else p["cham"] + 1
    st.success(f"Đã cập nhật dữ liệu cho {len(raw)} vị trí!")

# --- HIỂN THỊ KẾT QUẢ ---
raw = st.session_state.db.get("current_raw", [])
if raw:
    # 1. TÍNH TOÁN DỮ LIỆU CÁC BẢNG
    
    # Chuẩn bị Bảng B & Bảng A
    list_b = []
    for i in range(len(raw)):
        list_b.append({
            "VI TRI": i + 1,
            "SO VE": raw[i],
            **st.session_state.db["bang_b_points"][i]
        })
    df_b_full = pd.DataFrame(list_b)

    # Tính Bảng C (Gom điểm từ Bảng B theo SO VE 0-9)
    list_c = []
    for i in range(10):
        m = df_b_full[df_b_full["SO VE"] == i]
        list_c.append({
            "SO": i,
            "T DAU": m["dau"].sum(), 
            "T DUOI": m["duoi"].sum(),
            "T TONG": m["tong"].sum(), 
            "T HIEU": m["hieu"].sum(), 
            "T CHAM": m["cham"].sum()
        })
    df_c = pd.DataFrame(list_c)

    # Tính Bảng D & Dàn số
    dan_list = []
    matrix_data = np.zeros((10,10))
    for i in range(100):
        t = analyze_gdb_result(i)
        x, y = t["dau"], t["duoi"]
        
        # Lấy dữ liệu từ Bảng C
        s_dau = df_c.iloc[x]["T DAU"]
        s_duoi = df_c.iloc[y]["T DUOI"]
        s_tong = df_c.iloc[t["tong"]]["T TONG"]
        s_hieu = df_c.iloc[t["hieu"]]["T HIEU"]
        
        # Quy tắc chạm: kép nhân đôi
        if x == y:
            s_cham = df_c.iloc[x]["T CHAM"] * 2
        else:
            s_cham = df_c.iloc[x]["T CHAM"] + df_c.iloc[y]["T CHAM"]
            
        total = s_dau + s_duoi + s_tong + s_hieu + s_cham
        dan_list.append({"SO": f"{i:02d}", "DIEM": total})
        matrix_data[x, y] = total

    # 2. GIAO DIỆN HIỂN THỊ (SẮP XẾP THEO YÊU CẦU)
    
    # Bảng Dàn Số (Kết quả cuối cùng hiển thị đầu tiên)
    st.subheader(f"🔥 Dàn số tiềm năng (Top {num_dan} từ cao đến thấp)")
    top_dan = pd.DataFrame(dan_list).sort_values("DIEM", ascending=False).head(num_dan)
    st.info(" ".join(top_dan["SO"].tolist()))

    # Các Tab chi tiết
    t1, t2, t3, t4 = st.tabs(["📊 Bảng A (Cơ sở)", "📈 Bảng B (Điểm vị trí)", "🗂️ Bảng C (Tổng kết)", "🔢 Bảng D (Ma trận)"])
    
    with t1:
        # Bảng A: Toàn bộ cột thuộc tính giống SO VE
        data_a = []
        for i in range(len(raw)):
            v = raw[i]
            data_a.append({"VI TRI": i+1, "SO VE": v, "DAU": v, "DUOI": v, "TONG": v, "HIEU": v, "CHAM": v})
        st.dataframe(pd.DataFrame(data_a), use_container_width=True)

    with t2:
        # Bảng B: Hiển thị điểm tích lũy
        df_b_display = df_b_full.rename(columns={
            "dau": "DIEM DAU", "duoi": "DIEM DUOI", "tong": "DIEM TONG", "hieu": "DIEM HIEU", "cham": "DIEM CHAM"
        })
        st.dataframe(df_b_display, use_container_width=True)

    with t3:
        st.table(df_c)

    with t4:
        df_matrix = pd.DataFrame(matrix_data, 
                                 index=[f"Đầu {i}" for i in range(10)], 
                                 columns=[f"Đuôi {i}" for i in range(10)])
        st.dataframe(df_matrix, use_container_width=True)

    st.divider()
    st.download_button("💾 Lưu dữ liệu vào máy (.json)", json.dumps(st.session_state.db), "loto_data.json")
else:
    st.warning("Vui lòng tải ảnh kết quả lên để bắt đầu.")
