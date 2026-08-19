from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Show, ShowSeat
from bookings.models import Booking, BookingSeat

@api_view(['GET'])
@permission_classes([AllowAny])
def show_seats_api(request, show_id):
    show = get_object_or_404(Show, id=show_id)
    now = timezone.now()
    
    # Auto-release expired seat reservations
    expired_seats = ShowSeat.objects.filter(
        show=show,
        status='RESERVED',
        reserved_until__lt=now
    )
    if expired_seats.exists():
        expired_seats.update(status='AVAILABLE', reserved_until=None, reserved_by=None)
        
    seats_qs = show.show_seats.select_related('seat').order_by('seat__row', 'seat__number')
    
    seat_map = {}
    for ss in seats_qs:
        row = ss.seat.row
        if row not in seat_map:
            seat_map[row] = []
            
        effective_status = ss.get_effective_status()
        is_mine = (ss.status == 'RESERVED' and ss.reserved_by == request.user and not ss.is_expired())
        
        seat_map[row].append({
            'show_seat_id': ss.id,
            'seat_id': ss.seat.id,
            'row': ss.seat.row,
            'number': ss.seat.number,
            'label': ss.seat.seat_label,
            'seat_type': ss.seat.seat_type,
            'price': float(show.ticket_price),
            'status': effective_status,
            'is_mine': is_mine,
            'reserved_until': ss.reserved_until.isoformat() if ss.reserved_until else None
        })
        
    return Response({
        'show_id': show.id,
        'movie_title': show.movie.title,
        'theater_name': show.screen.theater.name,
        'screen_name': show.screen.name,
        'start_time': show.start_time.strftime('%b %d, %Y %I:%M %p'),
        'ticket_price': float(show.ticket_price),
        'seat_map': seat_map
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reserve_seats_api(request, show_id):
    """
    Reserves multiple seats for 2 minutes using atomic database transactions
    and row locking (select_for_update) for strict concurrency control.
    """
    seat_ids = request.data.get('seat_ids', [])
    if not seat_ids or not isinstance(seat_ids, list):
        return Response({'error': 'Please select at least one seat.'}, status=status.HTTP_400_BAD_REQUEST)
        
    now = timezone.now()
    hold_duration = timedelta(minutes=2)
    expiry_time = now + hold_duration
    
    try:
        with transaction.atomic():
            # Lock requested ShowSeat rows using select_for_update() to prevent race conditions
            locked_seats = list(
                ShowSeat.objects.select_for_update().filter(
                    show_id=show_id,
                    id__in=seat_ids
                ).select_related('seat')
            )
            
            if len(locked_seats) != len(seat_ids):
                return Response({'error': 'One or more selected seats do not exist.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Verify availability for each locked seat
            for ss in locked_seats:
                # If seat is currently reserved by someone else and not expired, fail request
                if ss.status == 'BOOKED':
                    return Response({'error': f'Seat {ss.seat.seat_label} is already booked.'}, status=status.HTTP_409_CONFLICT)
                elif ss.status == 'RESERVED' and ss.reserved_by != request.user and ss.reserved_until > now:
                    return Response({'error': f'Seat {ss.seat.seat_label} is currently reserved by another user.'}, status=status.HTTP_409_CONFLICT)

            # Update seats to RESERVED status with 2-min expiration lock
            for ss in locked_seats:
                ss.status = 'RESERVED'
                ss.reserved_until = expiry_time
                ss.reserved_by = request.user
                ss.save()
                
            show = locked_seats[0].show
            total_amount = show.ticket_price * len(locked_seats)
            
            # Cancel any previous PENDING bookings for this user on this show to avoid stale states
            Booking.objects.filter(user=request.user, show=show, status='PENDING').update(status='EXPIRED')
            
            # Create new PENDING booking
            booking = Booking.objects.create(
                user=request.user,
                show=show,
                total_amount=total_amount,
                status='PENDING'
            )
            
            for ss in locked_seats:
                BookingSeat.objects.create(booking=booking, show_seat=ss, price=show.ticket_price)
                
            return Response({
                'message': f'{len(locked_seats)} seat(s) reserved for 2 minutes.',
                'booking_id': str(booking.id),
                'total_amount': float(total_amount),
                'reserved_until': expiry_time.isoformat(),
                'expires_in_seconds': 120
            }, status=status.HTTP_200_OK)
            
    except Exception as exc:
        return Response({'error': f'Failed to reserve seats: {str(exc)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
