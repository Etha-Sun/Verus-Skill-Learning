import pytest

from skillopt_verusage.verus_release import (
    FORMAL_VERUS_COMMIT,
    FORMAL_VERUS_VERSION,
    validate_formal_verus,
)


def test_formal_verus_identity_accepts_september_12_release() -> None:
    result = validate_formal_verus(
        {
            "version": FORMAL_VERUS_VERSION,
            "commit": FORMAL_VERUS_COMMIT,
            "profile": "release",
            "platform": {"os": "linux", "arch": "x86_64"},
            "toolchain": "1.88.0-x86_64-unknown-linux-gnu",
        }
    )
    assert result["commit"] == FORMAL_VERUS_COMMIT


def test_formal_verus_identity_rejects_verusage_comparator_commit() -> None:
    with pytest.raises(ValueError, match="formal Verus identity mismatch"):
        validate_formal_verus(
            {
                "version": "0.2025.09.11.ddc6611",
                "commit": "ddc66116aa7a844a9e19cc50922fe85c84b8b4a5",
                "profile": "release",
            }
        )
