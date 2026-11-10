"""RFP Classifier Agent.

Determines whether an uploaded document is a legitimate RFP for Nexova.
If not, the ticket is marked as `descartado` and the pipeline stops.

Departments are defined per Nexova BRIEFING:
- seleccion (Talent Selection Operations)
- capacitacion (Corporate Training)
- soporte (Customer Support outsourcing)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

# Department definitions matching the BRIEFING
DEPARTMENTS: dict[str, dict[str, str]] = {
    "seleccion": {
        "name": "Talent Selection Operations",
        "responsible": "Javier Almeida",
        "description": "Roles a cubrir, tiempo estimado de cierre, horas de consultoría necesarias",
    },
    "capacitacion": {
        "name": "Corporate Training",
        "responsible": "Elena Vargas",
        "description": "Programas de formación aplicables, duración, modalidad",
    },
    "soporte": {
        "name": "Customer Support (outsourcing)",
        "responsible": "Roberto Díaz",
        "description": "Dotación de agentes, turnos, SLA de respuesta comprometido",
    },
}

ClassificationResult = Literal["rfp_valida", "descartado"]


class ClassifierAgent:
    """Classifies whether a document is a valid RFP for Nexova.

    Uses keyword-based heuristics and pattern matching for the initial
    classification, following the BRIEFING criteria. The classifier looks for:
    - RFP-like language (propuesta, solicitud, request for proposal, etc.)
    - Service requests matching Nexova offerings
    - Client context (not a vendor pitch)
    """

    def __init__(self) -> None:
        self.rfp_indicators = [
            r"\brfp\b",
            r"\brequest for proposal\b",
            r"\bsolicitud de propuesta\b",
            r"\bpropuesta\s+(económica|de servicios|comercial)\b",
            r"\bcotizaci[óo]n\b",
            r"\bquote\b",
            r"\bproposal\b",
            r"\bpresupuesto\b",
            r"\bbudget\b",
            r"\boutsourcing\b",
            r"\bservicios?\s+de\s+(soporte|selecci[óo]n|c capacitaci[óo]n|formaci[óo]n)\b",
            r"\bsupport\s+services?\b",
            r"\btraining\s+program\b",
            r"\bselection\s+process\b",
            r"\bheadhunting\b",
        ]

        self.vendor_indicators = [
            r"\bsomos\s+proveedores?\b",
            r"\bsomos\s+una?\s+(consultora|empresa|compañ[íi]a|firma)\b",
            r"\bnuestro\s+producto\b",
            r"\bnuestra\s+plataforma\b",
            r"\bnuestra\s+empresa\b",
            r"\bnuestra\s+compañ[íi]a\b",
            r"\bte ofrecemos\b",
            r"\ble\s+ofrecemos\b",
            r"\bofrecemos\s+soluciones\b",
            r"\bpartner\s+program\b",
            r"\bdisponemos\s+de\s+una\s+soluci[oó]n\b",
            r"\bquisier[ae]mos\s+presentarles?\b",
            r"\bnuestro\s+sistema\s+de\s+(ats| applicant tracking|gesti[oó]n)\b",
            r"\bqueremos\s+ser\s+su\s+proveedor\b",
            r"\bnos\s+(dedicamos|especializamos)\s+a\b",
        ]

        # Keywords that suggest client seeking services vs vendor selling
        self.client_indicators = [
            r"\bbus[ck]amos\b",
            r"\bnecesitamos\b",
            r"\brequerimos\b",
            r"\bestamos\s+buscando\b",
            r"\bme\s+gustar[íi]a\s+recibir\b",
            r"\bwe\s+are\s+looking\b",
            r"\bwe\s+need\b",
            r"\bwe\s+require\b",
            r"\bpor\s+favor\s+(env[íi]en|coticen)\b",
            r"\bplease\s+(send|quote|provide)\b",
        ]

        self.service_keywords = [
            "selecci", "selección", "selection", "headhunting",
            "capacitaci", "capacitación", "training", "formación", "formacion",
            "soporte", "support", "outsourcing", "agentes", "agents",
            "liderazgo", "leadership", "mandos medios", "middle management",
            "búsqueda ejecutiva", "executive search",
        ]

    def classify(self, markdown_text: str) -> ClassificationResult:
        """Classify the document as a valid RFP or not.

        Args:
            markdown_text: The Markdown content of the uploaded document.

        Returns:
            "rfp_valida" if the document appears to be a legitimate RFP,
            "descartado" if it does not.
        """
        text_lower = markdown_text.lower()

        # Count RFP indicators
        rfp_score = self._count_matches(text_lower, self.rfp_indicators)
        vendor_score = self._count_matches(text_lower, self.vendor_indicators)
        client_score = self._count_matches(text_lower, self.client_indicators)
        service_score = self._count_matches(text_lower, self.service_keywords)

        logger.info(
            "Classifier scores — rfp=%d vendor=%d client=%d service=%d",
            rfp_score, vendor_score, service_score, client_score,
        )

        # Decision logic
        # 1. Strong vendor pitch signal overrides everything
        if vendor_score > rfp_score:
            logger.info("Classifier: DISCARDED (vendor pitch detected)")
            return "descartado"

        # 2. Strong RFP signal with client context (e.g., "we are looking")
        if rfp_score >= 2 and client_score >= 1:
            logger.info("Classifier: VALID RFP (client seeking services)")
            return "rfp_valida"

        # 3. RFP indicator + service request (e.g., "proposal for training")
        if rfp_score >= 1 and service_score >= 1:
            logger.info("Classifier: VALID RFP (service request detected)")
            return "rfp_valida"

        # 4. No indicators at all
        if rfp_score == 0 and vendor_score == 0:
            logger.info("Classifier: DISCARDED (no RFP indicators found)")
            return "descartado"

        # 5. Weak RFP signal but no vendor pitch
        if rfp_score >= 1:
            logger.info("Classifier: VALID RFP (minimum RFP indicators)")
            return "rfp_valida"

        logger.info("Classifier: DISCARDED (default rejection)")
        return "descartado"

        if rfp_score == 0 and vendor_score == 0:
            logger.info("Classifier: DISCARDED (no RFP indicators found)")
            return "descartado"

        # Default: if weak signals, accept as RFP
        if rfp_score >= 1:
            logger.info("Classifier: VALID RFP (minimum RFP indicators)")
            return "rfp_valida"

        logger.info("Classifier: DISCARDED (default rejection)")
        return "descartado"

    def _count_matches(self, text: str, patterns: list[str]) -> int:
        count = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count

    def detect_applicable_departments(self, markdown_text: str) -> list[str]:
        """Detect which Nexova departments are relevant based on document content.

        Returns a list of department_ids that should be activated.
        Never activates all three by default.
        """
        text_lower = markdown_text.lower()
        activated: list[str] = []

        # Check for seleccion signals
        selection_signals = [
            "selecci", "headhunting", "búsqueda ejecutiva", "executive search",
            "mandos medios", "middle management", "reclutamiento", "recruitment",
            "roles a cubrir", "positions to fill", "contratación", "hiring",
            "candidatos", "candidates", "perfiles", "profiles",
        ]
        if self._count_matches(text_lower, selection_signals) >= 1:
            activated.append("seleccion")

        # Check for capacitacion signals
        training_signals = [
            "capacitaci", "training", "formación", "formacion", "liderazgo",
            "leadership", "programa", "program", "taller", "workshop",
            "curso", "course", "capacitación corporativa",
            "corporate training", "trimestral", "quarterly",
        ]
        if self._count_matches(text_lower, training_signals) >= 1:
            activated.append("capacitacion")

        # Check for soporte signals
        support_signals = [
            "soporte", "support", "outsourcing", "agentes", "agents",
            "atención al cliente", "customer service", "customer support",
            "24/7", "turnos", "shifts", "sla", "mesa de ayuda",
            "help desk", "service desk",
        ]
        if self._count_matches(text_lower, support_signals) >= 1:
            activated.append("soporte")

        logger.info("Detected departments: %s", activated)
        return activated


def classify_rfp(markdown_text: str) -> dict:
    """Convenience function to classify an RFP document.

    Returns:
        Dict with classification result and detected departments.
    """
    agent = ClassifierAgent()
    result = agent.classify(markdown_text)
    departments = agent.detect_applicable_departments(markdown_text) if result == "rfp_valida" else []
    return {
        "classification": result,
        "departments_needed": departments,
        "departments_detail": {d: DEPARTMENTS[d] for d in departments},
    }
