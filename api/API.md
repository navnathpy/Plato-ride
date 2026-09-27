# API contract · v1

Base URL: `http://127.0.0.1:8788`. Request/response bodies use UTF-8 JSON. Every amount is an integer in INR, not paise. Timestamps use ISO 8601 UTC (`...Z`); driver input may use another explicit timezone offset. The `date` search parameter is a calendar date in Pune (`UTC+05:30`).

All offers, sessions, bookings and estimates are development demos. Booking confirmation means a database reservation only. **No payment is collected and no real driver is dispatched.**

## Authentication

```http
POST /v1/demo/sessions
Content-Type: application/json

{"name":"Navnath Demo","role":"rider"}
```

Returns `201`:

```json
{
  "token": "<random opaque bearer token>",
  "expires_at": "2026-09-27T06:00:00Z",
  "user": {"id":"usr_<32 hex characters>","name":"Navnath Demo","role":"rider"},
  "demo": true
}
```

Use `Authorization: Bearer <token>` for authenticated operations. The token is returned only on session creation. Store it securely in an integrated app. A new session creates a new isolated demo user; repeating a name does not log into the previous user. Accepted roles are `rider` and `driver`, with no verification. Sessions expire after 12 hours.

`DELETE /v1/demo/sessions/current` revokes the current token and returns `{"signed_out":true}`. No body is required. `GET /v1/me` returns the current `user`.

## Endpoints

| Method | Path | Auth | Result |
|---|---|---|---|
| GET | `/health` | Public | Service state, demo mode, `production_ready:false` |
| POST | `/v1/demo/sessions` | Public | New isolated demo identity and token |
| DELETE | `/v1/demo/sessions/current` | Any session | Revoke this token |
| GET | `/v1/me` | Any session | Current user |
| GET | `/v1/locations` | Public | `{locations:[...],demo:true}` |
| GET | `/v1/estimates` | Public | `{estimate:{...}}` |
| GET | `/v1/rides` | Public | `{rides:[...],demo:true}` |
| GET | `/v1/rides/{ride_id}` | Public | `{ride:{...}}`, including terminal offers |
| POST | `/v1/rides` | Driver | Publish offer, returns `201 {ride:{...}}` |
| GET | `/v1/driver/rides` | Driver | Own latest 100 offers including terminal ones |
| PATCH | `/v1/rides/{ride_id}` | Owning driver | Transition offer status |
| POST | `/v1/bookings` | Any session | Reserve inventory, returns `201 {booking:{...}}` |
| GET | `/v1/bookings` | Any session | Own bookings, all statuses |
| POST | `/v1/bookings/{booking_id}/cancel` | Owning passenger | Cancel and restore inventory |
| GET | `/v1/history` | Any session | Own completed/cancelled bookings |
| GET | `/v1/impact` | Public | Founder commitment; verified metrics are `null` |

## Locations, matches and estimates

Location IDs: `hinjawadi`, `wakad`, `baner`, `aundh`, `shivajinagar`, `pune-station`, `viman-nagar`, `kharadi`, `magarpatta`, `hadapsar`, `swargate`, `kothrud`.

Each location has `{id,name,area,lat,lng}`. Coordinates identify approximate areas, not a rider's live position or a verified pickup point.

```http
GET /v1/rides?service=shared&origin_id=hinjawadi&destination_id=shivajinagar&seats=2
```

All search fields are optional. `service` is `shared` or `cab`; omit it to return both. Origin and destination filter exact IDs and are directional. `seats` is requested passengers, 1–6 (default 1). Only future, scheduled offers with enough inventory are returned, ordered by departure. Optional `date=YYYY-MM-DD` uses Pune time; `limit` is 1–100 (default 50).

```http
GET /v1/estimates?service=cab&origin_id=hinjawadi&destination_id=shivajinagar
```

Both route IDs are required. Service defaults to `shared`. Returns an explicitly illustrative formula: straight-line distance × 1.3; shared INR 6/km with INR 35 minimum per seat; cab INR 50 + INR 14/km with INR 120 minimum per vehicle. Rounded to INR 5. This is not a road route or live fare. A booking uses its offer's stored price, not this estimate.

## Publish shared ride

```http
POST /v1/rides
Authorization: Bearer <driver-token>
Content-Type: application/json

{
  "service":"shared",
  "origin_id":"hinjawadi",
  "destination_id":"shivajinagar",
  "departure_at":"2026-09-27T03:30:00Z",
  "seats":3,
  "fare_per_seat_inr":90,
  "vehicle":{"make":"Maruti","model":"Swift","color":"White","plate":"DEMO 001"}
}
```

Replace the sample departure with a date 5 minutes to 30 days in the future. `service` defaults to `shared`. Passenger capacity is 1–6. Shared fare is an integer INR 20–2500. Vehicle fields are required non-empty text, max 30 characters each. A driver may have at most 20 active offers.

Cab offer uses `"service":"cab"` and `"fare_total_inr":360`, **omitting** `fare_per_seat_inr`. Total cab fare is an integer INR 100–10000. The two price fields cannot be supplied together.

Ride object:

```json
{
  "id":"ride_<32 hex characters>",
  "service":"shared",
  "driver":{"id":"usr_<32 hex characters>","name":"Aditi · Demo"},
  "origin":{"id":"hinjawadi","name":"Hinjawadi Phase 1","area":"IT Park","lat":18.5913,"lng":73.7389},
  "destination":{"id":"shivajinagar","name":"Shivajinagar","area":"Central Pune","lat":18.5308,"lng":73.8475},
  "departure_at":"2026-09-27T03:30:00Z",
  "seats_total":3,
  "seats_available":3,
  "fare_per_seat_inr":90,
  "fare_total_inr":null,
  "currency":"INR",
  "status":"scheduled",
  "vehicle":{"make":"Maruti","model":"Swift","color":"White","plate":"DEMO 001"},
  "demo":true
}
```

For a cab, `fare_per_seat_inr` is `null`, `fare_total_inr` holds the whole-vehicle price, and capacity represents the maximum passenger count.

## Reserve and cancel

```http
POST /v1/bookings
Authorization: Bearer <passenger-token>
Content-Type: application/json

{"ride_id":"ride_<32 hex characters>","seats":2}
```

For a shared ride at INR 90 per seat, `total_inr` is 180 and `seats_reserved` is 2. For a cab at INR 360 per vehicle with capacity 4, `total_inr` is 360 and `seats_reserved` is 4; `seats` still records the requested 2 passengers. No other passenger can reserve that cab. All inventory checks, updates and booking insertion occur in a single immediate transaction.

Returns `201` with:

```json
{
  "booking":{
    "id":"booking_<32 hex characters>",
    "ride_id":"ride_<32 hex characters>",
    "seats":2,
    "seats_reserved":2,
    "total_inr":180,
    "currency":"INR",
    "status":"confirmed",
    "created_at":"2026-09-26T18:00:00Z",
    "updated_at":"2026-09-26T18:00:00Z",
    "ride":"<full ride object, not a string in actual responses>",
    "payment_status":"not_collected_demo",
    "demo":true
  }
}
```

The price is computed on the server. Client-supplied totals and unrecognized fields are rejected. Booking an owned offer or making a second active booking for the same offer returns `409`. A driver session may book another driver's offer as a passenger.

```http
POST /v1/bookings/booking_<32 hex characters>/cancel
Authorization: Bearer <passenger-token>
Content-Type: application/json

{}
```

Cancellation is allowed while the ride remains `scheduled`. The caller's cancelled booking is returned with `200`. Repeating cancellation is safe and does not restore inventory twice. An active/completed ride cannot be cancelled by a passenger. Another user's booking returns `404`. Rebooking a previously cancelled offer is allowed if it is still available.

`GET /v1/bookings` and `GET /v1/history` accept `limit=1..100` (default 50) and `offset=0..10000` (default 0); responses contain `bookings`, `limit`, `offset` and `demo`. History includes only completed/cancelled records.

## Driver transitions

```http
PATCH /v1/rides/ride_<32 hex characters>
Authorization: Bearer <owning-driver-token>
Content-Type: application/json

{"status":"in_progress"}
```

Allowed transitions:

```text
scheduled -> in_progress -> completed
scheduled -> cancelled
in_progress -> cancelled
```

Terminal rides cannot reopen. Completion marks confirmed bookings `completed`. Driver cancellation marks confirmed bookings `cancelled` and restores the vehicle's available capacity. Offer status, booking status and inventory changes are atomic. Only the owning driver can transition an offer. In this demo a driver can manually start early for testing; production pickup verification and dispatch must replace this shortcut.

## Errors and limits

Errors use:

```json
{"error":{"code":"insufficient_seats","message":"There are not enough seats remaining."}}
```

| HTTP | Common code | Meaning |
|---|---|---|
| 400 | `validation_error`, `invalid_json` | Invalid values, extra fields, malformed JSON or duplicate keys |
| 401 | `unauthorized` | Missing, expired or revoked session |
| 403 | `forbidden`, `origin_not_allowed` | Role restriction or disallowed browser origin |
| 404 | `not_found` | Missing endpoint/resource or resource belongs to another user |
| 409 | `insufficient_seats`, `duplicate_booking`, `own_ride`, `ride_unavailable`, `invalid_transition`, `limit_reached` | Reservation or lifecycle conflict |
| 413 | `body_too_large` | Body outside supported 1–16384 byte bounds |
| 415 | `unsupported_media_type` | JSON Content-Type required |
| 429 | `rate_limited` | Limit exceeded; `Retry-After: 60` |
| 503 | `database_unavailable` | Temporary database access failure |

Body-bearing endpoints require one valid Content-Length and `application/json`; chunked encoding is unsupported. Unknown/duplicate query fields are rejected. JSON booleans do not count as integers. Rate limits: 120 requests/minute/IP plus 10 new sessions/minute/IP. Data/credentials are not written to access logs. API responses use `Cache-Control: no-store`.

No real financial, carbon, temperature or tree-planting results are asserted by this service. `/v1/impact` describes the proposed 50% profit allocation and returns `null` for unverified outputs.
