from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name

class CastMember(models.Model):
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=100, default='Actor')
    photo_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

class Movie(models.Model):
    AGE_RATINGS = [
        ('U', 'Universal'),
        ('UA', 'Parental Guidance'),
        ('A', 'Adults Only'),
        ('PG-13', 'Parents Strongly Cautioned'),
        ('R', 'Restricted'),
    ]

    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField()
    duration_minutes = models.IntegerField(default=120)
    release_date = models.DateField(db_index=True)
    genres = models.ManyToManyField(Genre, related_name='movies')
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, related_name='movies')
    age_rating = models.CharField(max_length=10, choices=AGE_RATINGS, default='UA')
    trailer_youtube_url = models.URLField(max_length=500, help_text="YouTube URL or embed link")
    poster_url = models.URLField(max_length=500, blank=True, default="https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800")
    backdrop_url = models.URLField(max_length=500, blank=True, default="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1600")
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Aggregated fields (auto-updated by signals/reviews/bookings)
    avg_rating = models.FloatField(default=0.0, db_index=True)
    total_reviews = models.IntegerField(default=0)
    total_bookings = models.IntegerField(default=0, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['release_date']),
            models.Index(fields=['avg_rating']),
            models.Index(fields=['total_bookings']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-release_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Movie.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def youtube_embed_url(self):
        if not self.trailer_youtube_url:
            return ""
        url = self.trailer_youtube_url
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
            return f"https://www.youtube.com/embed/{video_id}"
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
            return f"https://www.youtube.com/embed/{video_id}"
        return url

    def __str__(self):
        return self.title

class MovieCast(models.Model):
    movie = models.ForeignKey(Movie, on_delete=CASCADE, related_name='cast_members') if False else models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='cast_members')
    cast_member = models.ForeignKey(CastMember, on_delete=models.CASCADE, related_name='movie_appearances')
    character_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.cast_member.name} as {self.character_name} in {self.movie.title}"

class UserMovieView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewed_movies')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='user_views')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.username} viewed {self.movie.title} at {self.viewed_at}"
