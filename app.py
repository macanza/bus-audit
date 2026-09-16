import streamlit as st
import os
from datetime import date, datetime, timedelta
from PIL import Image

st.set_page_config(page_title="Tirth Yatra Photo Portal",
                   layout="wide", page_icon="🚌")

STORAGE_DIR = "Bus_Folders"
GUIDE_IMAGE_PATH = "guide.jpg"
os.makedirs(STORAGE_DIR, exist_ok=True)

# -------------------------------------------------------------
# Crop Single Sample Pictures From Poster
# -------------------------------------------------------------


def get_cropped_guide(crop_coords):
    if os.path.exists(GUIDE_IMAGE_PATH):
        try:
            with Image.open(GUIDE_IMAGE_PATH) as img:
                w, h = img.size
                box = (
                    int(crop_coords[0] * w),
                    int(crop_coords[1] * h),
                    int(crop_coords[2] * w),
                    int(crop_coords[3] * h)
                )
                return img.crop(box)
        except Exception:
            return None
    return None


CROP_ODO = (0.015, 0.545, 0.250, 0.680)   # Departure Odometer (#9)
CROP_GROUP = (0.015, 0.208, 0.255, 0.350)  # Departure Group (#1)
CROP_GLASS = (0.745, 0.208, 0.985, 0.350)  # Refreshment & Glass (#4)
CROP_MEAL = (0.015, 0.360, 0.255, 0.500)  # Meal / Lunch (#5)

# -------------------------------------------------------------
# Top Header & Trip Details
# -------------------------------------------------------------
st.title("🚌 Tirth Yatra - Quick Photo Upload")
st.info("⚠️ **Rules:** All photos must be taken with **GPS Map Camera** showing location and the complete Bus Number.")

# One-time poster upload fallback
if not os.path.exists(GUIDE_IMAGE_PATH):
    st.warning("📌 Upload the poster once below to load reference images:")
    uploaded_poster = st.file_uploader("Upload Guide Poster", type=[
                                       "jpg", "png", "jpeg"], key="setup_guide")
    if uploaded_poster:
        with open(GUIDE_IMAGE_PATH, "wb") as f:
            f.write(uploaded_poster.getbuffer())
        st.rerun()

# Row 1: Bus Numbers (Initial and Replacement)
col_b1, col_b2 = st.columns(2)
with col_b1:
    bus_no = st.text_input("Start Bus Number (Bus 1)",
                           placeholder="e.g. AR 20 A 6004").strip().upper()
with col_b2:
    new_bus_no = st.text_input("New / Return Bus Number (Bus 2 - Optional)",
                               placeholder="Fill only if bus changed mid-trip").strip().upper()

# Row 2: Conductor & Dates
col_g, col_d1, col_d2 = st.columns([2, 1, 1])
with col_g:
    team_guide = st.text_input(
        "Team Guide Name", placeholder="e.g. Gurpreet Singh").strip()
with col_d1:
    trip_start = st.date_input("Trip Start Date", value=date.today())
with col_d2:
    trip_end = st.date_input(
        "Trip End Date", value=date.today() + timedelta(days=3))

st.divider()

# =============================================================
# 1. ODOMETER PHOTOS (4 REQUIRED)
# =============================================================
st.subheader("⏱️ 1. Odometer Photos (4 Photos Required)")
st.caption(
    "Punjab Start (Bus 1) ➔ Dest Arrival (Bus 1) ➔ Return Start (Bus 2) ➔ Punjab Arrival (Bus 2)")

col_ref1, col_box1 = st.columns([1, 3])
with col_ref1:
    odo_guide = get_cropped_guide(CROP_ODO)
    if odo_guide:
        st.image(odo_guide, caption="Reference: Odometer",
                 use_container_width=True)

with col_box1:
    odo_files = st.file_uploader(
        "Upload All 4 Odometer Photos Here",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="batch_odo"
    )
    if len(odo_files) > 4:
        st.error(
            f"❌ Too many! Only 4 photos allowed (Selected: {len(odo_files)}).")
    elif len(odo_files) == 4:
        st.success("✅ Exactly 4 Odometer photos selected.")
    if odo_files:
        p_cols = st.columns(min(len(odo_files), 4))
        for i, f in enumerate(odo_files[:4]):
            p_cols[i].image(f, caption=f"Odo {i+1}", use_container_width=True)

st.divider()

# =============================================================
# 2. YATRI GROUP PHOTOS (4 REQUIRED)
# =============================================================
st.subheader("👥 2. Yatri Group Photos (4 Photos Required)")
st.caption("Departure Banner ➔ Inside Cabin ➔ Return Group ➔ MLA/VIP Group")

col_ref2, col_box2 = st.columns([1, 3])
with col_ref2:
    grp_guide = get_cropped_guide(CROP_GROUP)
    if grp_guide:
        st.image(grp_guide, caption="Reference: Group Photo",
                 use_container_width=True)

with col_box2:
    group_files = st.file_uploader(
        "Upload All 4 Yatri Group Photos Here",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="batch_group"
    )
    if len(group_files) > 4:
        st.error(
            f"❌ Too many! Only 4 photos allowed (Selected: {len(group_files)}).")
    elif len(group_files) == 4:
        st.success("✅ Exactly 4 Group photos selected.")
    if group_files:
        p_cols = st.columns(min(len(group_files), 4))
        for i, f in enumerate(group_files[:4]):
            p_cols[i].image(
                f, caption=f"Group {i+1}", use_container_width=True)

st.divider()

# =============================================================
# 3. DISTRIBUTION PHOTOS (GLASS & REFRESHMENTS)
# =============================================================
st.subheader("🥤 3. Glass & Refreshment Distribution")
st.caption("Steel glass distribution & tea/snack service inside the bus")

col_ref3, col_box3 = st.columns([1, 3])
with col_ref3:
    glass_guide = get_cropped_guide(CROP_GLASS)
    if glass_guide:
        st.image(glass_guide, caption="Reference: Glass & Refreshment",
                 use_container_width=True)

with col_box3:
    dist_files = st.file_uploader(
        "Upload Distribution Photos (1 or 2 Photos)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="batch_dist"
    )
    if len(dist_files) > 2:
        st.error(f"❌ Maximum 2 photos allowed.")
    elif dist_files:
        p_cols = st.columns(min(len(dist_files), 2))
        for i, f in enumerate(dist_files[:2]):
            p_cols[i].image(
                f, caption=f"Distribution {i+1}", use_container_width=True)

st.divider()

# =============================================================
# 4. MEALS PHOTOS (BREAKFAST, LUNCH, DINNER)
# =============================================================
st.subheader("🍽️ 4. Passenger Meals")
st.caption("Breakfast, Lunch, Dinner, or Hi-Tea photos in one place")

col_ref4, col_box4 = st.columns([1, 3])
with col_ref4:
    meal_guide = get_cropped_guide(CROP_MEAL)
    if meal_guide:
        st.image(meal_guide, caption="Reference: Meals",
                 use_container_width=True)

with col_box4:
    meal_files = st.file_uploader(
        "Upload Meals Photos (Up to 3 Photos)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="batch_meals"
    )
    if len(meal_files) > 3:
        st.error(f"❌ Maximum 3 meal photos allowed.")
    elif meal_files:
        p_cols = st.columns(min(len(meal_files), 3))
        for i, f in enumerate(meal_files[:3]):
            p_cols[i].image(f, caption=f"Meal {i+1}", use_container_width=True)

st.divider()

# =============================================================
# SAVE BUTTON & DIRECT STORAGE
# =============================================================
if st.button("💾 SAVE ALL PHOTOS TO FOLDER", type="primary", use_container_width=True):
    if not bus_no:
        st.error("❌ Please type the Start Bus Number at the top before saving!")
    elif len(odo_files) > 4 or len(group_files) > 4 or len(dist_files) > 2 or len(meal_files) > 3:
        st.error("❌ Please check photo limits before saving.")
    else:
        # If changed, folder name will clearly show both (e.g., AR_20_A_6004_CHANGED_TO_PB_03_AB_1234)
        if new_bus_no:
            bus_folder_name = f"{bus_no.replace(' ', '_')}_CHANGED_TO_{new_bus_no.replace(' ', '_')}"
        else:
            bus_folder_name = bus_no.replace(" ", "_")

        batch_folder_name = f"{trip_start}_to_{trip_end}"
        bus_folder = os.path.join(
            STORAGE_DIR, batch_folder_name, bus_folder_name)
        os.makedirs(bus_folder, exist_ok=True)

        # Write trip_info.txt
        info_path = os.path.join(bus_folder, "trip_info.txt")
        with open(info_path, "w", encoding="utf-8") as f_info:
            f_info.write(f"START BUS NUMBER : {bus_no}\n")
            f_info.write(
                f"RETURN BUS NUMBER: {new_bus_no if new_bus_no else 'SAME AS START BUS'}\n")
            f_info.write(
                f"BUS CHANGED      : {'YES' if new_bus_no else 'NO'}\n")
            f_info.write(
                f"TEAM GUIDE       : {team_guide if team_guide else 'Not Specified'}\n")
            f_info.write(f"TRIP DURATION    : {trip_start} to {trip_end}\n")
            f_info.write(
                f"SUBMISSION TIME  : {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n")

        # Save files
        def save_files(files, prefix):
            cnt = 0
            for idx, uf in enumerate(files, start=1):
                img = Image.open(uf)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(os.path.join(
                    bus_folder, f"{prefix}_{idx}.jpg"), "JPEG", quality=85)
                cnt += 1
            return cnt

        saved_total = 0
        saved_total += save_files(odo_files[:4], "01_Odometer")
        saved_total += save_files(group_files[:4], "02_Yatri_Group")
        saved_total += save_files(dist_files[:2], "03_Distribution")
        saved_total += save_files(meal_files[:3], "04_Meals")

        if saved_total > 0:
            st.success(f"✅ Successfully saved {saved_total} photos!")
            st.info(f"""
            📁 **Folder Created:** `{bus_folder}`
            * **Departure Bus:** {bus_no}
            * **Return Bus:** {new_bus_no if new_bus_no else 'Same Bus'}
            * **Team Guide:** {team_guide if team_guide else 'N/A'}
            * **Duration:** {trip_start} to {trip_end}
            """)
        else:
            st.warning(
                "⚠️ No photos were selected. Please choose photos to save.")
