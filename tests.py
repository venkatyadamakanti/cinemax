from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from movies.models import Movie, Genre, Language
from theaters.models import City, Theater, Screen, Seat
from shows.models import Show, ShowSeat
from bookings.models import Booking, BookingSeat, Ticket
from payments.models import PaymentTransaction
from reviews.models import Review
from bookings.pdf_generator import generate_pdf_ticket

class CinemaxTestSuite(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        self.admin = User.objects.create_superuser(username='adminuser', password='admin123', email='admin@example.com')

        self.lang = Language.objects.create(name='English', code='en')
        self.genre = Genre.objects.create(name='Sci-Fi', slug='sci-fi')
        self.movie = Movie.objects.create(
            title='Interstellar Test',
            description='Test description',
            duration_minutes=169,
            release_date=timezone.now().date(),
            age_rating='UA',
            language=self.lang,
            trailer_youtube_url='https://youtube.com/watch?v=test'
        )
        self.movie.genres.add(self.genre)

        self.city = City.objects.create(name='Mumbai', state='MH')
        self.theater = Theater.objects.create(name='PVR Test', city=self.city, address='Test addr')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1', total_seats=10)
        self.seat = Seat.objects.create(screen=self.screen, row='A', number=1, seat_type='REGULAR', base_price=250.00)

        self.show = Show.objects.create(
            movie=self.movie,
            screen=self.screen,
            start_time=timezone.now() - timedelta(hours=3), # Show in the past
            end_time=timezone.now() - timedelta(hours=1),
            ticket_price=250.00
        )
        self.show_seat = ShowSeat.objects.create(show=self.show, seat=self.seat, status='AVAILABLE')

    def test_movie_discovery_filter_api(self):
        response = self.client.get('/api/movies/?q=Interstellar&genre=sci-fi')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_count'], 1)
        self.assertEqual(data['results'][0]['title'], 'Interstellar Test')

    def test_seat_reservation_2min_lock(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f'/api/shows/{self.show.id}/reserve-seats/',
            data={'seat_ids': [self.show_seat.id]},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'RESERVED')
        self.assertIsNotNone(self.show_seat.reserved_until)

    def test_idempotent_payment_webhook(self):
        self.client.force_login(self.user)
        # Reserve seat & create booking
        res = self.client.post(
            f'/api/shows/{self.show.id}/reserve-seats/',
            data={'seat_ids': [self.show_seat.id]},
            content_type='application/json'
        )
        booking_id = res.json()['booking_id']

        # Initiate payment
        pay_res = self.client.post(
            '/api/payments/initiate/',
            data={'booking_id': booking_id, 'gateway': 'MOCK'},
            content_type='application/json'
        )
        tx_id = pay_res.json()['transaction_id']

        # First webhook call
        wh_res1 = self.client.post(
            '/api/payments/webhook/',
            data={'transaction_id': tx_id, 'status': 'SUCCESS'},
            content_type='application/json'
        )
        self.assertEqual(wh_res1.status_code, 200)

        # Duplicate webhook call (Idempotency verification)
        wh_res2 = self.client.post(
            '/api/payments/webhook/',
            data={'transaction_id': tx_id, 'status': 'SUCCESS'},
            content_type='application/json'
        )
        self.assertEqual(wh_res2.status_code, 200)
        self.assertIn('Idempotent', wh_res2.json()['message'])

    def test_pdf_ticket_generation(self):
        booking = Booking.objects.create(user=self.user, show=self.show, total_amount=250.00, status='CONFIRMED')
        BookingSeat.objects.create(booking=booking, show_seat=self.show_seat, price=250.00)
        PaymentTransaction.objects.create(
            booking=booking,
            user=self.user,
            gateway='MOCK',
            transaction_id='TXN-TEST-123',
            amount=250.00,
            status='SUCCESS'
        )

        ticket = generate_pdf_ticket(booking)
        self.assertIsNotNone(ticket.pdf_file)
        self.assertIsNotNone(ticket.qr_code_image)

    def test_verified_viewer_review_restriction(self):
        self.client.force_login(self.user)

        # Attempt to leave review without booking -> Should be forbidden
        unauth_res = self.client.post(
            f'/api/movies/{self.movie.id}/reviews/',
            data={'rating': 5, 'comment': 'Great movie!'},
            content_type='application/json'
        )
        self.assertEqual(unauth_res.status_code, 403)

        # Confirm booking for past show
        b = Booking.objects.create(user=self.user, show=self.show, total_amount=250.00, status='CONFIRMED')

        # Now submit review -> Should succeed and mark verified
        auth_res = self.client.post(
            f'/api/movies/{self.movie.id}/reviews/',
            data={'rating': 5, 'comment': 'Great movie!'},
            content_type='application/json'
        )
        self.assertEqual(auth_res.status_code, 201)
        rev = Review.objects.get(movie=self.movie, user=self.user)
        self.assertTrue(rev.is_verified_viewer)

    def test_admin_analytics_api(self):
        self.client.force_login(self.admin)
        res = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('kpis', data)
        self.assertIn('booking_trends', data)
        self.assertIn('theater_occupancy', data)
