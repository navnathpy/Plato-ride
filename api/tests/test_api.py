"""Integration tests use a real HTTP listener and temporary SQLite database."""
import concurrent.futures
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import server


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = server.Database(Path(self.tmp.name) / "test.sqlite3", seed=False)
        self.http = server.PlatoRideServer(("127.0.0.1", 0), self.db, rate_limit=10000, session_limit=10000)
        self.thread = threading.Thread(target=self.http.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()
        self.port = self.http.server_port

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, method, path, body=None, token=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        request_headers = {"Content-Type": "application/json"}
        if token:
            request_headers["Authorization"] = "Bearer " + token
        request_headers.update(headers or {})
        payload = raw if raw is not None else (json.dumps(body) if body is not None else None)
        try:
            connection.request(method, path, payload, request_headers)
            response = connection.getresponse()
            data = response.read()
            return response.status, json.loads(data) if data else None, dict(response.getheaders())
        finally:
            connection.close()

    def session(self, role="rider", name="Demo Person"):
        status, data, _ = self.request("POST", "/v1/demo/sessions", {"name": name, "role": role})
        self.assertEqual(status, 201, data)
        self.assertTrue(data["demo"])
        return data["token"], data["user"]

    def ride_body(self, **updates):
        result = {"origin_id": "hinjawadi", "destination_id": "shivajinagar", "departure_at": server.iso(server.utcnow() + timedelta(hours=2)),
                  "seats": 3, "fare_per_seat_inr": 90, "vehicle": {"make": "Demo", "model": "Car", "color": "Green", "plate": "DEMO 001"}}
        result.update(updates)
        return result

    def ride(self, token=None, **updates):
        if token is None:
            token, _ = self.session("driver")
        status, data, _ = self.request("POST", "/v1/rides", self.ride_body(**updates), token)
        self.assertEqual(status, 201, data)
        return data["ride"], token

    def book(self, token, ride_id, seats=1):
        return self.request("POST", "/v1/bookings", {"ride_id": ride_id, "seats": seats}, token)

    def test_health_locations_and_truthful_impact(self):
        status, data, headers = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertFalse(data["production_ready"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        _, data, _ = self.request("GET", "/v1/locations")
        self.assertEqual(len(data["locations"]), 12)
        _, data, _ = self.request("GET", "/v1/impact")
        self.assertEqual(data["commitment"]["profit_share"], 0.5)
        self.assertIsNone(data["verified_trees_planted"])
        self.assertIsNone(data["disbursed_inr"])

    def test_estimates_are_explicitly_illustrative(self):
        status, data, _ = self.request("GET", "/v1/estimates?origin_id=hinjawadi&destination_id=shivajinagar")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["estimate"]["fare_per_seat_inr"], 35)
        self.assertTrue(data["estimate"]["estimated"])
        self.assertIn("Not a road route", data["estimate"]["method"])
        self.assertEqual(self.request("GET", "/v1/estimates?origin_id=hinjawadi&destination_id=hinjawadi")[0], 400)

    def test_seed_is_idempotent_and_marked_demo(self):
        self.db.seed()
        self.db.seed()
        status, data, _ = self.request("GET", "/v1/rides")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["rides"]), 9)
        self.assertTrue(all(ride["demo"] and "Demo" in ride["driver"]["name"] for ride in data["rides"]))
        self.assertEqual(sum(ride["service"] == "cab" for ride in data["rides"]), 2)

    def test_session_tokens_are_random_hashed_and_revocable(self):
        token, user = self.session(name="Same Display Name")
        other, other_user = self.session(name="Same Display Name")
        self.assertNotEqual(token, other)
        self.assertNotEqual(user["id"], other_user["id"])
        with self.db.connection() as conn:
            hashes = [row[0] for row in conn.execute("SELECT token_hash FROM sessions")]
        self.assertNotIn(token, hashes)
        self.assertIn(hashlib.sha256(token.encode()).hexdigest(), hashes)
        self.assertEqual(self.request("GET", "/v1/me", token=token)[1]["user"]["id"], user["id"])
        self.assertEqual(self.request("DELETE", "/v1/demo/sessions/current", token=token)[0], 200)
        self.assertEqual(self.request("GET", "/v1/me", token=token)[0], 401)
        self.assertEqual(self.request("GET", "/v1/me", token=other)[0], 200)

    def test_expired_and_missing_sessions_are_rejected(self):
        token, _ = self.session()
        with self.db.connection(write=True) as conn:
            conn.execute("UPDATE sessions SET expires_at=?", (server.iso(server.utcnow() - timedelta(seconds=1)),))
        self.assertEqual(self.request("GET", "/v1/bookings", token=token)[0], 401)
        self.assertEqual(self.request("GET", "/v1/bookings")[0], 401)

    def test_matching_filters_direction_seats_and_pune_date(self):
        first, _ = self.ride(seats=3)
        self.ride(origin_id="shivajinagar", destination_id="hinjawadi", seats=3)
        self.ride(seats=1)
        status, data, _ = self.request("GET", "/v1/rides?origin_id=hinjawadi&destination_id=shivajinagar&seats=2")
        self.assertEqual(status, 200)
        self.assertEqual([ride["id"] for ride in data["rides"]], [first["id"]])
        self.assertEqual(self.request("GET", "/v1/rides?date=2026-02-30")[0], 400)
        self.assertEqual(self.request("GET", "/v1/rides?seats=1&seats=2")[0], 400)
        self.assertEqual(self.request("GET", "/v1/rides?origin_id=x%27%20OR%201=1--")[0], 400)

    def test_booking_uses_server_fare_and_enforces_ownership(self):
        ride, _ = self.ride()
        alice, _ = self.session(name="Alice Demo")
        bob, _ = self.session(name="Bob Demo")
        status, data, _ = self.book(alice, ride["id"], 2)
        self.assertEqual(status, 201)
        booking = data["booking"]
        self.assertEqual(booking["total_inr"], 180)
        self.assertEqual(booking["payment_status"], "not_collected_demo")
        self.assertEqual(booking["ride"]["seats_available"], 1)
        self.assertEqual(len(self.request("GET", "/v1/bookings", token=alice)[1]["bookings"]), 1)
        self.assertEqual(self.request("GET", "/v1/bookings", token=bob)[1]["bookings"], [])
        self.assertEqual(self.request("POST", f"/v1/bookings/{booking['id']}/cancel", {}, bob)[0], 404)
        self.assertEqual(self.request("POST", "/v1/bookings", {"ride_id": ride["id"], "seats": 1, "total_inr": 1}, bob)[0], 400)

    def test_duplicate_own_and_oversized_booking_fail_without_losing_seats(self):
        ride, driver = self.ride(seats=2)
        alice, _ = self.session()
        bob, _ = self.session()
        self.assertEqual(self.book(driver, ride["id"])[1]["error"]["code"], "own_ride")
        self.assertEqual(self.book(alice, ride["id"])[0], 201)
        self.assertEqual(self.book(alice, ride["id"])[1]["error"]["code"], "duplicate_booking")
        self.assertEqual(self.book(bob, ride["id"], 2)[1]["error"]["code"], "insufficient_seats")
        self.assertEqual(self.request("GET", "/v1/rides/" + ride["id"])[1]["ride"]["seats_available"], 1)

    def test_cancellation_is_idempotent_and_allows_rebooking(self):
        ride, _ = self.ride(seats=2)
        rider, _ = self.session()
        booking = self.book(rider, ride["id"], 2)[1]["booking"]
        for _ in range(2):
            status, data, _ = self.request("POST", f"/v1/bookings/{booking['id']}/cancel", {}, rider)
            self.assertEqual(status, 200)
            self.assertEqual(data["booking"]["ride"]["seats_available"], 2)
        self.assertEqual(len(self.request("GET", "/v1/history", token=rider)[1]["bookings"]), 1)
        self.assertEqual(self.book(rider, ride["id"], 2)[0], 201)

    def test_concurrent_bookings_never_oversell(self):
        ride, _ = self.ride(seats=3)
        tokens = [self.session()[0] for _ in range(10)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            outcomes = list(executor.map(lambda token: self.book(token, ride["id"]), tokens))
        self.assertEqual(sum(status == 201 for status, _, _ in outcomes), 3)
        self.assertEqual(sum(status == 409 for status, _, _ in outcomes), 7)
        with self.db.connection() as conn:
            self.assertEqual(conn.execute("SELECT seats_available FROM rides WHERE id=?", (ride["id"],)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT SUM(seats) FROM bookings WHERE ride_id=?", (ride["id"],)).fetchone()[0], 3)

    def test_concurrent_cancel_restores_seats_only_once(self):
        ride, _ = self.ride(seats=3)
        rider, _ = self.session()
        booking = self.book(rider, ride["id"], 2)[1]["booking"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(lambda _: self.request("POST", f"/v1/bookings/{booking['id']}/cancel", {}, rider), range(8)))
        self.assertTrue(all(outcome[0] == 200 for outcome in outcomes))
        self.assertEqual(self.request("GET", "/v1/rides/" + ride["id"])[1]["ride"]["seats_available"], 3)

    def create_cab(self):
        driver, _ = self.session("driver")
        body = self.ride_body(service="cab", seats=4, fare_total_inr=360)
        del body["fare_per_seat_inr"]
        status, data, _ = self.request("POST", "/v1/rides", body, driver)
        self.assertEqual(status, 201, data)
        return data["ride"], driver

    def test_cab_booking_is_exclusive_fixed_fare_and_restores_capacity(self):
        ride, _ = self.create_cab()
        alice, _ = self.session()
        bob, _ = self.session()
        status, data, _ = self.book(alice, ride["id"], 2)
        self.assertEqual(status, 201)
        booking = data["booking"]
        self.assertEqual(booking["seats"], 2)
        self.assertEqual(booking["seats_reserved"], 4)
        self.assertEqual(booking["total_inr"], 360)
        self.assertIsNone(booking["ride"]["fare_per_seat_inr"])
        self.assertEqual(booking["ride"]["seats_available"], 0)
        self.assertEqual(self.book(bob, ride["id"])[0], 409)
        self.assertEqual(self.request("GET", "/v1/rides?service=cab")[1]["rides"], [])
        self.assertEqual(self.request("POST", f"/v1/bookings/{booking['id']}/cancel", {}, alice)[0], 200)
        self.assertEqual(self.request("GET", "/v1/rides?service=cab")[1]["rides"][0]["seats_available"], 4)
        status, data, _ = self.book(bob, ride["id"], 4)
        self.assertEqual(status, 201)
        self.assertEqual(data["booking"]["total_inr"], 360)

    def test_concurrent_cab_bookings_have_one_winner(self):
        ride, _ = self.create_cab()
        tokens = [self.session()[0] for _ in range(6)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            outcomes = list(executor.map(lambda token: self.book(token, ride["id"]), tokens))
        self.assertEqual(sum(status == 201 for status, _, _ in outcomes), 1)
        self.assertEqual(sum(status == 409 for status, _, _ in outcomes), 5)

    def test_service_pricing_fields_are_not_interchangeable(self):
        driver, _ = self.session("driver")
        self.assertEqual(self.request("POST", "/v1/rides", self.ride_body(service="cab", fare_total_inr=360), driver)[0], 400)
        self.assertEqual(self.request("POST", "/v1/rides", self.ride_body(fare_total_inr=360), driver)[0], 400)
        status, data, _ = self.request("GET", "/v1/estimates?origin_id=hinjawadi&destination_id=shivajinagar&service=cab")
        self.assertEqual(status, 200)
        self.assertIsNone(data["estimate"]["fare_per_seat_inr"])
        self.assertGreaterEqual(data["estimate"]["fare_total_inr"], 120)
        self.assertEqual(self.request("GET", "/v1/rides?service=bus")[0], 400)

    def test_driver_lifecycle_propagates_completion_and_protects_owner(self):
        ride, driver = self.ride()
        other_driver, _ = self.session("driver")
        rider, _ = self.session()
        booking = self.book(rider, ride["id"])[1]["booking"]
        path = "/v1/rides/" + ride["id"]
        self.assertEqual(self.request("PATCH", path, {"status": "in_progress"}, other_driver)[0], 404)
        self.assertEqual(self.request("PATCH", path, {"status": "completed"}, driver)[0], 409)
        self.assertEqual(self.request("PATCH", path, {"status": "in_progress"}, driver)[0], 200)
        self.assertEqual(self.request("POST", f"/v1/bookings/{booking['id']}/cancel", {}, rider)[0], 409)
        self.assertEqual(self.request("PATCH", path, {"status": "completed"}, driver)[0], 200)
        self.assertEqual(self.request("GET", "/v1/history", token=rider)[1]["bookings"][0]["status"], "completed")
        self.assertEqual(self.request("PATCH", path, {"status": "cancelled"}, driver)[0], 409)
        self.assertEqual(self.book(other_driver, ride["id"])[0], 409)

    def test_driver_cancellation_updates_passengers_and_inventory(self):
        ride, driver = self.ride(seats=3)
        rider, _ = self.session()
        self.book(rider, ride["id"], 2)
        status, data, _ = self.request("PATCH", "/v1/rides/" + ride["id"], {"status": "cancelled"}, driver)
        self.assertEqual(status, 200)
        self.assertEqual(data["ride"]["seats_available"], 3)
        self.assertEqual(self.request("GET", "/v1/bookings", token=rider)[1]["bookings"][0]["status"], "cancelled")
        self.assertEqual(self.request("GET", "/v1/rides")[1]["rides"], [])

    def test_strict_validation_rejects_bad_roles_numbers_and_dates(self):
        self.assertEqual(self.request("POST", "/v1/demo/sessions", {"name": "Admin Demo", "role": "admin"})[0], 400)
        rider, _ = self.session()
        self.assertEqual(self.request("POST", "/v1/rides", self.ride_body(), rider)[0], 403)
        driver, _ = self.session("driver")
        invalid = [{"seats": True}, {"seats": 7}, {"seats": 0}, {"fare_per_seat_inr": 1}, {"fare_per_seat_inr": 90.5},
                   {"destination_id": "hinjawadi"}, {"origin_id": "unknown"}, {"departure_at": "2030-01-01T12:00:00"},
                   {"departure_at": server.iso(server.utcnow() - timedelta(hours=1))}, {"vehicle": {"plate": "only plate"}}]
        for update in invalid:
            with self.subTest(update=update):
                self.assertEqual(self.request("POST", "/v1/rides", self.ride_body(**update), driver)[0], 400)

    def test_parameterized_names_cannot_change_schema(self):
        token, user = self.session(name="Robert'); DROP TABLE users;--")
        self.assertEqual(self.request("GET", "/v1/me", token=token)[1]["user"]["name"], user["name"])
        self.assertEqual(self.session()[1]["role"], "rider")

    def test_invalid_json_duplicate_keys_and_payload_bounds(self):
        for raw in ('{"name":"Demo","name":"Other","role":"rider"}', '{"name": NaN}', '[1,2,3]', '{bad', '{"name":"' + 'x' * 16400 + '"}'):
            with self.subTest(raw=raw[:50]):
                self.assertIn(self.request("POST", "/v1/demo/sessions", raw=raw)[0], (400, 413))
        self.assertEqual(self.request("POST", "/v1/demo/sessions", {"name": "Demo", "role": "rider"}, headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/v1/demo/sessions", {"name": "Demo\ud800", "role": "rider"})[0], 400)
        self.assertEqual(self.request("POST", "/v1/demo/sessions", raw="{}", headers={"Content-Length": "²"})[0], 400)

    def test_cors_has_exact_local_allowlist(self):
        status, _, headers = self.request("GET", "/health", headers={"Origin": "http://localhost:8081"})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "http://localhost:8081")
        status, _, headers = self.request("GET", "/health", headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        status, _, headers = self.request("OPTIONS", "/v1/bookings", headers={"Origin": "http://localhost:8081", "Access-Control-Request-Headers": "authorization,content-type"})
        self.assertEqual(status, 204)
        self.assertIn("POST", headers["Access-Control-Allow-Methods"])
        self.assertEqual(self.request("OPTIONS", "/v1/bookings", headers={"Origin": "http://localhost:8081", "Access-Control-Request-Headers": "x-unapproved"})[0], 403)

    def test_limits_are_enforced(self):
        self.http.limiter = server.RateLimiter(limit=2, session_limit=1)
        self.assertEqual(self.request("GET", "/health")[0], 200)
        self.assertEqual(self.request("GET", "/health")[0], 200)
        status, data, headers = self.request("GET", "/health")
        self.assertEqual(status, 429)
        self.assertEqual(data["error"]["code"], "rate_limited")
        self.assertEqual(headers["Retry-After"], "60")

    def test_database_survives_reopening(self):
        ride, _ = self.ride()
        reopened = server.Database(self.db.path, seed=False)
        with reopened.connection() as conn:
            self.assertEqual(conn.execute("SELECT id FROM rides").fetchone()[0], ride["id"])


class StartupTests(unittest.TestCase):
    def test_network_and_production_refusals(self):
        for args in (("--host", "0.0.0.0"), ("--production",), ("--origin", "https://example.com"), ("--origin", "*")):
            with self.subTest(args=args), patch("sys.stderr"), self.assertRaises(SystemExit) as raised:
                server.main(args)
            self.assertEqual(raised.exception.code, 2)

    def test_origin_validation(self):
        self.assertTrue(server.validate_origin("http://localhost:8081"))
        self.assertTrue(server.validate_origin("http://127.0.0.1:5173"))
        self.assertTrue(server.validate_origin("http://192.168.1.20:8081", allow_lan=True))
        for value in ("http://localhost:8081/", "http://localhost.evil:8081", "http://user@localhost:8081", "null", "*", "http://8.8.8.8:8081", "http://localhost:99999"):
            self.assertFalse(server.validate_origin(value), value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
