"""Run one nonprofit checkout signup against Infrai."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nonprofit_signup.infrai_client import InfraiClient, InfraiError
from nonprofit_signup.signup_checkout import DonorReceipt, NonprofitSignupService, SignupRequest, VolunteerReminder


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a donor account and send its confirmation email.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--donation-cents", required=True, type=int)
    parser.add_argument("--verify-base-url", required=True)
    parser.add_argument("--volunteer-shift")
    parser.add_argument("--volunteer-starts-at")
    args = parser.parse_args()
    reminder = None
    if args.volunteer_shift and args.volunteer_starts_at:
        reminder = VolunteerReminder(args.volunteer_shift, args.volunteer_starts_at)
    client = InfraiClient()
    service = NonprofitSignupService(client, args.verify_base_url)
    created_user_id = None
    original_create = client.create_user

    def track_user(payload: dict[str, object]) -> dict[str, object]:
        nonlocal created_user_id
        user = original_create(payload)
        created_user_id = str(user["user_id"])
        return user

    client.create_user = track_user
    try:
        result = service.register_donor(
            SignupRequest(args.email, args.password, args.name, DonorReceipt(args.donation_cents, args.campaign), reminder)
        )
        print(f"created user {result.user_id}; sent verification email {result.message_id}")
        print(f"verification link: {result.verification_url}")
    finally:
        if created_user_id is not None:
            client.delete_user(created_user_id)
            try:
                client.get_user(created_user_id)
            except InfraiError as exc:
                if exc.status_code != 404:
                    raise
            else:
                raise RuntimeError(f"user {created_user_id} still exists after deletion")
            print(f"deleted user {created_user_id}; verified absent")


if __name__ == "__main__":
    main()
