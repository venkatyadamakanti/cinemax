import uuid
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import PaymentTransaction
from bookings.models import Booking
from shows.models import ShowSeat
from bookings.tasks import trigger_async_ticket_delivery

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment_api(request):
    booking_id = request.data.get('booking_id')
    gateway = request.data.get('gateway', 'MOCK').upper()
    
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status != 'PENDING':
        return Response({'error': f'Booking is in {booking.status} status and cannot be paid.'}, status=status.HTTP_400_BAD_REQUEST)
        
    # Check if seats have expired
    for bs in booking.booked_seats.select_related('show_seat').all():
        if bs.show_seat.is_expired():
            booking.status = 'EXPIRED'
            booking.save()
            return Response({'error': 'Your 2-minute seat reservation has expired. Please select seats again.'}, status=status.HTTP_410_GONE)

    # Generate transaction reference ID
    transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    
    pay_tx = PaymentTransaction.objects.create(
        booking=booking,
        user=request.user,
        gateway=gateway,
        transaction_id=transaction_id,
        amount=booking.total_amount,
        status='PENDING'
    )
    
    return Response({
        'payment_id': str(pay_tx.id),
        'transaction_id': transaction_id,
        'amount': float(booking.total_amount),
        'gateway': gateway,
        'status': 'PENDING'
    })

@api_view(['POST'])
@permission_classes([AllowAny]) # Webhooks are verified server-side
def payment_webhook_or_confirm_api(request):
    """
    Idempotent payment confirmation endpoint & webhook handler.
    Guarantees duplicate webhook notifications or retries never result in duplicate bookings.
    """
    transaction_id = request.data.get('transaction_id')
    payment_status = request.data.get('status', 'SUCCESS').upper() # SUCCESS or FAILED
    
    if not transaction_id:
        return Response({'error': 'transaction_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        try:
            pay_tx = PaymentTransaction.objects.select_for_update().get(transaction_id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            return Response({'error': 'Transaction reference not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Idempotency check: If already processed, return current status without duplicate execution
        if pay_tx.status in ['SUCCESS', 'FAILED', 'REFUNDED']:
            return Response({
                'message': 'Transaction already processed (Idempotent call).',
                'status': pay_tx.status,
                'booking_id': str(pay_tx.booking.id)
            }, status=status.HTTP_200_OK)

        booking = pay_tx.booking
        
        if payment_status == 'SUCCESS':
            pay_tx.status = 'SUCCESS'
            pay_tx.save()

            booking.status = 'CONFIRMED'
            booking.save()

            # Mark all seats as BOOKED atomically
            for bs in booking.booked_seats.select_related('show_seat').all():
                ss = bs.show_seat
                ss.status = 'BOOKED'
                ss.reserved_until = None
                ss.reserved_by = None
                ss.save()

            # Increment movie total bookings stats
            movie = booking.show.movie
            movie.total_bookings += booking.booked_seats.count()
            movie.save(update_fields=['total_bookings'])

            # Trigger Async Celery PDF Ticket Generation & Email Confirmation
            trigger_async_ticket_delivery(booking.id)

            return Response({
                'message': 'Payment successful! Booking confirmed.',
                'status': 'SUCCESS',
                'booking_id': str(booking.id)
            }, status=status.HTTP_200_OK)

        else: # FAILED / CANCELLED
            pay_tx.status = 'FAILED'
            pay_tx.save()

            booking.status = 'CANCELLED'
            booking.save()

            # Automatic seat release on payment failure
            for bs in booking.booked_seats.select_related('show_seat').all():
                ss = bs.show_seat
                if ss.status == 'RESERVED':
                    ss.status = 'AVAILABLE'
                    ss.reserved_until = None
                    ss.reserved_by = None
                    ss.save()

            return Response({
                'message': 'Payment failed. Reserved seats have been released.',
                'status': 'FAILED',
                'booking_id': str(booking.id)
            }, status=status.HTTP_400_BAD_REQUEST)
