from django.contrib import admin
from .models import Show, ShowSeat

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ('movie', 'screen', 'start_time', 'ticket_price', 'is_cancelled')
    list_filter = ('movie', 'screen__theater', 'is_cancelled', 'start_time')
    search_fields = ('movie__title', 'screen__theater__name')

@admin.register(ShowSeat)
class ShowSeatAdmin(admin.ModelAdmin):
    list_display = ('show', 'seat', 'status', 'reserved_until', 'reserved_by')
    list_filter = ('status', 'show__movie')
