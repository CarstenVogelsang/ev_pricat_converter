"""Firecrawl Service for website branding analysis."""
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from app import db
from app.models import Config


@dataclass
class FirecrawlResult:
    """Result of Firecrawl analysis."""
    success: bool
    error: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_primary_color: Optional[str] = None
    text_secondary_color: Optional[str] = None
    raw_response: Optional[dict] = None


class FirecrawlService:
    """Service for Firecrawl API integration."""

    API_BASE_URL = 'https://api.firecrawl.dev/v1'
    TIMEOUT = 60  # seconds
    DEFAULT_CREDIT_COST = Decimal('0.005')  # Euro per credit

    def __init__(self):
        self.api_key = Config.get_value('firecrawl_api_key', '')

    def _get_headers(self) -> dict:
        """Get API request headers."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _get_credit_cost(self) -> Decimal:
        """Get cost per credit from config."""
        cost_str = Config.get_value('firecrawl_credit_kosten', '0.005')
        try:
            return Decimal(cost_str)
        except (ValueError, TypeError):
            return self.DEFAULT_CREDIT_COST

    def _track_usage(
        self, kunde, user_id: int, credits: int = 1, endpoint: str = 'scrape/branding'
    ) -> None:
        """Track API usage for billing."""
        from app.models import KundeApiNutzung

        kosten = self._get_credit_cost() * credits

        nutzung = KundeApiNutzung(
            kunde_id=kunde.id,
            user_id=user_id,
            api_service='firecrawl',
            api_endpoint=endpoint,
            credits_used=credits,
            kosten_euro=kosten,
            beschreibung=f'Website-Analyse: {kunde.website_url}'
        )
        db.session.add(nutzung)
        # Commit happens in _save_to_kunde_ci

    def analyze_branding(self, kunde, user_id: int = None) -> FirecrawlResult:
        """
        Analyze a Kunde's website for branding information.

        Args:
            kunde: Kunde entity with website_url set
            user_id: ID of user triggering the call (for billing)

        Returns:
            FirecrawlResult with extracted branding data
        """
        from app.models import KundeCI

        result = FirecrawlResult(success=False)

        if not self.api_key:
            result.error = 'Firecrawl API-Key nicht konfiguriert'
            return result

        if not kunde.website_url:
            result.error = 'Website-URL nicht gesetzt'
            return result

        try:
            # Call Firecrawl API
            response = httpx.post(
                f'{self.API_BASE_URL}/scrape',
                headers=self._get_headers(),
                json={
                    'url': kunde.website_url,
                    'formats': ['branding']
                },
                timeout=self.TIMEOUT
            )

            response.raise_for_status()
            data = response.json()

            # Extract branding data
            response_data = data.get('data', {})
            branding = response_data.get('branding', {})
            colors = branding.get('colors', {})
            # images can be at branding.images or data.images
            branding_images = branding.get('images', {})
            root_images = response_data.get('images', {})

            result.success = True
            # Try branding.logo first, then branding.images.logo, then data.images.logo
            result.logo_url = (
                branding.get('logo') or
                branding_images.get('logo') or
                root_images.get('logo')
            )
            result.primary_color = colors.get('primary')
            result.secondary_color = colors.get('secondary')
            result.accent_color = colors.get('accent')
            result.background_color = colors.get('background')
            result.text_primary_color = colors.get('textPrimary')
            result.text_secondary_color = colors.get('textSecondary')
            result.raw_response = data

            # Track API usage (only on success and if user_id provided)
            if user_id:
                self._track_usage(kunde, user_id, credits=1, endpoint='scrape/branding')

            # Save to KundeCI
            self._save_to_kunde_ci(kunde, result, KundeCI)

        except httpx.HTTPStatusError as e:
            result.error = f'API-Fehler: {e.response.status_code}'
        except httpx.RequestError as e:
            result.error = f'Verbindungsfehler: {str(e)}'
        except Exception as e:
            result.error = f'Unerwarteter Fehler: {str(e)}'

        return result

    def _save_to_kunde_ci(self, kunde, result: FirecrawlResult, KundeCI) -> None:
        """Save Firecrawl result to KundeCI table."""
        kunde_ci = kunde.ci or KundeCI(kunde_id=kunde.id)

        kunde_ci.logo_url = result.logo_url
        kunde_ci.primary_color = result.primary_color
        kunde_ci.secondary_color = result.secondary_color
        kunde_ci.accent_color = result.accent_color
        kunde_ci.background_color = result.background_color
        kunde_ci.text_primary_color = result.text_primary_color
        kunde_ci.text_secondary_color = result.text_secondary_color
        kunde_ci.analysiert_am = datetime.utcnow()
        kunde_ci.analyse_url = kunde.website_url
        kunde_ci.raw_response = json.dumps(result.raw_response) if result.raw_response else None

        if not kunde.ci:
            db.session.add(kunde_ci)

        db.session.commit()

    @staticmethod
    def reparse_logo_from_raw(kunde_ci) -> Optional[str]:
        """
        Re-extract logo URL from stored raw_response.

        This is useful when the extraction logic is updated and we want
        to apply it to existing data without making a new API call.

        Args:
            kunde_ci: KundeCI entity with raw_response

        Returns:
            Logo URL if found, None otherwise
        """
        if not kunde_ci or not kunde_ci.raw_response:
            return None

        try:
            data = json.loads(kunde_ci.raw_response)
            response_data = data.get('data', {})
            branding = response_data.get('branding', {})
            # images can be at branding.images or data.images
            branding_images = branding.get('images', {})
            root_images = response_data.get('images', {})

            # Try branding.logo first, then branding.images.logo, then data.images.logo
            logo_url = (
                branding.get('logo') or
                branding_images.get('logo') or
                root_images.get('logo')
            )

            if logo_url and logo_url != kunde_ci.logo_url:
                kunde_ci.logo_url = logo_url
                db.session.commit()

            return logo_url
        except (json.JSONDecodeError, TypeError):
            return None
