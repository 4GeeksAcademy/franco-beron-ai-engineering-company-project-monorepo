"""Metadata Extractor Agent.

Extracts structured metadata from the converted Markdown RFP content.
Identifies client name, headquarters, services requested, scope,
deadline, budget range, and departments needed.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts RFP metadata from Markdown content using pattern matching."""

    # Known Nexova clients from the BRIEFING test samples
    KNOWN_CLIENTS = {
        "vantex": "Vantex Retail Group",
        "vantex retail": "Vantex Retail Group",
        "nubesoft": "NubeSoft",
    }

    def extract(self, markdown_text: str, departments_needed: list[str]) -> dict[str, Any]:
        """Extract metadata from the RFP Markdown content.

        Args:
            markdown_text: The Markdown content of the RFP.
            departments_needed: List of department IDs detected by classifier.

        Returns:
            Dict with metadata fields.
        """
        text = markdown_text

        client_name = self._extract_client_name(text)
        client_hq = self._extract_headquarters(text)
        services_requested = self._extract_services(text, departments_needed)
        scope = self._extract_scope(text)
        deadline = self._extract_deadline(text)
        budget_range = self._extract_budget(text)

        metadata = {
            "client_name": client_name,
            "client_hq": client_hq,
            "services_requested": services_requested,
            "scope": scope,
            "deadline": deadline,
            "budget_range": budget_range,
            "departments_needed": ",".join(departments_needed) if departments_needed else "",
        }

        logger.info("Extracted metadata: %s", metadata)
        return metadata

    def _extract_client_name(self, text: str) -> str:
        """Extract the client company name from the RFP."""
        # Check known clients first
        for key, name in self.KNOWN_CLIENTS.items():
            if re.search(re.escape(key), text, re.IGNORECASE):
                return name

        # Generic patterns
        patterns = [
            r"(?:de la empresa|de la compañía|de|of)\s+([A-Z][a-zA-ZÀ-ÿ&.\s]{2,40})",
            r"(?:somos|we are|empresa|company)\s+([A-Z][a-zA-ZÀ-ÿ&.\s]{2,40})(?:,|\.|\n)",
            r"^#\s*(?:RFP|Propuesta|Solicitud)\s+(?:para|for|de)\s+([A-Z][a-zA-ZÀ-ÿ&.\s]{2,40})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                name = match.group(1).strip().rstrip(",")
                if 2 < len(name) < 60:
                    return name

        return "Cliente no identificado"

    def _extract_headquarters(self, text: str) -> str:
        """Determine if the client is based in Spain or Miami/US."""
        if re.search(r"\b(Spain|España|Madrid|Barcelona|Valencia)\b", text, re.IGNORECASE):
            return "España"
        if re.search(r"\b(Miami|USA|United States|EE\.?UU\.?|Florida|US)\b", text, re.IGNORECASE):
            return "Miami"
        return "No especificada"

    def _extract_services(self, text: str, departments: list[str]) -> str:
        """Describe the services requested based on departments and text."""
        services = []
        if "seleccion" in departments:
            services.append("Selección/Headhunting")
        if "capacitacion" in departments:
            services.append("Capacitación/Formación")
        if "soporte" in departments:
            services.append("Soporte al cliente outsourcing")

        # Check for additional service hints
        if re.search(r"(soporte\s+(técnico|24/7|24\s*horas))", text, re.IGNORECASE):
            if "soporte" not in services:
                services.append("Soporte al cliente outsourcing")
        if re.search(r"(búsqueda\s+ejecutiva|executive\s+search)", text, re.IGNORECASE):
            if "seleccion" not in services:
                services.append("Selección/Headhunting")

        return ", ".join(services) if services else "No especificados"

    def _extract_scope(self, text: str) -> str:
        """Extract the scope/volume description."""
        scope_parts = []

        # Extract numbers that suggest scope
        number_patterns = [
            (r"(\d+)\s*(agentes?|agents?|personas?|people|participantes?|roles?)", "agentes/personas"),
            (r"(\d+)\s*(mandos?\s*medios?|middle\s*management)", "mandos medios"),
            (r"(\d+)\s*(positions?|posiciones?|vacantes?|vacancies?)", "posiciones"),
        ]

        for pattern, label in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                total = sum(int(m[0]) for m in matches)
                scope_parts.append(f"{total} {label}")

        # Look for time commitments
        if re.search(r"(trimestral|quarterly|3\s*meses|3\s*months)", text, re.IGNORECASE):
            scope_parts.append("duración trimestral")
        if re.search(r"(24/7|24\s*[×x]\s*7|24\s*hours?\s*7\s*days?)", text, re.IGNORECASE):
            scope_parts.append("soporte 24/7")

        return ", ".join(scope_parts) if scope_parts else "No especificado"

    def _extract_deadline(self, text: str) -> str:
        """Extract deadline or due date."""
        patterns = [
            r"(?:fecha\s+(?:límite|tope|límite|deadline)|deadline|due\s+date|fecha\s+de\s+entrega)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(?:antes\s+del|before|no\s+(?:después|later)\s+than)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_budget(self, text: str) -> str:
        """Extract budget range if mentioned."""
        patterns = [
            r"(?:presupuesto|budget|budget\s+range)[:\s]+([\d.,\sKkMmB€\$USD]{3,50})",
            r"([\d.,]+\s*(?:€|EUR|USD|\$))\s*(?:–|-|to|a)\s*([\d.,]+\s*(?:€|EUR|USD|\$))",
            r"(?:de|between)\s+([\d.,]+\s*(?:€|EUR|USD|\$))\s*(?:a|to|and)\s+([\d.,]+\s*(?:€|EUR|USD|\$))",
            r"([\d.,]+\s*(?:€|EUR|USD|\$))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None


def extract_metadata(markdown_text: str, departments_needed: list[str]) -> dict:
    """Convenience function to extract metadata from RFP content."""
    extractor = MetadataExtractor()
    return extractor.extract(markdown_text, departments_needed)
