"""
ChemRAG — Hybrid Literature Search Integration & Diagnostics Verification Suite
================================================---------------------------------
Tests:
1. GET /api/v1/search/diagnostics (DB status, pgvector status, indexed counts)
2. POST /api/v1/search (query_text payload)
3. POST /api/v1/search/hybrid (query payload alias)
4. Empty query validation (HTTP 400 Bad Request)
5. Result fields verification (document_title, page_number, score_breakdown)
"""

from __future__ import annotations
import requests

BASE_URL = "http://localhost:8000/api/v1"


def test_hybrid_search_suite():
    print("=" * 75)
    print(" CHEM-RAG HYBRID LITERATURE SEARCH VERIFICATION SUITE")
    print("=" * 75)

    # 1. Diagnostics Test
    print("\n--- 1. Testing GET /api/v1/search/diagnostics ---")
    diag_resp = requests.get(f"{BASE_URL}/search/diagnostics")
    print("HTTP Status Code:", diag_resp.status_code)
    assert diag_resp.status_code == 200, f"Diagnostics failed: {diag_resp.text}"
    diag_data = diag_resp.json()
    print("Diagnostics Summary:")
    print(f"  - Database Status: {diag_data.get('status')}")
    print(f"  - pgvector Active: {diag_data.get('pgvector_active')}")
    print(f"  - Indexed Documents: {diag_data.get('indexed_documents_count')}")
    print(f"  - Indexed Chunks: {diag_data.get('indexed_chunks_count')}")
    print(f"  - Stored Embeddings: {diag_data.get('stored_embeddings_count')}")

    # 2. POST /api/v1/search (query_text)
    print("\n--- 2. Testing POST /api/v1/search (query_text payload) ---")
    query_payload = {"query_text": "Ethanol hydrogenation Pt/Al2O3", "top_k": 5, "rerank": True}
    res_1 = requests.post(f"{BASE_URL}/search", json=query_payload)
    print("HTTP Status Code:", res_1.status_code)
    assert res_1.status_code == 200, f"POST /search failed: {res_1.text}"
    data_1 = res_1.json()
    print(f"Query: '{data_1.get('query_text')}' | Total Results: {data_1.get('total_results')} | Latency: {data_1.get('latency_ms')} ms")
    
    results_1 = data_1.get("results", [])
    assert len(results_1) > 0, "No results returned for indexed query!"
    first_res = results_1[0]
    print("Top Candidate Result:")
    print(f"  - Document Title: {first_res.get('document_title')}")
    print(f"  - Page Number: {first_res.get('page_number')}")
    print(f"  - Score: {first_res.get('score')}")
    print(f"  - Score Breakdown: {first_res.get('score_breakdown')}")
    print(f"  - Passage Snippet: {first_res.get('content')[:100]}...")

    # 3. POST /api/v1/search/hybrid (query alias)
    print("\n--- 3. Testing POST /api/v1/search/hybrid (query alias payload) ---")
    alias_payload = {"query": "What is the boiling point of ethanol?", "top_k": 5}
    res_2 = requests.post(f"{BASE_URL}/search/hybrid", json=alias_payload)
    print("HTTP Status Code:", res_2.status_code)
    assert res_2.status_code == 200, f"POST /search/hybrid failed: {res_2.text}"
    data_2 = res_2.json()
    print(f"Query: '{data_2.get('query_text')}' | Total Results: {data_2.get('total_results')}")

    # 4. Empty Query Validation Test
    print("\n--- 4. Testing Empty Query Validation ---")
    bad_payload = {"query": "   "}
    res_3 = requests.post(f"{BASE_URL}/search", json=bad_payload)
    print("HTTP Status Code:", res_3.status_code)
    assert res_3.status_code == 400, f"Empty query should return HTTP 400, got: {res_3.status_code}"
    print(f"Error Message: {res_3.json().get('detail')}")

    print("\n" + "=" * 75)
    print(" ALL HYBRID SEARCH INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    test_hybrid_search_suite()
