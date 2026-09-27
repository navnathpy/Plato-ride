# Plato-Ride

**Shared rides. Private cabs. A greener Pune.**

Built for Navnath Sonawane, IT Engineer, Pune. This working development MVP includes a native Android/iPhone codebase, a responsive vision website, a browser demo with Google Maps, and a separate local API.

## Start here

| Part | Location | What is ready |
|---|---|---|
| Vision website | `website/` | Responsive product story, founder mission and profit pledge |
| Browser demo | `website/dist/app.html` | Shared/cab search, local bookings, cancellation, trip stages, seat offers and history |
| Native mobile app | `mobile/` | Android/iOS source with the same core flows and device-local persistence |
| Development API | `api/` | SQLite-backed multi-user demo sessions, ride offers, transactional reservations and trip lifecycle |
| Launch plan | `LAUNCH-PLAN.md` | Concrete service integrations and operating decisions still required |
| Hosting and maps | `HOSTING.md` | GitHub Pages and Google Maps configuration |
| Verification | `VERIFICATION.md` | Checks actually run and limits of those checks |

The browser demo, native offline demo, and API currently have **separate data**. The native API adapter is supplied but not connected to the screens. This is not a production Uber/Ola replacement, and it is not published in either app store.

## Try it locally

Website, with Python 3:

```sh
cd website
python -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Then visit http://127.0.0.1:4173/ and select **Try the demo**.

Mobile, with Node.js 24 LTS:

```sh
cd mobile
npm ci
npm start
```

Follow `mobile/README.md` for phone/emulator setup. You can also use `npm run web` to inspect the same React Native UI in a browser.

API, with Python 3.11+:

```sh
cd api
python server.py serve
```

The development API listens at http://127.0.0.1:8788. See `api/API.md` for its complete contract and `api/README.md` for limits. It intentionally refuses production mode.

## Product decisions

- Pune first; both shared rides and private cabs.
- Shared rides charge per passenger seat. Private cabs charge one whole-vehicle fare.
- Illustrative fares, drivers, availability, and manual trip simulations are clearly labelled.
- The environmental pledge is **50% of profits after expenses**, not 50% of fares or revenue.
- No fake funded-tree, survival, carbon-saving, live-driver or verified-safety claims.
- No real contact, identity, location or payment details are needed to try the demo.

> Protecting our Mother Earth is our responsibility. Let’s cherish and preserve her beauty together.

The source archive excludes dependencies, local databases, caches, credentials, and Git internals. Run `npm ci` to recreate mobile dependencies from the included lockfile. The native source is editable; cloud/store builds remain a separate launch step.
