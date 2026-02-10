from rest_framework import serializers
from .models import ParkingSlot, ParkingBooking
import math

class ParkingSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSlot
        fields = '__all__'

class ParkingBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingBooking
        fields = '__all__'
        read_only_fields = ['created_at', 'bill_number']
    
    def create(self, validated_data):
        # Calculate initial amount based on booked duration
        duration = (validated_data['booked_until'] - validated_data['booked_from']).total_seconds() / 60
        validated_data['duration_minutes'] = int(duration)
        
        # Calculate amount: ₹10 per hour, NO FREE MINUTES
        hours = math.ceil(duration / 60)
        validated_data['total_amount'] = round(float(hours) * 10.00, 2)
        
        return super().create(validated_data)