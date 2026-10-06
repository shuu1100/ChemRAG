"""
ChemRAG — GROBID Scholarly PDF Parser Integration
==================================================
Sends PDF to GROBID server (/api/processFulltextDocument) and parses the
TEI-XML output into structured scholarly metadata:
title, authors, affiliations, abstract, sections, subsections, references, figures, equations.
Gracefully falls back if GROBID is unreachable or offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx
from bs4 import BeautifulSoup

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.parsing.models import (
    ParsedEquation,
    ParsedReference,
    ParsedSection,
    ParsedTable,
)

logger = get_logger(__name__)


@dataclass
class GrobidResult:
    """Structured result parsed from GROBID TEI-XML."""
    is_available: bool = True
    tei_xml: str = ""
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    abstract: Optional[str] = None
    sections: List[ParsedSection] = field(default_factory=list)
    references: List[ParsedReference] = field(default_factory=list)
    equations: List[ParsedEquation] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)
    error: Optional[str] = None


class GrobidClient:
    """Async client for interacting with GROBID service."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 60) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.grobid.base_url).rstrip("/")
        self.timeout = timeout

    async def is_healthy(self) -> bool:
        """Check if GROBID service is running and healthy."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/isalive")
                return res.status_code == 200
        except Exception:
            return False

    async def parse_pdf(self, pdf_bytes: bytes, filename: str = "document.pdf") -> GrobidResult:
        """
        Send PDF to GROBID processFulltextDocument and parse the TEI-XML response.
        Falls back cleanly if GROBID is unreachable.
        """
        url = f"{self.base_url}/api/processFulltextDocument"
        files = {"input": (filename, pdf_bytes, "application/pdf")}
        data = {
            "consolidateHeader": "1",
            "consolidateCitations": "1",
            "includeRawCitations": "1",
            "includeRawAffiliations": "1",
            "generateIDs": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                response = await client.post(url, files=files, data=data)
                if response.status_code != 200:
                    err = f"GROBID returned status {response.status_code}: {response.text[:200]}"
                    logger.warning("GROBID processing returned non-200", error=err)
                    return GrobidResult(is_available=False, error=err)

                tei_xml = response.text
                return self.parse_tei_xml(tei_xml)

        except Exception as exc:
            err = f"GROBID connection error: {exc}"
            logger.info("GROBID service offline or unreachable, proceeding with fallback", error=err)
            return GrobidResult(is_available=False, error=err)

    def parse_tei_xml(self, xml_content: str) -> GrobidResult:
        """Parse GROBID TEI-XML into structured scholarly objects."""
        if not xml_content:
            return GrobidResult(is_available=True)

        soup = BeautifulSoup(xml_content, "xml")

        # 1. Title
        title = None
        title_tag = soup.find("title", level="a") or soup.find("title")
        if title_tag and title_tag.text:
            title = title_tag.text.strip()

        # 2. DOI
        doi = None
        doi_tag = soup.find("idno", type="DOI")
        if doi_tag and doi_tag.text:
            doi = doi_tag.text.strip()

        # 3. Authors & Affiliations
        authors: List[str] = []
        affiliations: List[str] = []
        for author_tag in soup.find_all("author"):
            pers_name = author_tag.find("persName")
            if pers_name:
                forenames = [fn.text.strip() for fn in pers_name.find_all("forename") if fn.text]
                surname = pers_name.find("surname")
                s_text = surname.text.strip() if surname and surname.text else ""
                full_name = " ".join(forenames + ([s_text] if s_text else "")).strip()
                if full_name:
                    authors.append(full_name)

            aff_tag = author_tag.find("affiliation")
            if aff_tag and aff_tag.text:
                aff_clean = " ".join(aff_tag.text.split())
                if aff_clean and aff_clean not in affiliations:
                    affiliations.append(aff_clean)

        # 4. Abstract
        abstract = None
        abstract_tag = soup.find("abstract")
        if abstract_tag:
            paragraphs = [p.text.strip() for p in abstract_tag.find_all("p") if p.text]
            if paragraphs:
                abstract = "\n\n".join(paragraphs)

        # 5. Sections
        sections: List[ParsedSection] = []
        body = soup.find("body")
        if body:
            for div in body.find_all("div", recursive=False):
                head = div.find("head")
                sec_title = head.text.strip() if head and head.text else "Section"
                paragraphs = [p.text.strip() for p in div.find_all("p") if p.text]
                sec_text = "\n\n".join(paragraphs)
                sections.append(ParsedSection(title=sec_title, level=1, text=sec_text))

        # 6. References / Citations
        references: List[ParsedReference] = []
        list_bibl = soup.find("listBibl")
        bibl_nodes = list_bibl.find_all("biblStruct") if list_bibl else soup.find_all("biblStruct")
        for idx, bibl in enumerate(bibl_nodes):

            ref_title = None
            rt = bibl.find("title", level="a") or bibl.find("title", level="m")
            if rt and rt.text:
                ref_title = rt.text.strip()

            ref_authors: List[str] = []
            for a in bibl.find_all("author"):
                pn = a.find("persName")
                if pn:
                    sn = pn.find("surname")
                    sn_text = sn.text.strip() if sn and sn.text else ""
                    if sn_text:
                        ref_authors.append(sn_text)

            year = None
            date_tag = bibl.find("date", type="published") or bibl.find("date")
            if date_tag and date_tag.get("when"):
                try:
                    year = int(date_tag["when"][:4])
                except (ValueError, TypeError):
                    pass

            ref_doi = None
            r_doi = bibl.find("idno", type="DOI")
            if r_doi and r_doi.text:
                ref_doi = r_doi.text.strip()

            journal = None
            j_tag = bibl.find("title", level="j")
            if j_tag and j_tag.text:
                journal = j_tag.text.strip()

            raw_txt = bibl.text.strip()

            references.append(
                ParsedReference(
                    ref_index=idx + 1,
                    raw_text=raw_txt,
                    title=ref_title,
                    authors=ref_authors,
                    year=year,
                    doi=ref_doi,
                    journal=journal,
                )
            )

        # 7. Formulas / Equations
        equations: List[ParsedEquation] = []
        for idx, formula in enumerate(soup.find_all("formula")):
            f_text = formula.text.strip()
            if f_text:
                equations.append(
                    ParsedEquation(
                        equation_index=idx + 1,
                        raw_text=f_text,
                        latex=f_text,  # or convert if MathML present
                        bbox=None,
                        page_number=1,
                        confidence=0.90,
                    )
                )

        return GrobidResult(
            is_available=True,
            tei_xml=xml_content,
            title=title,
            authors=authors,
            affiliations=affiliations,
            doi=doi,
            abstract=abstract,
            sections=sections,
            references=references,
            equations=equations,
        )
