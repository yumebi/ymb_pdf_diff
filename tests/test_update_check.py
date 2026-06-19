import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ymb_pdf_diff.update_check import check_for_update


def _mock_response(json_data, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_data
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def test_returns_update_info_when_newer_version_available():
    with patch("ymb_pdf_diff.update_check.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"latest_version": "0.2.0", "download_url": "https://example.com/dl"})
        info = check_for_update("0.1.0")
        assert info is not None
        assert info.latest_version == "0.2.0"
        assert info.download_url == "https://example.com/dl"
    print("OK: test_returns_update_info_when_newer_version_available")


def test_returns_none_when_already_up_to_date():
    with patch("ymb_pdf_diff.update_check.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"latest_version": "0.1.0", "download_url": "https://example.com/dl"})
        assert check_for_update("0.1.0") is None
    print("OK: test_returns_none_when_already_up_to_date")


def test_returns_none_when_current_is_newer():
    with patch("ymb_pdf_diff.update_check.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"latest_version": "0.1.0", "download_url": "https://example.com/dl"})
        assert check_for_update("0.5.0") is None
    print("OK: test_returns_none_when_current_is_newer")


def test_returns_none_on_network_error():
    with patch("ymb_pdf_diff.update_check.requests.get") as mock_get:
        mock_get.side_effect = Exception("network down")
        assert check_for_update("0.1.0") is None
    print("OK: test_returns_none_on_network_error")


def test_returns_none_on_http_error_status():
    with patch("ymb_pdf_diff.update_check.requests.get") as mock_get:
        mock_get.return_value = _mock_response({}, status_ok=False)
        assert check_for_update("0.1.0") is None
    print("OK: test_returns_none_on_http_error_status")


def test_returns_none_on_malformed_json():
    with patch("ymb_pdf_diff.update_check.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"unexpected": "shape"})
        assert check_for_update("0.1.0") is None
    print("OK: test_returns_none_on_malformed_json")


if __name__ == "__main__":
    test_returns_update_info_when_newer_version_available()
    test_returns_none_when_already_up_to_date()
    test_returns_none_when_current_is_newer()
    test_returns_none_on_network_error()
    test_returns_none_on_http_error_status()
    test_returns_none_on_malformed_json()
