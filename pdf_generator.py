import os
import io
import qrcode
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from .models import Ticket

def generate_pdf_ticket(booking):
    # 1. Generate QR Code
    verification_data = f"CINEMAX-VERIFY-BOOKING:{booking.id}|SHOW:{booking.show.id}|USER:{booking.user.username}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(verification_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="white")
    
    qr_io = io.BytesIO()
    qr_img.save(qr_io, format='PNG')
    qr_io.seek(0)
    
    # 2. Build PDF Document with ReportLab
    pdf_io = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_io,
        pagesize=(400, 600),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    dark_bg = colors.HexColor('#0F172A')
    accent_gold = colors.HexColor('#F59E0B')
    text_muted = colors.HexColor('#64748B')
    
    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=dark_bg,
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'TicketSubtitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=accent_gold,
        alignment=1
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=text_muted
    )
    
    value_style = ParagraphStyle(
        'ValueStyle',
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=dark_bg
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("CINEMAX TICKETS", title_style))
    elements.append(Paragraph("E-TICKET ADMIT ONE", subtitle_style))
    elements.append(Spacer(1, 15))
    
    # Movie Title
    movie_style = ParagraphStyle(
        'MovieTitle',
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=dark_bg
    )
    elements.append(Paragraph(booking.show.movie.title, movie_style))
    elements.append(Paragraph(f"Language: {booking.show.movie.language.name if booking.show.movie.language else 'English'} | Rating: {booking.show.movie.age_rating}", label_style))
    elements.append(Spacer(1, 10))
    
    # Details Grid
    seats_list = ", ".join([bs.show_seat.seat.seat_label for bs in booking.booked_seats.all()])
    payment_tx = booking.payments.filter(status='SUCCESS').first()
    payment_ref = payment_tx.transaction_id if payment_tx else "N/A"
    
    data = [
        [Paragraph("THEATER", label_style), Paragraph("SCREEN & TIMING", label_style)],
        [Paragraph(booking.show.screen.theater.name, value_style), Paragraph(f"{booking.show.screen.name} | {booking.show.start_time.strftime('%b %d, %Y %I:%M %p')}", value_style)],
        [Spacer(1, 6), Spacer(1, 6)],
        [Paragraph("BOOKED SEATS", label_style), Paragraph("BOOKING ID", label_style)],
        [Paragraph(seats_list or "N/A", value_style), Paragraph(str(booking.id)[:8].upper(), value_style)],
        [Spacer(1, 6), Spacer(1, 6)],
        [Paragraph("TOTAL PAID", label_style), Paragraph("PAYMENT REF", label_style)],
        [Paragraph(f"₹{booking.total_amount}", value_style), Paragraph(payment_ref[:16], value_style)],
    ]
    
    table = Table(data, colWidths=[180, 180])
    table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))
    
    # Add QR Code Image
    qr_rl_img = RLImage(qr_io, width=120, height=120)
    qr_rl_img.hAlign = 'CENTER'
    elements.append(qr_rl_img)
    
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Scan QR code at the theater entrance for entry verification.", ParagraphStyle('CenterNote', parent=label_style, alignment=1)))
    
    doc.build(elements)
    
    pdf_io.seek(0)
    qr_io.seek(0)
    
    # 3. Save or update Ticket instance
    ticket, created = Ticket.objects.get_or_create(booking=booking)
    ticket.qr_code_image.save(f"qr_{booking.id}.png", ContentFile(qr_io.read()), save=False)
    ticket.pdf_file.save(f"ticket_{booking.id}.pdf", ContentFile(pdf_io.read()), save=True)
    
    return ticket
