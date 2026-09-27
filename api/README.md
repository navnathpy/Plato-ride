# Plato-Ride development API

A runnable Python 3.11+ service for the Pune prototype. It supports shared rides and exclusive cab bookings, uses SQLite for persistence, and requires no third-party packages.

This is **development software with unverified demo identities**. Seeded drivers, vehicles, availability and prices are fictitious. It does not dispatch real cabs, take payments, verify phone numbers or provide emergency assistance. The mobile app runs its own offline demo by default; this API is an optional integration foundation.

## Run

From this directory:

```powershell
python server.py serve
```

If Python is not on PATH on the supplied Windows development machine:

```powershell
& 'C:\Users\navna\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' server.py serve
```

Open `http://127.0.0.1:8788/health`. The default database is `data/platoride.sqlite3`; that folder is ignored by Git. Startup inserts seven shared rides and two cab offers once. Departures are relative to the first startup. Existing seed departures are not silently changed on later starts. To get a fresh set, use a new development database path:

```powershell
python server.py serve --db data/fresh-demo.sqlite3
```

To start without seed data:

```powershell
python server.py serve --no-seed --db data/empty-demo.sqlite3
```

Stop with Ctrl+C. There is no deployment script because this server deliberately refuses `--production`.

## Test

```powershell
python -m unittest discover -s tests -v
```

The suite uses temporary databases and real HTTP requests, including concurrent attempts to book the same seats or cab. It checks booking isolation, token expiry/revocation, immutable server-computed prices, cancellation idempotency, driver status transitions, validation, request limits, CORS, startup refusals and persistence.

## What works

- Browse 12 Pune pickup/drop areas and filter demo offers by service, exact origin, exact destination, Pune date and passenger count.
- Create separate random rider or driver demo sessions, valid for 12 hours. Only SHA-256 token digests are persisted. A display name never restores or grants an earlier account.
- Publish a shared ride or cab offer from a driver session; see only that driver's offers under `/v1/driver/rides`.
- Reserve shared seats using the driver-set per-seat price. Reserve an entire cab at its driver-set total price, regardless of passenger count up to vehicle capacity.
- Cancel a scheduled booking and restore its reserved inventory exactly once. An immediate SQLite transaction serializes competing reservations and cancellations.
- Start, complete or cancel an owned ride. Completion/cancellation updates the affected passenger bookings in the same transaction.
- View the authenticated user's bookings and completed/cancelled history. One user cannot cancel another user's booking.
- Read the founder's commitment to devote **50% of profits** to planting and irrigating trees. Impact counters are `null` until verified real records exist.

Shared route matching currently requires the same origin/destination IDs. It does not calculate walking pickup points, intermediate-route compatibility, live road distance, detours, traffic or arrival predictions. Cabs use published demo offers; dispatch to a live available driver is a production adapter still to implement.

## Network and browser setup

The default listener is `127.0.0.1:8788`. CORS allows only the exact origins `http://localhost:8081`, `http://127.0.0.1:8081`, `http://localhost:5173`, and `http://127.0.0.1:5173`. Requests with any other browser `Origin` are rejected. CORS does not replace authentication.

Override the local allowlist with repeatable `--origin` options:

```powershell
python server.py serve --origin http://localhost:8081 --origin http://localhost:3000
```

For deliberate testing from a physical phone on a trusted private Wi-Fi network:

```powershell
python server.py serve --host 0.0.0.0 --allow-demo-lan
```

Use the computer's private LAN IPv4 address and port `8788` in the client. A phone's `localhost` is the phone itself. For Android Emulator, the host alias is typically `10.0.2.2`; iOS Simulator on a Mac can use the Mac's loopback listener. Native development builds may require cleartext-HTTP development configuration; production must use HTTPS. Do not put this demo server on the public internet, forward its port or send it real identity documents/payment details. The LAN switch explicitly opts into exposing self-selected, unverified identities to that network.

When a browser runs on a private LAN address, pass that exact origin and `--allow-demo-lan`. Wildcards, public domains, credentials in origins and URL paths are rejected. Native HTTP clients generally do not send an `Origin` header.

Requests are limited per client IP to 120/minute; creating demo sessions is separately limited to 10/minute. Limits live in memory and reset on restart. They are useful for development, not a distributed abuse-control system.

## Production integration work

Before real journeys, replace the demo boundaries and review the full operating model:

1. Identity provider with real phone verification, account recovery, session rotation/revocation, driver onboarding and appropriate verification. Do not promote this self-selected `role` field to a production privilege.
2. Production application server behind TLS, shared database with migrations/backups, distributed rate limiting, secrets management, monitoring, retention controls and recovery procedures. The standard-library HTTP server is for local development.
3. Licensed maps, geocoding, route matching, live location permission/retention, reliable dispatch, driver acceptance, trip events and notifications. The demo estimate is a formula, not a map route.
4. Payment provider and signed webhook verification, idempotent payment/booking coordination, receipts, refunds, reconciliation and driver settlements. No card or bank information belongs in this API.
5. Support tooling, incident handling, consent/privacy controls and an operational safety program. Research applicable requirements for Pune/Maharashtra with qualified advisers before launch; this package is not a compliance assessment.
6. Financial accounting that determines actual profits, records the 50% allocation, and publishes verifiable planting, irrigation, survival and disbursement records. Booking value is neither revenue nor profit; speculative CO₂ and tree counts must not be displayed as verified impact.

Use [API.md](API.md) for the request and response contract. The API intentionally reports `production_ready: false` and marks demo data in its responses.
