# Plato-Ride website & browser demo

Responsive vision website and an interactive local demo for shared rides and private cabs. Plain HTML, CSS, and JavaScript; no package installation or build step.

## Run locally

From this folder, with Python 3 installed:

```sh
python -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Open http://127.0.0.1:4173/ for the vision website or http://127.0.0.1:4173/app.html for the demo. Use an HTTP server rather than double-clicking app.html, because JavaScript modules need an HTTP origin.

## Demo behavior

- Shared rides show per-seat prices; private cabs use one whole-car price and reserve the whole vehicle.
- Sample routes include Baner–Hinjewadi, Wakad–Hinjewadi, Kothrud–Shivajinagar, Viman Nagar–Magarpatta, Kalyani Nagar–Viman Nagar, and Hinjewadi–Baner.
- Initial sample journeys depart tomorrow in the browser’s local time. After a day has passed, Profile → Reset demo data creates fresh samples.
- Search exact pickup/destination, date, service type, and passenger count.
- Review/confirm a sample booking, simulate trip stages, cancel before a trip starts, and retain history.
- Offer and remove local shared rides. You cannot book your own offer.
- Local browser storage persists the demo on this device only. No authentication, real dispatch, payment, multi-user sync, API connection, or emergency feature is claimed. Google Maps supplies an embedded Pune overview and links to the selected driving route.
- All environmental figures are pledges. There are no fabricated planted-tree or carbon counters.

## Check

```sh
node --test tests/core.test.mjs
node --check dist/app.mjs
```

The tests cover shared fares, exclusive cab inventory, cancellations, invalid input, trip state transitions, and own-offer restrictions.

## Files

- `dist/index.html`: product vision
- `dist/app.html`, `dist/app.mjs`, `dist/core.mjs`: browser demo and domain logic
- `dist/styles.css`: responsive styling, keyboard focus, reduced-motion support
- `dist/assets/plato-ride-hero.webp`: original generated concept image, not an operating-location photo

Google Fonts supplies DM Sans and Manrope, with local system-font fallbacks. The demo loads Google Maps, but no payment SDK, analytics, or booking service.

GitHub Pages publishes this website through the included Actions workflow. See `../HOSTING.md` for setup and optional restricted Maps Embed API key configuration.
