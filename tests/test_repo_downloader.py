from unittest.mock import patch, AsyncMock

import pytest

from repo_downloader import AsyncRepoDownloader
from schemas import ContentsResponse


@patch('aiohttp.ClientSession.get')
def test_repo_downloader(request_mock: AsyncMock, tmp_path):
    request_mock.return_value.__aenter__.return_value.json = ContentsResponse(
        name=""
    )
