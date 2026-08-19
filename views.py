from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Booking, Ticket
from .pdf_generator import generate_pdf_ticket

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_booking_history_api(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        'show__movie', 'show__screen__theater'
    ).prefetch_related('booked_seats__show_seat__seat', 'payments').order_by('-created_at')

    data = []
    for b in bookings:
        seats = [bs.show_seat.seat.seat_label for bs in b.booked_seats.all()]
        has_ticket = hasattr(b, 'ticket') and bool(b.ticket.pdf_file)

        data.append({
            'booking_id': str(b.id),
            'movie_title': b.show.movie.title,
            'poster_url': b.show.movie.poster_url,
            'theater_name': b.show.screen.theater.name,
            'screen_name': b.show.screen.name,
            'show_time': b.show.start_time.strftime('%b %d, %Y %I:%M %p'),
            'seats': seats,
            'total_amount': float(b.total_amount),
            'status': b.status,
            'created_at': b.created_at.strftime('%b %d, %Y %I:%M %p'),
            'has_ticket': has_ticket
        })

    return Response({'bookings': data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_ticket_pdf_api(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'CONFIRMED':
        return Response({'error': 'Ticket is only available for confirmed bookings.'}, status=400)

    ticket = getattr(booking, 'ticket', None)
    if not ticket or not ticket.pdf_file:
        ticket = generate_pdf_ticket(booking)

    if not ticket.pdf_file:
        raise Http404("PDF ticket could not be found.")

    response = FileResponse(ticket.pdf_file.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Cinemax_Ticket_{str(booking.id)[:8]}.pdf"'
    return response
