from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from .models import ParkingSlot, ParkingBooking
from .serializers import ParkingSlotSerializer, ParkingBookingSerializer
from datetime import datetime
import math
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
import json

# Add test endpoint at the top
@api_view(['GET'])
def test_api(request):
    """Test if API is working"""
    return Response({
        'status': 'success',
        'message': 'API is working!',
        'timestamp': timezone.now().isoformat()
    })

class ParkingSlotViewSet(viewsets.ModelViewSet):
    queryset = ParkingSlot.objects.all()
    serializer_class = ParkingSlotSerializer

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available parking slots"""
        available_slots = ParkingSlot.objects.filter(is_occupied=False, is_reserved=False)
        serializer = self.get_serializer(available_slots, many=True)
        return Response(serializer.data)

class ParkingBookingViewSet(viewsets.ModelViewSet):
    queryset = ParkingBooking.objects.all().order_by('-created_at')
    serializer_class = ParkingBookingSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search bookings by various criteria"""
        query = request.query_params.get('q', '')
        if query:
            bookings = ParkingBooking.objects.filter(
                Q(vehicle_number__icontains=query) |
                Q(owner_name__icontains=query) |
                Q(phone_number__icontains=query) |
                Q(bill_number__icontains=query) |
                Q(parking_slot__icontains=query)
            ).order_by('-created_at')
        else:
            bookings = ParkingBooking.objects.all().order_by('-created_at')
        
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def get_slots(request):
    """Get all parking slots"""
    try:
        slots = ParkingSlot.objects.all()
        serializer = ParkingSlotSerializer(slots, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def sensor_data(request):
    """Handle sensor data updates"""
    sensor_id = request.data.get('sensor_id')
    is_occupied = request.data.get('is_occupied')
    
    try:
        slot = ParkingSlot.objects.get(sensor_id=sensor_id)
        
        # Update slot status
        slot.is_occupied = is_occupied
        slot.save()
        
        # Handle vehicle entry
        if is_occupied:
            # Find active booking for this slot
            active_booking = ParkingBooking.objects.filter(
                parking_slot=slot.slot_number,
                status='reserved',
                booked_from__lte=timezone.now(),
                booked_until__gte=timezone.now()
            ).first()
            
            if active_booking:
                active_booking.status = 'active'
                active_booking.actual_entry_time = timezone.now()
                active_booking.save()
                
        # Handle vehicle exit
        else:
            # Find active booking for this slot
            active_booking = ParkingBooking.objects.filter(
                parking_slot=slot.slot_number,
                status='active'
            ).first()
            
            if active_booking:
                # Complete the booking
                active_booking.status = 'completed'
                active_booking.actual_exit_time = timezone.now()
                
                # Calculate actual amount
                entry_time = active_booking.actual_entry_time or active_booking.booked_from
                exit_time = active_booking.actual_exit_time
                duration = (exit_time - entry_time).total_seconds() / 60
                active_booking.duration_minutes = int(duration)
                
                # Calculate with fixed rate of ₹10 per hour, NO FREE MINUTES
                hours = math.ceil(duration / 60)
                active_booking.total_amount = round(float(hours) * 10.00, 2)
                
                active_booking.save()
                
                # Free the slot
                slot.is_reserved = False
                slot.is_occupied = False
                slot.save()
        
        return Response({
            'status': 'success', 
            'slot_number': slot.slot_number,
            'sensor_id': sensor_id,
            'is_occupied': is_occupied,
            'timestamp': timezone.now().isoformat()
        })
        
    except ParkingSlot.DoesNotExist:
        return Response({'error': 'Sensor not found'}, status=404)

@api_view(['POST'])
def create_booking(request):
    """Create a new parking booking"""
    try:
        data = request.data
        
        # Get the parking slot
        slot_number = data.get('parking_slot')
        try:
            slot = ParkingSlot.objects.get(slot_number=slot_number)
            
            # Check if slot is available
            if slot.is_occupied or slot.is_reserved:
                return Response({
                    'error': f'Slot {slot_number} is already occupied or reserved'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Reserve the slot
            slot.is_reserved = True
            slot.save()
            
        except ParkingSlot.DoesNotExist:
            return Response({'error': 'Parking slot not found'}, status=404)
        
        # Parse datetime strings
        booked_from_str = data.get('booked_from')
        booked_until_str = data.get('booked_until')
        
        try:
            # Handle timezone aware strings
            if 'Z' in booked_from_str:
                booked_from = datetime.fromisoformat(booked_from_str.replace('Z', '+00:00'))
                booked_until = datetime.fromisoformat(booked_until_str.replace('Z', '+00:00'))
            else:
                booked_from = datetime.fromisoformat(booked_from_str)
                booked_until = datetime.fromisoformat(booked_until_str)
        except Exception as e:
            return Response({'error': f'Invalid datetime format: {str(e)}'}, status=400)
        
        # Validate booking duration (minimum 1 hour)
        duration = (booked_until - booked_from).total_seconds() / 60
        if duration < 60:
            return Response({
                'error': 'Minimum booking duration is 1 hour'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create booking data with fixed rate
        booking_data = {
            'vehicle_number': data['vehicle_number'],
            'owner_name': data['owner_name'],
            'phone_number': data['phone_number'],
            'parking_slot': slot_number,
            'booked_from': booked_from,
            'booked_until': booked_until,
            'sensor_id': slot.sensor_id,
            'floor_number': slot.floor_number,
            'status': 'reserved'
        }
        
        serializer = ParkingBookingSerializer(data=booking_data)
        if serializer.is_valid():
            booking = serializer.save()
            
            return Response({
                'status': 'success',
                'message': 'Parking booking created successfully',
                'bill_number': booking.bill_number,
                'vehicle_number': booking.vehicle_number,
                'owner_name': booking.owner_name,
                'phone_number': booking.phone_number,
                'parking_slot': booking.parking_slot,
                'duration_minutes': int(duration),
                'total_amount': booking.total_amount,
                'booking': serializer.data,
                'slot_reserved': True,
                'slot_number': slot_number
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_booking_details(request, bill_number):
    """Get detailed booking information"""
    try:
        booking = ParkingBooking.objects.get(bill_number=bill_number)
        serializer = ParkingBookingSerializer(booking)
        
        # Calculate breakdown with fixed rate
        duration_minutes = booking.duration_minutes or 0
        
        breakdown = []
        hours = math.ceil(duration_minutes / 60)
        
        for i in range(1, hours + 1):
            if i == 1:
                description = f"First hour"
            else:
                description = f"Hour {i}"
            
            breakdown.append({
                'description': description,
                'rate': '₹10/hour',
                'amount': 10.00
            })
        
        # Generate QR code data for payment
        qr_data = generate_qr_data(booking)
        
        response_data = serializer.data
        response_data['breakdown'] = breakdown
        response_data['qr_data'] = qr_data
        
        return Response(response_data)
        
    except ParkingBooking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)

def generate_qr_data(booking):
    """Generate QR code data for UPI payment"""
    # Create UPI payment URL
    upi_id = "ravirajvibhute09@okicici"  # Replace with your actual UPI ID
    amount = float(booking.total_amount)
    
    # UPI payment URL format: upi://pay?pa=UPI_ID&pn=MerchantName&am=Amount&tn=TransactionNote
    upi_url = f"upi://pay?pa={upi_id}&pn=Smart%20Parking%20System&am={amount}&tn=Parking%20Bill%20{booking.bill_number}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert image to base64 string
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        'upi_url': upi_url,
        'upi_id': upi_id,
        'amount': amount,
        'bill_number': booking.bill_number,
        'qr_code_base64': img_str,
        'payment_details': {
            'payee_name': 'Smart Parking System',
            'transaction_note': f'Parking Bill: {booking.bill_number}',
            'currency': 'INR'
        }
    }

@api_view(['GET'])
def generate_qr_code(request, bill_number):
    """Generate and return QR code image for payment"""
    try:
        booking = ParkingBooking.objects.get(bill_number=bill_number)
        
        # Generate QR code data
        qr_data = generate_qr_data(booking)
        
        # Return QR code as base64 string
        return Response({
            'status': 'success',
            'bill_number': bill_number,
            'amount': float(booking.total_amount),
            'qr_code': qr_data['qr_code_base64'],
            'upi_url': qr_data['upi_url'],
            'payment_url': qr_data['upi_url']
        })
        
    except ParkingBooking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_payment_qr(request, bill_number):
    """Generate QR code image and return as PNG response"""
    try:
        booking = ParkingBooking.objects.get(bill_number=bill_number)
        
        # Create UPI payment URL
        upi_id = "ravirajvibhute09@okicici"  # Replace with your actual UPI ID
        amount = float(booking.total_amount)
        upi_url = f"upi://pay?pa={upi_id}&pn=Smart%20Parking%20System&am={amount}&tn=Parking%20Bill%20{booking.bill_number}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes buffer
        buffer = BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)
        
        # Return image response
        from django.http import HttpResponse
        response = HttpResponse(buffer.getvalue(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="payment_qr_{bill_number}.png"'
        return response
        
    except ParkingBooking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)

@api_view(['GET'])
def available_slots(request):
    """Get all available parking slots"""
    available_slots = ParkingSlot.objects.filter(is_occupied=False, is_reserved=False)
    serializer = ParkingSlotSerializer(available_slots, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def booking_history(request):
    """Get all booking history"""
    bookings = ParkingBooking.objects.all().order_by('-created_at')
    serializer = ParkingBookingSerializer(bookings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def all_slots(request):
    """Get ALL parking slots (available, reserved, occupied)"""
    all_slots = ParkingSlot.objects.all().order_by('slot_number')
    serializer = ParkingSlotSerializer(all_slots, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def active_bookings(request):
    """Get all active bookings (reserved and active status)"""
    now = timezone.now()
    active_bookings = ParkingBooking.objects.filter(
        Q(status='reserved') | Q(status='active'),
        booked_until__gt=now
    ).order_by('booked_from')
    
    serializer = ParkingBookingSerializer(active_bookings, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def cancel_booking(request):
    """Cancel an active booking"""
    try:
        bill_number = request.data.get('bill_number')
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        if not bill_number:
            return Response({'error': 'Bill number is required'}, status=400)
        
        with transaction.atomic():
            # Get the booking
            booking = ParkingBooking.objects.get(bill_number=bill_number)
            
            # Check if booking can be cancelled
            if booking.status not in ['reserved', 'active']:
                return Response({
                    'error': f'Booking with status "{booking.status}" cannot be cancelled'
                }, status=400)
            
            # Get the parking slot
            try:
                slot = ParkingSlot.objects.get(slot_number=booking.parking_slot)
                
                # Free the slot
                slot.is_reserved = False
                slot.is_occupied = False
                slot.save()
                
                # Update booking status
                booking.status = 'cancelled'
                booking.cancelled_at = timezone.now()
                booking.cancellation_reason = cancellation_reason
                booking.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Booking cancelled successfully',
                    'bill_number': booking.bill_number,
                    'parking_slot': booking.parking_slot,
                    'slot_freed': True
                })
                
            except ParkingSlot.DoesNotExist:
                return Response({'error': 'Parking slot not found'}, status=404)
                
    except ParkingBooking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def extend_booking(request):
    """Extend an active booking"""
    try:
        bill_number = request.data.get('bill_number')
        new_exit_time_str = request.data.get('new_exit_time')
        
        if not bill_number or not new_exit_time_str:
            return Response({'error': 'Bill number and new exit time are required'}, status=400)
        
        # Parse new exit time
        try:
            if 'Z' in new_exit_time_str:
                new_exit_time = datetime.fromisoformat(new_exit_time_str.replace('Z', '+00:00'))
            else:
                new_exit_time = datetime.fromisoformat(new_exit_time_str)
        except Exception as e:
            return Response({'error': f'Invalid datetime format: {str(e)}'}, status=400)
        
        # Get the booking
        booking = ParkingBooking.objects.get(bill_number=bill_number)
        
        # Check if booking can be extended
        if booking.status not in ['reserved', 'active']:
            return Response({
                'error': f'Booking with status "{booking.status}" cannot be extended'
            }, status=400)
        
        if new_exit_time <= booking.booked_until:
            return Response({
                'error': 'New exit time must be after current exit time'
            }, status=400)
        
        # Calculate additional duration
        additional_minutes = (new_exit_time - booking.booked_until).total_seconds() / 60
        
        if additional_minutes < 60:
            return Response({
                'error': 'Minimum extension is 1 hour'
            }, status=400)
        
        # Calculate additional amount
        additional_hours = math.ceil(additional_minutes / 60)
        additional_amount = round(float(additional_hours) * 10.00, 2)
        
        # Update booking
        booking.booked_until = new_exit_time
        booking.total_amount += additional_amount
        
        if booking.duration_minutes:
            booking.duration_minutes += int(additional_minutes)
        
        booking.save()
        
        return Response({
            'status': 'success',
            'message': 'Booking extended successfully',
            'bill_number': booking.bill_number,
            'additional_amount': additional_amount,
            'new_total_amount': booking.total_amount,
            'new_exit_time': new_exit_time
        })
        
    except ParkingBooking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def confirm_payment(request):
    """Confirm payment for a booking"""
    try:
        bill_number = request.data.get('bill_number')
        
        if not bill_number:
            return Response({'error': 'Bill number is required'}, status=400)
        
        booking = ParkingBooking.objects.get(bill_number=bill_number)
        
        # Update booking payment status
        booking.is_paid = True
        
        # If booking is completed and paid, update status
        if booking.status == 'completed':
            booking.status = 'paid'
        elif booking.status == 'reserved' or booking.status == 'active':
            # Mark as paid but keep the current status
            pass
        
        booking.save()
        
        return Response({
            'status': 'success',
            'message': 'Payment confirmed successfully',
            'bill_number': booking.bill_number,
            'amount': booking.total_amount,
            'is_paid': booking.is_paid,
            'status': booking.status
        })
        
    except ParkingBooking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)