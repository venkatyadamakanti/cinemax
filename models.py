import uuid
from django.db import models
from django.contrib.auth.models import User
from bookings.models import Booking

class PaymentTransaction(models.Model):
    GATEWAY_CHOICES = [
        ('STRIPE', 'Stripe'),
        ('RAZORPAY', 'Razorpay'),
        ('MOCK', 'Mock Gateway'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='STRIPE')
    transaction_id = models.CharField(max_length=150, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status} - ₹{self.amount}"
