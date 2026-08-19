from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Review

@receiver([post_save, post_delete], sender=Review)
def update_movie_rating_stats(sender, instance, **kwargs):
    movie = instance.movie
    aggregate = movie.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    movie.avg_rating = round(aggregate['avg'] or 0.0, 1)
    movie.total_reviews = aggregate['count'] or 0
    movie.save(update_fields=['avg_rating', 'total_reviews'])
