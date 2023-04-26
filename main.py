"""Entrypoint."""

import asyncio
import os
from base64 import b64decode
from urllib.parse import urljoin, urlparse
from tempfile import TemporaryDirectory

import aiohttp
import aiofiles

from schemas import ContentsResponse
from repo_downloader import AsyncRepoDownloader

REPO_URL = os.getenv('REPO_URL')
API_PATH = os.getenv('API_PATH', 'api/v1')
SEMAPHORE_LIMIT = int(os.getenv('LIMIT', 3))


if __name__ == '__main__':
    ...
