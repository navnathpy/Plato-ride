# Plato-Ride verification

Verified on 26–27 September 2026 in the supplied Windows environment.

| Check | Result |
|---|---|
| Mobile TypeScript (`npm run typecheck`) | Passed |
| Expo SDK dependency compatibility (`expo install --check`, offline local SDK metadata) | Dependencies up to date |
| Mobile domain tests (`npm test`) | 4 tests passed |
| Android export | Hermes bundle generated successfully |
| iOS export | Hermes bundle generated successfully |
| React Native web export | Web bundle generated successfully |
| Browser demo and Google Maps URL tests | 8 tests passed |
| Browser JavaScript syntax | Passed |
| Development API integration tests | 24 tests passed |

The API suite covers real HTTP and SQLite operations, concurrent shared reservations, exclusive cab inventory, concurrent/idempotent cancellation, per-user booking isolation, server-calculated fares, session hashing/expiry/revocation, input validation, CORS and startup restrictions.

The mobile and browser domain tests cover per-seat versus whole-car pricing, capacity reservation/restoration, invalid input, self-booking restrictions, offer removal, ordered trip progress, and terminal trip states.

## Interface checks

- Website hero, navigation and responsive layout inspected in the in-app browser.
- Browser demo: searched two shared seats, reviewed ₹180 from two ₹90 seats, confirmed and cancelled a sample booking; searched four-passenger cab and verified one ₹319 whole-car fare.
- React Native web export inspected at a 390 × 844 phone viewport.
- Native UI in its web export: private-cab search, fare review, booking, simulated arrival/start/completion, and impact page checked. Completion appeared as one **demo** trip, without claiming real environmental impact.
- Revised branding inspected in the website and mobile UI.

## Limits

The mobile screens were exercised through React Native Web, not on physical Android/iOS hardware. Native exports validate bundling, not signing, native installation, device permissions or store acceptance. No signed APK/IPA was produced. No live driver dispatch, native location tracking, identity provider, payment, push notification, emergency/support system, or production service was tested. The API adapter is provided separately and is not connected to the offline screens.

The website demo stores local state independently from the native app and API. Real multi-user production app behavior requires those layers to be integrated and tested together. Accessibility includes labelled controls and keyboard paths, but no formal accessibility audit is claimed.

Google Maps: official Pune share/embed URL integrated into the browser and native WebView, with selected-route direction URLs. No GPS permission is requested. An optional domain-restricted Maps Embed API key enables the website’s route-specific iframe.
