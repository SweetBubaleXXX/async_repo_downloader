import argparse
import asyncio
import logging
import os

from repo_downloader.downloader import AsyncRepoDownloader

parser = argparse.ArgumentParser()
parser.add_argument('repo_url')
parser.add_argument('download_path')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-t', '--tasks', type=int, default=3)


async def main():
    args = parser.parse_args()
    if not os.path.isdir(args.download_path):
        raise ValueError("Directory doesn't exist")
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s: %(message)s',
    )
    downloader = AsyncRepoDownloader(args.repo_url, tasks_limit=args.tasks)
    await downloader.download(args.download_path)


if __name__ == '__main__':
    asyncio.run(main())
