from django.core.management.base import BaseCommand
from parking_app.models import ParkingSlot

class Command(BaseCommand):
    help = 'Create initial parking slots with sensors'

    def handle(self, *args, **options):
        slots_data = [
            {'slot_number': 'A01', 'sensor_id': 'SENSOR_001', 'floor_number': 1},
            {'slot_number': 'A02', 'sensor_id': 'SENSOR_002', 'floor_number': 1},
            {'slot_number': 'A03', 'sensor_id': 'SENSOR_003', 'floor_number': 1},
            {'slot_number': 'A04', 'sensor_id': 'SENSOR_004', 'floor_number': 1},
        ]
        
        for slot_data in slots_data:
            slot, created = ParkingSlot.objects.get_or_create(
                slot_number=slot_data['slot_number'],
                defaults={
                    'sensor_id': slot_data['sensor_id'],
                    'floor_number': slot_data['floor_number']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created slot: {slot.slot_number} (Sensor: {slot.sensor_id})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Slot already exists: {slot.slot_number}')
                )
        
        self.stdout.write(self.style.SUCCESS('🎉 Parking slots initialization complete!'))