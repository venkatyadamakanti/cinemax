from django.db import models
from django.contrib.auth.models import User
from movies.models import Movie

class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews', db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', db_index=True)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)]) # 1 to 5 stars
    comment = models.TextField()
    is_verified_viewer = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('movie', 'user') # One review per movie per user
        indexes = [
            models.Index(fields=['movie', 'created_at']),
            models.Index(fields=['flagged']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        verified_str = " (Verified)" if self.is_verified_viewer else ""
        return f"{self.user.username}'s {self.rating}★ review for {self.movie.title}{verified_str}"

class ReviewReport(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_reports')
    reason = models.CharField(max_length=255)
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user')

    def __str__(self):
        return f"Report by {self.user.username} on Review #{self.review.id}"
