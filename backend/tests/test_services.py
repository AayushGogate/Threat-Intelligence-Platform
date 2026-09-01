import pytest

from app.models.ioc import IOCType
from app.services.validation import validate_ioc, ValidationError
from app.services.normalization import normalize_ioc
from app.services.scoring import calculate_score


class TestValidation:
    def test_valid_ipv4(self):
        validate_ioc(IOCType.IPV4, "192.0.2.10")  # should not raise

    def test_invalid_ipv4(self):
        with pytest.raises(ValidationError):
            validate_ioc(IOCType.IPV4, "999.999.999.999")

    def test_valid_domain(self):
        validate_ioc(IOCType.DOMAIN, "example.com")

    def test_invalid_domain(self):
        with pytest.raises(ValidationError):
            validate_ioc(IOCType.DOMAIN, "not a domain")

    def test_valid_sha256(self):
        validate_ioc(IOCType.SHA256, "a" * 64)

    def test_invalid_sha256_wrong_length(self):
        with pytest.raises(ValidationError):
            validate_ioc(IOCType.SHA256, "a" * 63)

    def test_valid_cve(self):
        validate_ioc(IOCType.CVE, "CVE-2024-12345")

    def test_invalid_cve(self):
        with pytest.raises(ValidationError):
            validate_ioc(IOCType.CVE, "NOT-A-CVE")

    def test_empty_value_rejected(self):
        with pytest.raises(ValidationError):
            validate_ioc(IOCType.IPV4, "")


class TestNormalization:
    def test_domain_lowercased(self):
        assert normalize_ioc(IOCType.DOMAIN, "Example.COM.") == "example.com"

    def test_hash_lowercased(self):
        assert normalize_ioc(IOCType.SHA256, "A" * 64) == "a" * 64

    def test_email_lowercased(self):
        assert normalize_ioc(IOCType.EMAIL, "User@Example.COM") == "user@example.com"

    def test_cve_uppercased(self):
        assert normalize_ioc(IOCType.CVE, "cve-2024-1234") == "CVE-2024-1234"


class TestScoring:
    def test_score_within_bounds(self, db_session):
        from app.models.ioc import IOC, Source

        source = Source(name="Test Source", reliability="A")
        db_session.add(source)
        db_session.flush()

        ioc = IOC(type=IOCType.IPV4, value="192.0.2.5", normalized_value="192.0.2.5", primary_source_id=source.id)
        db_session.add(ioc)
        db_session.flush()

        score, breakdown = calculate_score(db_session, ioc)
        assert 0 <= score <= 100
        assert "Final Score" in breakdown
