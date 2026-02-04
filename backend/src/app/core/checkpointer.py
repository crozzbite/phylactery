import logging
import pickle

from langgraph.checkpoint.serde.base import SerializerProtocol

from .security.encryption import encryptor

logger = logging.getLogger("core.persistence")

class EncryptedSerializer(SerializerProtocol):
    """
    Serializer that encrypts data using Fernet before saving, 
    and decrypts it after loading.
    
    Format: Encrypted(Pickle(Object))
    """
    def dumps(self, obj: object) -> bytes:
        try:
            data = pickle.dumps(obj)
            return encryptor.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption serialization failed: {e}")
            raise

    def loads(self, data: bytes) -> object:
        if not data:
            return None
        try:
            decrypted = encryptor.decrypt(data)
            return pickle.loads(decrypted)
        except Exception as e:
            logger.error(f"Decryption deserialization failed: {e}")
            raise
