from django.contrib import admin
from .models import ParkingSlot, ParkingBooking

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ['slot_number', 'sensor_id', 'is_occupied', 'is_reserved', 'created_at']
    list_filter = ['is_occupied', 'is_reserved', 'floor_number']
    search_fields = ['slot_number', 'sensor_id']

@admin.register(ParkingBooking)
class ParkingBookingAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'vehicle_number', 'owner_name', 'parking_slot', 
                    'status', 'total_amount', 'created_at']
    list_filter = ['status', 'is_paid', 'created_at']
    search_fields = ['bill_number', 'vehicle_number', 'owner_name', 'phone_number']
    readonly_fields = ['created_at']
    fieldsets = [
        ('Booking Information', {
            'fields': ['bill_number', 'vehicle_number', 'owner_name', 'phone_number']
        }),
        ('Parking Details', {
            'fields': ['parking_slot', 'sensor_id', 'floor_number']
        }),
        ('Timing', {
            'fields': ['booked_from', 'booked_until', 'actual_entry_time', 'actual_exit_time']
        }),
        ('Payment', {
            'fields': ['status', 'total_amount', 'is_paid', 'rate_per_hour', 'free_minutes']
        }),
        ('Cancellation', {
            'fields': ['cancelled_at', 'cancellation_reason'],
            'classes': ['collapse']
        }),
    ]