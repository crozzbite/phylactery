import os
import httpx
from typing import Dict
from src.app.core.security.audit import AuditLogger

class N8NGuardedBridge:
    """
    Secure Bridge for n8n automation flows.
    Enforces allowlisting and audits all execution attempts.
    """
    
    def __init__(self) -> None:
        self.n8n_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.n8n_api_key = os.getenv("N8N_API_KEY")
        self.audit = AuditLogger("n8n_bridge_audit.jsonl")
        
        # Security Allowlist: only these flow IDs are allowed to be triggered by the agent
        self.ALLOWED_FLOWS = [
            "send_notification",
            "log_to_sheets",
            "trigger_deploy",
            "send_slack_alert"
        ]

    async def trigger_flow(
        self, 
        flow_id: str, 
        payload: Dict[str, object], 
        user_id: str
    ) -> Dict[str, object]:
        """
        Triggers an n8n webhook only if the flow_id is allowlisted.
        """
        # 1. Allowlist Validation
        if flow_id not in self.ALLOWED_FLOWS:
            await self.audit.log_event(
                "N8N_FLOW_UNAUTHORIZED",
                {"user_id": user_id, "flow_id": flow_id},
                "BLOCKED", "HIGH",
                user_id=user_id
            )
            return {
                "status": "error",
                "message": f"Flow ID '{flow_id}' is not in the allowlist."
            }
            
        # 2. Audit Authorized Execution
        await self.audit.log_event(
            "N8N_FLOW_TRIGGERED",
            {"user_id": user_id, "flow_id": flow_id},
            "AUTHORIZED", "LOW",
            user_id=user_id
        )
        
        # 3. Execution (Assuming n8n webhook format)
        webhook_url = f"{self.n8n_url}/webhook/{flow_id}"
        headers = {}
        if self.n8n_api_key:
            headers["X-N8N-API-KEY"] = self.n8n_api_key
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url, 
                    json={**payload, "invoked_by": user_id},
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return {
                    "status": "success",
                    "n8n_response": response.json() if response.status_code != 204 else {}
                }
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"n8n returned error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to trigger n8n: {str(e)}"}

# Global instance
n8n_guarded = N8NGuardedBridge()
