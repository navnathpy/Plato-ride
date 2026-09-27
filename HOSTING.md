# GitHub Pages hosting

Repository: https://github.com/navnathpy/Plato-ride

This repository includes a GitHub Actions workflow at `.github/workflows/pages.yml`. It checks the website, transactional API and mobile source, then deploys `website/dist` to GitHub Pages. The native app source is saved in GitHub; Pages does not execute the Python API or distribute signed phone applications.

## Enable Pages once

1. Open the repository’s **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Open **Actions → Test and deploy Plato-Ride → Run workflow**. If an earlier run failed because Pages was not enabled, rerun it after changing the source.
4. Wait for all checks and the deployment to succeed. Use the URL reported by the deployment. The expected project URL is `https://navnathpy.github.io/Plato-ride/`; it should only be treated as live after a successful deployment.

The workflow publishes only the static website and local browser demo. Changes pushed to `main` trigger new checks and deployment.

## Google Maps

The default map is Google’s official share/embed map of Pune. It requires internet access and does not use the rider’s GPS. A selected-route link opens Google Maps directions with the chosen pickup and destination. Native Android/iPhone screens use an embedded WebView city map and the same route link. There are no fake moving cars or live driver positions.

To replace the website city overview with a route-specific embedded map, enable **Maps Embed API** in your Google Cloud project and add a browser key as the repository Actions variable `GOOGLE_MAPS_EMBED_API_KEY`. Restrict that key to your website’s HTTP referrers (for example `https://navnathpy.github.io/*`) and Maps Embed API. The key is client-visible by design; do not supply a server/service-account secret. The workflow generates `website/dist/maps-config.js` during deployment. Locally, run `website/scripts/configure-maps.mjs` with `MAPS_EMBED_KEY` in the environment.

Live driver positions, automatic route matching, in-app travel-time/fare calculation, native Google Maps SDK configuration, and production dispatch remain future integrations. The Python API is still local development software.

Official references: [Google Maps embedding](https://developers.google.com/maps/documentation/embed/embedding-map), [Maps direction URLs](https://developers.google.com/maps/documentation/urls/get-started), [GitHub Pages setup](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).
