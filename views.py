import csv
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDay, ExtractHour
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from bookings.models import Booking, BookingSeat
from movies.models import Movie
from theaters.models import Theater, Screen, Seat
from django.contrib.auth.models import User

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_api(request):
    """
    Real-time business insights and analytics using optimized Django ORM aggregations.
    Executed efficiently over large datasets (100,000+ bookings).
    """
    # Date Range Filter
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    now = timezone.now()
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
        except ValueError:
            start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=30)

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            end_date = timezone.make_aware(end_date)
        except ValueError:
            end_date = now
    else:
        end_date = now

    confirmed_bookings = Booking.objects.filter(
        status='CONFIRMED',
        created_at__range=(start_date, end_date)
    )

    all_bookings_range = Booking.objects.filter(created_at__range=(start_date, end_date))

    # 1. Total Revenue Statistics
    revenue_aggregate = confirmed_bookings.aggregate(total_rev=Sum('total_amount'))
    total_revenue = revenue_aggregate['total_rev'] or 0.0

    today = now.date()
    daily_revenue = Booking.objects.filter(status='CONFIRMED', created_at__date=today).aggregate(s=Sum('total_amount'))['s'] or 0.0
    weekly_revenue = Booking.objects.filter(status='CONFIRMED', created_at__gte=now - timedelta(days=7)).aggregate(s=Sum('total_amount'))['s'] or 0.0
    monthly_revenue = Booking.objects.filter(status='CONFIRMED', created_at__gte=now - timedelta(days=30)).aggregate(s=Sum('total_amount'))['s'] or 0.0
    yearly_revenue = Booking.objects.filter(status='CONFIRMED', created_at__gte=now - timedelta(days=365)).aggregate(s=Sum('total_amount'))['s'] or 0.0

    # 2. Booking Trends (by day)
    booking_trends = confirmed_bookings.annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('day')

    trends_data = [{
        'date': item['day'].strftime('%Y-%m-%d') if item['day'] else '',
        'bookings': item['count'],
        'revenue': float(item['revenue'] or 0)
    } for item in booking_trends]

    # 3. Theater Occupancy Percentage
    theaters = Theater.objects.all().annotate(
        total_capacity=Sum('screens__total_seats'),
        booked_seats=Count('screens__shows__bookings__booked_seats', filter=Q(screens__shows__bookings__status='CONFIRMED', screens__shows__bookings__created_at__range=(start_date, end_date))),
        total_shows=Count('screens__shows', filter=Q(screens__shows__start_time__range=(start_date, end_date)))
    )

    occupancy_data = []
    for t in theaters:
        cap = (t.total_capacity or 100) * (t.total_shows or 1)
        occ_pct = round((t.booked_seats / cap * 100), 2) if cap > 0 else 0.0
        occupancy_data.append({
            'theater_id': t.id,
            'theater_name': t.name,
            'city': t.city.name,
            'occupancy_pct': occ_pct,
            'total_booked_seats': t.booked_seats
        })

    # 4. Most Booked Movies
    top_movies = Movie.objects.filter(
        shows__bookings__status='CONFIRMED',
        shows__bookings__created_at__range=(start_date, end_date)
    ).annotate(
        period_bookings=Count('shows__bookings__booked_seats'),
        period_revenue=Sum('shows__bookings__total_amount')
    ).order_by('-period_bookings')[:5]

    top_movies_data = [{
        'title': m.title,
        'bookings_count': m.period_bookings,
        'revenue': float(m.period_revenue or 0),
        'avg_rating': m.avg_rating
    } for m in top_movies]

    # 5. Top Performing Theaters by Revenue
    top_theaters = Theater.objects.filter(
        screens__shows__bookings__status='CONFIRMED',
        screens__shows__bookings__created_at__range=(start_date, end_date)
    ).annotate(
        revenue=Sum('screens__shows__bookings__total_amount')
    ).order_by('-revenue')[:5]

    top_theaters_data = [{
        'name': t.name,
        'city': t.city.name,
        'revenue': float(t.revenue or 0)
    } for t in top_theaters]

    # 6. Peak Booking Hours
    peak_hours = all_bookings_range.annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')

    peak_hours_dict = {i: 0 for i in range(24)}
    for ph in peak_hours:
        if ph['hour'] is not None:
            peak_hours_dict[ph['hour']] = ph['count']

    peak_hours_data = [{'hour': f"{h:02d}:00", 'bookings': count} for h, count in peak_hours_dict.items()]

    # 7. Cancellation & Refund Statistics
    cancellations_count = all_bookings_range.filter(status='CANCELLED').count()
    total_range_count = all_bookings_range.count() or 1
    cancellation_rate = round((cancellations_count / total_range_count) * 100, 2)

    # 8. User Growth Report
    total_users = User.objects.count()
    new_users_period = User.objects.filter(date_joined__range=(start_date, end_date)).count()

    return Response({
        'date_range': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
        },
        'kpis': {
            'total_revenue': float(total_revenue),
            'daily_revenue': float(daily_revenue),
            'weekly_revenue': float(weekly_revenue),
            'monthly_revenue': float(monthly_revenue),
            'yearly_revenue': float(yearly_revenue),
            'confirmed_bookings_count': confirmed_bookings.count(),
            'total_users': total_users,
            'new_users_period': new_users_period,
            'cancellation_rate_pct': cancellation_rate,
            'cancellations_count': cancellations_count
        },
        'booking_trends': trends_data,
        'theater_occupancy': occupancy_data,
        'top_movies': top_movies_data,
        'top_theaters': top_theaters_data,
        'peak_hours': peak_hours_data
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_analytics_csv_api(request):
    """
    Exports administrative analytics report as a downloadable CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cinemax_analytics_report_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['CINEMAX BUSINESS ANALYTICS REPORT'])
    writer.writerow(['Generated At', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([])

    # Revenue Summary
    writer.writerow(['REVENUE SUMMARY'])
    writer.writerow(['Metric', 'Amount (INR)'])
    writer.writerow(['Total Revenue (All Time)', Booking.objects.filter(status='CONFIRMED').aggregate(s=Sum('total_amount'))['s'] or 0.0])
    writer.writerow(['Last 30 Days Revenue', Booking.objects.filter(status='CONFIRMED', created_at__gte=timezone.now() - timedelta(days=30)).aggregate(s=Sum('total_amount'))['s'] or 0.0])
    writer.writerow(['Total Confirmed Bookings', Booking.objects.filter(status='CONFIRMED').count()])
    writer.writerow([])

    # Top Movies
    writer.writerow(['TOP PERFORMING MOVIES'])
    writer.writerow(['Movie Title', 'Total Booked Seats', 'Total Revenue (INR)', 'Average Rating'])
    for m in Movie.objects.order_by('-total_bookings')[:10]:
        writer.writerow([m.title, m.total_bookings, m.shows.filter(bookings__status='CONFIRMED').aggregate(s=Sum('bookings__total_amount'))['s'] or 0.0, m.avg_rating])
    writer.writerow([])

    # Top Theaters
    writer.writerow(['THEATER PERFORMANCE & OCCUPANCY'])
    writer.writerow(['Theater Name', 'City', 'Total Revenue (INR)'])
    for t in Theater.objects.annotate(rev=Sum('screens__shows__bookings__total_amount', filter=Q(screens__shows__bookings__status='CONFIRMED'))).order_by('-rev'):
        writer.writerow([t.name, t.city.name, t.rev or 0.0])

    return response
