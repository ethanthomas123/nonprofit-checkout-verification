from nonprofit_signup.signup_checkout import DonorReceipt, NonprofitSignupService, SignupRequest, VolunteerReminder


class RecordingGateway:
    def __init__(self) -> None:
        self.user_payload: dict[str, object] = {}
        self.email_payload: dict[str, object] = {}
        self.email_key = ""

    def create_user(self, payload: dict[str, object]) -> dict[str, object]:
        self.user_payload = payload
        return {"user_id": "donor-42"}

    def send_email(self, payload: dict[str, object], idempotency_key: str) -> dict[str, object]:
        self.email_payload = payload
        self.email_key = idempotency_key
        return {"message_id": "message-99"}


def test_checkout_creates_the_owner_then_sends_a_receipt_verification_link() -> None:
    gateway = RecordingGateway()
    service = NonprofitSignupService(gateway, "https://checkout.example.org")
    result = service.register_donor(
        SignupRequest(
            "donor@example.org",
            "correct-horse-battery-staple",
            "Mina",
            DonorReceipt(2500, "river-cleanup"),
            VolunteerReminder("Saturday sorting", "2026-10-03T09:00:00Z"),
        )
    )
    assert gateway.user_payload["metadata"] == {
        "campaign_code": "river-cleanup",
        "donation_cents": 2500,
        "volunteer_shift": "Saturday sorting",
        "volunteer_starts_at": "2026-10-03T09:00:00Z",
    }
    assert "user_id=donor-42" in result.verification_url
    assert "Confirm email" in str(gateway.email_payload["html"])
    assert result.message_id == "message-99"
    assert gateway.email_key.startswith("nonprofit-email-")

