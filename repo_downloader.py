"""Entrypoint."""

import asyncio
import os
from base64 import b64decode
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp

from schemas import ContentsResponse


class AsyncRepoDownloader():
    def __init__(self, api_path: str, tasks_limit: int) -> None:
        self.api_path = api_path
        self._base_url: str | None = None
        self._work_dir: str | None = None
        self._semaphore = asyncio.Semaphore(tasks_limit)
        self._tasks: list[asyncio.Task] = []

    @property
    def base_url(self) -> str:
        if self._base_url is None:
            raise ValueError('Base url not set')
        return self._base_url

    @property
    def work_dir(self) -> str:
        if self._work_dir is None:
            raise ValueError('Current working directory not set')
        return self._work_dir

    async def download(self, repo_url: str, download_path: str):
        parsed_url = urlparse(repo_url)
        repo_owner, repo_name = str(parsed_url.path).rsplit('/', maxsplit=2)
        self._base_url = urljoin(
            str(parsed_url.netloc),
            '/'.join(('api', self.api_path, repo_owner, repo_name)),
        )
        self._work_dir = os.path.join(download_path, repo_name)
        await self.fetch_item('/')
        await asyncio.wait(self._tasks)
        self._tasks.clear()

    async def fetch_item(self, path: str):
        await self._semaphore.acquire()
        repo_item = await self.get_item_metadata(self.base_url, path)
        if isinstance(repo_item, list):
            self._semaphore.release()
            await self.fetch_dir(repo_item)
        elif repo_item.content:
            asyncio.create_task(self.write_file(repo_item))

    async def fetch_dir(self, entries: list[ContentsResponse]):
        for entry in entries:
            if entry.type == 'dir':
                os.mkdir(os.path.join(self.work_dir, entry.path))
            await self.fetch_item(entry.path)

    async def get_item_metadata(
        self,
        base_url: str,
        path: str,
    ) -> ContentsResponse | list[ContentsResponse]:
        async with aiohttp.ClientSession(base_url) as session:
            async with session.get(path) as resp:
                parsed_resp = await resp.json()
                if isinstance(parsed_resp, list):
                    return [
                        ContentsResponse.parse_obj(entry)
                        for entry in parsed_resp
                    ]
                return ContentsResponse.parse_obj(parsed_resp)

    async def write_file(self, file_contents: ContentsResponse):
        file_path = os.path.join(self.work_dir, file_contents.path)
        async with aiofiles.open(file_path, 'wb') as file_d:
            await file_d.write(b64decode(file_contents.content))
        self._semaphore.release()
