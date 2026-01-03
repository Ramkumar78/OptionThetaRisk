
import pytest
import os

def test_groupby_axis_regression():
    """
    Scans the codebase for the deprecated 'groupby(level=0, axis=1)' pattern.
    This ensures no regressions are introduced.
    """
    file_path = "option_auditor/screener.py"

    if not os.path.exists(file_path):
        pytest.fail(f"File not found: {file_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Check for specific variations
    if "groupby(level=0, axis=1)" in content:
        pytest.fail(f"Found deprecated 'groupby(level=0, axis=1)' in {file_path}")

    if "groupby(axis=1)" in content:
        # We need to be careful if there are valid uses of axis=1 in groupby (rare/deprecated)
        # But let's flag it to be safe
        pytest.fail(f"Found deprecated 'groupby(..., axis=1)' in {file_path}")

if __name__ == "__main__":
    pytest.main([__file__])
