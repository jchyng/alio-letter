"""
hwp/hwpx → pdf 변환 테스트 (LibreOffice 필요).

실행:
    cd pipeline
    pytest tests/test_convert.py -v
"""

from pathlib import Path

import pytest

from scraper import convert_attachment

SAMPLE_DIR = Path(__file__).parent / "sample"

HWP_FILE = SAMPLE_DIR / "sample.hwp"
HWPX_FILE = SAMPLE_DIR / "sample.hwpx"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for f in [HWP_FILE.with_suffix(".pdf"), HWPX_FILE.with_suffix(".pdf")]:
        if f.exists():
            f.unlink()


@pytest.mark.skipif(not HWP_FILE.exists(), reason="hwp 샘플 파일 없음")
def test_hwp_converts_to_pdf():
    result = convert_attachment(str(HWP_FILE), "hwp")

    assert result != "", "변환 실패"
    assert result.endswith(".pdf")
    assert Path(result).exists()
    assert Path(result).stat().st_size > 0


@pytest.mark.skipif(not HWPX_FILE.exists(), reason="hwpx 샘플 파일 없음")
def test_hwpx_converts_to_pdf():
    result = convert_attachment(str(HWPX_FILE), "hwpx")

    assert result != "", "변환 실패"
    assert result.endswith(".pdf")
    assert Path(result).exists()
    assert Path(result).stat().st_size > 0


def test_pdf_returns_empty():
    assert convert_attachment("dummy.pdf", "pdf") == ""


def test_image_returns_empty():
    assert convert_attachment("dummy.jpg", "jpg") == ""
