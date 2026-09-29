# Planto-Ride website and booking client

Static HTML/CSS/JavaScript, hosted through GitHub Pages. Source is in `dist/`. The app uses the HTTP API and never seeds or simulates bookings.

Set `PLANTO_API_URL` in your shell, run `node website/scripts/configure-api.mjs` from the repository root, then serve `website/dist` on port 4173. GitHub Actions uses the repository variable of the same name. An unset API URL shows unavailable state and disables backend operations without fabricating data.

- `index.html`: vision, founder story and environmental commitment.
- `app.html`, `app.mjs`, `client.mjs`: accounts, rides, driver offers, safety and Cashfree checkout.
- `track.html`: revocable, expiring shared journey links; token in URL fragment.
- `pay.html`: scoped hosted payment flow for native clients; token in URL fragment.
- `privacy.html`: current data flows and operator policy prerequisites.
- `maps.mjs`: Google Maps overview / optional key-backed route preview.
- `assets/planto-ride-logo.png`: user-supplied logo, unchanged.

Sign-in tokens stay in memory. No credentials are written to browser storage. Only the public API base URL and optional restricted browser Maps key belong in static configuration. Cashfree secrets stay exclusively on the backend. Share links convey access to trip/vehicle/location information until revoked or expired; recipients should be trusted.

Run `node --test website/tests/*.test.mjs`. GitHub Actions checks the web client, API, mobile TypeScript and all platform exports before publishing.
