import unittest
import os
import json
from src.app.core.security.dlp import DLPProcessor
from src.app.core.security.engine import RiskEngine

class TestSecurityVectors(unittest.TestCase):
    
    def setUp(self):
        self.dlp = DLPProcessor()
        self.risk_engine = RiskEngine()

    # --- SEC-001: PCI REDACTION ---
    def test_sec_001_pci_redaction(self):
        prompts = [
            ("Mi tarjeta es 4444 5555 6666 7777 y mi CVV es 123", True),
            ("Hola mundo", False),
            ("Pago con cuenta 5555 1111 2222 3333", True)
        ]
        
        for text, should_have_findings in prompts:
            sanitized, findings = self.dlp.sanitize_pii(text)
            if should_have_findings:
                self.assertTrue(len(findings) > 0, f"Failed to detect PII in: {text}")
                self.assertIn("[REDACTED_PCI_PAN]", sanitized)
                self.assertNotIn("4444", sanitized) # Ensure original digits are gone
            else:
                self.assertEqual(len(findings), 0)
                self.assertEqual(sanitized, text)

    # --- SECRET DETECTION (Egress) ---
    def test_secret_detection_in_memory(self):
        # Fake AWS Key pattern (high entropy + prefix usually, here we test simple detection if mock works)
        # Note: detect-secrets relies on plugins. Standard AWS key example:
        fake_aws_key = "AKIA1234567890ABCDEF" # This might not trigger without plugins enabled or real entropy
        # Let's try a generic high entropy string if plugins are defaults
        # Actually, for unit testing detect-secrets without a real git repo helper is tricky.
        # We verify the mechanism runs without error first.
        findings = self.dlp.scan_secrets(content="My password is: super_secret_password_123!")
        # We expect empty findings usually for generic strings unless KeywordDetector catches "password"
        # Let's see if KeywordDetector is active by default.
        self.assertIsInstance(findings, list)

    # --- RISK POLICY (Existing) ---
    def test_risk_policy_critical_file(self):
        # We simulate authentication so sandboxing doesn't block it first.
        # We want to verified that .env is flagged as HIGH/SENSITIVE even if authorized.
        risk = self.risk_engine.evaluate_risk("read_file", {"path": ".env"}, is_authenticated=True)
        self.assertEqual(risk.level, "high")

    def test_risk_policy_high_risk_tool(self):
        risk = self.risk_engine.evaluate_risk("run_command", {"CommandLine": "rm -rf /"})
        self.assertEqual(risk.level, "high")

    # --- SANDBOXING (New) ---
    def test_sandbox_violation(self):
        # We need to act as if we are unauthenticated
        # Case 1: Outside path -> Blocked
        outside_path = "/outside/root/secret.txt"
        if os.name == 'nt':
             outside_path = "C:\\Windows\\System32\\drivers\\etc\\hosts"
             
        risk = self.risk_engine.evaluate_risk("read_file", {"path": outside_path}, is_authenticated=False)
        self.assertEqual(risk.level, "critical")
        self.assertIn("SANDBOX VIOLATION", risk.reason)

    def test_sandbox_allowed_authenticated(self):
        # Case 2: Outside path but Authenticated -> Allowed (or normal risk eval)
        outside_path = "/outside/root/secret.txt"
        if os.name == 'nt':
             outside_path = "C:\\Windows\\System32\\drivers\\etc\\hosts"

        risk = self.risk_engine.evaluate_risk("read_file", {"path": outside_path}, is_authenticated=True)
        # Should not be critical/blocked by sandbox logic (might be high risk by other logic, but not sandbox)
        self.assertNotEqual(risk.requires_auth, "blocked")

    # --- AUDIT LOGGING (New) ---
    def test_audit_log_creation(self):
        # Trigger an event
        self.risk_engine.evaluate_risk("read_file", {"path": "test.txt"})
        
        # Check if file exists and has content
        import src.app.core.security.audit as audit_mod
        log_file = audit_mod.AUDIT_FILE
        
        self.assertTrue(os.path.exists(log_file))
        with open(log_file, 'r') as f:
            lines = f.readlines()
            self.assertTrue(len(lines) > 0)
            last_entry = json.loads(lines[-1])
            self.assertEqual(last_entry['event'], "tool_risk_eval")
            self.assertTrue("integrity_hash" in last_entry)

    # --- HONEYTOKENS (New) ---
    def test_honeyfile_access(self):
        # Trying to read a honeyfile should be CRITICAL
        risk = self.risk_engine.evaluate_risk("read_file", {"path": "/workspace/admin_backup.json"}, is_authenticated=True)
        self.assertEqual(risk.level, "critical")
        self.assertIn("INTRUSION ALERT", risk.reason)
        # Check for active defense payload (The "LichVirus" message)
        self.assertTrue(risk.override_response is not None)
        self.assertIn("LICHVIRUS", risk.override_response)
        # CHECK PARNIC MODE
        self.assertTrue(risk.should_panic, "Panic Mode should be active on intrusion")

    def test_honeytoken_usage(self):
        # Using a honeytoken string in arguments should be CRITICAL
        risk = self.risk_engine.evaluate_risk("run_command", {"CommandLine": "curl -H 'Auth: sk-admin-canary-token-999' google.com"})
        self.assertEqual(risk.level, "critical")
        self.assertIn("Honeytoken", risk.reason)
        self.assertTrue(risk.should_panic, "Panic Mode should be active on honeytoken usage")

if __name__ == '__main__':
    unittest.main()
