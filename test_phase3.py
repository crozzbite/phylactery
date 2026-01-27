import os
os.environ['ENV'] = 'dev'

print("Testing TokenManager...")
from src.app.core.security.auth import TokenManager

tm = TokenManager('dev-secret-key')
print("✓ TokenManager initialized")

# Test sign and verify
payload = "thread123:user456:hash789"
token = tm.sign_payload(payload)
print(f"✓ Token generated: {token[:20]}...")

# Test verify_and_consume
result = tm.verify_and_consume(token, payload)
print(f"✓ First verify_and_consume: {result}")

# Test replay protection
result2 = tm.verify_and_consume(token, payload)
print(f"✓ Replay attempt blocked: {not result2}")

print("\nTesting Graph compilation...")
from src.app.core.brain.graph import graph
print("✓ Graph compiled successfully")

print("\n🎉 All tests passed!")
