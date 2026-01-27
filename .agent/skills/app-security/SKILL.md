---
name: app-security
description: Security utilities for PII sanitization and Secret Detection using regex and detect-secrets.
metadata:
  version: "1.0.0"
  author: "SkullRender"
  tags: ["security", "dlp", "pii", "secrets", "compliance"]
  dependencies:
    - "detect-secrets"
---

# App Security Skill

Este skill proporciona las herramientas y guías para asegurar que el código y los datos manejados por Phylactery estén libres de secretos (API Keys, tokens) y PII (Información de Identificación Personal).

## 🚦 PR Verification Workflow (CI Gate)
Antes de crear cualquier Pull Request o realizar cambios críticos, el Agente DEBE ejecutar los tests de vectores de seguridad. Si fallan, se ABORTA la operación.

```bash
python -m src.app.core.security.test_security_vectors
python -m src.app.core.security.test_auth_vectors
```

## 🛡️ Detección de Secretos (detect-secrets)

Phylactery adopta `detect-secrets` (Yelp) como estándar para escanear archivos antes de leerlos o escribirlos.

### Instalación
```bash
pip install detect-secrets
```

### Uso Programático (Python)

El Agente debe usar estas funciones para validar contenido:

```python
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

def scan_text_for_secrets(content: str) -> list[dict]:
    """
    Escanea un string en memoria buscando secretos.
    Retorna una lista de hallazgos.
    """
    secrets = SecretsCollection()
    # Nota: scan_file requiere un archivo físico.
    # Para scanear strings en memoria, usaremos una lógica wrapper o archivo temporal.
    # Aquí un ejemplo canónico de configuración:
    with default_settings():
        # Lógica personalizada del agente
        pass
    
    #... lógica de parsing de resultados ...
    return findings
```

### Uso en CLI (Auditoría Manual)
Para auditar el repositorio:
```bash
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline
```

## 🔍 Sanitización de PII (Regex)

Para PII estructurada, usamos reglas regex "Fail-Fast".

### Patrones Soportados
- **Email:** `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+`
- **Credit Card (Potential):** `(?:\d[ -]*?){13,16}` (Requiere validación Luhn adicional)
- **IPv4:** `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b`

### Estrategia de Redacción
Todo match debe ser reemplazado por un token opaco:
- `user@example.com` -> `[REDACTED_EMAIL]`
- `4444 5555...` -> `[REDACTED_PCI]`

## 🚨 Reglas de Uso para el Agente

1.  **Ingress Guard:** NUNCA procesar texto del usuario sin pasarlo por `sanitize_pii()` primero.
2.  **Egress Guard:** NUNCA escribir archivos (`write_file`) sin escanear con `scan_secrets()`.
3.  **Logs:** NUNCA loguear el contenido raw si se detectó un secreto/PII. Loguear solo "DLP Filter Triggered".
4.  **Falsos Positivos:** Si un secreto es falso, usar `# pragma: allowlist secret` con precaución.

## 🔑 HMAC Approval Signing (AuthModule)

Para flujos de aprobación humana (HITL), usamos firmas HMAC-SHA256 para garantizar la integridad del payload.

### Estructura del Token
El token no es solo un hash, es un sobre con: `version.timestamp.nonce.signature`.

### Implementación Estándar (Python)

```python
import hmac
import hashlib
import time
import secrets
import base64

class TokenManager:
    def __init__(self, secret_key: str):
        self.secret = secret_key.encode()

    def sign_payload(self, payload: str) -> str:
        """Genera un token firmado para un payload."""
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)
        
        # Data to sign: timestamp + nonce + payload
        msg = f"{timestamp}:{nonce}:{payload}".encode()
        
        signature = hmac.new(self.secret, msg, hashlib.sha256).hexdigest()
        
        # Token format: v1.timestamp.nonce.signature
        return f"v1.{timestamp}.{nonce}.{signature}"

    def verify_token(self, token: str, payload: str, max_age_seconds=300) -> bool:
        """Valida firma y expiración."""
        try:
            ver, ts, nonce, sig = token.split('.')
            if ver != "v1": return False
            
            # 1. Check Expiration
            if time.time() - int(ts) > max_age_seconds:
                return False
                
            # 2. Re-compute signature
            msg = f"{ts}:{nonce}:{payload}".encode()
            expected_sig = hmac.new(self.secret, msg, hashlib.sha256).hexdigest()
            
            # 3. Constant time compare
            return hmac.compare_digest(sig, expected_sig)
        except Exception:
            return False
```
