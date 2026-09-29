# Connect Planto-Ride hosting

The owner chose to connect backend hosting separately. GitHub Pages already hosts the static site at https://navnathpy.github.io/Plato-ride/. It cannot run the API or database.

## 1. Deploy the API

Use a host supporting a persistent volume and Python 3.12 or Docker. Build `api/Dockerfile`, mount persistent storage at `/data`, and expose internal port 8788 through the host's HTTPS proxy. Run **one API worker/instance** for this SQLite deployment. Do not put the database on ephemeral storage or a network filesystem. Back up the database and test restoration. Horizontal scaling requires moving transactions and rate limits to shared infrastructure.

Set environment variables privately on that host:

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_PATH` | `/data/planto.sqlite3` |
| `WEB_URL` | `https://navnathpy.github.io/Plato-ride` |
| `PUBLIC_API_URL` | Your API's HTTPS base URL, without trailing slash |
| `ALLOWED_ORIGINS` | `https://navnathpy.github.io` (origin only, no path) |
| `CASHFREE_MODE` | `sandbox` during acceptance testing; `production` after go-live checks |
| `CASHFREE_CLIENT_ID` | Cashfree Payment Gateway App ID for the selected mode |
| `CASHFREE_CLIENT_SECRET` | Corresponding secret, stored only in the host secret store |

The supplied `.env.example` contains placeholders, never actual credentials. Dashboard email/password are not payment API credentials. No account password was saved in the repository. Restrict operator shell access and secret access. Disable request-body/Authorization logging at the proxy. Enforce a 16 KB request-body limit before the application and per-client rate limits at the proxy; the API also limits requests, but by default sees the proxy as one client. Only enable trusted forwarded client IP handling for your specific proxy addresses, never arbitrary internet headers. Configure request timeouts, TLS, monitoring and backups before opening public signups.

Verify `/health` over HTTPS. The initial database is empty. Do not copy a test database into production.

## 2. Connect the website and phones

In GitHub repository Settings → Secrets and variables → Actions → **Variables**, add public variable `PLANTO_API_URL` with the API HTTPS base URL. Run the existing **Test and deploy Planto-Ride** workflow. It writes only the public API URL to `website/dist/config.js`; never add Cashfree secrets to this file or GitHub Pages.

For mobile builds set `EXPO_PUBLIC_API_URL` to the same HTTPS API URL. Native apps access this API directly; authentication tokens remain in memory and users sign in after restarting. Rebuild after changing the URL. See `mobile/README.md` for EAS build commands.

## 3. Configure Cashfree

The owner reports that their merchant account is activated. API keys, domain approval and actual payment processing were **not verified in this task**.

1. Obtain Payment Gateway App ID and Secret Key from the merchant dashboard. Enter them only in your backend secret store, matching sandbox/production mode.
2. Whitelist the website domain as required by Cashfree.
3. Configure payment webhooks to `https://YOUR_API/v1/payments/webhook`. Preserve the raw request body and `x-webhook-signature` / `x-webhook-timestamp` headers.
4. Complete a sandbox journey, pay after completion and check successful, failed, cancelled and delayed payments. Verify duplicate webhook delivery does not double-process a payment. A client checkout return alone never marks payment paid.
5. Switch the backend mode and both keys together for live use. Run an owner-approved live transaction and refund acceptance test before launch. No live payment was performed here.

The backend stores a durable order history for each booking. It reuses active checkout sessions and retries an uncertain creation with the same order ID, payload and idempotency key. An expired or terminated order is replaced only after checking previous orders and payment attempts; unresolved bank payments block replacement. A per-booking lease prevents concurrent checkout creation. Status reconciliation verifies order ID, currency and amount. Signed webhooks can settle both current and historical orders and update an idempotent paid flag. No payout or automatic refund operation is implemented. Publish your support/refund policy and handle refunds through Cashfree's merchant process.

## 4. Approve real accounts and vehicles

Follow `api/README.md`. Verify identity, phone ownership, driver licence, vehicle registration, insurance and service eligibility through your secured operations process; verify Ladies eligibility where requested. Keep supporting records outside the repository. Approval is a deliberate operator action, not a checkbox a user can grant themselves.

## Google Maps

The default map embeds Pune without an API key. Selected-route links open Google directions. Optionally set Actions variable `GOOGLE_MAPS_EMBED_API_KEY` to a Maps Embed API browser key restricted to your website referrer and that API. It is client-visible by design; do not use a server secret. Recent driver coordinates appear through separate authenticated trip data and revocable sharing links, not as simulated moving cars on the overview.

Official integration references: [Cashfree web checkout](https://www.cashfree.com/docs/payments/online/web/redirect), [webhook verification](https://www.cashfree.com/docs/payments/online/webhooks/signature-verification), [Google Maps Embed](https://developers.google.com/maps/documentation/embed/embedding-map).
