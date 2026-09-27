# Plato-Ride mobile

A working native React Native / Expo app for Android and iOS, with shared rides and private cabs. This is a **development MVP with an offline demo**, not a launched ride-hailing service. No real drivers, payments, OTP, GPS or emergency support are connected. Google Maps is embedded as a Pune overview, with directions links for the selected route.

## Run the app

Install Node.js 24 LTS (the version used to verify this project). From this folder:

```sh
npm ci
npm start
```

Open the project in an Expo Go version compatible with Expo SDK 57. Scan the development QR code using Expo Go on Android or the Camera app on iPhone, with the computer and phone on the same network. If Expo Go on a device does not support this SDK, create a compatible development/native build instead. See [Expo’s device-development guide](https://docs.expo.dev/get-started/start-developing/).

Other commands:

```sh
npm run web
npm run android
npm run ios
```

The Android command requires a configured Android emulator or device. The iOS simulator command requires macOS and Xcode. This Windows environment exported both native bundles; it did not run iOS Simulator or produce a signed APK/IPA.

## What works

- Select pickup/destination from 12 Pune areas, swap a route, and choose 1–4 passengers.
- Search shared seats or private cabs, with Economy, Electric and Comfort sample categories.
- Shared prices multiply by seat count; cab fares are fixed for the whole vehicle, which becomes exclusively reserved.
- Review a sample fare and book; simulate arrival, start and completion; cancel before starting; view history.
- Offer shared seats, remove your own offers, and block booking your own offer.
- Retain bookings/profile/offers using AsyncStorage. One active local booking is allowed at a time.
- Explore an embedded Google Maps overview and open the selected driving route in Google Maps. Internet is required; the embedded overview does not show live drivers.
- Read the 50%-of-profits environmental pledge, with no fabricated impact results.
- Edit the display name and reset sample data.

Sample departures are 15–45 minutes after initialization. If samples expire, use **You → Reset demo data**. The profile name defaults to Navnath for this founder demo. No account is created.

## Check and export

```sh
npm run typecheck
npm test
npm run export
```

The export creates JavaScript/Hermes bundles for Android/iOS plus a browser build. **An export is not an installable app or an app-store submission.** Expo SDK dependency versions were checked using `expo install --check`; Android, iOS and web export succeeded.

## Native build profiles

`eas.json` contains:

- `preview`: Android APK; iOS Simulator build.
- `device-preview`: Android APK; physical iPhone internal-distribution build.
- `production`: store builds with version increments.

After choosing your own unique app identifiers and signing into your Expo account:

```sh
npx eas-cli@latest login
npx eas-cli@latest build:configure
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest build --platform ios --profile preview
```

For a physical iPhone, use `--profile device-preview` and configure the required signing/provisioning. `com.platoride.pune` is a provisional identifier; availability and ownership are not verified. Store distribution requires your developer accounts and signing setup. See [Expo’s build prerequisites](https://docs.expo.dev/build/setup/). No paid account, signing certificate, store submission or cloud build was created during this task.

## API boundary

The UI uses `src/storage.ts` and `src/domain.ts` for the local demo. `src/api.ts` supplies an optional typed client for the sibling Python API. It supports sessions, ride search, booking, cancellation, driver offers and status updates, with timeouts and structured errors. It is **not wired into the screens**. Setting `EXPO_PUBLIC_API_URL` alone does not enable server mode or synchronize data.

For an integrated pilot, replace the local repository with the API adapter, map server ride/booking types, and implement driver-controlled real trip events. Keep demo simulation controls out of a real rider app. Demo session tokens in the optional client stay in memory; production authentication must use secure, revocable sessions and device-appropriate storage.

No secret belongs in `EXPO_PUBLIC_*`; these values are embedded in client bundles. The optional API is deliberately local-development-only.

## Structure

- `App.tsx`: rider, offer, trips, impact and profile flows
- `src/domain.ts`: deterministic booking/inventory/state rules
- `src/storage.ts`: validated device-local persistence
- `src/ui.tsx`, `src/styles.ts`: reusable native interface primitives
- `src/api.ts`: optional HTTP integration adapter
- `src/domain.test.ts`: meaningful fare, inventory and trip-state tests
- `app.json`, `eas.json`: platform metadata and native build profiles
