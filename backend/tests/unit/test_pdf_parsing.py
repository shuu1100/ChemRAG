"""
ChemRAG — Scientific PDF Parsing Tests
======================================
Tests:
- PyMuPDF layout extraction with spatial coordinates
- Preservation of bounding boxes and typography
- Table extraction with header context retention
- Equation extraction with LaTeX conversion and confidence
- Explicit parsing failures (EmptyPDFError, CorruptedPDFError)
- GROBID client TEI-XML parsing and graceful offline fallback
"""
from __future__ import annotations

import pymupdf
import pytest

from backend.app.parsing.equation_extractor import EquationExtractor
from backend.app.parsing.grobid_client import GrobidClient, GrobidResult
from backend.app.parsing.layout_extractor import (
    CorruptedPDFError,
    EmptyPDFError,
    LayoutExtractor,
)
from backend.app.parsing.models import BoundingBox, ParsedDocument, ParsedPage, ParsedTable
from backend.app.parsing.service import ScientificPDFParser
from backend.app.parsing.table_extractor import TableExtractor


def create_test_chemistry_pdf() -> bytes:
    """Generate in-memory synthetic scientific PDF with typography, equations, and tables."""
    doc = pymupdf.open()
    page = doc.new_page(width=595.0, height=842.0)  # Standard A4

    # Title & Metadata
    page.insert_text((50, 70), "Asymmetric Catalysis in Organic Synthesis", fontsize=16)
    page.insert_text((50, 95), "Author: Rosalind Franklin, Cambridge University", fontsize=10)
    page.insert_text(
        (50, 120),
        "Abstract: We report enantioselective hydrogenation utilizing chiral ruthenium catalysts.",
        fontsize=10,
    )

    # Section & Body Text
    page.insert_text((50, 160), "1. Introduction", fontsize=12)
    page.insert_text(
        (50, 180),
        "Transition metal catalyzed transformations require precise control over thermodynamics.",
        fontsize=10,
    )

    # Equation with label (1)
    page.insert_text((50, 220), "k = A exp(-E_a / RT)  (1)", fontsize=11)


    # Table with lines and headers
    page.insert_text((50, 260), "Table 1: Optimization of Hydrogenation Conditions", fontsize=11)
    page.draw_rect(pymupdf.Rect(50, 275, 520, 375))
    page.draw_line(pymupdf.Point(50, 305), pymupdf.Point(520, 305))
    page.draw_line(pymupdf.Point(50, 340), pymupdf.Point(520, 340))

    page.insert_text((60, 295), "Catalyst", fontsize=10)
    page.insert_text((180, 295), "Solvent", fontsize=10)
    page.insert_text((300, 295), "Temp (°C)", fontsize=10)
    page.insert_text((420, 295), "Yield (%)", fontsize=10)

    page.insert_text((60, 330), "Ru-BINAP", fontsize=10)
    page.insert_text((180, 330), "MeOH", fontsize=10)
    page.insert_text((300, 330), "60", fontsize=10)
    page.insert_text((420, 330), "94", fontsize=10)

    page.insert_text((60, 365), "Rh-DuPhos", fontsize=10)
    page.insert_text((180, 365), "THF", fontsize=10)
    page.insert_text((300, 365), "25", fontsize=10)
    page.insert_text((420, 365), "88", fontsize=10)

    # Footnote
    page.insert_text((50, 395), "a Reaction run under 10 bar H2 pressure.", fontsize=9)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestLayoutExtraction:
    def test_extract_pages_and_coordinates(self) -> None:
        pdf_bytes = create_test_chemistry_pdf()
        extractor = LayoutExtractor()
        doc = extractor.extract(pdf_bytes, filename="test_chem.pdf")

        assert doc.page_count == 1
        assert len(doc.pages) == 1

        page = doc.pages[0]
        assert page.width == 595.0
        assert page.height == 842.0
        assert len(page.blocks) > 0

        # Verify page coordinates survived parsing
        for block in page.blocks:
            assert block.bbox is not None
            assert block.bbox.x0 >= 0
            assert block.bbox.y0 >= 0
            assert block.bbox.width > 0
            assert block.bbox.height > 0
            for line in block.lines:
                for span in line.spans:
                    assert span.bbox is not None
                    assert span.font_size > 0

    def test_explicit_error_on_empty_bytes(self) -> None:
        extractor = LayoutExtractor()
        with pytest.raises(EmptyPDFError, match="empty PDF bytes"):
            extractor.extract(b"", filename="empty.pdf")

    def test_explicit_error_on_corrupted_pdf(self) -> None:
        extractor = LayoutExtractor()
        with pytest.raises(CorruptedPDFError, match="Failed to open PDF document"):
            extractor.extract(b"NOT A REAL PDF %%% INVALID", filename="corrupt.pdf")


class TestEquationExtraction:
    def test_equation_extracted_with_latex_and_confidence(self) -> None:
        pdf_bytes = create_test_chemistry_pdf()
        extractor = LayoutExtractor()
        doc = extractor.extract(pdf_bytes)

        eq_extractor = EquationExtractor()
        equations = eq_extractor.extract_from_page(doc.pages[0])

        assert len(equations) >= 1
        eq = equations[0]
        assert "exp" in eq.raw_text or "E_a" in eq.latex or "RT" in eq.raw_text
        assert eq.confidence >= 0.70

        assert eq.page_number == 1
        assert eq.bbox is not None

    def test_latex_normalization(self) -> None:
        eq_extractor = EquationExtractor()
        raw = "ΔH = -54.2 kJ/mol, k = A exp(-E_a / RT)"
        normalized = eq_extractor.normalize_to_latex(raw)
        assert r"\Delta" in normalized
        assert "E_{a}" in normalized or "E_a" in normalized


class TestTableExtraction:
    def test_table_preserves_header_context(self) -> None:
        table = ParsedTable(
            table_index=1,
            caption="Table 1: Reaction Optimization",
            bbox=BoundingBox(50, 100, 500, 200),
            page_number=1,
            headers=["Catalyst", "Solvent", "Temp (°C)", "Yield (%)"],
            rows=[
                ["Ru-BINAP", "MeOH", "60", "94"],
                ["Rh-DuPhos", "THF", "25", "88"],
            ],
            units={"Temp (°C)": "°C", "Yield (%)": "%"},
            footnotes=["a Isolated yield after chromatography."],
        )
        retrieval_text = table.generate_retrieval_text()

        # Every row retains full table title and column header names!
        assert "[Table 1: Reaction Optimization]" in retrieval_text
        assert "Catalyst: Ru-BINAP" in retrieval_text
        assert "Yield (%): 94" in retrieval_text
        assert "Catalyst: Rh-DuPhos" in retrieval_text
        assert "Notes: a Isolated yield" in retrieval_text

    def test_heuristic_table_extraction(self) -> None:
        text = """
        Table 2: Solubility in Organic Solvents
        Solvent | Temp (K) | Solubility (g/L)
        Ethanol | 298 | 42.5
        Acetone | 298 | 88.0
        * Measured at atmospheric pressure.
        """
        table_extractor = TableExtractor()
        tables = table_extractor.extract_from_text(text, page_number=2)

        assert len(tables) == 1
        tab = tables[0]
        assert "Table 2" in tab.caption
        assert len(tab.headers) == 3
        assert len(tab.rows) == 2
        assert tab.units.get("Temp (K)") == "K"
        assert tab.units.get("Solubility (g/L)") == "g/L"
        assert "Solvent: Ethanol" in tab.retrieval_text


class TestGrobidIntegration:
    def test_grobid_tei_xml_parser(self) -> None:
        sample_tei = """<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title level="a">Stereoselective Synthesis of Biaryls</title>
                    </titleStmt>
                    <sourceDesc>
                        <biblStruct>
                            <analytic>
                                <author>
                                    <persName>
                                        <forename>Ada</forename>
                                        <surname>Yonath</surname>
                                    </persName>
                                    <affiliation>Weizmann Institute</affiliation>
                                </author>
                                <idno type="DOI">10.1002/anie.20250012</idno>
                            </analytic>
                        </biblStruct>
                    </sourceDesc>
                </fileDesc>
                <profileDesc>
                    <abstract>
                        <p>A novel cross-coupling methodology is reported.</p>
                    </abstract>
                </profileDesc>
            </teiHeader>
            <text>
                <body>
                    <div>
                        <head>Results and Discussion</head>
                        <p>High yields were obtained under mild conditions.</p>
                    </div>
                </body>
                <back>
                    <div type="references">
                        <listBibl>
                            <biblStruct>
                                <analytic>
                                    <title level="a">Pioneering Cross-Coupling</title>
                                    <author><persName><surname>Suzuki</surname></persName></author>
                                </analytic>
                                <monogr>
                                    <title level="j">Chem. Rev.</title>
                                    <imprint><date when="2020">2020</date></imprint>
                                </monogr>
                            </biblStruct>
                        </listBibl>
                    </div>
                </back>
            </text>
        </TEI>
        """
        client = GrobidClient(base_url="http://localhost:8070")
        result = client.parse_tei_xml(sample_tei)

        assert result.title == "Stereoselective Synthesis of Biaryls"
        assert "Ada Yonath" in result.authors
        assert result.doi == "10.1002/anie.20250012"
        assert "novel cross-coupling" in result.abstract
        assert len(result.sections) == 1
        assert result.sections[0].title == "Results and Discussion"
        assert len(result.references) == 1
        assert "Suzuki" in result.references[0].authors

    @pytest.mark.asyncio
    async def test_grobid_graceful_offline_fallback(self) -> None:
        # Client pointing to a non-existent port
        client = GrobidClient(base_url="http://127.0.0.1:9999", timeout=1)
        result = await client.parse_pdf(b"%PDF-1.4 dummy", filename="dummy.pdf")
        assert result.is_available is False
        assert result.error is not None


class TestScientificPDFParser:
    @pytest.mark.asyncio
    async def test_full_parser_orchestration(self) -> None:
        pdf_bytes = create_test_chemistry_pdf()
        parser = ScientificPDFParser()
        # Run parsing with GROBID disabled or offline fallback
        doc = await parser.parse(pdf_bytes, filename="paper.pdf", enable_grobid=False)

        assert isinstance(doc, ParsedDocument)
        assert doc.page_count == 1
        assert len(doc.pages) == 1
        assert len(doc.pages[0].blocks) > 0
        # Check equation was extracted
        assert len(doc.equations) >= 1
        # Check coordinates exist
        assert doc.pages[0].blocks[0].bbox.width > 0
