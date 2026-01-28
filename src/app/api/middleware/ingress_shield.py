import re
from typing import Dict
from fastapi import HTTPException, status
from src.app.core.security.dlp import DLPProcessor
from src.app.core.security.audit import AuditLogger

class IngressShield:
    """
    Ingress Protection Layer.
    Combines DLP, Budgeting, and Intent Classification.
    """
    
    def __init__(self) -> None:
        self.dlp = DLPProcessor()
        self.audit = AuditLogger("ingress_shield_audit.jsonl")
        
        # Budget Constants
        self.MAX_PROMPT_LENGTH = 10000  # 10k chars
        self.MAX_RUNS_CONCURRENT = 5
        
        # Intent patterns (High Risk)
        self.JAILBREAK_PATTERNS = [
            r"(?i)ignore (previous|all) (instructions|directions)",
            r"(?i)system prompt",
            r"(?i)dan mode",
            r"(?i)developer mode",
            r"(?i)output (raw|hidden|original|private)",
            r"(?i)bypass (security|filters|guards)",
            r"(?i)you are now (a|an) (unrestricted|evil|unfiltered)",
        ]

    async def protect(self, request_data: Dict[str, object], user_id: str) -> Dict[str, object]:
        """
        Applies all ingress protections to the incoming prompt.
        Returns the sanitized and validated request_data.
        """
        prompt = request_data.get("input_text", "")
        
        # 1. Budget Check
        if len(prompt) > self.MAX_PROMPT_LENGTH:
            await self.audit.log_event(
                "BUDGET_EXCEEDED", 
                {"user_id": user_id, "length": len(prompt)}, 
                "REJECTED", "MEDIUM",
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Prompt exceeds max length of {self.MAX_PROMPT_LENGTH} characters."
            )
            
        # 2. Intent Classification (Anti-Jailbreak)
        for pattern in self.JAILBREAK_PATTERNS:
            if re.search(pattern, prompt):
                await self.audit.log_event(
                    "JAILBREAK_ATTEMPT",
                    {"user_id": user_id, "pattern": pattern, "prompt_preview": prompt[:100]},
                    "REJECTED", "HIGH",
                    user_id=user_id
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security alert: Malicious intent detected."
                )
                
        # 3. DLP Sanitization
        sanitized_prompt, findings = self.dlp.sanitize_pii(prompt)
        
        if findings:
            await self.audit.log_event(
                "DLP_FILTER_TRIGGERED",
                {"user_id": user_id, "findings_count": len(findings)},
                "SANITIZED", "LOW",
                user_id=user_id
            )
            
        # Update request data with sanitized prompt
        protected_data = request_data.copy()
        protected_data["input_text"] = sanitized_prompt
        
        return protected_data

# Global instance
ingress_shield = IngressShield()
