from typing import Literal

from pydantic import BaseModel


class ContentsResponse(BaseModel):
    name: str
    path: str
    type: Literal['file', 'dir', 'symlink', 'submodule']
    encoding: str | None
    content: str | None
    sha: str
    url: str
    download_url: str
