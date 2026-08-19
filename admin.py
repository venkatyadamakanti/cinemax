from django.contrib import admin
from .models import Genre, Language, CastMember, Movie, MovieCast, UserMovieView

class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 1

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'language', 'age_rating', 'release_date', 'avg_rating', 'total_bookings', 'is_active')
    list_filter = ('is_active', 'age_rating', 'genres', 'language', 'release_date')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [MovieCastInline]

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role')
    search_fields = ('name', 'role')

@admin.register(UserMovieView)
class UserMovieViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'viewed_at')
