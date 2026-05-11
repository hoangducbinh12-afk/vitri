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

# --- KHỞI TẠO BỘ NHỚ ---
if 'db' not in st.session_state:
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "history": []}

# Nút RESET ALL trên Sidebar
if st.sidebar.button("❌ RESET ALL", use_container_width=True):
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "history": []}
    st.rerun()

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
    uploaded_json = st.file_uploader("📂 Nạp dữ liệu cũ (JSON)", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
    
    run_btn = st.button("🔥 CẬP NHẬT TỔNG LỰC", use_container_width=True)

# --- XỬ LÝ LOGIC ---
if uploaded_file and run_btn:
    reader = load_ocr()
    image = Image.open(uploaded_file)
    results = reader.readtext(np.array(image))
    results.sort(key=lambda x: x[0][0][1]) # Sắp xếp từ trên xuống dưới
    
    all_digits_list, detected_gdb = [], None
    for (bbox, text, prob) in results:
        clean_text = "".join([d for d in text if d.isdigit()])
        if clean_text:
            if detected_gdb is None and len(clean_text) in [5, 6]:
                detected_gdb = int(clean_text[-2:])
            for digit in clean_text: all_digits_list.append(int(digit))

    if detected_gdb is not None:
        raw = all_digits_list
        target = analyze_gdb_result(detected_gdb)
        
        rank_val = "N/A"
        loai_val = "N/A"
        
        # 1. Tính toán Vị trí (Rank) dựa trên điểm cũ trước khi update
        if st.session_state.db["current_raw"] and st.session_state.db["bang_b_points"]:
            old_raw = st.session_state.db["current_raw"]
            old_pts = st.session_state.db["bang_b_points"]
            df_temp = pd.DataFrame([{"S": old_raw[i], **old_pts[i]} for i in range(len(old_raw))])
            
            list_c_temp = []
            for i in range(10):
                m = df_temp[df_temp["S"] == i]
                list_c_temp.append({"S":i, "dau":m["dau"].sum(), "duoi":m["duoi"].sum(), "tong":m["tong"].sum(), "hieu":m["hieu"].sum(), "cham":m["cham"].sum()})
            df_c_temp = pd.DataFrame(list_c_temp)
            
            dan_scores = []
            for i in range(100):
                t = analyze_gdb_result(i)
                x, y = t["dau"], t["duoi"]
                score = df_c_temp.iloc[x]["dau"] + df_c_temp.iloc[y]["duoi"] + df_c_temp.iloc[t["tong"]]["tong"] + df_c_temp.iloc[t["hieu"]]["hieu"]
                score += (df_c_temp.iloc[x]["cham"] * 2) if x==y else (df_c_temp.iloc[x]["cham"] + df_c_temp.iloc[y]["cham"])
                dan_scores.append({"SO": f"{i:02d}", "DIEM": score})
            
            df_rank = pd.DataFrame(dan_scores).sort_values("DIEM", ascending=False).reset_index(drop=True)
            rank_found = df_rank[df_rank["SO"] == f"{detected_gdb:02d}"].index
            if len(rank_found) > 0:
                rank_val = int(rank_found[0]) + 1
                loai_val = "A" if rank_val <= 70 else "T"

        # 2. Cập nhật điểm cho Bảng B (Cuốn chiếu)
        if not st.session_state.db["current_raw"]:
            # Lần đầu load ảnh: Khởi tạo điểm = 1
            st.session_state.db["bang_b_points"] = [{"dau":1,"duoi":1,"tong":1,"hieu":1,"cham":1} for _ in range(len(raw))]
        else:
            points = st.session_state.db["bang_b_points"]
            old_raw = st.session_state.db["current_raw"]
            for i in range(min(len(old_raw), len(points))):
                val, p = old_raw[i], points[i]
                p["dau"] = 0 if val == target["dau"] else p["dau"] + 1
                p["duoi"] = 0 if val == target["duoi"] else p["duoi"] + 1
                p["tong"] = 0 if val == target["tong"] else p["tong"] + 1
                p["hieu"] = 0 if val == target["hieu"] else p["hieu"] + 1
                p["cham"] = 0 if val in target["cham"] else p["cham"] + 1

        # 3. Lưu lịch sử
        st.session_state.db["history"].insert(0, {
            "Kỳ": len(st.session_state.db["history"]) + 1,
            "Số về": f"{detected_gdb:02d}",
            "Vị trí": rank_val,
            "Loại": loai_val
        })
        st.session_state.db["current_raw"] = raw
        st.success(f"Đã cập nhật GĐB: {detected_gdb:02d}")
    else:
        st.error("Không tìm thấy GĐB trên ảnh!")

# --- GIAO DIỆN HIỂN THỊ ---
if st.session_state.db["current_raw"] and st.session_state.db["bang_b_points"]:
    raw = st.session_state.db["current_raw"]
    pts = st.session_state.db["bang_b_points"]
    
    # Tính toán bảng C & D để lấy Dàn
    df_b = pd.DataFrame([{"S": raw[i], **pts[i]} for i in range(len(raw))])
    list_c = []
    for i in range(10):
        m = df_b[df_b["S"] == i]
        list_c.append({"S":i, "T DAU":m["dau"].sum(), "T DUOI":m["duoi"].sum(), "T TONG":m["tong"].sum(), "T HIEU":m["hieu"].sum(), "T CHAM":m["cham"].sum()})
    df_c = pd.DataFrame(list_c)

    dan_final = []
    for i in range(100):
        t = analyze_gdb_result(i)
        x, y = t["dau"], t["duoi"]
        score = df_c.iloc[x]["T DAU"] + df_c.iloc[y]["T DUOI"] + df_c.iloc[t["tong"]]["T TONG"] + df_c.iloc[t["hieu"]]["T HIEU"]
        score += (df_c.iloc[x]["T CHAM"] * 2) if x==y else (df_c.iloc[x]["T CHAM"] + df_c.iloc[y]["T CHAM"])
        dan_final.append({"SO": f"{i:02d}", "DIEM": score})
    
    df_dan = pd.DataFrame(dan_final).sort_values("DIEM", ascending=False)

    # --- HIỂN THỊ DÀN 1 & 2 ---
    st.write("### 🎯 DÀN SỐ TỔNG LỰC")
    c1, c2 = st.columns(2)
    with c1:
        num1 = st.number_input("Số lượng Dàn 1:", 1, 100, 49)
        d1 = " ".join(df_dan.head(num1)["SO"].tolist())
        st.text_area("Dàn 1 (Copy tại đây):", value=d1, height=150)
    with c2:
        num2 = st.number_input("Số lượng Dàn 2:", 1, 100, 100)
        d2 = " ".join(df_dan.head(num2)["SO"].tolist())
        st.text_area("Dàn 2 (Copy tại đây):", value=d2, height=150)

    # --- CÁC TAB CHI TIẾT ---
    tabs = st.tabs(["🕒 Lịch sử", "🎲 Bảng B (Điểm)", "📊 Bảng A (Cơ sở)", "💾 Sao lưu"])
    
    with tabs[0]:
        st.subheader("Bảng Lịch sử Thống kê")
        if st.session_state.db["history"]:
            st.table(pd.DataFrame(st.session_state.db["history"]))
    
    with tabs[1]:
        st.subheader("Bảng B - Chi tiết điểm vị trí")
        st.dataframe(df_b.rename(columns={"dau":"DIEM DAU","duoi":"DIEM DUOI","tong":"DIEM TONG","hieu":"DIEM HIEU","cham":"DIEM CHAM"}), use_container_width=True)

    with tabs[2]:
        st.subheader("Bảng A - Dữ liệu gốc các vị trí")
        df_a_display = pd.DataFrame([{"Vị trí": i+1, "Số về": raw[i]} for i in range(len(raw))])
        st.dataframe(df_a_display, use_container_width=True)

    with tabs[3]:
        st.subheader("Quản lý dữ liệu")
        st.download_button("💾 TẢI FILE DỮ LIỆU (.JSON)", json.dumps(st.session_state.db), "loto_data.json", use_container_width=True)
else:
    st.info("Vui lòng tải ảnh kết quả đầu tiên để khởi tạo dữ liệu.")
