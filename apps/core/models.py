from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class BinanceModel(models.Model):
    """
    Modelo abstracto para manejar la encriptación de claves API usando Fernet.
    Se puede heredar en otros modelos como TradingSettings.
    """

    class Meta:
        abstract = True

    def encrypt_data(self, data):
        """Encriptar los datos con la clave de Fernet."""
        fernet = Fernet(settings.ENCRYPTED_FIELDS_KEY)
        return fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, data):
        """Desencriptar los datos con la clave de Fernet."""
        fernet = Fernet(settings.ENCRYPTED_FIELDS_KEY)
        return fernet.decrypt(data.encode()).decode()

    @property
    def api_key_token(self):
        """Método para obtener el api_key desencriptado"""
        return self.decrypt_data(self.api_key)

    @property
    def api_secret_token(self):
        """Método para obtener el api_secret desencriptado"""
        return self.decrypt_data(self.api_secret)
