import re
import tempfile
import os
from typing import List, Dict, Tuple, TypedDict
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

class PIIFinding(TypedDict):
    type: str # e.g. "EMAIL", "PCI_PAN"
    count: int
    position: int

class SecretFinding(TypedDict):
    type: str
    line: int
    hashed_value: str
    is_verified: bool

class DLPProcessor:
    """
    Data Loss Prevention Processor.
    Responsible for:
    1. Sanitizing PII from text (Ingress).
    2. Detecting Secrets in content (Egress).
    """

    # PII Regex Patterns (Fail-Fast)
    PATTERNS = {
        "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        # Basic Credit Card (13-16 digits grouped) - Failsafe check
        "PCI_PAN": r'(?:\d[ -]*?){13,16}', 
        "IPV4": r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    }

    def sanitize_pii(self, text: str) -> Tuple[str, List[PIIFinding]]:
        """
        Sanitizes PII from input text.
        Returns: (sanitized_text, findings_metadata)
        """
        sanitized_text = text
        findings = []

        for pii_type, pattern in self.PATTERNS.items():
            matches = list(re.finditer(pattern, text))
            # Process in reverse order to keep indices valid during replacement
            for match in reversed(matches):
                start, end = match.span()
                original_value = match.group()
                
                # Special validation for PCI (Luhn could go here, for now simple length check)
                if pii_type == "PCI_PAN":
                    # Remove separators to check digit count
                    digits = re.sub(r'\D', '', original_value)
                    if len(digits) < 13 or len(digits) > 16:
                        continue # False positive
                
                redaction_token = f"[REDACTED_{pii_type}]"
                
                # Replace in text
                sanitized_text = (
                    sanitized_text[:start] + 
                    redaction_token + 
                    sanitized_text[end:]
                )

                findings.append({
                    "type": pii_type,
                    "count": 1,
                    "position": start # approximate original pos
                })
        
        return sanitized_text, findings



    def scan_secrets(self, filename: str = None, content: str = None) -> List[SecretFinding]:
        """
        Scans for secrets (API Keys, Tokens) using detect-secrets.
        Supports scanning a specific file OR content in memory (via temp file).
        """
        findings = []
        target_file = filename
        is_temp = False

        try:
            # 1. Handle Memory Content
            if content is not None:
                tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".scan")
                tmp.write(content)
                tmp.close()
                target_file = tmp.name
                is_temp = True
            
            if not target_file or not os.path.exists(target_file):
                return []

            # 2. Run Detect-Secrets
            secrets = SecretsCollection()
            with default_settings():
                secrets.scan_file(target_file)
            
            # 3. Parse Results
            # SecretsCollection stores results in .data dictionary keyed by filename
            file_results = secrets.data.get(target_file, [])
            
            for secret in file_results:
                findings.append({
                    "type": secret.type, # e.g. "AWS Key"
                    "line": secret.line_number,
                    "hashed_value": secret.secret_hash, # Safe to log
                    "is_verified": secret.is_verified
                })
                
        finally:
            # 4. Cleanup
            if is_temp and target_file and os.path.exists(target_file):
                os.remove(target_file)
        
        return findings

    def validate_ingress(self, prompt: str) -> str:
        """
        Facade for Ingress Sanitization.
        Raises SecurityException logic if CRITICAL PII is found? 
        Or just sanitizes (default).
        """
        clean_text, findings = self.sanitize_pii(prompt)
        if findings:
            # Here we could log (without PII)
            pass
        return clean_text
