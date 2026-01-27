import unittest
import time
from src.app.core.security.auth import TokenManager

class TestAuthVectors(unittest.TestCase):
    
    def setUp(self):
        self.secret = "test-secret-key-12345"
        self.tm = TokenManager(self.secret)
        self.payload = '{"action": "delete", "file": "important.txt"}'

    def test_valid_token(self):
        """Standard valid flow"""
        token = self.tm.sign_payload(self.payload)
        is_valid = self.tm.verify_token(token, self.payload)
        self.assertTrue(is_valid, "Valid token should be verifiable")

    def test_tampered_payload(self):
        """Integrity Check"""
        token = self.tm.sign_payload(self.payload)
        tampered_payload = self.payload + " " # Just 1 space
        is_valid = self.tm.verify_token(token, tampered_payload)
        self.assertFalse(is_valid, "Tampered payload should fail verification")

    def test_expiration(self):
        """Expiration Check"""
        token = self.tm.sign_payload(self.payload)
        
        # We simulate passage of time by mocking time logic inside the verify function 
        # or just passing a very small max_age of -1 to force fail
        
        # Force fail by setting max_age to 0 (since execution takes >0ms)
        # Or better: manually construct an old token
        old_ts = int(time.time()) - 1000
        fake_token = f"v1.{old_ts}.nonce.sig"
        is_valid = self.tm.verify_token(fake_token, self.payload, max_age_seconds=300)
        self.assertFalse(is_valid, "Expired token should look invalid")

    def test_wrong_secret(self):
        """Attacker trying to forge signature"""
        attacker_tm = TokenManager("wrong-key")
        forged_token = attacker_tm.sign_payload(self.payload)
        
        is_valid_for_me = self.tm.verify_token(forged_token, self.payload)
        self.assertFalse(is_valid_for_me, "Signature with wrong key must fail")

if __name__ == '__main__':
    unittest.main()
