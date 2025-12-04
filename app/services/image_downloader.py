"""Async Image Downloader Service.

Downloads product images in parallel using async HTTP requests.
"""
import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiohttp


@dataclass
class DownloadStats:
    """Statistics for a download batch."""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0  # Already exists


@dataclass
class DownloadResult:
    """Result of image download operation."""
    success: bool
    stats: DownloadStats = field(default_factory=DownloadStats)
    downloaded_files: list = field(default_factory=list)
    failed_urls: list = field(default_factory=list)
    errors: list = field(default_factory=list)


class ImageDownloader:
    """Async image downloader with parallel execution."""

    def __init__(
        self,
        max_concurrent: int = 5,
        timeout: int = 30,
        skip_existing: bool = True
    ):
        """
        Initialize downloader.

        Args:
            max_concurrent: Maximum parallel downloads
            timeout: Timeout per download in seconds
            skip_existing: Skip download if file already exists
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.skip_existing = skip_existing
        self._semaphore = None

    def _get_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split('/')[-1] if '/' in path else path
        # Clean filename
        filename = filename.split('?')[0]  # Remove query params
        return filename or 'unknown.jpg'

    async def _download_single(
        self,
        session: aiohttp.ClientSession,
        url: str,
        target_dir: Path,
        stats: DownloadStats,
        downloaded_files: list,
        failed_urls: list,
        errors: list
    ) -> None:
        """Download a single image."""
        async with self._semaphore:
            filename = self._get_filename_from_url(url)
            target_path = target_dir / filename

            # Skip if exists
            if self.skip_existing and target_path.exists():
                stats.skipped += 1
                return

            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()

                        # Verify it's actually an image (basic check)
                        content_type = response.headers.get('content-type', '')
                        if not content_type.startswith('image/') and len(content) < 100:
                            raise ValueError(f"Invalid content type: {content_type}")

                        # Write file
                        with open(target_path, 'wb') as f:
                            f.write(content)

                        stats.success += 1
                        downloaded_files.append(str(target_path))
                    else:
                        stats.failed += 1
                        failed_urls.append(url)
                        errors.append(f"HTTP {response.status} for {url}")

            except asyncio.TimeoutError:
                stats.failed += 1
                failed_urls.append(url)
                errors.append(f"Timeout downloading {url}")
            except aiohttp.ClientError as e:
                stats.failed += 1
                failed_urls.append(url)
                errors.append(f"Client error for {url}: {str(e)}")
            except Exception as e:
                stats.failed += 1
                failed_urls.append(url)
                errors.append(f"Error downloading {url}: {str(e)}")

    async def _download_batch(
        self,
        urls: list[str],
        target_dir: Path
    ) -> DownloadResult:
        """Download a batch of images asynchronously."""
        result = DownloadResult(success=True)
        result.stats.total = len(urls)

        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create session with custom headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (pricat-converter/1.0)',
            'Accept': 'image/*,*/*'
        }

        connector = aiohttp.TCPConnector(limit=self.max_concurrent * 2)

        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            tasks = [
                self._download_single(
                    session,
                    url,
                    target_dir,
                    result.stats,
                    result.downloaded_files,
                    result.failed_urls,
                    result.errors
                )
                for url in urls
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        result.success = result.stats.failed == 0
        return result

    def download_all(
        self,
        urls: list[str],
        target_dir: Path,
        max_concurrent: Optional[int] = None
    ) -> DownloadResult:
        """
        Download all images synchronously (wraps async method).

        Args:
            urls: List of image URLs to download
            target_dir: Directory to save images
            max_concurrent: Override max concurrent downloads

        Returns:
            DownloadResult with statistics and file paths
        """
        if max_concurrent:
            self.max_concurrent = max_concurrent

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))

        # Run async download
        return asyncio.run(self._download_batch(unique_urls, target_dir))

    async def download_all_async(
        self,
        urls: list[str],
        target_dir: Path,
        max_concurrent: Optional[int] = None
    ) -> DownloadResult:
        """
        Download all images asynchronously.

        Args:
            urls: List of image URLs to download
            target_dir: Directory to save images
            max_concurrent: Override max concurrent downloads

        Returns:
            DownloadResult with statistics and file paths
        """
        if max_concurrent:
            self.max_concurrent = max_concurrent

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))

        return await self._download_batch(unique_urls, target_dir)


def get_image_target_dir(base_dir: Path, lieferant_vedes_id: str, lieferant_name: str) -> Path:
    """
    Get target directory for supplier images.

    Args:
        base_dir: Base images directory
        lieferant_vedes_id: VEDES ID of supplier
        lieferant_name: Name of supplier

    Returns:
        Path like base_dir/0000001872_LEGO_Spielwaren_GmbH/
    """
    # Clean name for filesystem
    safe_name = "".join(c if c.isalnum() or c in ' _-' else '_' for c in lieferant_name)
    safe_name = safe_name.replace(' ', '_')[:30]  # Limit length

    dir_name = f"{lieferant_vedes_id}_{safe_name}"
    return base_dir / dir_name
