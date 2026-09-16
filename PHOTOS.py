import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import zipfile
from datetime import date, timedelta
from PIL import Image

# Page setup
st.set_page_config(page_title="Mukh Mantri Yatra - Fleet Audit",
                   layout="wide", page_icon="🚌")

DATA_DIR = "yatra_fleet_storage"
DB_PATH = "yatra_fleet.db"
os.makedirs(DATA_DIR, exist_ok=True)

# 13 Checkpoints mapped directly from the guidelines poster
PHOTO_SCHEMA = {
    "1. Departure & Onward Journey": {
        "09_odo_departure": "09. Punjab Departure Odometer [MANDATORY]",
        "01_group_departure": "01. Departure Group Photo (Banner View) [MANDATORY]",
        "02_travel_cabin": "02. Travel Group Photo (Inside Cabin)",
        "03_breakfast": "03. Breakfast Photo",
        "04_glass_refreshment": "04. Refreshment & Steel Glass Distribution [MANDATORY]"
    },
    "2. Meals & VIP Visits": {
        "05_lunch": "05. Lunch Photo",
        "06_hitea": "06. Hi-Tea Photo",
        "07_dinner": "07. Dinner Group Photo",
        "13_mla_visit": "13. MLA Ji / VIP Group Photo (If Visited)"
    },
    "3. Destination & Return Leg": {
        "10_odo_dest_arrival": "10. Destination Arrival Odometer [MANDATORY]",
        "11_odo_return_start": "11. Return Start Odometer [MANDATORY]",
        "12_odo_final_arrival": "12. Punjab Arrival Final Odometer [MANDATORY]",
        "08_group_return": "08. Return Group Photo (Final Stop) [MANDATORY]"
    }
}

ALL_KEYS = [k for group in PHOTO_SCHEMA.values() for k in group.keys()]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fleet_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_no TEXT,
            trip_date TEXT,
            photo_key TEXT,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bus_no, trip_date, photo_key) ON CONFLICT REPLACE
        );
    """)
    return conn


def save_image(file, bus_no, trip_date, photo_key):
    clean_bus = bus_no.strip().replace(" ", "_").upper()
    target_dir = os.path.join(DATA_DIR, str(trip_date), clean_bus)
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, f"{photo_key}.jpg")
    img = Image.open(file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(file_path, "JPEG", quality=85)

    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO fleet_uploads (bus_no, trip_date, photo_key, file_path) VALUES (?, ?, ?, ?)",
            (clean_bus, str(trip_date), photo_key, file_path)
        )
    conn.close()


def build_zip(target_date):
    date_path = os.path.join(DATA_DIR, str(target_date))
    zip_buffer = io.BytesIO()
    if os.path.exists(date_path):
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(date_path):
                for f in files:
                    fp = os.path.join(root, f)
                    zf.write(fp, os.path.relpath(fp, DATA_DIR))
    zip_buffer.seek(0)
    return zip_buffer


# Main UI
st.title("🚌 Tirth Yatra Fleet Reporting & Photo Audit")

tab_upload, tab_dashboard = st.tabs(
    ["📸 Conductor / Driver Portal", "📊 Admin Audit & ZIP Export"])

# Tab 1: Driver Upload Form
with tab_upload:
    st.info("⚠️ **Important:** All photos must be taken with **GPS Map Camera** showing location, date, and Bus Number.")

    col1, col2 = st.columns(2)
    with col1:
        bus_input = st.text_input(
            "Enter Full Bus Number (e.g., AR 20 A 6004)", placeholder="AR 20 A 6004").upper()
    with col2:
        departure_date = st.date_input(
            "Trip Departure Date", value=date.today())

    selected_stage = st.radio("Select Reporting Stage", list(
        PHOTO_SCHEMA.keys()), horizontal=True)
    st.markdown("---")

    slots = PHOTO_SCHEMA[selected_stage]
    files_to_upload = {}

    for key, label in slots.items():
        files_to_upload[key] = st.file_uploader(
            label, type=["jpg", "jpeg", "png"], key=f"{bus_input}_{key}")

    if st.button("📤 Submit Milestone Photos", type="primary", use_container_width=True):
        if not bus_input.strip():
            st.error("Please enter the Bus Number before submitting.")
        else:
            saved = 0
            for k, f in files_to_upload.items():
                if f is not None:
                    save_image(f, bus_input, departure_date, k)
                    saved += 1
            if saved > 0:
                st.success(
                    f"Successfully saved {saved} photo(s) for {bus_input}!")
            else:
                st.warning("Please select at least one photo to upload.")

# Tab 2: Admin Dashboard
with tab_dashboard:
    col_filter, col_download = st.columns([2, 2])
    with col_filter:
        audit_date = st.date_input(
            "View Departure Batch", value=date.today() - timedelta(days=2))

    conn = get_db()
    df = pd.read_sql(
        "SELECT bus_no, photo_key, file_path, uploaded_at FROM fleet_uploads WHERE trip_date = ?",
        conn,
        params=(str(audit_date),)
    )
    conn.close()

    with col_download:
        zip_file = build_zip(audit_date)
        st.download_button(
            label=f"📥 Download All Photos for Batch {audit_date} (.ZIP)",
            data=zip_file,
            file_name=f"TirthYatra_Batch_{audit_date}.zip",
            mime="application/zip",
            use_container_width=True
        )

    st.markdown("---")

    if df.empty:
        st.warning(f"No records found for departure batch {audit_date}.")
    else:
        buses = sorted(df["bus_no"].unique())
        matrix = []

        for b in buses:
            b_data = df[df["bus_no"] == b]
            keys = set(b_data["photo_key"].tolist())

            row = {"Bus Number": b}
            row["Start Odo (#9)"] = "✅" if "09_odo_departure" in keys else "❌"
            row["Dest Odo (#10)"] = "✅" if "10_odo_dest_arrival" in keys else "❌"
            row["Return Start (#11)"] = "✅" if "11_odo_return_start" in keys else "❌"
            row["Return Arr (#12)"] = "✅" if "12_odo_final_arrival" in keys else "❌"
            row["Glass/Refresh (#4)"] = "✅" if "04_glass_refreshment" in keys else "❌"
            row["Meals Logged"] = sum(
                1 for m in ["03_breakfast", "05_lunch", "06_hitea", "07_dinner"] if m in keys)
            row["Total Uploaded"] = f"{len(keys)} / 13"

            odos_done = all(k in keys for k in [
                            "09_odo_departure", "10_odo_dest_arrival", "11_odo_return_start", "12_odo_final_arrival"])
            if odos_done and "04_glass_refreshment" in keys:
                row["Status"] = "🟢 Complete"
            elif "09_odo_departure" not in keys:
                row["Status"] = "🔴 No Start Odo"
            elif not odos_done:
                row["Status"] = "🟡 In Transit / Odo Missing"
            else:
                row["Status"] = "🟠 Missing Refreshment"

            matrix.append(row)

        st.dataframe(pd.DataFrame(matrix),
                     use_container_width=True, hide_index=True)

        st.markdown("### 🔍 Bus Photo Audit Gallery")
        sel_inspect_bus = st.selectbox("Select Bus to Review", buses)
        bus_photos = df[df["bus_no"] == sel_inspect_bus]

        gallery_cols = st.columns(4)
        for idx, (_, p_row) in enumerate(bus_photos.iterrows()):
            if os.path.exists(p_row["file_path"]):
                with gallery_cols[idx % 4]:
                    img = Image.open(p_row["file_path"])
                    st.image(
                        img, caption=f"{p_row['photo_key']}", use_container_width=True)
