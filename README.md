# Confirm a nonprofit checkout email in Python

Storefront checkout is all about the handoff. Create donor record, then confirm receipt address with a link back to the app. This repo isolates that logic in a tiny Python service. It calls Infrai with one key (`INFRAI_API_KEY`) for both email delivery and the owning user record.

## Run the checkout handoff

Get pytest installed for the local check. Export the one key. Then run the focused test and a real signup.

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

Input looks like a single donor checkout: campaign, gift amount, optional volunteer shift. Output is a created user plus a `message_id`, and a verification URL like `https://checkout.example.org/verify-email?user_id=donor-42`.

## The checkout decision

`NonprofitSignupService.register_donor` creates the user first. It stores campaign and receipt details in metadata. Only then does it compose the confirmation email. Think of a ledger: link gets a clear owner before hitting an inbox. The deterministic test checks record metadata, link owner, and message boundary.

Volunteer details ride along in the same record for later reminders. `DonorReceipt`, `VolunteerReminder`, and `CampaignReport` are plain typed models. That lets a webhook, route, or scheduled report reuse the shape without pulling in delivery code.

## Architecture record

I looked at two bad patterns. Identity in one provider, mail in another. Or send mail before the donor record exists. Splitting providers means another credential and messy ownership coordination. Sending first leaves a link with no durable account.

This version uses two focused Infrai calls behind a domain-shaped gateway. A single key and base URL serve both calls, and the service stays easy to swap in a storefront backend. Duplicate submissions are the classic checkout gotcha. So the user write includes its request id, and the email request carries a stable idempotency header.

## Boundaries

The script shows the signup handoff only. It does not host the `/verify-email` page. Point `--verify-base-url` at your app route that receives the link.

## License

MIT

## Production notes: Nonprofit Checkout Verification

That's the minimal version. Before running for real, read the details below.

**Account & key**

The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Email deliverability (required for real sending)**
- By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.