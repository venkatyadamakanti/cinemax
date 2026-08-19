import uuid
from django.db import models
from django.contrib.auth.models import User
from shows.models import Show, ShowSeat

class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', db_index=True)
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='bookings', db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['show', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {str(self.id)[:8]} - {self.user.username} - {self.status}"

class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_seats')
    show_seat = models.ForeignKey(ShowSeat, on_delete=models.CASCADE, related_name='booking_records')
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"Seat {self.show_seat.seat.seat_label} for Booking {str(self.booking.id)[:8]}"

class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='ticket')
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='pdf_tickets/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket for Booking {str(self.booking.id)[:8]}"
