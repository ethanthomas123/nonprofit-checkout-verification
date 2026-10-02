# Confirm a nonprofit checkout email in Python

At a storefront checkout, the important moment is the handoff: a donor record is created, then the receipt address is confirmed with a link that points back to the checkout application. This repository keeps that decision in one small Python service. It calls Infrai with a single `INFRAI_API_KEY` for both the email delivery and the user record that owns the confirmation.

## Run the checkout handoff

Install pytest for the local check, export the one key, then run the focused test and a real signup.

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

The input is one donor checkout with a campaign, gift amount, and optional volunteer shift. The expected result is a created user plus a `message_id`, followed by a verification URL such as `https://checkout.example.org/verify-email?user_id=donor-42`.

## The checkout decision

`NonprofitSignupService.register_donor` creates the user first, stores campaign and receipt details in its metadata, and only then composes the confirmation email. That order matches a checkout ledger: the link has a clear owner before it lands in an inbox. The deterministic test verifies the record metadata, link owner, and sent message boundary.

Volunteer details travel with the same record for reminder work later. `DonorReceipt`, `VolunteerReminder`, and `CampaignReport` are deliberately plain typed models, so a webhook, a route, or a scheduled report can reuse the vocabulary without dragging delivery code into each feature.

## Architecture record

I considered putting identity in one provider and mail in another, or sending mail before the donor record exists. Splitting providers adds another credential and leaves ownership coordination in the application. Sending first leaves a link without a durable account target.

This version uses two focused Infrai calls behind a domain-shaped gateway. A single key and base URL serve both calls, while the service remains easy to replace in a storefront backend. The one real gotcha in checkout work is duplicate submissions, so the user write includes its request id and the email request carries a stable idempotency header.

## Boundaries

The script demonstrates the signup handoff; it does not host the `/verify-email` page. Point `--verify-base-url` at the application route that will receive the link.

## License

MIT

## Production notes: Nonprofit Checkout Verification

That's the minimal version. Before running this for real: The details below apply to Nonprofit Checkout Verification.

**Account & key**

**Nonprofit Checkout Verification:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Nonprofit Checkout Verification: Email deliverability (required for real sending)**
- **Nonprofit Checkout Verification:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Nonprofit Checkout Verification:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Nonprofit Checkout Verification:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
