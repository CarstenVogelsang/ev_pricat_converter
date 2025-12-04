"""Elena Import Trigger Service.

Triggers Elena import via HTTP GET request to getData.php.
"""
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class ImportResult:
    """Result of Elena import trigger."""
    success: bool
    status_code: int = 0
    response_text: str = ''
    url: str = ''
    errors: list = field(default_factory=list)


class ImportTrigger:
    """Triggers Elena import via HTTP GET."""

    def __init__(self, timeout: int = 60):
        """
        Initialize import trigger.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout

    def _build_url(
        self,
        base_url: str,
        startdir: str,
        importfile: str,
        debuglevel: int = 1
    ) -> str:
        """
        Build Elena getData.php URL.

        Args:
            base_url: Base URL (e.g., https://direct.e-vendo.de)
            startdir: Start directory parameter
            importfile: Import filename
            debuglevel: Debug level (0-3)

        Returns:
            Full URL with query parameters
        """
        # Ensure base_url doesn't have trailing slash
        base_url = base_url.rstrip('/')

        # Build query parameters
        params = {
            'startdir': startdir,
            'importfile': importfile,
            'debuglevel': str(debuglevel)
        }

        query_string = urllib.parse.urlencode(params)
        return f"{base_url}/importer/getData.php?{query_string}"

    def trigger(
        self,
        base_url: str,
        startdir: str,
        importfile: str,
        debuglevel: int = 1
    ) -> ImportResult:
        """
        Trigger Elena import via HTTP GET.

        Args:
            base_url: Base URL (e.g., https://direct.e-vendo.de)
            startdir: Start directory parameter
            importfile: Import filename
            debuglevel: Debug level (0=none, 1=errors, 2=warnings, 3=all)

        Returns:
            ImportResult with response details
        """
        result = ImportResult(success=False)

        if not base_url:
            result.errors.append("Base URL not configured")
            return result

        if not startdir:
            result.errors.append("startdir not configured")
            return result

        if not importfile:
            result.errors.append("importfile not specified")
            return result

        url = self._build_url(base_url, startdir, importfile, debuglevel)
        result.url = url

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url)

                result.status_code = response.status_code
                result.response_text = response.text

                # Check for success
                if response.status_code == 200:
                    # Elena might return specific success indicators in response
                    # For now, we consider 200 as success
                    result.success = True
                else:
                    result.errors.append(f"HTTP {response.status_code}")

        except httpx.TimeoutException:
            result.errors.append(f"Request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            result.errors.append(f"Request failed: {str(e)}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")

        return result

    def trigger_for_lieferant(
        self,
        lieferant,
        importfile: str,
        debuglevel: int = 1
    ) -> ImportResult:
        """
        Trigger Elena import for a specific supplier.

        Args:
            lieferant: Lieferant entity with elena_base_url and elena_startdir
            importfile: Import filename
            debuglevel: Debug level

        Returns:
            ImportResult with response details
        """
        result = ImportResult(success=False)

        if not lieferant.elena_base_url:
            result.errors.append("elena_base_url not configured for supplier")
            return result

        if not lieferant.elena_startdir:
            result.errors.append("elena_startdir not configured for supplier")
            return result

        return self.trigger(
            base_url=lieferant.elena_base_url,
            startdir=lieferant.elena_startdir,
            importfile=importfile,
            debuglevel=debuglevel
        )

    async def trigger_async(
        self,
        base_url: str,
        startdir: str,
        importfile: str,
        debuglevel: int = 1
    ) -> ImportResult:
        """
        Trigger Elena import asynchronously.

        Args:
            base_url: Base URL
            startdir: Start directory parameter
            importfile: Import filename
            debuglevel: Debug level

        Returns:
            ImportResult with response details
        """
        result = ImportResult(success=False)

        if not base_url or not startdir or not importfile:
            result.errors.append("Missing required parameters")
            return result

        url = self._build_url(base_url, startdir, importfile, debuglevel)
        result.url = url

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)

                result.status_code = response.status_code
                result.response_text = response.text

                if response.status_code == 200:
                    result.success = True
                else:
                    result.errors.append(f"HTTP {response.status_code}")

        except httpx.TimeoutException:
            result.errors.append(f"Request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            result.errors.append(f"Request failed: {str(e)}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")

        return result
