from django.contrib import admin
from .models import Review, ReviewReport

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('movie', 'user', 'rating', 'is_verified_viewer', 'flagged', 'created_at')
    list_filter = ('rating', 'is_verified_viewer', 'flagged')
    search_fields = ('movie__title', 'user__username', 'comment')

@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'reason', 'reported_at')
