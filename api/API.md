# API contract

Interactive schema is available at `/docs` and `/openapi.json` on your backend. Use `Authorization: Bearer TOKEN` for private endpoints. Session tokens are returned by registration/login and held in memory by the clients. Error text is in `detail`. All prices are integer INR and server-owned after offer publication.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Connection and payment configuration state; no secrets |
| POST | `/v1/auth/register` | Name, +91 phone, password, rider/driver role, optional gender; starts unapproved |
| POST | `/v1/auth/login` | Phone and password; 12-hour session |
| DELETE | `/v1/auth/session` | Revoke current session |
| GET / PATCH | `/v1/me` | Own profile / trusted contact |
| GET | `/v1/rides` | Public future offers filtered by origin, destination, service, ladies, seats and Pune-local date |
| POST | `/v1/rides` | Approved driver + approved vehicle publishes an offer |
| GET | `/v1/driver/rides` | Own offers |
| POST | `/v1/rides/{id}/close` | Close own offer with no active bookings |
| POST / DELETE | `/v1/rides/{id}/location` | Owner shares/stops foreground location during active bookings |
| POST | `/v1/bookings` | Atomic reservation; one active journey per rider |
| GET | `/v1/bookings` | Own passenger bookings and bookings on own driver offers |
| POST | `/v1/bookings/{id}/cancel` | Cancel before trip start and release reserved seats |
| POST | `/v1/bookings/{id}/start` | Driver-only six-digit rider PIN, limited incorrect attempts |
| POST | `/v1/bookings/{id}/complete` | Driver-only completion after start |
| POST / DELETE | `/v1/bookings/{id}/share` | Create/revoke 2-hour opaque journey link |
| GET | `/v1/shared/{token}` | Minimal shared trip information, no rider phone or PIN |
| POST | `/v1/incidents` | Store account's report, optional own booking ID |
| POST | `/v1/bookings/{id}/payment` | Create/retrieve Cashfree payment session after completion |
| POST | `/v1/bookings/{id}/payment-status` | Check Cashfree order server-side |
| POST | `/v1/bookings/{id}/checkout-link` | 10-minute hosted payment link for native app |
| POST | `/v1/checkout/{token}` | Exchange scoped link for payment session |
| POST | `/v1/checkout/{token}/status` | Scoped payment reconciliation |
| POST | `/v1/payments/webhook` | Raw-body HMAC verification and idempotent settlement |

Services: shared (max 6), car (API value `cab`, max 4), bike (1 passenger). Shared totals multiply seat price; exclusive services reserve the entire vehicle and charge its fare once. Exact area matching is case-insensitive. Only eligible women riders with an all-women party can reserve Ladies offers; only verified women drivers can publish them. There is no fallback that silently changes this selection.

API calls never interpret Cashfree checkout browser results as proof of payment. Successful payment requires trusted server reconciliation or a valid matching signed webhook. Safety reporting never initiates an emergency call or SMS automatically.
