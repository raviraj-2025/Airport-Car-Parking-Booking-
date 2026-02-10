from django.db import models
from django.utils import timezone
import uuid
import math

class ParkingSlot(models.Model):
    slot_number = models.CharField(max_length=10, unique=True)
    floor_number = models.IntegerField(default=1)
    is_occupied = models.BooleanField(default=False)
    is_reserved = models.BooleanField(default=False)
    sensor_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.slot_number} - {self.sensor_id}"

class ParkingBooking(models.Model):
    STATUS_CHOICES = [
        ('reserved', 'Reserved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('paid', 'Paid'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('wallet', 'Wallet'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    bill_number = models.CharField(max_length=20, unique=True)
    vehicle_number = models.CharField(max_length=20)
    owner_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    parking_slot = models.CharField(max_length=10)
    
    # Booking times
    booked_from = models.DateTimeField()
    booked_until = models.DateTimeField()
    actual_entry_time = models.DateTimeField(null=True, blank=True)
    actual_exit_time = models.DateTimeField(null=True, blank=True)
    
    # Status and amounts
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='reserved')
    duration_minutes = models.IntegerField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    
    # Payment details
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cash')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    upi_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional info
    sensor_id = models.CharField(max_length=50, blank=True, null=True)
    floor_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.bill_number:
            self.bill_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate amount if not set
        if self.total_amount == 0 and self.booked_from and self.booked_until:
            duration = (self.booked_until - self.booked_from).total_seconds() / 60
            self.duration_minutes = int(duration)
            
            # ₹10 per hour, NO FREE MINUTES, round up to nearest hour
            hours = math.ceil(duration / 60)
            self.total_amount = round(float(hours) * 10.00, 2)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.bill_number} - {self.vehicle_number} - {self.status}"
    
    def generate_payment_qr_data(self):
        """Generate QR code data for UPI payment"""
        import qrcode
        import base64
        from io import BytesIO
        
        # Create UPI payment URL
        upi_id = "ravirajvibhute09@okicici"  # Replace with your actual UPI ID
        amount = float(self.total_amount)
        
        # UPI payment URL format
        upi_url = f"upi://pay?pa={upi_id}&pn=Smart%20Parking%20System&am={amount}&tn=Parking%20Bill%20{self.bill_number}"
        
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
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            'upi_url': upi_url,
            'qr_code_base64': img_str,
            'amount': amount,
            'bill_number': self.bill_number
        }