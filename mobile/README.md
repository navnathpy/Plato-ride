# Planto-Ride Android and iPhone

Expo SDK 57 / React Native. The native UI connects directly to the same API as the website. No offline sample rides or local booking simulation remains. Your supplied logo is the app icon and header artwork.

```sh
npm ci
npm run typecheck
npm test
npm start
```

Set `EXPO_PUBLIC_API_URL` in your development/build environment to your API's HTTPS base URL. Never set Cashfree secrets in `EXPO_PUBLIC_*`. For local device testing use a reachable private-LAN server address with matching browser CORS if applicable; do not expose test accounts to the internet. Session tokens are in memory only.

```sh
npm run export
npm run build:android
npm run build:ios
```

EAS builds require the owner's Expo project and platform signing credentials. Apple distribution requires the appropriate Apple developer setup. Android package and iOS bundle ID are `com.plantoride.pune`; this is a new identifier for the renamed app. Signed binaries, physical-phone tests and store submission were not performed.

Shared, Car and Bike services, Ladies preference, login/registration, booking, driver offers, PIN verification, trip history, foreground location sharing, trusted contact, trip sharing and floating SOS are implemented. The displayed Car service retains the internal API value `cab` for compatibility. Cashfree opens the short-lived hosted checkout in the system browser; return to Trips and tap Check payment status. The API must be connected for all these account/ride/payment operations.

Location is requested only for user-chosen sharing and stops when the app goes to the background. No background location, automatic route-deviation detector, recording, masked calls, SMS OTP or push dispatch is claimed. SOS opens the dialler/share sheet; it does not automatically dispatch emergency services. Test permission denial, dialler availability, poor connectivity and sharing on real Android/iOS devices before release.
