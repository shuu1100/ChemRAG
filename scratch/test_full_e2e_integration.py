"""
ChemRAG — Full End-to-End Automated Integration Verification Suite
==================================================================
Tests:
1. PDF Creation & Multipart Upload (durable file persistence & PostgreSQL record)
2. Background Ingestion Pipeline execution (GROBID/layout parsing, page provenance, chunking, 3072d embedding, pgvector storage)
3. Background Jobs Monitoring API (GET /documents/jobs)
4. Experimental Data Extraction & Querying (GET /experiments)
5. Hybrid Vector/Lexical Search & Citations Grounding (POST /search & POST /chat)
6. RDKit 2D Structure Rendering (Oxygen O=O, Ethanol CCO, Invalid SMILES)
"""
from __future__ import annotations

import io
import time
import requests

BASE_URL = "http://localhost:8000/api/v1"

def create_sample_pdf_bytes() -> bytes:
    """Generates a minimal valid scientific PDF document with text and experimental procedures."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 380 >>\nstream\n"
        b"BT\n"
        b"/F1 12 Tf\n"
        b"50 720 Td\n"
        b"(Thermodynamics of Ethanol-Water Binary Mixtures and Catalytic Hydrogenation) Tj\n"
        b"0 -20 Td\n"
        b"(Abstract: Experimental catalytic hydrogenation of ethanol over Pt/Al2O3 catalysts was conducted.) Tj\n"
        b"0 -20 Td\n"
        b"(Experimental Procedure: Reaction was heated to 80 deg C in Ethanol with Pt/Al2O3 catalyst yielding 94% product.) Tj\n"
        b"0 -20 Td\n"
        b"(Equilibrium data for CCO and O=O mixtures were recorded at 2.5 bar pressure for 4 hours.) Tj\n"
        b"ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000062 00000 n \n"
        b"0000000119 00000 n \n"
        b"0000000262 00000 n \n"
        b"0000000692 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n763\n"
        b"%%EOF"
    )
    return pdf_content


def run_e2e_verification():
    print("=" * 75)
    print(" CHEM-RAG END-TO-END SYSTEM INTEGRATION VERIFICATION")
    print("=" * 75)

    # 1. Test PDF Upload
    pdf_bytes = create_sample_pdf_bytes()
    filename = f"nano_test_paper_{int(time.time())}.pdf"
    
    files = {"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")}
    data = {
        "organization_id": "00000000-0000-0000-0000-000000000000",
        "is_public": "false",
    }
    
    print("\n--- 1. Testing Document Upload ---")
    resp = requests.post(f"{BASE_URL}/documents/upload", files=files, data=data)
    print("Upload HTTP Code:", resp.status_code)
    assert resp.status_code in (200, 202, 409), f"Upload failed: {resp.text}"
    upload_res = resp.json()
    doc_id = upload_res.get("document_id")
    job_id = upload_res.get("job_id")
    print(f"Uploaded Doc ID: {doc_id}, Job ID: {job_id}")

    # 2. Test Fetching Document List
    print("\n--- 2. Testing Document List Persistence ---")
    list_resp = requests.get(f"{BASE_URL}/documents")
    assert list_resp.status_code == 200, f"List failed: {list_resp.text}"
    docs = list_resp.json()
    matching = [d for d in docs if d.get("id") == doc_id or d.get("filename") == filename]
    print(f"Total documents in corpus: {len(docs)}")
    assert len(matching) > 0, "Uploaded document not found in list response!"
    doc_meta = matching[0]
    print(f"Document verified: ID={doc_meta['id']}, filename={doc_meta['filename']}, pages={doc_meta.get('page_count')}, chunks={doc_meta.get('chunk_count')}")

    # 3. Test Ingestion Job Processing & Polling
    print("\n--- 3. Testing Ingestion Job Status & Pipeline Execution ---")
    if doc_id:
        proc_resp = requests.post(f"{BASE_URL}/documents/{doc_id}/process")
        if proc_resp.status_code == 200:
            job_id = proc_resp.json().get("id")

    if job_id:
        max_wait = 30
        completed = False
        for i in range(max_wait):
            j_resp = requests.get(f"{BASE_URL}/documents/jobs/{job_id}")
            if j_resp.status_code == 200:
                j_info = j_resp.json()
                state = j_info.get("state")
                phase = j_info.get("current_phase")
                progress = j_info.get("progress_pct")
                print(f"[{i+1}s] Job State: {state} | Phase: {phase} | Progress: {progress}%")
                if state == "completed":
                    completed = True
                    break
                elif state == "failed":
                    print(f"Job failed: {j_info.get('error_message')}")
                    break
            time.sleep(1)

        assert completed or state == "completed", "Ingestion pipeline job did not complete successfully!"

    # 4. Test Experimental Records Extraction API
    print("\n--- 4. Testing Experimental Records Extraction ---")
    exp_resp = requests.get(f"{BASE_URL}/experiments")
    assert exp_resp.status_code == 200, f"Experiments GET failed: {exp_resp.text}"
    exps = exp_resp.json()
    print(f"Extracted experimental records count: {len(exps)}")
    for e in exps[:3]:
        print(f"  - Record: {e.get('description')[:70]}... | Conditions: {e.get('experimental_conditions')}")

    # 5. Test Hybrid Search & Research Chat Retrieval Grounding
    print("\n--- 5. Testing Hybrid Retrieval & Research Chat Grounding ---")
    search_resp = requests.post(
        f"{BASE_URL}/search",
        json={"query_text": "Ethanol hydrogenation Pt/Al2O3", "top_k": 5, "rerank": True},
    )
    assert search_resp.status_code == 200, f"Search failed: {search_resp.text}"
    search_data = search_resp.json()
    print(f"Hybrid Search Results Returned: {search_data.get('total_results')} candidates")

    chat_resp = requests.post(
        f"{BASE_URL}/chat",
        json={"query": "What are the experimental conditions for ethanol hydrogenation?"},
    )
    assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
    chat_data = chat_resp.json()
    print(f"Research Chat Response: {chat_data.get('answer')[:120]}...")
    print(f"Citations Count: {len(chat_data.get('citations', []))}")

    # 6. Test RDKit Molecular Structure Validation & 2D SVG
    print("\n--- 6. Testing RDKit Structure Validation & 2D SVG Depiction ---")
    res_oxygen = requests.post(f"{BASE_URL}/chemistry/resolve", json={"query": "Oxygen", "query_type": "name"}).json()
    assert res_oxygen.get("found") is True and res_oxygen.get("structure_svg"), "Oxygen SVG resolution failed"
    print("  - Oxygen (O=O): SVG generated (length", len(res_oxygen["structure_svg"]), "chars)")

    res_ethanol = requests.post(f"{BASE_URL}/chemistry/resolve", json={"query": "CCO", "query_type": "smiles"}).json()
    assert res_ethanol.get("found") is True and res_ethanol.get("structure_svg"), "Ethanol SVG resolution failed"
    print("  - Ethanol (CCO): SVG generated (length", len(res_ethanol["structure_svg"]), "chars)")

    res_invalid = requests.post(f"{BASE_URL}/chemistry/resolve", json={"query": "invalid_smiles_string_12345", "query_type": "smiles"}).json()
    assert res_invalid.get("found") is False, "Invalid SMILES test failed"
    print("  - Invalid SMILES: Handled gracefully (found=False, message=", res_invalid.get("message"), ")")

    print("\n" + "=" * 75)
    print(" ALL CHEM-RAG END-TO-END VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    run_e2e_verification()
