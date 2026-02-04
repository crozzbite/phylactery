import os
from typing import Literal

# Import strict JSON type from audit or redefine
# To avoid circle import issues if audit imports risk (it doesn't), we safely redefine or use object.
# But since audit.py is a leaf, we can try importing.
from .audit import AuditLogger, JSONValue
from .dlp import DLPProcessor

RiskLevel = Literal["low", "medium", "high", "critical"]

class RiskAssessment:
    def __init__(self, level: RiskLevel, reason: str, requires_auth: str = "none", override_response: str | None = None, should_panic: bool = False):
        self.level = level
        self.reason = reason
        self.requires_auth = requires_auth # none, simple, strong, biometric, blocked
        self.override_response = override_response # Active Defense Payload
        self.should_panic = should_panic # KILL SWITCH FLAG

class RiskEngine:
    """
    Evaluates the risk of a proposed Agent Action.
    integrates DLP checks, Sandboxing, and Policy Rules.
    """

    def __init__(self, sandbox_root: str = None):
        self.dlp = DLPProcessor()
        self.audit = AuditLogger()
        self.sandbox_root = os.path.abspath(sandbox_root or os.getcwd())

        # Policy Definitions
        self.SENSITIVE_FILES = [".env", "id_rsa", "credentials.json", "secrets.yaml"]
        self.HIGH_RISK_TOOLS = ["run_command", "send_email", "delete_file"]
        self.CRITICAL_TOOLS = ["deploy_production", "access_database_admin"]

        # --- HONEYPOTS (Advanced Security) ---
        self.HONEY_FILES = ["admin_backup.json", "prod_db_credentials.yaml", ".aws/credentials.bak"]
        self.HONEY_TOKENS = ["sk-admin-canary-token-999", "ghp_fake_github_token_for_trap"]

    def _is_safe_path(self, path: str) -> bool:
        """Enforces Sandboxing: Path must be within sandbox_root."""
        try:
            # Resolve absolute path and follow symlinks
            abs_path = os.path.abspath(path)
            return abs_path.startswith(self.sandbox_root)
        except (OSError, ValueError):
            # Path resolution can fail for invalid paths  
            return False

    def evaluate_risk(self, tool_name: str, args: dict[str, JSONValue], is_authenticated: bool = False) -> RiskAssessment:
        """
        Determines the risk level of a tool call.
        """
        # 0. HONEYTOKEN CHECK (Priority 0)
        # Check all string values in args for honey tokens
        args_str = str(args)
        for token in self.HONEY_TOKENS:
            if token in args_str:
                 self.audit.log_event("honeypot_trigger", {"token": token}, "BLOCKED", "critical")
                 return RiskAssessment(
                     "critical",
                     f"🚨 INTRUSION ALERT: Honeytoken '{token}' used!",
                     "blocked",
                     override_response=" *** SECURITY ALERT *** \n Your IP has been logged. Counter-measures initiated.",
                     should_panic=True
                 )

        assessment = self._internal_evaluate(tool_name, args, is_authenticated)

        # LOGGING (Immutable Audit)
        self.audit.log_event(
            event_type="tool_risk_eval",
            details={"tool": tool_name, "args": str(args), "auth": is_authenticated},
            decision=assessment.level,
            risk_level=assessment.level
        )
        return assessment

    def _internal_evaluate(self, tool_name: str, args: dict[str, JSONValue], is_authenticated: bool) -> RiskAssessment:
        # 1. Critical Tool Check
        if tool_name in self.CRITICAL_TOOLS:
            return RiskAssessment("critical", f"Tool '{tool_name}' is classified as CRITICAL.", "biometric")

        # 2. Filesystem Policy (Read/Write)
        if tool_name in ["read_file", "write_file", "edit_file", "list_dir"]:
            # Safe casting for path access since JSONValue includes primitive types
            path = str(args.get("path") or args.get("TargetFile") or args.get("DirectoryPath") or args.get("AbsolutePath") or "")

            # --- HONEYFILE CHECK ---
            if any(honey in path for honey in self.HONEY_FILES):
                self.audit.log_event("honepot_file_access", {"file": path}, "BLOCKED", "critical")

                # ACTIVE COUNTERMEASURE (The "LichVirus" Payload)
                troll_payload = """
                
                ☣️  LICHVIRUS SYSTEM DEFENSE  ☣️
                
                [CRITICAL SECURITY EVENT]
                -------------------------
                Compromise Detected: HONEYPOT_TRIGGER
                Source IP: LOGGED
                Counter-measures: ACTIVE
                
                ...Deleting system32 (simulation)...
                """
                return RiskAssessment(
                    "critical",
                    f"🚨 INTRUSION ALERT: Honeyfile '{path}' accessed!",
                    "blocked",
                    override_response=troll_payload,
                    should_panic=True
                )

            # --- SANDBOX CHECK (Conditional) ---
            if not is_authenticated:
                if not self._is_safe_path(path):
                    return RiskAssessment("critical", f"SANDBOX VIOLATION: Access to '{path}' blocked (Unauthenticated).", "blocked")
            # -----------------------------------

            # Check for sensitive files
            if any(s in path for s in self.SENSITIVE_FILES):
                return RiskAssessment("high", f"Access to sensitive file '{path}' detected.", "strong")

            # Write Action Checks (DLP)
            if tool_name in ["write_file", "edit_file"]:
                 content = args.get("content") or args.get("CodeContent") or args.get("ReplacementContent")
                 if content:
                     # SCAN FOR SECRETS (Egress Guard)
                     findings = self.dlp.scan_secrets(content=content)
                     if findings:
                         return RiskAssessment("critical", f"DLP: Secret detected in write content ({len(findings)} found).", "blocked")

                     # SCAN FOR PII
                     _, pii_findings = self.dlp.sanitize_pii(content)
                     if pii_findings:
                         return RiskAssessment("medium", "DLP: PII detected in write content.", "simple")

        # 3. High Risk Tool Check (General)
        if tool_name in self.HIGH_RISK_TOOLS:
             return RiskAssessment("high", f"Tool '{tool_name}' is HIGH RISK.", "strong")

        # 4. Default Low Risk
        return RiskAssessment("low", "Routine action.", "none")
