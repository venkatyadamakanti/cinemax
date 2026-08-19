from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from movies import views as movie_views
from reviews import views as review_views
from shows import views as show_views
from payments import views as payment_views
from bookings import views as booking_views
from reports import views as report_views
from core import views as core_views

urlpatterns = [
    # Admin Interface (Prompt 3 & 6)
    path('admin/', admin.site.urls),

    # Frontend Single Page Web App Template
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    # Auth APIs
    path('api/auth/register/', core_views.register_api, name='api_register'),
    path('api/auth/login/', core_views.login_api, name='api_login'),
    path('api/auth/logout/', core_views.logout_api, name='api_logout'),
    path('api/auth/user/', core_views.current_user_api, name='api_user'),

    # Movie Discovery & Filtering APIs (Prompt 1)
    path('api/movies/', movie_views.movie_list_api, name='api_movie_list'),
    path('api/movies/count/', movie_views.movie_count_api, name='api_movie_count'),
    path('api/movies/recommendations/', movie_views.recommendations_api, name='api_recommendations'),
    path('api/movies/<slug:slug>/', movie_views.movie_detail_api, name='api_movie_detail'),

    # Review & Rating APIs (Prompt 3)
    path('api/movies/<int:movie_id>/reviews/', review_views.submit_review_api, name='api_submit_review'),
    path('api/reviews/<int:review_id>/edit/', review_views.edit_review_api, name='api_edit_review'),
    path('api/reviews/<int:review_id>/report/', review_views.report_review_api, name='api_report_review'),

    # Seat Reservation APIs (Prompt 5)
    path('api/shows/<int:show_id>/seats/', show_views.show_seats_api, name='api_show_seats'),
    path('api/shows/<int:show_id>/reserve-seats/', show_views.reserve_seats_api, name='api_reserve_seats'),

    # Payment & Webhook APIs (Prompt 4)
    path('api/payments/initiate/', payment_views.initiate_payment_api, name='api_initiate_payment'),
    path('api/payments/webhook/', payment_views.payment_webhook_or_confirm_api, name='api_payment_webhook'),

    # Booking & Ticket History APIs (Prompt 2)
    path('api/bookings/history/', booking_views.user_booking_history_api, name='api_booking_history'),
    path('api/bookings/<uuid:booking_id>/download-ticket/', booking_views.download_ticket_pdf_api, name='api_download_ticket'),

    # Admin Real-time Analytics Dashboard APIs (Prompt 6)
    path('api/analytics/dashboard/', report_views.admin_analytics_api, name='api_admin_analytics'),
    path('api/analytics/export-csv/', report_views.export_analytics_csv_api, name='api_export_csv'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
