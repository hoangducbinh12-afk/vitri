import streamlit as st
import easyocr
import pandas as pd
import json
import numpy as np
from PIL import Image

# --- CẤU HÌNH HẰNG SỐ HIỆU ---
HIEU_CHART = {0: [0,11,22,33,44,55,66,77,88,99], 1: [9,10,21,32,43,54,65,76,87,98],
              2: [8,19,20,31,42,53,64,75,86,97], 3: [7,18,29,30,41,52,63,74,85,96],
              4: [6,17,28,39,40,51,62,73,84,95], 5: [5,16,27,38,49,50,61,72,83,94],
              6: [4,15,26,37,48,59,60,71,82,93], 7: [3,14,25,36,47,58,69,70,81,92],
              8: [2,13,24,35,46,57,68,79,80,91], 9: [1,12,23,34,45,56,67,78,89,90]}

st.set_page_config(page_title="Hệ thống Thống kê Lô học Pro", layout="wide")

# --- KHỞI TẠO SESSION STATE ---
if 'db' not in st.session_state:
    st.session_state.db = {"bang_b": [], "current_raw": []}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

def get_hieu(num):
    for h, nums in HIEU_CHART.items():
        if num in nums: return h
    return 0

def analyze_gdb(num):
    s = f"{num:02d}"
    x, y = int(s[0]), int(s[1])
    return {
        "dau": x, "duoi": y, "tong": (x + y) % 10, 
        "hieu": get_hieu(num), "cham": [x, y]
    }

# --- SIDEBAR ---
with st.sidebar:
    st.header("Cấu hình dữ liệu")
    uploaded_file = st.file_uploader("1. Tải ảnh kết quả", type=["png", "jpg", "jpeg"])
    gdb_input = st.number_input("2. Nhập 2 số cuối GĐB hôm nay", min_value=0, max_value=99, value=0)
    
    uploaded_json = st.file_uploader("Nạp dữ liệu cũ (JSON)", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
    
    num_display = st.slider("Số lượng dàn số hiển thị", 10, 100, 20)
    run_btn = st.button("Phân tích & Cập nhật")

# --- XỬ LÝ DỮ LIỆU ---
if uploaded_file and run_btn:
    image = Image.open(uploaded_file)
    results = reader.readtext(np.array(image), detail=0)
    raw_text = "".join([res for res in results if res.isdigit()])
    raw = [int(d) for d in raw_text]
    st.session_state.db["current_raw"] = raw

    target = analyze_gdb(gdb_input)
    
    # Khởi tạo Bảng B (Bảng lưu điểm tích lũy)
    if not st.session_state.db["bang_b"] or len(st.session_state.db["bang_b"]) != len(raw):
        st.session_state.db["bang_b"] = [{"dau":0,"duoi":0,"tong":0,"hieu":0,"cham":0} for _ in range(len(raw))]

    # Cập nhật điểm (Nguyên tắc Reset về 0 hoặc +1)
    for i in range(len(raw)):
        val = raw[i]
        p = st.session_state.db["bang_b"][i]
        p["dau"] = 0 if val == target["dau"] else p["dau"] + 1
        p["duoi"] = 0 if val == target["duoi"] else p["duoi"] + 1
        p["tong"] = 0 if val == target["tong"] else p["tong"] + 1
        p["hieu"] = 0 if val == target["hieu"] else p["hieu"] + 1
        p["cham"] = 0 if val in target["cham"] else p["cham"] + 1
    
    st.success("Đã cập nhật dữ liệu mới!")

# --- HIỂN THỊ KẾT QUẢ ---
raw = st.session_state.db.get("current_raw", [])
if raw and st.session_state.db["bang_b"]:
    # 1. TÍNH TOÁN CÁC BẢNG TRƯỚC KHI HIỂN THỊ
    
    # Bảng A & B (Kết hợp hiển thị)
    list_a_b = []
    for i in range(len(raw)):
        val = raw[i]
        list_a_b.append({
            "VI TRI": i + 1,
            "SO VE": val,
            "DAU": val, "DUOI": val, "TONG": (val+val)%10, "HIEU": get_hieu(val), "CHAM": val, # Cơ sở tính toán (Bảng A)
            "DIEM DAU": st.session_state.db["bang_b"][i]["dau"],
            "DIEM DUOI": st.session_state.db["bang_b"][i]["duoi"],
            "DIEM TONG": st.session_state.db["bang_b"][i]["tong"],
            "DIEM HIEU": st.session_state.db["bang_b"][i]["hieu"],
            "DIEM CHAM": st.session_state.db["bang_b"][i]["cham"],
        })
    df_ab = pd.DataFrame(list_a_b)

    # Bảng C (Tổng điểm theo số 0-9)
    list_c = []
    for i in range(10):
        # Lọc những vị trí có SO VE là i
        mask = df_ab["SO VE"] == i
        list_c.append({
            "SO": i,
            "T DAU": df_ab.loc[mask, "DIEM DAU"].sum(),
            "T DUOI": df_ab.loc[mask, "DIEM DUOI"].sum(),
            "T TONG": df_ab.loc[mask, "DIEM TONG"].sum(),
            "T HIEU": df_ab.loc[mask, "DIEM HIEU"].sum(),
            "T CHAM": df_ab.loc[mask, "DIEM CHAM"].sum(),
        })
    df_c = pd.DataFrame(list_c)

    # Bảng D & Dàn số
    list_d_flat = []
    for i in range(100):
        t = analyze_gdb(i)
        x, y = t["dau"], t["duoi"]
        score_dau = df_c.iloc[x]["T DAU"]
        score_duoi = df_c.iloc[y]["T DUOI"]
        score_tong = df_c.iloc[t["tong"]]["T TONG"]
        score_hieu = df_c.iloc[t["hieu"]]["T HIEU"]
        
        if x == y: # Kép bằng
            score_cham = df_c.iloc[x]["T CHAM"] * 2
        else:
            score_cham = df_c.iloc[x]["T CHAM"] + df_c.iloc[y]["T CHAM"]
            
        total_score = score_dau + score_duoi + score_tong + score_hieu + score_cham
        list_d_flat.append({"SO": f"{i:02d}", "DIEM": total_score, "x": x, "y": y})

    # --- GIAO DIỆN HIỂN THỊ ---
    
    # Phần Dàn Số (Ưu tiên đầu tiên)
    st.subheader(f"🔥 Dàn số tiềm năng (Top {num_display})")
    df_dan = pd.DataFrame(list_d_flat).sort_values(by="DIEM", ascending=False).head(num_display)
    st.info(" ".join(df_dan["SO"].tolist()))

    tabs = st.tabs(["Bảng A (Cơ sở)", "Bảng B (Điểm vị trí)", "Bảng C (Tổng kết số)", "Bảng D (Ma trận 100 số)"])

    with tabs[0]:
        st.dataframe(df_ab[["VI TRI", "SO VE", "DAU", "DUOI", "TONG", "HIEU", "CHAM"]], use_container_width=True)

    with tabs[1]:
        st.dataframe(df_ab[["VI TRI", "SO VE", "DIEM DAU", "DIEM DUOI", "DIEM TONG", "DIEM HIEU", "DIEM CHAM"]], use_container_width=True)

    with tabs[2]:
        st.table(df_c)

    with tabs[3]:
        # Tạo ma trận D
        matrix_d = np.zeros((10, 10))
        for item in list_d_flat:
            matrix_d[item['x'], item['y']] = item['DIEM']
        df_matrix = pd.DataFrame(matrix_d, index=[f"Đầu {i}" for i in range(10)], columns=[f"Đuôi {i}" for i in range(10)])
        st.dataframe(df_matrix.style.background_gradient(cmap='YlOrRd'), use_container_width=True)

    # Nút lưu JSON
    st.download_button("Lưu dữ liệu máy tính (.json)", json.dumps(st.session_state.db), "loto_data.json")
else:
    st.warning("Vui lòng nạp dữ liệu ảnh hoặc file JSON cũ.")
