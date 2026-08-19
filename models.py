from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from movies.models import Movie
from theaters.models import Screen, Seat

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows', db_index=True)
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='shows', db_index=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, default=300.00, db_index=True)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['movie', 'start_time']),
            models.Index(fields=['screen', 'start_time']),
            models.Index(fields=['start_time']),
            models.Index(fields=['ticket_price']),
        ]
        ordering = ['start_time']

    def __str__(self):
        return f"{self.movie.title} at {self.screen.theater.name} ({self.screen.name}) - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

class ShowSeat(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('RESERVED', 'Temporarily Reserved (2 min hold)'),
        ('BOOKED', 'Booked'),
    ]

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='show_seats', db_index=True)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='show_seats')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='AVAILABLE', db_index=True)
    reserved_until = models.DateTimeField(null=True, blank=True, db_index=True)
    reserved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='held_seats')

    class Meta:
        unique_together = ('show', 'seat')
        indexes = [
            models.Index(fields=['show', 'status']),
            models.Index(fields=['reserved_until']),
        ]

    def is_expired(self):
        if self.status == 'RESERVED' and self.reserved_until:
            return timezone.now() > self.reserved_until
        return False

    def get_effective_status(self):
        if self.status == 'RESERVED' and self.is_expired():
            return 'AVAILABLE'
        return self.status

    def __str__(self):
        return f"{self.show} - Seat {self.seat.seat_label} ({self.get_effective_status()})"
