import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from movies.models import Genre, Language, CastMember, Movie, MovieCast
from theaters.models import City, Theater, Screen, Seat
from shows.models import Show, ShowSeat
from bookings.models import Booking, BookingSeat, Ticket
from payments.models import PaymentTransaction
from reviews.models import Review

class Command(BaseCommand):
    help = 'Seeds Cinemax database with movies, theaters, shows, verified reviews, and bulk bookings.'

    def add_arguments(self, parser):
        parser.add_argument('--bookings', type=int, default=100, help='Number of historical bookings to seed (e.g., 100000 for load test)')

    def handle(self, *args, **options):
        num_bookings = options['bookings']
        self.stdout.write(self.style.SUCCESS('[+] Starting Cinemax database seeder...'))

        # 1. Create Default Admin User (admin / admin123)
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cinemax.com',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
                'last_name': 'User'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('  * Admin account created: username=admin, password=admin123'))
        else:
            self.stdout.write(self.style.NOTICE('  - Admin user already exists'))

        # 2. Create Regular Demo User (demo / demo123)
        demo_user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@cinemax.com',
                'first_name': 'Demo',
                'last_name': 'Viewer'
            }
        )
        if created:
            demo_user.set_password('demo123')
            demo_user.save()
            self.stdout.write(self.style.SUCCESS('  * Demo viewer created: username=demo, password=demo123'))


        # 3. Create Genres
        genres_names = ['Action', 'Sci-Fi', 'Thriller', 'Drama', 'Comedy', 'Romance', 'Adventure', 'Animation']
        genre_objs = []
        for gname in genres_names:
            g, _ = Genre.objects.get_or_create(name=gname)
            genre_objs.append(g)

        # 4. Create Languages
        languages_data = [('English', 'en'), ('Hindi', 'hi'), ('Telugu', 'te'), ('Tamil', 'ta')]
        lang_objs = []
        for name, code in languages_data:
            l, _ = Language.objects.get_or_create(name=name, defaults={'code': code})
            lang_objs.append(l)

        # 5. Create Cities & Theaters
        city_mumbai, _ = City.objects.get_or_create(name='Mumbai', defaults={'state': 'Maharashtra'})
        city_bengaluru, _ = City.objects.get_or_create(name='Bengaluru', defaults={'state': 'Karnataka'})
        city_delhi, _ = City.objects.get_or_create(name='Delhi', defaults={'state': 'NCR'})

        theaters_data = [
            ('PVR ICON Phoenix', city_mumbai, 'Lower Parel, Mumbai'),
            ('INBOX IMAX Forum', city_bengaluru, 'Koramangala, Bengaluru'),
            ('Cinepolis Select CityWalk', city_delhi, 'Saket, New Delhi'),
        ]

        theaters = []
        for name, city, addr in theaters_data:
            t, _ = Theater.objects.get_or_create(name=name, city=city, defaults={'address': addr})
            theaters.append(t)

        # 6. Create Screens & Seats
        screens = []
        for t in theaters:
            s1, _ = Screen.objects.get_or_create(theater=t, name='Screen 1 (IMAX)', defaults={'screen_type': 'IMAX', 'total_seats': 40})
            s2, _ = Screen.objects.get_or_create(theater=t, name='Screen 2 (4DX)', defaults={'screen_type': '4DX', 'total_seats': 40})
            screens.extend([s1, s2])

        for screen in screens:
            if not screen.seats.exists():
                seats_to_create = []
                for r_idx, row_letter in enumerate(['A', 'B', 'C', 'D']):
                    for num in range(1, 11):
                        stype = 'VIP' if row_letter == 'D' else ('PREMIUM' if row_letter in ['B', 'C'] else 'REGULAR')
                        price = 450.00 if stype == 'VIP' else (350.00 if stype == 'PREMIUM' else 250.00)
                        seats_to_create.append(Seat(screen=screen, row=row_letter, number=num, seat_type=stype, base_price=price))
                Seat.objects.bulk_create(seats_to_create)

        # 7. Create Sample Movies
        movies_data = [
            {
                'title': 'Dune: Part Two',
                'description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
                'duration_minutes': 166,
                'release_date': timezone.now().date() - timedelta(days=20),
                'age_rating': 'UA',
                'trailer_youtube_url': 'https://www.youtube.com/watch?v=Way9Dexny3w',
                'poster_url': 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800',
                'backdrop_url': 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1600',
                'genres': [genre_objs[0], genre_objs[1], genre_objs[6]],
                'lang': lang_objs[0]
            },
            {
                'title': 'Oppenheimer',
                'description': 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.',
                'duration_minutes': 180,
                'release_date': timezone.now().date() - timedelta(days=60),
                'age_rating': 'A',
                'trailer_youtube_url': 'https://www.youtube.com/watch?v=uYPbbksJxIg',
                'poster_url': 'https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=800',
                'backdrop_url': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1600',
                'genres': [genre_objs[0], genre_objs[3]],
                'lang': lang_objs[0]
            },
            {
                'title': 'Kalki 2898 AD',
                'description': 'A modern avatar of Vishnu, believed to have descended to earth to protect the world from evil forces.',
                'duration_minutes': 181,
                'release_date': timezone.now().date() - timedelta(days=10),
                'age_rating': 'UA',
                'trailer_youtube_url': 'https://www.youtube.com/watch?v=kQDd1AhGIHk',
                'poster_url': 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800',
                'backdrop_url': 'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=1600',
                'genres': [genre_objs[0], genre_objs[1], genre_objs[2]],
                'lang': lang_objs[2]
            },
            {
                'title': 'Stree 2',
                'description': 'Chanderi is haunted once again by a terrifying headless monster known as Sarkata.',
                'duration_minutes': 149,
                'release_date': timezone.now().date() - timedelta(days=5),
                'age_rating': 'UA',
                'trailer_youtube_url': 'https://www.youtube.com/watch?v=KVnheXwqF08',
                'poster_url': 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800',
                'backdrop_url': 'https://images.unsplash.com/photo-1514533450685-4493e01d1fdc?w=1600',
                'genres': [genre_objs[4], genre_objs[2]],
                'lang': lang_objs[1]
            }
        ]

        created_movies = []
        for mdata in movies_data:
            movie, created = Movie.objects.get_or_create(
                title=mdata['title'],
                defaults={
                    'description': mdata['description'],
                    'duration_minutes': mdata['duration_minutes'],
                    'release_date': mdata['release_date'],
                    'age_rating': mdata['age_rating'],
                    'trailer_youtube_url': mdata['trailer_youtube_url'],
                    'poster_url': mdata['poster_url'],
                    'backdrop_url': mdata['backdrop_url'],
                    'language': mdata['lang'],
                }
            )
            if created:
                movie.genres.set(mdata['genres'])
            created_movies.append(movie)

        # 8. Create Shows & ShowSeats
        now = timezone.now()
        shows = []
        for movie in created_movies:
            for screen in screens[:3]:
                for day_offset in range(0, 3):
                    start = now + timedelta(days=day_offset, hours=4 + day_offset*3)
                    end = start + timedelta(minutes=movie.duration_minutes)
                    show, s_created = Show.objects.get_or_create(
                        movie=movie,
                        screen=screen,
                        start_time=start,
                        defaults={'end_time': end, 'ticket_price': 300.00}
                    )
                    shows.append(show)
                    if s_created:
                        show_seats = [ShowSeat(show=show, seat=seat, status='AVAILABLE') for seat in screen.seats.all()]
                        ShowSeat.objects.bulk_create(show_seats)

        self.stdout.write(self.style.SUCCESS(f'  * Created catalog with {len(created_movies)} movies, {len(screens)} screens, and {len(shows)} shows.'))

        # 9. Create Historical Seed Bookings for Performance Analytics Test
        if num_bookings > 0:
            self.stdout.write(self.style.NOTICE(f'[+] Seeding {num_bookings} historical bookings for analytics query benchmark...'))
            
            # Create pool of buyers
            buyers = []
            for i in range(1, 25):
                u, _ = User.objects.get_or_create(username=f"user_{i}", defaults={'email': f"user_{i}@example.com"})
                buyers.append(u)

            ref_show = shows[0]
            avail_show_seats = list(ref_show.show_seats.all()[:10])

            bookings_batch = []
            payments_batch = []
            
            base_time = timezone.now() - timedelta(days=60)
            
            for b_i in range(num_bookings):
                created_dt = base_time + timedelta(minutes=b_i * (60 * 24 * 60 // max(num_bookings, 1)))
                user = random.choice(buyers)
                b_status = 'CONFIRMED' if random.random() > 0.1 else 'CANCELLED'
                
                b = Booking(
                    user=user,
                    show=ref_show,
                    total_amount=300.00 * random.randint(1, 4),
                    status=b_status,
                )
                b.created_at = created_dt
                bookings_batch.append(b)

            Booking.objects.bulk_create(bookings_batch, batch_size=2000)
            
            # Seed corresponding PaymentTransactions
            inserted_bookings = Booking.objects.order_by('-created_at')[:num_bookings]
            for b in inserted_bookings:
                if b.status == 'CONFIRMED':
                    payments_batch.append(PaymentTransaction(
                        booking=b,
                        user=b.user,
                        gateway='STRIPE',
                        transaction_id=f"TXN-SEED-{b.id.hex[:10].upper()}",
                        amount=b.total_amount,
                        status='SUCCESS',
                        created_at=b.created_at
                    ))

            PaymentTransaction.objects.bulk_create(payments_batch, batch_size=2000)
            self.stdout.write(self.style.SUCCESS(f'  * Successfully seeded {num_bookings} bookings and payment transactions!'))

        # 10. Add sample verified reviews
        for movie in created_movies:
            # Add past confirmed booking for demo user so demo user is verified
            past_show, _ = Show.objects.get_or_create(
                movie=movie,
                screen=screens[0],
                start_time=now - timedelta(days=2),
                defaults={'end_time': now - timedelta(days=2, hours=-2), 'ticket_price': 300.00}
            )
            b, _ = Booking.objects.get_or_create(
                user=demo_user,
                show=past_show,
                defaults={'total_amount': 300.00, 'status': 'CONFIRMED'}
            )
            
            Review.objects.get_or_create(
                movie=movie,
                user=demo_user,
                defaults={
                    'rating': 5,
                    'comment': f"Absolutely mindblowing cinematic experience! A must watch for all movie lovers.",
                    'is_verified_viewer': True
                }
            )

        self.stdout.write(self.style.SUCCESS('[SUCCESS] Database Seeding Complete! Enjoy testing Cinemax.'))

