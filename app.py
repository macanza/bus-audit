import streamlit as st
import os
import io
import zipfile
import urllib.parse
from datetime import date, datetime, timedelta
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="Tirth Yatra Fleet Audit",
                   layout="wide", page_icon="🚌")

STORAGE_DIR = "Bus_Folders"
os.makedirs(STORAGE_DIR, exist_ok=True)

# -------------------------------------------------------------
# Session State & Reset Helper
# -------------------------------------------------------------
if "bus_form_key" not in st.session_state:
    st.session_state["bus_form_key"] = 0


def start_new_bus():
    st.session_state["bus_form_key"] += 1
    st.session_state.pop("last_submission", None)
    st.rerun()


fk = st.session_state["bus_form_key"]

# -------------------------------------------------------------
# High-Definition PDF Engine (Embeds All Images)
# -------------------------------------------------------------


def build_pdf_with_all_photos(bus, guide, start_d, end_d, photo_records):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    # --- Page 1: Official Summary Cover Sheet ---
    pdf.setFillColor(colors.HexColor("#0D47A1"))
    pdf.rect(0, page_h - 75, page_w, 75, fill=True, stroke=False)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(30, page_h - 40, "MUKH MANTRI TIRTH YATRA SCHEME")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(30, page_h - 60,
                   "Official Transport Department Photo Verification Dossier")

    # Metadata Card
    pdf.setFillColor(colors.HexColor("#F0F4F8"))
    pdf.roundRect(30, page_h - 225, page_w - 60,
                  130, 6, fill=True, stroke=False)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(45, page_h - 120, f"BUS NUMBER: {bus}")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(45, page_h - 145, f"Conductor / Team Guide: {guide}")
    pdf.drawString(45, page_h - 170, f"Trip Duration: {start_d}  to  {end_d}")
    pdf.drawString(45, page_h - 195,
                   f"Total Photos Verified & Attached: {len(photo_records)}")
    pdf.drawString(320, page_h - 195,
                   f"Date: {datetime.now().strftime('%d-%b-%Y, %I:%M %p')}")

    # Checklist Table
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(30, page_h - 255, "Verified Photo Manifest:")
    y = page_h - 280
    for idx, item in enumerate(photo_records, 1):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(35, y, f"✓ [{idx:02d}] {item['label']}")
        y -= 18
        if y < 60:
            break

    pdf.showPage()

    # --- Pages 2+: 2 Photos per Page (Large & Clear for Meter Numbers) ---
    for i in range(0, len(photo_records), 2):
        # Header banner
        pdf.setFillColor(colors.HexColor("#0D47A1"))
        pdf.rect(0, page_h - 40, page_w, 40, fill=True, stroke=False)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(25, page_h - 25, f"BUS: {bus} | FLEET AUDIT DOSSIER")
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(page_w - 25, page_h - 25,
                            f"Page {pdf.getPageNumber()}")

        batch = photo_records[i:i+2]
        slots = [
            (30, page_h - 410, page_w - 60, 350),  # Top slot
            (30, 40, page_w - 60, 350)             # Bottom slot
        ]

        for s_idx, photo in enumerate(batch):
            bx, by, bw, bh = slots[s_idx]

            # Border Card
            pdf.setFillColor(colors.HexColor("#FAFAFA"))
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.roundRect(bx, by, bw, bh, 6, fill=True, stroke=True)

            # Label Header inside Card
            pdf.setFillColor(colors.HexColor("#263238"))
            pdf.rect(bx, by + bh - 26, bw, 26, fill=True, stroke=False)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(bx + 12, by + bh - 18, photo["label"][:50])

            # Draw Image
            try:
                if os.path.exists(photo["path"]):
                    with Image.open(photo["path"]) as p_img:
                        p_img = ImageOps.exif_transpose(p_img)
                        if p_img.mode in ("RGBA", "P"):
                            p_img = p_img.convert("RGB")

                        max_w = bw - 20
                        max_h = bh - 40
                        img_w, img_h = p_img.size
                        ratio = min(max_w / img_w, max_h / img_h)
                        dest_w = img_w * ratio
                        dest_h = img_h * ratio
                        dest_x = bx + 10 + (max_w - dest_w) / 2
                        dest_y = by + 10 + (max_h - dest_h) / 2

                        img_buf = io.BytesIO()
                        p_img.save(img_buf, format="JPEG", quality=85)
                        img_buf.seek(0)
                        pdf.drawImage(ImageReader(img_buf), dest_x,
                                      dest_y, width=dest_w, height=dest_h)
            except Exception as err:
                pdf.setFillColor(colors.red)
                pdf.setFont("Helvetica", 10)
                pdf.drawString(bx + 20, by + bh / 2,
                               f"Render Error: {str(err)}")

        pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer


def create_folder_zip(folder_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for f in files:
                fp = os.path.join(root, f)
                zf.write(fp, os.path.relpath(fp, folder_path))
    zip_buffer.seek(0)
    return zip_buffer


# -------------------------------------------------------------
# Top Navigation & Add New Bus Button
# -------------------------------------------------------------
c_head, c_new_bus = st.columns([3, 1])
with c_head:
    st.title("🚌 Tirth Yatra Photo Portal")
with c_new_bus:
    st.write("")
    if st.button("➕ ADD NEW BUS (CLEAR ALL)", type="primary", use_container_width=True):
        start_new_bus()

# Show Success Bar if Bus was saved
if "last_submission" in st.session_state:
    sub = st.session_state["last_submission"]
    st.success(
        f"✅ **{sub['bus_no']}** Saved with **{sub['total_saved']} Photos**!")

    c1, c2, c3 = st.columns([1.5, 1.5, 1])
    with c1:
        st.download_button(
            label="📄 Download Photo PDF (With All Images)",
            data=sub["pdf_data"],
            file_name=f"{sub['bus_no']}_Full_Photo_Dossier.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with c2:
        st.link_button(
            label="📲 Share Verification on WhatsApp",
            url=sub["wa_url"],
            use_container_width=True
        )
    with c3:
        if st.button("Start Next Bus", key="start_next"):
            start_new_bus()
    st.divider()

# -------------------------------------------------------------
# Main Form (st.form)
# -------------------------------------------------------------
with st.form("main_trip_form", clear_on_submit=False):
    st.subheader("📝 Bus Details & Milestones")

    col_b, col_g = st.columns(2)
    with col_b:
        bus_input = st.text_input(
            "Enter Bus Number", placeholder="e.g. AR 20 A 6004 or PB 03 X 1234", key=f"bus_{fk}").strip().upper()
    with col_g:
        guide_input = st.text_input(
            "Conductor / Team Guide Name", placeholder="e.g. Gurpreet Singh", key=f"guide_{fk}").strip()

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        trip_start = st.date_input(
            "Trip Start Date", value=date.today(), key=f"d1_{fk}")
    with col_d2:
        trip_end = st.date_input(
            "Trip End Date", value=date.today() + timedelta(days=3), key=f"d2_{fk}")

    st.markdown("---")

    # 1. Odometers
    st.markdown("#### ⏱️ 1. Odometer Photos (4 Photos Required)")
    st.caption(
        "Upload Punjab Departure, Destination Arrival, Return Departure, and Final Arrival meter readings.")
    odo_uploads = st.file_uploader(
        "Select Odometer Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"odo_{fk}"
    )

    st.markdown("---")

    # 2. Group Photos
    st.markdown("#### 👥 2. Yatri Group Photos (4 Photos Required)")
    st.caption(
        "Upload Banner Photo, Inside Cabin Photo, Return Group Photo, and MLA/VIP Photo.")
    group_uploads = st.file_uploader(
        "Select Group Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"grp_{fk}"
    )

    st.markdown("---")

    # 3. Steel Glass & Refreshments
    st.markdown("#### 🥤 3. Steel Glass & Refreshment Distribution")
    dist_uploads = st.file_uploader(
        "Select Distribution Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"dist_{fk}"
    )

    st.markdown("---")

    # 4. Meals
    st.markdown("#### 🍽️ 4. Passenger Meals (Breakfast, Lunch, Dinner)")
    meal_uploads = st.file_uploader(
        "Select Meals Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"meal_{fk}"
    )

    st.markdown("---")
    submitted = st.form_submit_button(
        "💾 SAVE ALL PHOTOS & BUILD FULL PDF DOSSIER", type="primary", use_container_width=True)

# -------------------------------------------------------------
# Submission Handler
# -------------------------------------------------------------
if submitted:
    if not bus_input:
        st.error("❌ Please enter the Bus Number first!")
    elif not guide_input:
        st.error("❌ Please enter the Conductor / Guide Name!")
    elif not odo_uploads and not group_uploads and not dist_uploads and not meal_uploads:
        st.error(
            "❌ No photos selected, or files are still uploading. Please wait for files to show completely.")
    else:
        with st.spinner("⚡ Resizing photos and building multi-page Photo PDF..."):
            bus_clean = bus_input.replace(" ", "_")
            batch_folder = f"{trip_start}_to_{trip_end}"
            save_path = os.path.join(STORAGE_DIR, batch_folder, bus_clean)
            os.makedirs(save_path, exist_ok=True)

            photo_manifest = []

            def save_images(files, category, label_list):
                for idx, f in enumerate(files, start=1):
                    with Image.open(f) as img:
                        img = ImageOps.exif_transpose(img)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                        f_name = f"{category}_{idx}.jpg"
                        full_p = os.path.join(save_path, f_name)
                        img.save(full_p, "JPEG", quality=82, optimize=True)
                        lbl = label_list[idx-1] if idx - \
                            1 < len(label_list) else f"{category} #{idx}"
                        photo_manifest.append({"label": lbl, "path": full_p})

            save_images(odo_uploads, "01_Odometer", [
                "1. Punjab Departure Odometer Reading",
                "2. Destination Arrival Odometer Reading",
                "3. Return Start Odometer Reading",
                "4. Punjab Final Arrival Odometer Reading"
            ])
            save_images(group_uploads, "02_Group", [
                "1. Departure Banner Group Photo",
                "2. Inside Cabin Yatri Group Photo",
                "3. Destination Return Group Photo",
                "4. MLA / VIP Group Photo"
            ])
            save_images(dist_uploads, "03_Distribution", [
                "1. Steel Glass Distribution Photo",
                "2. Refreshment Distribution Photo"
            ])
            save_images(meal_uploads, "04_Meals", [
                "1. Breakfast Photo",
                "2. Lunch Photo",
                "3. Dinner Photo"
            ])

            # Generate PDF with embedded photos
            pdf_bytes = build_pdf_with_all_photos(
                bus_input, guide_input, trip_start, trip_end, photo_manifest)

            # Generate WhatsApp text
            wa_text = (
                f"🚌 *MUKH MANTRI TIRTH YATRA REPORT*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Bus Number:* {bus_input}\n"
                f"👤 *Team Guide:* {guide_input}\n"
                f"📅 *Dates:* {trip_start} to {trip_end}\n"
                f"📸 *Photos Logged:* {len(photo_manifest)} Photos Verified\n"
                f"✅ Full Photo PDF Dossier Generated.\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"

            st.session_state["last_submission"] = {
                "bus_no": bus_input,
                "total_saved": len(photo_manifest),
                "pdf_data": pdf_bytes,
                "wa_url": wa_url
            }
            st.rerun()

# -------------------------------------------------------------
# Section: Live Bus Folders on Server
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📁 Saved Bus Folders on Server")

batches = [d for d in os.listdir(STORAGE_DIR) if os.path.isdir(
    os.path.join(STORAGE_DIR, d))]
if not batches:
    st.info("No bus folders created yet. Upload your first bus above.")
else:
    for b_batch in sorted(batches, reverse=True):
        batch_full = os.path.join(STORAGE_DIR, b_batch)
        buses = [b for b in os.listdir(batch_full) if os.path.isdir(
            os.path.join(batch_full, b))]

        with st.expander(f"🗓️ Batch: {b_batch} ({len(buses)} Buses Completed)", expanded=True):
            cols = st.columns(3)
            for i, b_name in enumerate(sorted(buses)):
                bus_dir = os.path.join(batch_full, b_name)
                photo_count = len(
                    [f for f in os.listdir(bus_dir) if f.endswith('.jpg')])
                with cols[i % 3]:
                    st.write(f"🚌 **{b_name}** ({photo_count} photos)")
                    zip_data = create_folder_zip(bus_dir)
                    st.download_button(
                        label=f"📥 Download {b_name} (.ZIP)",
                        data=zip_data,
                        file_name=f"{b_name}_Photos.zip",
                        mime="application/zip",
                        key=f"dl_{b_batch}_{b_name}"
                    )
