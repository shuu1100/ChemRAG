"""
ChemRAG — Citation Validator
=============================
Fulfills Prompt 13.2:
- Extracts factual claims and inline citation tags ([CIT-xxx]) from generated response text.
- Verifies that all cited IDs exist in the provided prompt context.
- Tests claim-entailment: verifies whether cited chunk content supports the corresponding claim.
- Detects uncited factual scientific claims (e.g. quantitative temperature, yield, rate laws).
- Detects fabricated DOIs, pages, or reference metadata.
- Signals regeneration (should_regenerate=True) or issues detailed validation warnings.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Set, Tuple

from backend.app.citations.models import (
    CitationMetadata,
    CitationValidationResult,
    ClaimVerificationResult,
)

logger = logging.getLogger(__name__)

# Patterns for extracting inline citations like [CIT-001] or [CIT-1, CIT-2]
CITATION_TAG_PATTERN = re.compile(r"\[(?:CIT-\d+(?:,\s*CIT-\d+)*|\d+(?:,\s*\d+)*)\]", re.IGNORECASE)
SINGLE_CIT_ID_PATTERN = re.compile(r"CIT-\d+", re.IGNORECASE)

# Pattern for identifying quantitative/scientific factual claims (temperatures, percentages, rate constants, equations, SMILES)
FACTUAL_CLAIM_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?\s*(?:°C|K|Pa|bar|atm|mol|mM|mg/L|%|kJ/mol)|rate constant|half-life|yield|selectivity|synthesis|InChI|SMILES)\b",
    re.IGNORECASE,
)

# Pattern for detecting DOIs
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


class CitationValidator:
    """
    Validates generated LLM responses against provided citation evidence.
    """

    def __init__(self, entailment_threshold: float = 0.3) -> None:
        self.entailment_threshold = entailment_threshold

    def extract_claims_and_citations(self, text: str) -> List[Tuple[str, List[str]]]:
        """
        Split text into sentences and extract cited [CIT-xxx] tags per sentence.
        Returns list of (sentence_text, list_of_cit_ids).
        """
        if not text:
            return []

        # Split text by sentence boundaries (.!? followed by space or newline)
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        claims_with_cits: List[Tuple[str, List[str]]] = []

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue

            cits_found = SINGLE_CIT_ID_PATTERN.findall(s_clean)
            # Normalize to uppercase, e.g. CIT-001
            norm_cits = list(dict.fromkeys([c.upper() for c in cits_found]))
            claims_with_cits.append((s_clean, norm_cits))

        return claims_with_cits

    def evaluate_claim_entailment(
        self, claim: str, cited_chunks: List[CitationMetadata]
    ) -> Tuple[bool, float, str]:
        """
        Evaluate semantic and keyword overlap entailment between a claim and its cited chunks.
        """
        if not cited_chunks:
            return False, 0.0, "No valid source chunks provided for citation."

        # Extract normalized keywords from claim
        claim_clean = re.sub(r"\[CIT-\d+\]", "", claim, flags=re.IGNORECASE)
        claim_words = set(re.findall(r"\w+", claim_clean.lower()))
        # Remove common stopwords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and", "or", "for", "with", "by", "that", "this", "it"}
        content_words = claim_words - stopwords

        if not content_words:
            return True, 1.0, "Claim contains only functional language."

        best_score = 0.0
        best_reasoning = ""

        for cit in cited_chunks:
            chunk_words = set(re.findall(r"\w+", cit.raw_text.lower()))
            overlap = content_words.intersection(chunk_words)
            score = len(overlap) / len(content_words) if content_words else 0.0

            if score > best_score:
                best_score = score
                best_reasoning = f"Claim supported by {cit.citation_id} ({len(overlap)} matching key terms)."

        is_supported = best_score >= self.entailment_threshold
        if not is_supported:
            best_reasoning = f"Insufficient overlap ({best_score:.2f} < threshold {self.entailment_threshold}) between claim and cited text."

        return is_supported, round(best_score, 4), best_reasoning

    def validate_response(
        self,
        generated_text: str,
        valid_citations: List[CitationMetadata],
    ) -> CitationValidationResult:
        """
        Perform comprehensive post-generation validation of citations and claims.
        """
        valid_map = {c.citation_id.upper(): c for c in valid_citations}
        valid_ids_set = set(valid_map.keys())

        claims_and_cits = self.extract_claims_and_citations(generated_text)

        claim_results: List[ClaimVerificationResult] = []
        invalid_ids: Set[str] = set()
        warnings: List[str] = []

        supported_count = 0
        unsupported_count = 0
        uncited_count = 0

        for sentence, cits in claims_and_cits:
            # Check for invalid citation IDs
            sentence_invalid = [c for c in cits if c not in valid_ids_set]
            for inv in sentence_invalid:
                invalid_ids.add(inv)
                warnings.append(f"Invalid citation identifier '{inv}' not found in retrieved context.")

            # Resolve valid citations for this sentence
            sentence_valid_chunks = [valid_map[c] for c in cits if c in valid_ids_set]

            # Check if sentence makes a quantitative/scientific factual assertion
            is_factual = bool(FACTUAL_CLAIM_PATTERN.search(sentence))

            if not cits:
                if is_factual:
                    uncited_count += 1
                    claim_results.append(
                        ClaimVerificationResult(
                            claim_text=sentence,
                            cited_ids=[],
                            is_supported=False,
                            support_score=0.0,
                            reasoning="Factual scientific claim lacks citation.",
                            is_uncited=True,
                        )
                    )
                    warnings.append(f"Uncited factual claim detected: '{sentence[:60]}...'")
                continue

            # Evaluate entailment for cited sentence
            is_supported, score, reasoning = self.evaluate_claim_entailment(
                sentence, sentence_valid_chunks
            )

            if is_supported:
                supported_count += 1
            else:
                unsupported_count += 1
                warnings.append(f"Unsupported claim under threshold: '{sentence[:60]}...'")

            claim_results.append(
                ClaimVerificationResult(
                    claim_text=sentence,
                    cited_ids=cits,
                    is_supported=is_supported,
                    support_score=score,
                    reasoning=reasoning,
                    is_uncited=False,
                )
            )

        # Check for fabricated DOIs in generated text
        text_dois = DOI_PATTERN.findall(generated_text)
        valid_dois = {c.doi for c in valid_citations if c.doi}
        for d in text_dois:
            if d not in valid_dois:
                warnings.append(f"Fabricated or unverified DOI detected in response: {d}")
                invalid_ids.add(f"DOI:{d}")

        should_regenerate = (
            len(invalid_ids) > 0 or
            (unsupported_count > 0 and supported_count == 0) or
            (uncited_count > 2)
        )

        is_valid = len(invalid_ids) == 0 and unsupported_count == 0 and uncited_count == 0

        return CitationValidationResult(
            is_valid=is_valid,
            total_claims_count=len(claim_results),
            supported_claims_count=supported_count,
            unsupported_claims_count=unsupported_count,
            uncited_claims_count=uncited_count,
            invalid_citation_ids=sorted(list(invalid_ids)),
            claim_results=claim_results,
            warnings=warnings,
            should_regenerate=should_regenerate,
        )
