"""The signup decision used at a donation checkout."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
from typing import Any, Protocol
from urllib.parse import quote


@dataclass(frozen=True)
class DonorReceipt:
    donation_cents: int
    campaign_code: str


@dataclass(frozen=True)
class VolunteerReminder:
    shift_name: str
    starts_at: str


@dataclass(frozen=True)
class CampaignReport:
    campaign_code: str
    donor_count: int
    donation_cents: int


@dataclass(frozen=True)
class SignupRequest:
    email: str
    password: str
    name: str
    receipt: DonorReceipt
    volunteer_reminder: VolunteerReminder | None = None


@dataclass(frozen=True)
class SignupResult:
    user_id: str
    message_id: str
    verification_url: str


class SignupGateway(Protocol):
    def create_user(self, payload: dict[str, object]) -> dict[str, Any]:
        pass

    def send_email(self, payload: dict[str, object], idempotency_key: str) -> dict[str, Any]:
        pass


class NonprofitSignupService:
    def __init__(self, gateway: SignupGateway, verify_base_url: str) -> None:
        self.gateway = gateway
        self.verify_base_url = verify_base_url.rstrip("/")

    def register_donor(self, request: SignupRequest) -> SignupResult:
        signup_key = self._key("user", request.email, request.receipt.campaign_code)
        metadata: dict[str, object] = {
            "campaign_code": request.receipt.campaign_code,
            "donation_cents": request.receipt.donation_cents,
        }
        if request.volunteer_reminder:
            metadata["volunteer_shift"] = request.volunteer_reminder.shift_name
            metadata["volunteer_starts_at"] = request.volunteer_reminder.starts_at
        user = self.gateway.create_user(
            {
                "email": request.email,
                "password": request.password,
                "name": request.name,
                "metadata": metadata,
                "idempotency_key": signup_key,
            }
        )
        user_id = str(user["user_id"])
        verification_url = f"{self.verify_base_url}/verify-email?user_id={quote(user_id)}"
        email = self.gateway.send_email(
            {
                "to": request.email,
                "subject": "Confirm your email for the community checkout",
                "html": self._verification_html(request.name, verification_url),
            },
            self._key("email", user_id, request.email),
        )
        return SignupResult(user_id, str(email["message_id"]), verification_url)

    @staticmethod
    def campaign_report(receipts: list[DonorReceipt]) -> CampaignReport:
        if not receipts:
            return CampaignReport("none", 0, 0)
        campaign_code = receipts[0].campaign_code
        selected = [receipt for receipt in receipts if receipt.campaign_code == campaign_code]
        return CampaignReport(campaign_code, len(selected), sum(item.donation_cents for item in selected))

    @staticmethod
    def _key(kind: str, first: str, second: str) -> str:
        return f"nonprofit-{kind}-{sha256(f'{first}:{second}'.encode()).hexdigest()[:24]}"

    @staticmethod
    def _verification_html(name: str, verification_url: str) -> str:
        return (
            f"<h1>Thanks, {escape(name)}</h1>"
            "<p>Your donation checkout is recorded. Confirm this email to receive your receipt.</p>"
            f'<p><a href="{escape(verification_url, quote=True)}">Confirm email</a></p>'
        )
