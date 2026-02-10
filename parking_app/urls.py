from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'slots', views.ParkingSlotViewSet)
router.register(r'bookings', views.ParkingBookingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('test/', views.test_api, name='test_api'),
    path('get-slots/', views.get_slots, name='get_slots'),
    path('sensor-data/', views.sensor_data, name='sensor_data'),
    path('slots/available/', views.available_slots, name='available_slots'),
    
    # Booking endpoints
    path('create-booking/', views.create_booking, name='create_booking'),
    path('booking-history/', views.booking_history, name='booking_history'),
    path('booking/<str:bill_number>/', views.get_booking_details, name='get_booking_details'),
    path('bookings/search/', views.ParkingBookingViewSet.as_view({'get': 'search'}), name='booking_search'),
    path('all-slots/', views.all_slots, name='all_slots'),
    
    # Active bookings and cancellation
    path('active-bookings/', views.active_bookings, name='active_bookings'),
    path('cancel-booking/', views.cancel_booking, name='cancel_booking'),
    path('extend-booking/', views.extend_booking, name='extend_booking'),
    
    # Payment endpoint
    path('confirm-payment/', views.confirm_payment, name='confirm_payment'),
    
    # QR Code endpoints
    path('booking/<str:bill_number>/qr-code/', views.generate_qr_code, name='generate_qr_code'),
    path('booking/<str:bill_number>/qr-image/', views.get_payment_qr, name='get_payment_qr'),
]