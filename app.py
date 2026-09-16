import streamlit as st
import streamlit.components.v1 as components
import os
import io
import zipfile
import base64
from datetime import date, datetime, timedelta
from PIL import Image, ImageDraw, ImageOps

st.set_page_config(page_title="Tirth Yatra Fleet Portal",
                   layout="wide", page_icon="🚌")

STORAGE_DIR = "Bus_Folders"
GUIDE_IMAGE_PATH = "guide.jpg"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Session tracking for clean bus resets
if "bus_counter" not in st.session_state:
    st.session_state["bus_counter"] = 0


def reset_for_next_bus():
    st.session_state["bus_counter"] += 1
    st.session_state.pop("latest_submission", None)
    st.rerun()


curr_id = st.session_state["bus_counter"]

# Poster Crop Coordinates


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


CROP_ODO = (0.015, 0.545, 0.250, 0.680)
CROP_GROUP = (0.015, 0.208, 0.255, 0.350)
CROP_GLASS = (0.745, 0.208, 0.985, 0.350)
CROP_MEAL = (0.015, 0.360, 0.255, 0.500)

# Multi-page PDF Compiler supporting Bus 1 and Optional Bus 2


def build_photo_pdf(bus_no, bus_no2, guide, start_d, end_d, photo_items):
    pages = []
    bus_display = f"{bus_no} + {bus_no2}" if bus_no2 else bus_no

    # Cover / Audit Sheet
    cover = Image.new("RGB", (1240, 1754), color=(248, 249, 250))
    d = ImageDraw.Draw(cover)
    d.rectangle([(0, 0), (1240, 160)], fill=(26, 35, 126))
    d.text((50, 45), "MUKH MANTRI TIRTH YATRA REPORT", fill=(255, 255, 255))
    d.text((50, 100), "Transport Department - Fleet Photographic Audit Dossier",
           fill=(197, 202, 233))

    d.rectangle([(50, 200), (1190, 520)], fill=(
        255, 255, 255), outline=(220, 220, 220), width=2)
    info_text = (
        f"START BUS (BUS 1)   : {bus_no}\n\n"
        f"CHANGED BUS (BUS 2) : {bus_no2 if bus_no2 else 'N/A (Same Bus throughout trip)'}\n\n"
        f"TEAM GUIDE / COND.  : {guide}\n\n"
        f"TRIP DURATION       : {start_d} to {end_d}\n\n"
        f"TOTAL PHOTOS LOGGED : {len(photo_items)} Verified Images\n\n"
        f"TIMESTAMP           : {datetime.now().strftime('%d-%b-%Y %I:%M %p')}"
    )
    d.text((80, 230), info_text, fill=(33, 33, 33))

    d.text((50, 560), "DOCUMENTED MILESTONE CHECKPOINTS:", fill=(26, 35, 126))
    y = 610
    for idx, item in enumerate(photo_items, 1):
        d.text((70, y), f"[{idx:02d}]  {item['label']}", fill=(66, 66, 66))
        y += 40
        if y > 1650:
            break
    pages.append(cover)

    # Subsequent Pages: Full-size Photo with Header
    for item in photo_items:
        try:
            with Image.open(item["path"]) as raw:
                img = ImageOps.exif_transpose(raw)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                p = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
                p_draw = ImageDraw.Draw(p)
                p_draw.rectangle([(0, 0), (1240, 90)], fill=(38, 50, 56))
                p_draw.text(
                    (40, 30), f"{bus_display}  |  {item['label'].upper()}", fill=(255, 255, 255))

                img.thumbnail((1160, 1580), Image.Resampling.LANCZOS)
                pos_x = (1240 - img.width) // 2
                pos_y = 100 + (1620 - img.height) // 2
                p.paste(img, (pos_x, pos_y))
                pages.append(p)
        except Exception:
            continue

    buf = io.BytesIO()
    if pages:
        pages[0].save(buf, format="PDF", save_all=True,
                      append_images=pages[1:], resolution=100.0)
    buf.seek(0)
    return buf


def zip_folder(folder):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for f in files:
                p = os.path.join(root, f)
                zf.write(p, os.path.relpath(p, folder))
    buf.seek(0)
    return buf


# -------------------------------------------------------------
# TOP NAVIGATION & RESET
# -------------------------------------------------------------
col_title, col_new = st.columns([3, 1.2])
with col_title:
    st.title("🚌 Tirth Yatra Photo Portal")
with col_new:
    st.write("")
    if st.button("➕ START NEXT BUS (CLEAR)", type="primary", use_container_width=True):
        reset_for_next_bus()

# Poster upload check
if not os.path.exists(GUIDE_IMAGE_PATH):
    with st.expander("📌 First Time Setup: Upload Poster for Reference Photos"):
        up_poster = st.file_uploader("Upload Guide Poster (guide.jpg)", type=[
                                     "jpg", "png", "jpeg"], key="setup_poster")
        if up_poster:
            with open(GUIDE_IMAGE_PATH, "wb") as f:
                f.write(up_poster.getbuffer())
            st.success("Reference images activated!")
            st.rerun()

# -------------------------------------------------------------
# SUBMISSION BANNER (WITH NATIVE WHATSAPP PDF SHARE)
# -------------------------------------------------------------
if "latest_submission" in st.session_state:
    sub = st.session_state["latest_submission"]
    st.success(
        f"🎉 **{sub['bus']}** saved successfully with **{sub['count']} photos**!")

    b64_pdf = base64.b64encode(sub['pdf_bytes']).decode('utf-8')
    pdf_fname = f"{sub['bus'].replace('/', '_')}_Complete_Photo_Report.pdf"

    # Native Mobile Share Sheet Component
    share_button_html = f"""
    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
        <button id="shareBtn" style="
            background-color: #25D366; 
            color: white; 
            border: none; 
            padding: 14px 20px; 
            border-radius: 8px; 
            font-size: 16px; 
            font-weight: bold; 
            cursor: pointer; 
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;">
            📲 Share Full PDF via WhatsApp
        </button>
    </div>
    <script>
    document.getElementById('shareBtn').addEventListener('click', async () => {{
        try {{
            const b64 = "{b64_pdf}";
            const byteChars = atob(b64);
            const byteNums = new Array(byteChars.length);
            for (let i = 0; i < byteChars.length; i++) {{
                byteNums[i] = byteChars.charCodeAt(i);
            }}
            const file = new File([new Uint8Array(byteNums)], "{pdf_fname}", {{ type: "application/pdf" }});
            
            if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                await navigator.share({{
                    files: [file],
                    title: "{pdf_fname}",
                    text: "🚌 Mukh Mantri Tirth Yatra - Complete Photo Dossier for {sub['bus']}"
                }});
            }} else {{
                alert("Please tap Download PDF below, then attach it to WhatsApp.");
            }}
        }} catch (err) {{
            console.log("Share canceled or failed", err);
        }}
    }});
    </script>
    """
    components.html(share_button_html, height=65)

    c_d1, c_d2 = st.columns(2)
    with c_d1:
        st.download_button(
            label="📄 Download PDF Directly",
            data=sub['pdf_bytes'],
            file_name=pdf_fname,
            mime="application/pdf",
            use_container_width=True
        )
    with c_d2:
        st.download_button(
            label="📦 Download ZIP Folder",
            data=sub['zip_bytes'],
            file_name=f"{sub['bus'].replace('/', '_')}_photos.zip",
            mime="application/zip",
            use_container_width=True
        )
    st.divider()

# -------------------------------------------------------------
# FORM INPUTS
# -------------------------------------------------------------
with st.form(f"bus_form_{curr_id}", clear_on_submit=False):
    st.subheader("📝 Bus Details")

    # Bus 1 (Required) and Bus 2 (Optional)
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        in_bus = st.text_input("Bus Number (Bus 1 - Departure) *",
                               placeholder="e.g. AR 20 A 6004", key=f"bus_{curr_id}").strip().upper()
    with c_b2:
        in_bus2 = st.text_input("Bus 2 Number (Optional - If Bus Changed Mid-Trip)",
                                placeholder="e.g. PB 03 X 1234 (Leave blank if not changed)", key=f"bus2_{curr_id}").strip().upper()

    c_g, c_s, c_e = st.columns([1.5, 1, 1])
    with c_g:
        in_guide = st.text_input("Team Guide / Conductor Name *",
                                 placeholder="e.g. Gurpreet Singh", key=f"guide_{curr_id}").strip()
    with c_s:
        in_sdate = st.date_input(
            "Trip Start Date", value=date.today(), key=f"sd_{curr_id}")
    with c_e:
        in_edate = st.date_input(
            "Trip End Date", value=date.today() + timedelta(days=3), key=f"ed_{curr_id}")

    st.markdown("---")

    # 1. ODOMETER
    st.subheader("⏱️ 1. Odometer Photos (4 Required)")
    odo_caption = "Punjab Start (Bus 1) ➔ Destination Arrival (Bus 1) ➔ Return Start (Bus 2) ➔ Punjab Arrival (Bus 2)" if in_bus2 else "Punjab Start ➔ Destination Arrival ➔ Return Start ➔ Punjab Arrival"
    st.caption(odo_caption)
    r1, u1 = st.columns([1, 3])
    with r1:
        g_odo = get_cropped_guide(CROP_ODO)
        if g_odo:
            st.image(g_odo, caption="Reference: Odometer (Bus 1 & Bus 2)",
                     use_container_width=True)
    with u1:
        f_odo = st.file_uploader("Select 4 Odometers (Bus 1 & Bus 2)", type=[
                                 "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"f_odo_{curr_id}")

    st.markdown("---")

    # 2. GROUP PHOTOS
    st.subheader("👥 2. Yatri Group Photos (4 Required)")
    st.caption("Departure Banner ➔ Inside Cabin ➔ Return Group ➔ MLA / VIP Group")
    r2, u2 = st.columns([1, 3])
    with r2:
        g_grp = get_cropped_guide(CROP_GROUP)
        if g_grp:
            st.image(g_grp, caption="Reference: Group Photo",
                     use_container_width=True)
    with u2:
        f_grp = st.file_uploader("Select 4 Group Photos", type=[
                                 "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"f_grp_{curr_id}")

    st.markdown("---")

    # 3. DISTRIBUTION
    st.subheader("🥤 3. Steel Glass & Refreshments")
    st.caption("Steel Glass & tea/refreshment service")
    r3, u3 = st.columns([1, 3])
    with r3:
        g_gla = get_cropped_guide(CROP_GLASS)
        if g_gla:
            st.image(g_gla, caption="Reference: Glass / Refreshment",
                     use_container_width=True)
    with u3:
        f_dst = st.file_uploader("Select Distribution Photos", type=[
                                 "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"f_dst_{curr_id}")

    st.markdown("---")

    # 4. MEALS
    st.subheader("🍽️ 4. Passenger Meals")
    st.caption("Breakfast, Lunch, Dinner, or Hi-Tea")
    r4, u4 = st.columns([1, 3])
    with r4:
        g_mel = get_cropped_guide(CROP_MEAL)
        if g_mel:
            st.image(g_mel, caption="Reference: Meals",
                     use_container_width=True)
    with u4:
        f_mel = st.file_uploader("Select Meal Photos", type=[
                                 "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"f_mel_{curr_id}")

    st.markdown("---")
    save_trigger = st.form_submit_button(
        "💾 SAVE ALL PHOTOS & BUILD PHOTO PDF", type="primary", use_container_width=True)

if save_trigger:
    if not in_bus:
        st.error("❌ Please enter Primary Bus Number (Bus 1).")
    elif not in_guide:
        st.error("❌ Please enter the Team Guide Name.")
    elif not f_odo and not f_grp and not f_dst and not f_mel:
        st.error("❌ No photos selected! Please pick photos before saving.")
    else:
        with st.spinner("⏳ Compiling images into high-resolution PDF..."):
            folder_bus_name = f"{in_bus}_changed_to_{in_bus2}" if in_bus2 else in_bus
            clean_folder_name = folder_bus_name.replace(" ", "_")
            batch_tag = f"{in_sdate}_to_{in_edate}"
            bus_dest = os.path.join(STORAGE_DIR, batch_tag, clean_folder_name)
            os.makedirs(bus_dest, exist_ok=True)

            manifest = []

            def persist(files, prefix, tags):
                for idx, item in enumerate(files, 1):
                    with Image.open(item) as im:
                        im = ImageOps.exif_transpose(im)
                        if im.mode in ("RGBA", "P"):
                            im = im.convert("RGB")
                        im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                        path = os.path.join(bus_dest, f"{prefix}_{idx}.jpg")
                        im.save(path, "JPEG", quality=85)
                        lbl = tags[idx-1] if idx - \
                            1 < len(tags) else f"{prefix} #{idx}"
                        manifest.append({"label": lbl, "path": path})

            # Specific tags matching the poster's Bus 1 / Bus 2 odometer structure
            odo_labels = [
                f"9. Punjab Departure Odometer ({in_bus})",
                f"10. Destination Arrival Odometer ({in_bus})",
                f"11. Return Start Odometer ({in_bus2 if in_bus2 else in_bus})",
                f"12. Punjab Final Arrival Odometer ({in_bus2 if in_bus2 else in_bus})"
            ]

            persist(f_odo, "01_Odometer", odo_labels)
            persist(f_grp, "02_Group", ["1. Departure Banner Group", "2. Inside Cabin Yatri Group",
                    "3. Destination Return Group", "4. MLA / VIP Group Photo"])
            persist(f_dst, "03_Distribution", [
                    "1. Steel Glass Distribution", "2. Refreshment Distribution"])
            persist(f_mel, "04_Meals", [
                    "1. Breakfast Photo", "2. Lunch Photo", "3. Dinner Photo"])

            pdf_out = build_photo_pdf(
                in_bus, in_bus2, in_guide, in_sdate, in_edate, manifest)
            zip_out = zip_folder(bus_dest)

            display_title = f"{in_bus} (Return: {in_bus2})" if in_bus2 else in_bus

            st.session_state["latest_submission"] = {
                "bus": display_title,
                "count": len(manifest),
                "pdf_bytes": pdf_out.getvalue(),
                "zip_bytes": zip_out.getvalue()
            }
            st.rerun()

# -------------------------------------------------------------
# FOLDER REPOSITORY EXPLORER
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📁 Saved Bus Folders on System")

batch_dirs = [d for d in os.listdir(
    STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, d))]
if not batch_dirs:
    st.caption("No buses logged yet.")
else:
    for b_batch in sorted(batch_dirs, reverse=True):
        b_path = os.path.join(STORAGE_DIR, b_batch)
        buses = [b for b in os.listdir(
            b_path) if os.path.isdir(os.path.join(b_path, b))]
        with st.expander(f"🗓️ Trip Batch: {b_batch} ({len(buses)} Buses Saved)", expanded=True):
            cols = st.columns(3)
            for idx, b_name in enumerate(sorted(buses)):
                target_p = os.path.join(b_path, b_name)
                pic_count = len([f for f in os.listdir(
                    target_p) if f.endswith('.jpg')])
                with cols[idx % 3]:
                    st.write(f"🚌 **{b_name}** ({pic_count} photos)")
                    z_data = zip_folder(target_p)
                    st.download_button(
                        label=f"📥 Download {b_name} (.ZIP)",
                        data=z_data,
                        file_name=f"{b_name}_{b_batch}.zip",
                        mime="application/zip",
                        key=f"zip_{b_batch}_{b_name}"
                    )
