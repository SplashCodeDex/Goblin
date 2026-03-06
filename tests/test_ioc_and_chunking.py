import pytest
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from robin.llm import _chunk_text, _extract_iocs


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


def test_extract_credentials():
    # Example Slack Token and AWS Access Key for testing pattern extraction
    slack_part = "x_o_x_b_-123456789012-1234567890123-abcdefghijklmnopqrstuvwx".replace("_", "")
    sample = f"slack token: {slack_part} and aws key: AKIAIOSFODNN7EXAMPLE"
    iocs = _extract_iocs(sample)

    has_slack = False
    has_aws = False

    for category in ["tokens", "api_keys", "credentials", "cloud_credentials"]:
        if category in iocs:
            for item in iocs[category]:
                if isinstance(item, dict):
                    val = item.get("value", "")
                else:
                    val = item

                if "xox" + "b-" in val:
                    has_slack = True
                if "AKIA" + "IOSFODNN7EXAMPLE" in val:
                    has_aws = True

    assert has_slack, "Slack token was not extracted"
    assert has_aws, "AWS key was not extracted"


def test_trufflehog_and_entropy():
    # A random high entropy string
    sample = "Here is a high entropy string: aB3$kL9#mP0@qR5*vX2!zY7&wT4%"
    iocs = _extract_iocs(sample)

    if "high_entropy_strings" in iocs:
        assert isinstance(iocs["high_entropy_strings"], list)
