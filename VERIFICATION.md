# Verification — Planto-Ride upgrade

Verified locally on 27–29 September 2026:

- API: 33 tests passed in temporary databases. Coverage includes empty inventory, password/session behavior, driver and vehicle approval, three vehicle types, Ladies eligibility/no fallback, concurrent last-seat reservation, PIN ownership/lockout, role authorization, location freshness, sharing revocation/end-of-trip, last-shared-cancellation closure, payment amount ownership, durable order history, lost-response retry, active checkout reuse, terminal-order rotation, pending-payment blocking, concurrent checkout protection, historical settlement, forged/mismatched webhook rejection and incident ownership.
- Website: 6 tests passed for fare/capacity rules, missing-backend fail-closed behavior, authorization headers, API failures and Google Maps URLs. JavaScript syntax checked.
- Mobile: TypeScript and 3 tests passed. Android, iOS and web exports completed successfully with the new logo and location module.

Cashfree integration tests mock provider responses and sign local test webhooks. No real merchant credentials or live charges were used. API host activation, Cashfree domain/webhook acceptance, signed phone builds, physical-device testing, staffed safety operations and production load/security assessment remain unverified.

Dependency audit reports moderate transitive findings in Expo's Xcode/UUID build tooling. The suggested automated fix downgrades Expo across major versions and was not applied. Review compatible upstream fixes before signing/releasing applications. No high/critical npm finding was reported in this check.

Browser validation: account registration reached the API; a separately approved local test rider searched a locally published test offer, reserved it, received a private trip PIN and cancelled it successfully. These isolated fixtures exist only in a scratch database outside the repository. Bike capacity, Ladies selection, empty/unavailable states, tab navigation and SOS panel were checked. No emergency calls or messages were sent.

The final service choices are Shared, Car and Bike. Auto was removed from the website, mobile app and new API offers. The supplied investor deck informed the planned Pune corridors, Green Fund care cycle and workplace roadmap. Example financial/impact figures were not published as results, and the deck itself is excluded from the repository.
