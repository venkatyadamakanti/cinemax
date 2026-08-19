from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Avg, Min, Max
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Movie, Genre, Language, UserMovieView
from theaters.models import City, Theater
from shows.models import Show
from reviews.models import Review
from bookings.models import Booking

def filter_movies_queryset(request):
    qs = Movie.objects.filter(is_active=True).prefetch_related('genres', 'language')
    
    # 1. Search by title
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        
    # 2. Filter by Genre
    genre_slug = request.GET.get('genre', '').strip()
    if genre_slug:
        qs = qs.filter(genres__slug=genre_slug)
        
    # 3. Filter by Language
    lang_code = request.GET.get('language', '').strip()
    if lang_code:
        qs = qs.filter(language__code=lang_code)
        
    # 4. Filter by City
    city_id = request.GET.get('city', '').strip()
    if city_id:
        qs = qs.filter(shows__screen__theater__city_id=city_id).distinct()
        
    # 5. Filter by Theater
    theater_id = request.GET.get('theater', '').strip()
    if theater_id:
        qs = qs.filter(shows__screen__theater_id=theater_id).distinct()
        
    # 6. Filter by Rating
    min_rating = request.GET.get('min_rating', '').strip()
    if min_rating:
        try:
            qs = qs.filter(avg_rating__gte=float(min_rating))
        except ValueError:
            pass
            
    # 7. Filter by Release Date
    release_from = request.GET.get('release_from', '').strip()
    if release_from:
        qs = qs.filter(release_date__gte=release_from)
    release_to = request.GET.get('release_to', '').strip()
    if release_to:
        qs = qs.filter(release_date__lte=release_to)

    # 8. Sort
    sort = request.GET.get('sort', 'popularity').strip()
    if sort == 'newest':
        qs = qs.order_by('-release_date', '-id')
    elif sort == 'rating':
        qs = qs.order_by('-avg_rating', '-total_reviews')
    elif sort == 'popularity':
        qs = qs.order_by('-total_bookings', '-id')
    elif sort == 'title_asc':
        qs = qs.order_by('title')
    else:
        qs = qs.order_by('-release_date')
        
    return qs.distinct()

@api_view(['GET'])
@permission_classes([AllowAny])
def movie_list_api(request):
    qs = filter_movies_queryset(request)
    total_count = qs.count()
    
    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(page_number)
    
    data = []
    for movie in page_obj:
        data.append({
            'id': movie.id,
            'title': movie.title,
            'slug': movie.slug,
            'description': movie.description,
            'duration_minutes': movie.duration_minutes,
            'release_date': movie.release_date.strftime('%Y-%m-%d'),
            'age_rating': movie.age_rating,
            'poster_url': movie.poster_url,
            'backdrop_url': movie.backdrop_url,
            'avg_rating': movie.avg_rating,
            'total_reviews': movie.total_reviews,
            'language': movie.language.name if movie.language else 'English',
            'genres': [g.name for g in movie.genres.all()],
        })
        
    return Response({
        'total_count': total_count,
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'results': data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def movie_count_api(request):
    """Dynamically returns the matching count after each filter is applied"""
    qs = filter_movies_queryset(request)
    return Response({'matching_count': qs.count()})

@api_view(['GET'])
@permission_classes([AllowAny])
def recommendations_api(request):
    """
    "Recommended for You" section based on user's booking history and recently viewed movies.
    """
    recommended_movies = []
    
    if request.user.is_authenticated:
        # 1. Fetch genres from user's booking history
        booked_genres = Genre.objects.filter(
            movies__shows__bookings__user=request.user,
            movies__shows__bookings__status='CONFIRMED'
        ).distinct()
        
        # 2. Fetch recently viewed movies
        viewed_movie_ids = UserMovieView.objects.filter(user=request.user).values_list('movie_id', flat=True)[:5]
        viewed_genres = Genre.objects.filter(movies__id__in=viewed_movie_ids).distinct()
        
        combined_genres = (booked_genres | viewed_genres).distinct()
        
        if combined_genres.exists():
            recommended_movies = Movie.objects.filter(
                is_active=True,
                genres__in=combined_genres
            ).exclude(id__in=viewed_movie_ids).annotate(
                score=Count('id')
            ).order_by('-avg_rating', '-total_bookings')[:8]
            
    if not recommended_movies:
        # Fallback to top-rated & popular movies
        recommended_movies = Movie.objects.filter(is_active=True).order_by('-avg_rating', '-total_bookings')[:8]
        
    data = [{
        'id': m.id,
        'title': m.title,
        'slug': m.slug,
        'poster_url': m.poster_url,
        'avg_rating': m.avg_rating,
        'language': m.language.name if m.language else '',
        'genres': [g.name for g in m.genres.all()]
    } for m in recommended_movies]
    
    return Response({'recommendations': data})

@api_view(['GET'])
@permission_classes([AllowAny])
def movie_detail_api(request, slug):
    movie = get_object_or_404(Movie, slug=slug)
    
    # Log user view if authenticated
    if request.user.is_authenticated:
        UserMovieView.objects.update_or_create(user=request.user, movie=movie)
        
    # Fetch cast
    cast_data = [{
        'name': mc.cast_member.name,
        'role': mc.cast_member.role,
        'character_name': mc.character_name,
        'photo_url': mc.cast_member.photo_url
    } for mc in movie.cast_members.select_related('cast_member').all()]
    
    # Fetch reviews
    reviews_qs = movie.reviews.filter(flagged=False).select_related('user').order_by('-created_at')
    reviews_data = [{
        'id': r.id,
        'username': r.user.username,
        'rating': r.rating,
        'comment': r.comment,
        'is_verified_viewer': r.is_verified_viewer,
        'created_at': r.created_at.strftime('%b %d, %Y'),
        'can_edit': request.user.is_authenticated and r.user == request.user
    } for r in reviews_qs]
    
    # Check if current user is eligible to leave a verified review
    can_review = False
    if request.user.is_authenticated:
        can_review = Booking.objects.filter(
            user=request.user,
            show__movie=movie,
            status='CONFIRMED'
        ).exists()
        
    # Similar movies by genre and language
    similar = Movie.objects.filter(
        is_active=True,
        genres__in=movie.genres.all(),
        language=movie.language
    ).exclude(id=movie.id).distinct().order_by('-avg_rating')[:6]
    
    similar_data = [{
        'id': s.id,
        'title': s.title,
        'slug': s.slug,
        'poster_url': s.poster_url,
        'avg_rating': s.avg_rating
    } for s in similar]
    
    return Response({
        'id': movie.id,
        'title': movie.title,
        'slug': movie.slug,
        'description': movie.description,
        'duration_minutes': movie.duration_minutes,
        'release_date': movie.release_date.strftime('%Y-%m-%d'),
        'age_rating': movie.age_rating,
        'poster_url': movie.poster_url,
        'backdrop_url': movie.backdrop_url,
        'trailer_youtube_url': movie.trailer_youtube_url,
        'youtube_embed_url': movie.youtube_embed_url,
        'avg_rating': movie.avg_rating,
        'total_reviews': movie.total_reviews,
        'language': movie.language.name if movie.language else 'English',
        'genres': [g.name for g in movie.genres.all()],
        'cast': cast_data,
        'reviews': reviews_data,
        'can_review': can_review,
        'similar_movies': similar_data
    })
