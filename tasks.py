import logging
import threading
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Booking, Ticket
from .pdf_generator import generate_pdf_ticket

logger = logging.getLogger(__name__)

def process_ticket_delivery(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        if booking.status != 'CONFIRMED':
            logger.warning(f"Booking {booking_id} is not confirmed. Skipping ticket email.")
            return

        # 1. Generate PDF Ticket
        ticket = generate_pdf_ticket(booking)

        # 2. Compose Email
        user_email = booking.user.email or "customer@cinemax.com"
        movie_title = booking.show.movie.title
        show_time = booking.show.start_time.strftime("%b %d, %Y at %I:%M %p")
        theater_name = booking.show.screen.theater.name
        seats = ", ".join([bs.show_seat.seat.seat_label for bs in booking.booked_seats.all()])

        subject = f"🎟️ Your Ticket Confirmation - {movie_title} ({str(booking.id)[:8].upper()})"
        body = f"""Hi {booking.user.first_name or booking.user.username},

Thank you for booking with Cinemax! Your ticket has been confirmed.

BOOKING DETAILS:
- Movie: {movie_title}
- Theater: {theater_name} ({booking.show.screen.name})
- Timing: {show_time}
- Seats: {seats}
- Total Amount: ₹{booking.total_amount}
- Booking ID: {booking.id}

Your PDF ticket with scannable QR code is attached to this email. You can also download it anytime from your Cinemax Profile dashboard.

Enjoy your movie!
The Cinemax Team
"""

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )

        if ticket.pdf_file and hasattr(ticket.pdf_file, 'path') and ticket.pdf_file.path:
            email.attach_file(ticket.pdf_file.path)

        email.send(fail_silently=False)
        logger.info(f"Successfully sent ticket email for booking {booking_id} to {user_email}")
        return True

    except Exception as exc:
        logger.error(f"Error sending ticket email for booking {booking_id}: {exc}")
        raise exc

@shared_task(bind=True, max_retries=5, default_retry_delay=10)
def send_ticket_email_task(self, booking_id):
    try:
        process_ticket_delivery(booking_id)
    except Exception as exc:
        logger.warning(f"Retrying ticket email task for booking {booking_id} (Attempt {self.request.retries + 1})")
        raise self.retry(exc=exc)

def trigger_async_ticket_delivery(booking_id):
    """
    Triggers Celery task if broker available, otherwise executes in a background daemon thread
    to guarantee non-blocking async execution in all environments.
    """
    try:
        send_ticket_email_task.delay(str(booking_id))
    except Exception:
        # Fallback background thread
        thread = threading.Thread(target=process_ticket_delivery, args=(booking_id,), daemon=True)
        thread.start()
