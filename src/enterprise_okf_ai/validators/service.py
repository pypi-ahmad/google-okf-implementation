"""Validation service wrapper for OKF bundles."""

from __future__ import annotations

from pathlib import Path

from validators.okf_validator import OKFValidator, ValidationReport


class BundleValidator:
    """Run structural and semantic checks on an OKF directory."""

    def __init__(self, validator: OKFValidator | None = None):
        self._validator = validator or OKFValidator()

    def validate(self, okf_dir: str | Path) -> ValidationReport:
        """Validate an OKF bundle and return diagnostics."""

        return self._validator.validate(Path(okf_dir))
