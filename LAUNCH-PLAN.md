# Plato-Ride: from working demo to operating pilot

The current implementation is suitable for product demonstrations and engineering development. A real ride-hailing service needs further integration and operational work. The following items are not represented as already complete.

## 1. Agree the Pune pilot model

Support both shared rides and private cabs, as requested. Decide which vehicle categories and pickup areas the first pilot will cover, how shared rides are matched, the platform commission, cancellation rules, driver payouts, and how support operates. The present fares are illustrative; there is no approved commercial tariff or commission model.

## 2. Connect identity and operations

Choose a phone-verification identity provider and establish driver onboarding, document/vehicle checks, account recovery, and support roles. Replace self-selected demo roles. Add a driver app/workspace for accepting dispatches and an authenticated operational console. The current offer flow and API are a foundation, not a verified driver network.

## 3. Connect live journeys

Choose a map/routing provider, obtain keys, and add geocoding, route matching, pickup selection, driver availability, dispatch/acceptance, foreground/background location permissions, trip events, and push notifications. Validate behavior on real Android phones and iPhones, including offline recovery and reconnection. Replace rider-operated demo progress buttons with server-authorized trip events.

## 4. Connect payments and receipts

Choose a provider supporting the required local payment methods and onboard the business. Implement server-owned fares, payment order creation, verified webhooks, idempotent booking/payment coordination, receipts, refunds, reconciliation and driver settlement. No payment credentials should be put in mobile source or browser code.

## 5. Deploy the integrated service

Connect both apps to a production API/database with migrations, backups, access controls, request limits, logs, alerts, and recovery procedures. Replace the Python standard-library development server. Add secure data retention/deletion and customer-support workflows. The static website can remain separate from the booking infrastructure.

## 6. Make the environmental commitment measurable

Define a documented profit calculation with your accountant, a reporting interval, and the process for allocating 50% of profits. Select planting/irrigation partners. Record funds allocated and disbursed separately from tree planting, care, and survival outcomes. Publish figures only when supported by actual records. Booking totals are not revenue or profit.

## 7. Prepare a reviewed pilot and store builds

Obtain qualified local advice on the requirements applicable to the chosen transport/business model. Prepare privacy/consent text, incident response and operational safety procedures based on the actual service. This package does not make a legal compliance claim.

Provide an Expo project/account for cloud builds, unique bundle identifiers, app icons and store assets, Android signing, and Apple signing/provisioning. Conduct device QA and a controlled pilot before submitting to Google Play or Apple’s App Store. No signed APK, IPA, store listing, customer payment, or operating licence is included in this delivery.

See [Expo’s official build setup](https://docs.expo.dev/build/setup/) for native build and signing prerequisites.
