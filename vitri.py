import streamlit as st
import easyocr
import pandas as pd
import json
import numpy as np
from PIL import Image

# --- HẰNG SỐ HIỆU QUY ƯỚC ---
HIEU_CHART = {0: [0,11,22,33,44,55,66,77,88,99], 1: [9,10,21,32,43,54,65,76,87,98],
              2: [8,19,20,31,42,53,64,75,86,97], 3: [7,18,29,30,41,52,63,74,85,96],
              4: [6,17,28,39,40,51,62,73,84,95], 5: [5,16,27,38,49,50,61,72,83,94],
              6: [4,15,26,37,48,59,60,71,82,93], 7: [3,14,25,36,47,58,69,70,81,92],
              8: [2,13,24,35,46,57,68,79,80,91], 9: [1,12,23,34,45,56,67,78,89,90]}

st.set_page_config(page_title="Hệ thống Thống kê Lô học Pro", layout="wide")

# Khởi tạo bộ nhớ tạm
if 'db' not in st.session_state:
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "last_gdb": None}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

def analyze_gdb_result(num):
    s = f"{num:02d}"
    x, y = int(s[0]), int(s[1])
    h_val = next((h for h, nums in HIEU_CHART.items() if num in nums), 0)
    return {"dau": x, "duoi": y, "tong": (x + y) % 10, "hieu": h_val, "cham": [x, y]}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cấu hình dữ liệu")
    uploaded_file = st.file_uploader("1. Tải ảnh kết quả", type=["png", "jpg", "jpeg"])
    
    gdb_info = st.empty() # Chỗ để hiện GĐB sau khi quét
    
    uploaded_json = st.file_uploader("📂 Nạp dữ liệu cũ (JSON)", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
        st.success("Đã nạp file dữ liệu!")

    num_dan = st.slider("Số lượng dàn số hiển thị", 10, 100, 20)
    run_btn = st.button("🚀 Phân tích & Cập nhật")

# --- XỬ LÝ LOGIC ---
if uploaded_file and run_btn:
    reader = load_ocr()
    image = Image.open(uploaded_file)
    # Đọc ảnh với tọa độ để xác định GĐB ở đầu bảng
    results = reader.readtext(np.array(image))
    results.sort(key=lambda x: x[0][0][1]) # Sắp xếp từ trên xuống dưới
    
    all_digits_list = []
    detected_gdb = None

    for (bbox, text, prob) in results:
        clean_text = "".join([d for d in text if d.isdigit()])
        if clean_text:
            # GĐB là chuỗi 5 hoặc 6 số đầu tiên tìm thấy
            if detected_gdb is None and len(clean_text) in [5, 6]:
                detected_gdb = int(clean_text[-2:])
            
            for digit in clean_text:
                all_digits_list.append(int(digit))

    if detected_gdb is not None:
        gdb_info.metric("Kết quả hôm nay", f"{detected_gdb:02d}")
        raw = all_digits_list
        
        # TRƯỜNG HỢP 1: LẦN ĐẦU TIÊN (Khởi tạo điểm = 1)
        if not st.session_state.db["current_raw"]:
            st.session_state.db["current_raw"] = raw
            st.session_state.db["bang_b_points"] = [{"dau":1,"duoi":1,"tong":1,"hieu":1,"cham":1} for _ in range(len(raw))]
            st.session_state.db["last_gdb"] = detected_gdb
            st.info("Chào mừng! Ảnh đầu tiên đã được nạp với điểm mặc định là 1.")
        
        # TRƯỜNG HỢP 2: ĐÃ CÓ DỮ LIỆU (Tính toán nhảy điểm)
        else:
            target = analyze_gdb_result(detected_gdb)
            old_raw = st.session_state.db["current_raw"]
            points = st.session_state.db["bang_b_points"]
            
            # So sánh GĐB mới với bảng số cũ
            for i in range(min(len(old_raw), len(points))):
                val = old_raw[i]
                p = points[i]
                p["dau"] = 0 if val == target["dau"] else p["dau"] + 1
                p["duoi"] = 0 if val == target["duoi"] else p["duoi"] + 1
                p["tong"] = 0 if val == target["tong"] else p["tong"] + 1
                p["hieu"] = 0 if val == target["hieu"] else p["hieu"] + 1
                p["cham"] = 0 if val in target["cham"] else p["cham"] + 1
            
            # Cập nhật bảng số mới cho lần sau
            st.session_state.db["current_raw"] = raw
            st.session_state.db["last_gdb"] = detected_gdb
            st.success(f"Đã cập nhật điểm dựa trên GĐB: {detected_gdb:02d}")
    else:
        st.error("Lỗi: Không tìm thấy Giải Đặc Biệt (5-6 số) trên ảnh!")

# --- HIỂN THỊ KẾT QUẢ ---
raw = st.session_state.db.get("current_raw", [])
points_data = st.session_state.db.get("bang_b_points", [])

if raw and points_data:
    # 1. Tính toán Bảng C
    df_b_full = pd.DataFrame([{"VI TRI": i+1, "SO VE": raw[i], **points_data[i]} for i in range(len(raw))])
    
    list_c = []
    for i in range(10):
        m = df_b_full[df_b_full["SO VE"] == i]
        list_c.append({
            "SO": i,
            "T DAU": m["dau"].sum(), "T DUOI": m["duoi"].sum(),
            "T TONG": m["tong"].sum(), "T HIEU": m["hieu"].sum(), "T CHAM": m["cham"].sum()
        })
    df_c = pd.DataFrame(list_c)

    # 2. Tính toán Bảng D & Dàn số
    dan_list = []
    matrix_data = np.zeros((10,10))
    for i in range(100):
        t = analyze_gdb_result(i)
        x, y = t["dau"], t["duoi"]
        s_dau, s_duoi, s_tong, s_hieu = df_c.iloc[x]["T DAU"], df_c.iloc[y]["T DUOI"], df_c.iloc[t["tong"]]["T TONG"], df_c.iloc[t["hieu"]]["T HIEU"]
        s_cham = (df_c.iloc[x]["T CHAM"] * 2) if x==y else (df_c.iloc[x]["T CHAM"] + df_c.iloc[y]["T CHAM"])
        total = s_dau + s_duoi + s_tong + s_hieu + s_cham
        dan_list.append({"SO": f"{i:02d}", "DIEM": total})
        matrix_data[x, y] = total

    # --- UI LAYOUT ---
    st.title("📊 App Thống kê Vị trí & Thuộc tính")
    
    # Dàn số hiển thị đầu tiên
    st.subheader(f"🔥 Dàn số tiềm năng (Top {num_dan} từ cao đến thấp)")
    top_dan = pd.DataFrame(dan_list).sort_values("DIEM", ascending=False).head(num_dan)
    st.info(" ".join(top_dan["SO"].tolist()))

    t1, t2, t3, t4 = st.tabs(["📌 Bảng A (Cơ sở)", "📈 Bảng B (Điểm vị trí)", "🗂️ Bảng C (Tổng kết)", "🔢 Bảng D (Ma trận)"])
    
    with t1:
        data_a = [{"VI TRI": i+1, "SO VE": raw[i], "DAU": raw[i], "DUOI": raw[i], "TONG": raw[i], "HIEU": raw[i], "CHAM": raw[i]} for i in range(len(raw))]
        st.dataframe(pd.DataFrame(data_a), use_container_width=True)

    with t2:
        st.dataframe(df_b_full.rename(columns={"dau":"DIEM DAU","duoi":"DIEM DUOI","tong":"DIEM TONG","hieu":"DIEM HIEU","cham":"DIEM CHAM"}), use_container_width=True)

    with t3:
        st.table(df_c)

    with t4:
        df_matrix = pd.DataFrame(matrix_data, index=[f"Đầu {i}" for i in range(10)], columns=[f"Đuôi {i}" for i in range(10)])
        st.dataframe(df_matrix, use_container_width=True)

    # Nút lưu dữ liệu
    st.divider()
    st.download_button("💾 Lưu dữ liệu vào máy tính (.json)", json.dumps(st.session_state.db), "loto_data.json")
else:
    st.warning("Vui lòng tải ảnh kết quả đầu tiên lên để bắt đầu thống kê.")
