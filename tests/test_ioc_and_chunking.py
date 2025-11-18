import pytest
from llm import _chunk_text, _extract_iocs


def test_chunking_overlap():
    text = "A" * 5000
    chunks = _chunk_text(text, max_chars=1000, overlap=200)
    assert len(chunks) >= 5
    assert chunks[0].endswith("A")


def test_extract_iocs():
    sample = "email test x@y.com and btc 1BoatSLRHtKNngkdXEeobR76b53LETtpyT and eth 0x1111111111111111111111111111111111111111 and ip 8.8.8.8 and domain example.com"
    iocs = _extract_iocs(sample)
    assert "emails" in iocs and "x@y.com" in iocs["emails"]
    assert any(iocs[k] for k in iocs)
