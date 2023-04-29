import asyncio
import os
from base64 import b64decode
from urllib.parse import urlparse

import aiofiles
import aiohttp

from .schemas import ContentsResponse

API_BASE_URL = 'https://api.github.com'
CHUNK_SIZE = 1024


class AsyncRepoDownloader:
    def __init__(
        self,
        repo_url: str,
        *,
        api_base_url: str = API_BASE_URL,
        tasks_limit: int = 1,
    ) -> None:
        parsed_url = urlparse(repo_url)
        self._repo_owner, self._repo_name = (
            path.strip('/') for path in parsed_url.path.rsplit('/', maxsplit=1)
        )
        self._base_url = api_base_url
        self._api_path = f'/repos/{self._repo_owner}/{self._repo_name}/contents'
        self._work_dir: str | None = None
        self._semaphore = asyncio.Semaphore(tasks_limit)
        self._tasks: set[asyncio.Task] = set()

    @ property
    def repo_owner(self) -> str:
        return self._repo_owner

    @ property
    def repo_name(self) -> str:
        return self._repo_name

    async def download(self, download_path: str) -> None:
        self._work_dir = os.path.join(download_path, self._repo_name)
        os.mkdir(self.__get_work_dir())
        await self.__fetch_item('/')
        await asyncio.wait(self._tasks)
        self._tasks.clear()

    async def __fetch_item(self, path: str) -> None:
        await self._semaphore.acquire()
        repo_item = await self.__get_item_metadata(path)
        if isinstance(repo_item, list):
            self._semaphore.release()
            await self.__fetch_dir(repo_item)
        elif repo_item.content:
            self._tasks.add(asyncio.create_task(self.__write_file(repo_item)))
        elif repo_item.download_url:
            self._tasks.add(asyncio.create_task(self.__download_raw(repo_item)))

    async def __fetch_dir(self, entries: list[ContentsResponse]) -> None:
        for entry in entries:
            if entry.type == 'dir':
                os.mkdir(self.__get_destination(entry))
            await self.__fetch_item(entry.path)

    async def __get_item_metadata(
        self,
        item_path: str,
    ) -> ContentsResponse | list[ContentsResponse]:
        request_path = '/'.join((self._api_path, item_path)).rstrip('/')
        async with aiohttp.ClientSession(self._base_url) as session:
            async with session.get(request_path) as resp:
                resp.raise_for_status()
                parsed_resp = await resp.json()
                if isinstance(parsed_resp, list):
                    return [
                        ContentsResponse.parse_obj(entry)
                        for entry in parsed_resp
                    ]
                return ContentsResponse.parse_obj(parsed_resp)

    async def __write_file(self, file_contents: ContentsResponse) -> None:
        file_path = self.__get_destination(file_contents)
        async with aiofiles.open(file_path, 'wb') as file_d:
            await file_d.write(b64decode(file_contents.content))
        self._semaphore.release()

    async def __download_raw(self, metadata: ContentsResponse) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(metadata.download_url) as resp:
                await self.__write_chunks(self.__get_destination(metadata), resp)

    async def __write_chunks(self, path: str, resp: aiohttp.ClientResponse) -> None:
        async with aiofiles.open(path, 'wb') as file_d:
            while not resp.content.at_eof():
                chunk = await resp.content.read(CHUNK_SIZE)
                await file_d.write(chunk)

    def __get_destination(self, item: ContentsResponse) -> str:
        return os.path.join(self.__get_work_dir(), item.path)

    def __get_work_dir(self) -> str:
        if self._work_dir is None:
            raise AttributeError('Current working directory not set')
        return self._work_dir
