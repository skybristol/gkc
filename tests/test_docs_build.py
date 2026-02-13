import shutil
import subprocess

import pytest


@pytest.mark.docs
def test_mkdocs_build_strict(tmp_path):
    mkdocs = shutil.which("mkdocs")
    if mkdocs is None:
        pytest.skip("mkdocs is not installed. Run: poetry install --with docs")

    site_dir = tmp_path / "site"
    subprocess.run(
        [mkdocs, "build", "--strict", "--site-dir", str(site_dir)],
        check=True,
    )
