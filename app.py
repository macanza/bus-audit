import streamlit as st
import os
import io
import urllib.parse
from datetime import date, datetime, timedelta
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="Tirth Yatra Fleet Portal",
                   layout="wide", page_icon="🚌")

# -------------------------------------------------------------
# Session State for Resetting Form
# -------------------------------------------------------------
if "bus_key" not in st.session_state:
    st.session_state["bus_key"] = 0


def new_bus_reset():
    st.session_state["bus_key"] += 1
    st.session_state.pop("last_pdf", None)
    st.rerun()


bk = st.session_state["bus_key"]

# -------------------------------------------------------------
# PDF Engine: Embeds Every Image (2 Large Photos Per Page)
# -------------------------------------------------------------


def build_photo_pdf(bus, guide, start_d, end_d, photo_list):
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    pw, ph = A4

    # Page 1: Official Cover Sheet
    pdf.setFillColor(colors.HexColor("#0D47A1"))
    pdf.rect(0, ph - 70, pw, 70, fill=True, stroke=False)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(30, ph - 38, "MUKH MANTRI TIRTH YATRA SCHEME")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        30, ph - 58, "Punjab Transport Department | Fleet Milestone Verification Dossier")

    # Metadata Box
    pdf.setFillColor(colors.HexColor("#F0F4F8"))
    pdf.roundRect(30, ph - 210, pw - 60, 125, 6, fill=True, stroke=False)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(45, ph - 115, f"BUS REGISTRATION  : {bus}")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, ph - 140, f"Team Guide / Name : {guide}")
    pdf.drawString(45, ph - 162, f"Trip Journey Dates: {start_d}  to  {end_d}")
    pdf.drawString(
        45, ph - 184, f"Total Photos Attached: {len(photo_list)} Verified Images")
    pdf.drawString(
        330, ph - 184, f"Generated: {datetime.now().strftime('%d-%b-%Y, %I:%M %p')}")

    # Index Checklist
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(30, ph - 240, "Attached Milestone Photos Checklist:")
    y_pos = ph - 260
    for idx, item in enumerate(photo_list, 1):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(35, y_pos, f"✓ [{idx:02d}] {item['label']}")
        y_pos -= 17
        if y_pos < 50:
            break

    pdf.showPage()

    # Pages 2+: 2 Photos Per Page (Large size for clear odometer numbers)
    for i in range(0, len(photo_list), 2):
        # Header banner on image pages
        pdf.setFillColor(colors.HexColor("#0D47A1"))
        pdf.rect(0, ph - 35, pw, 35, fill=True, stroke=False)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(25, ph - 22, f"BUS: {bus} | TRIP PHOTO DOSSIER")
        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(pw - 25, ph - 22, f"Page {pdf.getPageNumber()}")

        batch = photo_list[i:i+2]
        slots = [
            (30, ph - 395, pw - 60, 345),  # Top Photo Box
            (30, 30, pw - 60, 345)         # Bottom Photo Box
        ]

        for s_idx, p_data in enumerate(batch):
            bx, by, bw, bh = slots[s_idx]

            # White Card with Border
            pdf.setFillColor(colors.HexColor("#FAFAFA"))
            pdf.setStrokeColor(colors.HexColor("#D0D7DE"))
            pdf.roundRect(bx, by, bw, bh, 6, fill=True, stroke=True)

            # Dark title strip inside card
            pdf.setFillColor(colors.HexColor("#263238"))
            pdf.rect(bx, by + bh - 24, bw, 24, fill=True, stroke=False)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(bx + 10, by + bh - 17, p_data["label"][:55])

            # Draw Image
            try:
                img = Image.open(p_data["file_obj"])
                # Prevents rotated/upside-down photos
                img = ImageOps.exif_transpose(img)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((1400, 1400), Image.Resampling.LANCZOS)

                max_w = bw - 20
                max_h = bh - 38
                iw, ih = img.size
                ratio = min(max_w / iw, max_h / ih)
                dest_w = iw * ratio
                dest_h = ih * ratio
                dest_x = bx + 10 + (max_w - dest_w) / 2
                dest_y = by + 8 + (max_h - dest_h) / 2

                img_stream = io.BytesIO()
                img.save(img_stream, format="JPEG", quality=80)
                img_stream.seek(0)
                pdf.drawImage(ImageReader(img_stream), dest_x,
                              dest_y, width=dest_w, height=dest_h)
            except Exception as e:
                pdf.setFillColor(colors.red)
                pdf.setFont("Helvetica", 9)
                pdf.drawString(bx + 15, by + bh / 2,
                               f"Error rendering photo: {e}")

        pdf.showPage()

    pdf.save()
    buf.seek(0)
    return buf


# -------------------------------------------------------------
# App Header & Controls
# -------------------------------------------------------------
col_h, col_reset = st.columns([3, 1])
with col_h:
    st.title("🚌 Tirth Yatra - Fleet Photo Portal")
with col_reset:
    st.write("")
    if st.button("➕ START NEW BUS (CLEAR ALL)", type="primary", use_container_width=True):
        new_bus_reset()

# Success Banner with Download & WhatsApp
if "last_pdf" in st.session_state:
    sub = st.session_state["last_pdf"]
    st.success(
        f"✅ Success! **{sub['bus']}** compiled with **{sub['total']} Photos** into PDF Dossier.")

    c_dl, c_wa = st.columns(2)
    with c_dl:
        st.download_button(
            label=f"📄 1. DOWNLOAD {sub['bus']} PHOTO PDF",
            data=sub["data"],
            file_name=f"{sub['bus']}_Photo_Dossier.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    with c_wa:
        st.link_button(
            label="📲 2. OPEN WHATSAPP TO SHARE",
            url=sub["wa_url"],
            use_container_width=True
        )
    st.info("💡 **How to share on phone:** Tap button 1 to download the PDF, then tap button 2 to open WhatsApp, tap the paperclip (📎) ➔ **Document**, and send your downloaded PDF.")
    st.divider()

# -------------------------------------------------------------
# Main Photo Submission Form
# -------------------------------------------------------------
with st.form("yatra_entry_form", clear_on_submit=False):
    st.subheader("Bus Identification")
    c1, c2 = st.columns(2)
    with c1:
        bus_no = st.text_input(
            "Bus Number", placeholder="e.g. AR 20 A 6004", key=f"b_{bk}").strip().upper()
    with c2:
        guide_name = st.text_input("Conductor / Team Guide Name",
                                   placeholder="e.g. Gurpreet Singh", key=f"g_{bk}").strip()

    c3, c4 = st.columns(2)
    with c3:
        d_start = st.date_input(
            "Trip Start Date", value=date.today(), key=f"ds_{bk}")
    with c4:
        d_end = st.date_input(
            "Trip End Date", value=date.today() + timedelta(days=3), key=f"de_{bk}")

    st.markdown("---")
    st.markdown("#### ⏱️ 1. Odometer Photos (4 Required)")
    st.caption(
        "Punjab Start ➔ Destination Arrival ➔ Return Departure ➔ Punjab Final Arrival")
    f_odos = st.file_uploader("Select Odometer Photos", type=[
                              "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"odo_{bk}")

    st.markdown("---")
    st.markdown("#### 👥 2. Yatri Group Photos (4 Required)")
    st.caption("Departure Banner ➔ Inside Cabin ➔ Return Group ➔ MLA / VIP Photo")
    f_groups = st.file_uploader("Select Group Photos", type=[
                                "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"grp_{bk}")

    st.markdown("---")
    st.markdown("#### 🥤 3. Steel Glass & Refreshment Distribution")
    f_dists = st.file_uploader("Select Distribution Photos", type=[
                               "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"dst_{bk}")

    st.markdown("---")
    st.markdown("#### 🍽️ 4. Passenger Meals")
    f_meals = st.file_uploader("Select Meals Photos (Breakfast, Lunch, Dinner)", type=[
                               "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"mel_{bk}")

    st.markdown("---")
    submitted = st.form_submit_button(
        "💾 GENERATE COMPLETE PHOTO PDF DOSSIER", type="primary", use_container_width=True)

# -------------------------------------------------------------
# Compile PDF on Submit
# -------------------------------------------------------------
if submitted:
    if not bus_no:
        st.error("❌ Please enter the Bus Number.")
    elif not guide_name:
        st.error("❌ Please enter the Conductor / Guide Name.")
    elif not f_odos and not f_groups and not f_dists and not f_meals:
        st.error("❌ No photos selected! Please pick photos before clicking Save.")
    else:
        with st.spinner("⏳ Compressing photos and compiling multi-page Photo PDF..."):
            all_photos = []

            def collect(files, labels, category):
                for idx, f in enumerate(files, 1):
                    lbl = labels[idx-1] if idx - \
                        1 < len(labels) else f"{category} #{idx}"
                    all_photos.append({"label": lbl, "file_obj": f})

            collect(f_odos, ["1. Punjab Departure Odometer", "2. Destination Arrival Odometer",
                    "3. Return Start Odometer", "4. Punjab Final Arrival Odometer"], "Odometer")
            collect(f_groups, ["1. Departure Banner Group Photo", "2. Inside Cabin Yatri Group Photo",
                    "3. Destination Return Group Photo", "4. MLA / VIP Group Photo"], "Group Photo")
            collect(f_dists, ["1. Steel Glass Distribution",
                    "2. Refreshment Distribution"], "Distribution")
            collect(f_meals, ["1. Breakfast Meal Photo",
                    "2. Lunch Meal Photo", "3. Dinner Meal Photo"], "Meal Photo")

            # Build full image PDF in memory
            pdf_data = build_photo_pdf(
                bus_no, guide_name, d_start, d_end, all_photos)

            # Pre-filled WhatsApp message
            wa_text = (
                f"🚌 *MUKH MANTRI TIRTH YATRA - TRIP REPORT*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Bus Number:* {bus_no}\n"
                f"👤 *Team Guide:* {guide_name}\n"
                f"📅 *Dates:* {d_start} to {d_end}\n"
                f"📸 *Photos Attached:* {len(all_photos)} Images Inside PDF\n"
                f"✅ Full Photo PDF Dossier Generated Successfully.\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            wa_link = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"

            st.session_state["last_pdf"] = {
                "bus": bus_no,
                "total": len(all_photos),
                "data": pdf_data,
                "wa_url": wa_link
            }
            st.rerun()
