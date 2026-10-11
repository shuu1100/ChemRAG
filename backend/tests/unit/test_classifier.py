"""
ChemRAG — Unit Tests for Document Classifier
=============================================
Tests heuristic rules, confidence calculation, parser selection, and fallbacks.
"""
from __future__ import annotations

import pytest

from backend.app.models.document import DocumentGenre
from backend.app.services.document_classifier import DocumentClassifier, GENRE_PARSER_MAP


class TestDocumentClassifier:
    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        return DocumentClassifier(confidence_threshold=0.40)

    def test_classify_safety_data_sheet(self, classifier: DocumentClassifier) -> None:
        text = """
        SAFETY DATA SHEET
        SECTION 1: IDENTIFICATION OF THE SUBSTANCE
        Product Name: Acetone
        CAS No: 67-64-1
        SECTION 2: HAZARDS IDENTIFICATION
        GHS Classification: Flammable liquids (Category 2)
        Signal Word: Danger
        H225: Highly flammable liquid and vapor
        SECTION 4: FIRST-AID MEASURES
        SECTION 8: EXPOSURE CONTROLS/PERSONAL PROTECTION
        SECTION 11: TOXICOLOGICAL INFORMATION
        """
        result = classifier.classify_text(text=text, filename="acetone_sds.pdf")
        assert result.genre == DocumentGenre.SDS
        assert result.confidence > 0.5
        assert result.parser_recommended == "sds_parser"
        assert result.is_confident is True

    def test_classify_standard_operating_procedure(self, classifier: DocumentClassifier) -> None:
        text = """
        STANDARD OPERATING PROCEDURE: SOP-QC-0042
        Title: Calibration of Analytical Balances
        1. PURPOSE AND SCOPE
        This procedure outlines the daily calibration steps for all analytical balances.
        2. RESPONSIBILITIES
        The QC Analyst is responsible for following this procedure.
        3. PROCEDURE STEPS
        3.1 Inspect the balance pan for cleanliness.
        4. REVISION HISTORY
        Rev 1.2: Effective Date: 2026-01-15
        Approval Signature: Dr. A. Smith
        """
        result = classifier.classify_text(text=text, filename="sop_balance_calib.pdf")
        assert result.genre == DocumentGenre.SOP
        assert result.confidence > 0.5
        assert result.parser_recommended == "sop_parser"

    def test_classify_research_paper(self, classifier: DocumentClassifier) -> None:
        text = """
        Synthesis and Catalytic Activity of Novel Ruthenium Complexes
        Abstract: We report here the design and synthesis of chiral ruthenium complexes...
        Introduction: Transition metal catalyzed hydrogenation represents...
        Materials and Methods: All reagents were obtained from Sigma-Aldrich...
        Results and Discussion: As shown in Table 1, high enantioselectivity was achieved...
        References:
        [1] Smith et al., J. Am. Chem. Soc. 2020.
        DOI: 10.1021/ja.2024.12345
        Electronic Supplementary Information available online.
        """
        result = classifier.classify_text(text=text, filename="jacs_paper.pdf")
        assert result.genre == DocumentGenre.RESEARCH_PAPER
        assert result.confidence > 0.5
        assert result.parser_recommended == "grobid_parser"

    def test_classify_textbook(self, classifier: DocumentClassifier) -> None:
        text = """
        Principles of Organic Chemistry (4th Edition)
        Table of Contents
        Chapter 1: Structure and Bonding
        Chapter 2: Alkanes and Cycloalkanes
        Chapter 3: Stereochemistry
        Problems and Solutions
        Exercises at end of chapter
        ISBN: 978-0-12-345678-9
        """
        result = classifier.classify_text(text=text, filename="organic_chemistry_vol1.pdf", page_count=450)
        assert result.genre == DocumentGenre.TEXTBOOK
        assert result.parser_recommended == "textbook_parser"

    def test_classify_experimental_report(self, classifier: DocumentClassifier) -> None:
        text = """
        EXPERIMENTAL REPORT / LABORATORY NOTEBOOK
        Run No: 2026-03-A
        Batch No: BATCH-88392
        Reaction Scheme: Suzuki cross-coupling
        Crude Product: 4.2g yellow solid
        Yield: 87%
        Purification Method: Flash column chromatography (hexanes/EtOAc 4:1)
        Analytical Data:
        1H-NMR (400 MHz, CDCl3): 7.82 (d, 2H), 7.45 (m, 3H)
        HPLC Analysis: 99.1% purity
        """
        result = classifier.classify_text(text=text, filename="exp_report_2026.pdf")
        assert result.genre == DocumentGenre.EXPERIMENTAL_REPORT
        assert result.parser_recommended == "experimental_parser"

    def test_classify_technical_report(self, classifier: DocumentClassifier) -> None:
        text = """
        TECHNICAL REPORT
        Deliverable D3.2: Assessment of Polymer Degradation Rates
        Executive Summary: This project report details accelerated weathering testing.
        Grant Agreement No: 894320
        Contract Number: CN-2025-99
        Prepared for: Department of Materials Research
        """
        result = classifier.classify_text(text=text, filename="report_d3_2.pdf")
        assert result.genre == DocumentGenre.TECHNICAL_REPORT
        assert result.parser_recommended == "tech_report_parser"

    def test_classify_unknown_fallback_to_generic_parser(self, classifier: DocumentClassifier) -> None:
        text = "Hello world, this is a short arbitrary note without chemistry indicators."
        result = classifier.classify_text(text=text, filename="random.pdf")
        assert result.genre == DocumentGenre.UNKNOWN
        assert result.parser_recommended == "generic_parser"
        assert result.confidence < 0.40
        assert result.is_confident is False
