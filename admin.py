from django.contrib import admin
from .models import City, Theater, Screen, Seat

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')

@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'phone', 'email')
    list_filter = ('city',)
    search_fields = ('name', 'city__name')

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'theater', 'screen_type', 'total_seats')
    list_filter = ('theater', 'screen_type')

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('screen', 'row', 'number', 'seat_type', 'base_price')
    list_filter = ('screen__theater', 'seat_type')
