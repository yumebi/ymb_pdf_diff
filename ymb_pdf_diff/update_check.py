from dataclasses import dataclass
from typing import Optional

import requests
from packaging.version import InvalidVersion, parse as parse_version

# TODO: 実際のGitHub公開リポジトリが決まったら owner/repo を差し替える
DEFAULT_VERSION_URL = "https://raw.githubusercontent.com/<owner>/<repo>/main/version.json"
DEFAULT_TIMEOUT = 3.0


@dataclass
class UpdateInfo:
    latest_version: str
    download_url: str


def check_for_update(
    current_version: str, version_url: str = DEFAULT_VERSION_URL, timeout: float = DEFAULT_TIMEOUT
) -> Optional[UpdateInfo]:
    """version.jsonを取得し、現在バージョンより新しい場合のみUpdateInfoを返す。

    通信失敗・形式不正・比較不能などは全てNoneを返す(起動を妨げないため、ここでは例外を投げない)。
    """
    try:
        response = requests.get(version_url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        latest_version = str(data["latest_version"])
        download_url = str(data.get("download_url", ""))
    except Exception:
        return None

    try:
        if parse_version(latest_version) <= parse_version(current_version):
            return None
    except InvalidVersion:
        return None

    return UpdateInfo(latest_version=latest_version, download_url=download_url)
