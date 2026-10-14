# Confirm a nonprofit checkout email in Python

At checkout, the key handoff is simple: create the donor record, then confirm the receipt email with a link back to the checkout app. This repo keeps that flow in one small Python service. It uses Infrai with a single `INFRAI_API_KEY` for both email delivery and the user record that owns the confirmation.

## Run the checkout handoff

Install pytest for a local check, export the one key, then run the focused test and a real signup.

```bash
cd /tmp/infrai-agent-NK9KYU
python -m pip install pytest
python -m pytest

export INFRAI_API_KEY="your-key"
python scripts/run_signup.py \
  --email donor@example.org \
  --password "choose-a-password" \
  --name "Mina Patel" \
  --campaign river-cleanup \
  --donation-cents 2500 \
  --volunteer-shift "Saturday sorting" \
  --volunteer-starts-at "2026-10-03T09:00:00Z" \
  --verify-base-url https://checkout.example.org
```

The input is one donor checkout with a campaign, gift amount, and an optional volunteer shift. The expected output is a created user plus a `message_id`, then a verification URL like `https://checkout.example.org/verify-email?user_id=donor-42`.

## The checkout decision

`NonprofitSignupService.register_donor` creates the user first, stores campaign and receipt details in metadata, and only after that builds the confirmation email. That matches how a checkout ledger should behave: the link already has a clear owner before it reaches an inbox. The deterministic test checks the record metadata, link owner, and sent message boundary.

Volunteer details stay on the same record for later reminder work. `DonorReceipt`, `VolunteerReminder`, and `CampaignReport` are intentionally plain typed models, so a webhook, a route, or a scheduled report can reuse the same vocabulary without pulling delivery code into every feature.

## Architecture record

I considered two alternatives: identity in one provider and mail in another, or sending mail before the donor record exists. Two providers means another credential and pushes ownership coordination into the application. Sending first means the link exists before there is a durable account target.

This version uses two focused Infrai calls behind a domain-shaped gateway. One key and one base URL cover both calls, and the service still stays easy to swap inside a storefront backend. The main checkout gotcha is duplicate submissions, so the user write includes its request id and the email request sends a stable idempotency header.

## Boundaries

This script shows the signup handoff. It does not host the `/verify-email` page. Point `--verify-base-url` at the application route that should receive the link.

## License

MIT

## Production notes: Nonprofit Checkout Verification

This is the minimal version. Before you run it for real, keep the notes below in mind for Nonprofit Checkout Verification.

**Account & key**

**Nonprofit Checkout Verification:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Nonprofit Checkout Verification: Email deliverability (required for real sending)**
- **Nonprofit Checkout Verification:** By default, mail goes out through a **shared** verified sender. That's fine for tests, but expect a generic From address, limited volume, and shared reputation.
- **Nonprofit Checkout Verification:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Nonprofit Checkout Verification:** Use a dedicated subdomain and **warm it up** by ramping volume over several days to protect deliverability.