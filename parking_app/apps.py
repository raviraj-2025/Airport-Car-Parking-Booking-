# parking_app/apps.py
from django.apps import AppConfig

class ParkingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parking_app'  # This MUST be 'parking_app' exactly