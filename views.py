from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Review, ReviewReport
from movies.models import Movie
from bookings.models import Booking

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_review_api(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    rating = request.data.get('rating')
    comment = request.data.get('comment', '').strip()

    if not rating or not str(rating).isdigit() or not (1 <= int(rating) <= 5):
        return Response({'error': 'Rating must be an integer between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)

    # Verified viewer check: User must have booked and watched the movie
    has_booked_and_watched = Booking.objects.filter(
        user=request.user,
        show__movie=movie,
        status='CONFIRMED',
        show__start_time__lte=timezone.now()
    ).exists()

    if not has_booked_and_watched:
        return Response({
            'error': 'Only verified viewers who have booked and watched this show can submit a review.'
        }, status=status.HTTP_403_FORBIDDEN)

    review, created = Review.objects.update_or_create(
        movie=movie,
        user=request.user,
        defaults={
            'rating': int(rating),
            'comment': comment,
            'is_verified_viewer': True,
        }
    )

    return Response({
        'message': 'Review submitted successfully!',
        'review_id': review.id,
        'rating': review.rating,
        'is_verified_viewer': review.is_verified_viewer
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_review_api(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    rating = request.data.get('rating')
    comment = request.data.get('comment', '').strip()

    if rating and str(rating).isdigit() and (1 <= int(rating) <= 5):
        review.rating = int(rating)
    if comment:
        review.comment = comment

    review.save()
    return Response({'message': 'Review updated successfully.'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_review_api(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    reason = request.data.get('reason', 'Inappropriate content').strip()

    report, created = ReviewReport.objects.get_or_create(
        review=review,
        user=request.user,
        defaults={'reason': reason}
    )

    # Flag review if multiple reports received
    if review.reports.count() >= 2:
        review.flagged = True
        review.save(update_fields=['flagged'])

    return Response({
        'message': 'Report submitted. Thank you for helping keep our community safe.',
        'review_flagged': review.flagged
    })
