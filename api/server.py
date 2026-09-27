"""Plato-Ride development API. Python 3.11+, standard library only.

Demo identities and seeded journeys are explicitly fictitious. Do not use this
server for real passengers, payments, or production identity verification.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import re
import secrets
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

UTC = timezone.utc
MAX_BODY = 16_384
DEFAULT_ORIGINS = ("http://localhost:8081", "http://127.0.0.1:8081", "http://localhost:5173", "http://127.0.0.1:5173")
LOCATIONS = [
    {"id": "hinjawadi", "name": "Hinjawadi Phase 1", "area": "IT Park", "lat": 18.5913, "lng": 73.7389},
    {"id": "wakad", "name": "Wakad", "area": "Wakad Chowk", "lat": 18.5987, "lng": 73.7641},
    {"id": "baner", "name": "Baner", "area": "Baner Road", "lat": 18.5590, "lng": 73.7868},
    {"id": "aundh", "name": "Aundh", "area": "Parihar Chowk", "lat": 18.5612, "lng": 73.8070},
    {"id": "shivajinagar", "name": "Shivajinagar", "area": "Central Pune", "lat": 18.5308, "lng": 73.8475},
    {"id": "pune-station", "name": "Pune Railway Station", "area": "Station Road", "lat": 18.5289, "lng": 73.8744},
    {"id": "viman-nagar", "name": "Viman Nagar", "area": "Viman Nagar Road", "lat": 18.5679, "lng": 73.9143},
    {"id": "kharadi", "name": "Kharadi", "area": "EON IT Park", "lat": 18.5515, "lng": 73.9348},
    {"id": "magarpatta", "name": "Magarpatta", "area": "Magarpatta City", "lat": 18.5157, "lng": 73.9270},
    {"id": "hadapsar", "name": "Hadapsar", "area": "Hadapsar Gadital", "lat": 18.5089, "lng": 73.9259},
    {"id": "swargate", "name": "Swargate", "area": "Swargate Junction", "lat": 18.5018, "lng": 73.8636},
    {"id": "kothrud", "name": "Kothrud", "area": "Karve Road", "lat": 18.5074, "lng": 73.8077},
]
LOCATION_MAP = {entry["id"]: entry for entry in LOCATIONS}


def utcnow():
    return datetime.now(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def identifier(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def require(condition, message, code="validation_error", status=400):
    if not condition:
        raise ApiError(status, code, message)


def fields(data, allowed, required=()):
    require(isinstance(data, dict), "Body must be a JSON object.")
    require(not (set(data) - set(allowed)), "Body contains unknown fields.")
    require(set(required) <= set(data), "A required field is missing.")


def string(value, label, minimum=1, maximum=80):
    require(isinstance(value, str), f"{label} must be text.")
    value = value.strip()
    require(minimum <= len(value) <= maximum, f"{label} must contain {minimum}–{maximum} characters.")
    require(not any(ord(char) < 32 or ord(char) == 127 for char in value), f"{label} contains control characters.")
    require(not any(0xD800 <= ord(char) <= 0xDFFF for char in value), f"{label} contains invalid Unicode.")
    return value


def integer(value, label, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum, f"{label} must be an integer from {minimum} to {maximum}.")
    return value


def route(origin_id, destination_id):
    require(isinstance(origin_id, str) and origin_id in LOCATION_MAP, "Unknown origin_id.")
    require(isinstance(destination_id, str) and destination_id in LOCATION_MAP, "Unknown destination_id.")
    require(origin_id != destination_id, "Origin and destination must differ.")
    return origin_id, destination_id


def query_fields(query, allowed):
    require(not (set(query) - set(allowed)), "Query contains unknown parameters.")
    require(all(len(value) == 1 for value in query.values()), "Query parameters may appear only once.")
    return {key: value[0] for key, value in query.items()}


def query_integer(value, label, minimum, maximum):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]{1,5}", value), f"{label} must be an integer.")
    return integer(int(value), label, minimum, maximum)


def fare_estimate(origin_id, destination_id, service="shared"):
    route(origin_id, destination_id)
    require(service in ("shared", "cab"), "service must be shared or cab.")
    start, end = LOCATION_MAP[origin_id], LOCATION_MAP[destination_id]
    lat1, lat2 = math.radians(start["lat"]), math.radians(end["lat"])
    dlat, dlng = lat2 - lat1, math.radians(end["lng"] - start["lng"])
    haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    distance = 6371 * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine)) * 1.3
    return {"origin_id": origin_id, "destination_id": destination_id, "currency": "INR", "service": service,
            "distance_km": round(distance, 1), "fare_per_seat_inr": max(35, int(round(distance * 6 / 5)) * 5) if service == "shared" else None,
            "fare_total_inr": max(120, int(round((50 + distance * 14) / 5)) * 5) if service == "cab" else None,
            "estimated": True, "demo": True,
            "method": "Illustrative straight-line distance × 1.3. Shared: INR 6/km, minimum INR 35 per seat. Cab: INR 50 + INR 14/km, minimum INR 120 per vehicle. Not a road route or live quote."}


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('rider','driver')), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rides (
 id TEXT PRIMARY KEY, driver_id TEXT NOT NULL REFERENCES users(id), origin_id TEXT NOT NULL, destination_id TEXT NOT NULL,
 departure_at TEXT NOT NULL, seats_total INTEGER NOT NULL CHECK(seats_total BETWEEN 1 AND 6),
 seats_available INTEGER NOT NULL CHECK(seats_available >= 0 AND seats_available <= seats_total),
 fare_per_seat_inr INTEGER CHECK(fare_per_seat_inr BETWEEN 20 AND 2500),
 fare_total_inr INTEGER CHECK(fare_total_inr BETWEEN 100 AND 10000),
 service TEXT NOT NULL CHECK(service IN ('shared','cab')),
 status TEXT NOT NULL CHECK(status IN ('scheduled','in_progress','completed','cancelled')),
 vehicle_json TEXT NOT NULL, created_at TEXT NOT NULL,
 CHECK((service='shared' AND fare_per_seat_inr IS NOT NULL AND fare_total_inr IS NULL) OR
       (service='cab' AND fare_per_seat_inr IS NULL AND fare_total_inr IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS bookings (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), ride_id TEXT NOT NULL REFERENCES rides(id),
 seats INTEGER NOT NULL CHECK(seats BETWEEN 1 AND 6), seats_reserved INTEGER NOT NULL CHECK(seats_reserved BETWEEN 1 AND 6),
 total_inr INTEGER NOT NULL CHECK(total_inr > 0),
 status TEXT NOT NULL CHECK(status IN ('confirmed','completed','cancelled')), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking ON bookings(user_id,ride_id) WHERE status='confirmed';
CREATE INDEX IF NOT EXISTS match_rides ON rides(status, origin_id, destination_id, departure_at);
CREATE INDEX IF NOT EXISTS own_bookings ON bookings(user_id,created_at);
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
"""


class Database:
    def __init__(self, path, seed=True):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
        if seed:
            self.seed()

    @contextmanager
    def connection(self, write=False):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.commit()
        except Exception:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()

    def seed(self):
        with self.connection(write=True) as conn:
            if conn.execute("SELECT value FROM metadata WHERE key='seeded'").fetchone():
                return
            now = utcnow()
            fixtures = [
                ("Aditi · Demo", "hinjawadi", "shivajinagar", 2, 3, 90, "Maruti", "Swift", "White"),
                ("Rahul · Demo", "hinjawadi", "shivajinagar", 3, 2, 85, "Hyundai", "i20", "Silver"),
                ("Priya · Demo", "wakad", "kharadi", 2.5, 3, 135, "Tata", "Nexon", "Blue"),
                ("Sameer · Demo", "baner", "magarpatta", 4, 2, 120, "Maruti", "Baleno", "Grey"),
                ("Meera · Demo", "kothrud", "viman-nagar", 5, 3, 110, "Honda", "City", "Silver"),
                ("Aarav · Demo", "kharadi", "hinjawadi", 6, 2, 145, "Tata", "Tiago", "Green"),
                ("Nisha · Demo", "shivajinagar", "hinjawadi", 8, 3, 90, "Maruti", "Swift", "Red"),
            ]
            for number, (name, origin, destination, hours, seats, fare, make, model, color) in enumerate(fixtures, 1):
                driver_id = identifier("usr")
                conn.execute("INSERT INTO users VALUES (?,?,?,?)", (driver_id, name, "driver", iso(now)))
                vehicle = {"make": make, "model": model, "color": color, "plate": f"DEMO {number:03d}"}
                conn.execute("INSERT INTO rides VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (identifier("ride"), driver_id, origin, destination, iso(now + timedelta(hours=hours)),
                              seats, seats, fare, None, "shared", "scheduled", json.dumps(vehicle), iso(now)))
            for number, (origin, destination, hours, fare) in enumerate((("hinjawadi", "shivajinagar", 1.5, 360), ("kharadi", "pune-station", 2, 280)), 1):
                driver_id = identifier("usr")
                conn.execute("INSERT INTO users VALUES (?,?,?,?)", (driver_id, f"Cab Partner {number} · Demo", "driver", iso(now)))
                vehicle = {"make": "Maruti", "model": "Dzire", "color": "White", "plate": f"DEMO CAB {number}"}
                conn.execute("INSERT INTO rides VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (identifier("ride"), driver_id, origin, destination, iso(now + timedelta(hours=hours)),
                              4, 4, None, fare, "cab", "scheduled", json.dumps(vehicle), iso(now)))
            conn.execute("INSERT INTO metadata VALUES ('seeded',?)", (iso(now),))


class RateLimiter:
    """Bounded, in-process limits for a small local demo (not distributed abuse defense)."""
    def __init__(self, limit=120, session_limit=10):
        self.limit, self.session_limit = limit, session_limit
        self.events = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, address, session=False):
        now = time.monotonic()
        key = (address, session)
        with self.lock:
            if len(self.events) > 4096:
                self.events = defaultdict(deque, {k: v for k, v in self.events.items() if v and v[-1] > now - 60})
                if key not in self.events and len(self.events) > 4096:
                    raise ApiError(429, "rate_limited", "Too many clients. Try again in one minute.")
            events = self.events[key]
            while events and events[0] <= now - 60:
                events.popleft()
            limit = self.session_limit if session else self.limit
            require(len(events) < limit, "Too many requests. Try again in one minute.", "rate_limited", 429)
            events.append(now)


def public_user(row):
    return {"id": row["id"], "name": row["name"], "role": row["role"]}


def ride_json(conn, row):
    driver = conn.execute("SELECT id,name FROM users WHERE id=?", (row["driver_id"],)).fetchone()
    return {"id": row["id"], "driver": dict(driver), "origin": LOCATION_MAP[row["origin_id"]],
            "destination": LOCATION_MAP[row["destination_id"]], "departure_at": row["departure_at"],
            "seats_total": row["seats_total"], "seats_available": row["seats_available"],
            "fare_per_seat_inr": row["fare_per_seat_inr"], "fare_total_inr": row["fare_total_inr"], "service": row["service"],
            "currency": "INR", "status": row["status"],
            "vehicle": json.loads(row["vehicle_json"]), "demo": True}


def booking_json(conn, row):
    ride = conn.execute("SELECT * FROM rides WHERE id=?", (row["ride_id"],)).fetchone()
    return {"id": row["id"], "ride_id": row["ride_id"], "seats": row["seats"], "seats_reserved": row["seats_reserved"], "total_inr": row["total_inr"],
            "currency": "INR", "status": row["status"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "ride": ride_json(conn, ride), "payment_status": "not_collected_demo", "demo": True}


class PlatoRideServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, database, origins=DEFAULT_ORIGINS, rate_limit=120, session_limit=10):
        self.database = database
        self.origins = set(origins)
        self.limiter = RateLimiter(rate_limit, session_limit)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "Plato-Ride-Development/1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, fmt, *args):
        # Do not log URLs, names, payloads, or authentication tokens.
        pass

    def json_response(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Vary", "Origin")
        origin = self.headers.get("Origin")
        if origin in self.server.origins:
            self.send_header("Access-Control-Allow-Origin", origin)
        if status == 429:
            self.send_header("Retry-After", "60")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def read_body(self):
        require(not self.headers.get("Transfer-Encoding"), "Transfer-Encoding is not supported.")
        lengths = self.headers.get_all("Content-Length", [])
        require(len(lengths) == 1 and re.fullmatch(r"[0-9]{1,6}", lengths[0]) is not None, "One valid Content-Length is required.")
        length = int(lengths[0])
        require(0 < length <= MAX_BODY, "Body must contain 1–16384 bytes.", "body_too_large", 413)
        require(self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() == "application/json",
                "Use Content-Type: application/json.", "unsupported_media_type", 415)
        try:
            def unique_keys(pairs):
                result = {}
                for key, value in pairs:
                    require(key not in result, "Duplicate JSON fields are not accepted.")
                    result[key] = value
                return result
            def reject_constant(value):
                raise ValueError(value)
            body = self.rfile.read(length)
            require(len(body) == length, "Incomplete request body.")
            data = json.loads(body.decode("utf-8"), object_pairs_hook=unique_keys, parse_constant=reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            raise ApiError(400, "invalid_json", "Request body is not valid JSON.")
        require(isinstance(data, dict), "Body must be a JSON object.")
        return data

    def user(self, conn):
        auth = self.headers.get("Authorization", "")
        require(re.fullmatch(r"Bearer [A-Za-z0-9_-]{40,100}", auth) is not None, "A valid demo session is required.", "unauthorized", 401)
        token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()
        row = conn.execute("SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?",
                           (token_hash, iso(utcnow()))).fetchone()
        require(row is not None, "Demo session is invalid or expired.", "unauthorized", 401)
        return row

    def dispatch(self):
        parsed = urlsplit(self.path)
        require(not parsed.scheme and not parsed.netloc and len(self.path) <= 2048, "Invalid request path.")
        path = parsed.path.rstrip("/") or "/"
        require(not parsed.fragment, "URL fragments are not supported.")
        try:
            query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=20, strict_parsing=True)
        except ValueError:
            raise ApiError(400, "validation_error", "Invalid query parameters.")
        origin = self.headers.get("Origin")
        require(origin is None or origin in self.server.origins, "This browser origin is not allowed.", "origin_not_allowed", 403)
        self.server.limiter.check(self.client_address[0])
        if self.command == "OPTIONS":
            require(not query, "OPTIONS does not accept query parameters.")
            requested_headers = {part.strip().lower() for part in self.headers.get("Access-Control-Request-Headers", "").split(",") if part.strip()}
            require(requested_headers <= {"authorization", "content-type"}, "Requested CORS headers are not allowed.", "origin_not_allowed", 403)
            self.send_response(204)
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        method = self.command
        if method == "GET" and path == "/health":
            query_fields(query, ())
            return self.json_response(200, {"status": "ok", "service": "platoride-api", "mode": "development-demo", "production_ready": False})
        if method == "GET" and path == "/v1/locations":
            query_fields(query, ())
            return self.json_response(200, {"locations": LOCATIONS, "demo": True})
        if method == "GET" and path == "/v1/estimates":
            params = query_fields(query, ("origin_id", "destination_id", "service"))
            return self.json_response(200, {"estimate": fare_estimate(params.get("origin_id"), params.get("destination_id"), params.get("service", "shared"))})
        if method == "GET" and path == "/v1/impact":
            query_fields(query, ())
            return self.json_response(200, {"commitment": {"profit_share": 0.5, "purpose": "Planting and irrigating trees in the city",
                                                         "basis": "Profits, not total booking value or revenue", "status": "Founder commitment; production accounting and verification pending"},
                                            "verified_trees_planted": None, "verified_co2_saved_kg": None, "disbursed_inr": None, "demo": True})
        if method == "POST" and path == "/v1/demo/sessions":
            query_fields(query, ())
            self.server.limiter.check(self.client_address[0], session=True)
            data = self.read_body()
            fields(data, ("name", "role"), ("name", "role"))
            name = string(data["name"], "name", 2, 60)
            require(data["role"] in ("rider", "driver"), "role must be rider or driver.")
            now, token, user_id = utcnow(), secrets.token_urlsafe(32), identifier("usr")
            expires = iso(now + timedelta(hours=12))
            with self.server.database.connection(write=True) as conn:
                conn.execute("DELETE FROM sessions WHERE expires_at<=?", (iso(now),))
                conn.execute("INSERT INTO users VALUES (?,?,?,?)", (user_id, name, data["role"], iso(now)))
                conn.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, expires))
            return self.json_response(201, {"token": token, "expires_at": expires, "user": {"id": user_id, "name": name, "role": data["role"]}, "demo": True})
        write = method in ("POST", "PATCH", "DELETE")
        with self.server.database.connection(write=write) as conn:
            status, payload = self.route_database(conn, method, path, query)
        self.json_response(status, payload)

    def route_database(self, conn, method, path, query):
        if method == "GET" and path == "/v1/rides":
            params = query_fields(query, ("origin_id", "destination_id", "seats", "date", "limit", "service"))
            conditions, values = ["status='scheduled'", "departure_at> ?"], [iso(utcnow())]
            if "service" in params:
                require(params["service"] in ("shared", "cab"), "service must be shared or cab.")
                conditions.append("service=?")
                values.append(params["service"])
            for key in ("origin_id", "destination_id"):
                if key in params:
                    require(params[key] in LOCATION_MAP, f"Unknown {key}.")
                    conditions.append(f"{key}=?")  # Column names come only from the fixed tuple above.
                    values.append(params[key])
            if "origin_id" in params and "destination_id" in params:
                route(params["origin_id"], params["destination_id"])
            seats = query_integer(params.get("seats", "1"), "seats", 1, 6)
            limit = query_integer(params.get("limit", "50"), "limit", 1, 100)
            conditions.append("seats_available>=?")
            values.append(seats)
            if "date" in params:
                try:
                    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", params["date"]), "date must use YYYY-MM-DD.")
                    # Pune calendar date; convert the inclusive/exclusive range to UTC.
                    start = datetime.strptime(params["date"], "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                except ValueError:
                    raise ApiError(400, "validation_error", "date must be a valid YYYY-MM-DD date.")
                conditions.extend(("departure_at>=?", "departure_at<?"))
                values.extend((iso(start), iso(start + timedelta(days=1))))
            values.append(limit)
            rows = conn.execute("SELECT * FROM rides WHERE " + " AND ".join(conditions) + " ORDER BY departure_at,id LIMIT ?", values).fetchall()
            return 200, {"rides": [ride_json(conn, row) for row in rows], "demo": True}
        if method == "GET" and re.fullmatch(r"/v1/rides/ride_[a-f0-9]{32}", path):
            query_fields(query, ())
            row = conn.execute("SELECT * FROM rides WHERE id=?", (path.rsplit("/", 1)[1],)).fetchone()
            require(row is not None, "Ride not found.", "not_found", 404)
            return 200, {"ride": ride_json(conn, row)}
        user = self.user(conn)
        if method == "GET" and path == "/v1/me":
            query_fields(query, ())
            return 200, {"user": public_user(user), "demo": True}
        if method == "DELETE" and path == "/v1/demo/sessions/current":
            query_fields(query, ())
            digest = hashlib.sha256(self.headers["Authorization"][7:].encode()).hexdigest()
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))
            return 200, {"signed_out": True}
        if method == "GET" and path == "/v1/driver/rides":
            query_fields(query, ())
            require(user["role"] == "driver", "A driver demo session is required.", "forbidden", 403)
            rows = conn.execute("SELECT * FROM rides WHERE driver_id=? ORDER BY departure_at DESC LIMIT 100", (user["id"],)).fetchall()
            return 200, {"rides": [ride_json(conn, row) for row in rows], "demo": True}
        if method == "POST" and path == "/v1/rides":
            query_fields(query, ())
            require(user["role"] == "driver", "A driver demo session is required.", "forbidden", 403)
            data = self.read_body()
            required = ("origin_id", "destination_id", "departure_at", "seats", "vehicle")
            fields(data, (*required, "service", "fare_per_seat_inr", "fare_total_inr"), required)
            service = data.get("service", "shared")
            require(service in ("shared", "cab"), "service must be shared or cab.")
            origin, destination = route(data["origin_id"], data["destination_id"])
            departure_text = string(data["departure_at"], "departure_at", 20, 40)
            try:
                departure = datetime.fromisoformat(departure_text.replace("Z", "+00:00"))
                require(departure.tzinfo is not None, "departure_at must include a timezone.")
            except ValueError:
                raise ApiError(400, "validation_error", "departure_at must be an ISO 8601 timestamp with timezone.")
            require(utcnow() + timedelta(minutes=5) <= departure <= utcnow() + timedelta(days=30), "Departure must be 5 minutes to 30 days in the future.")
            seats = integer(data["seats"], "seats", 1, 6)
            if service == "shared":
                require("fare_total_inr" not in data, "Shared rides use fare_per_seat_inr only.")
                per_seat_fare, total_fare = integer(data.get("fare_per_seat_inr"), "fare_per_seat_inr", 20, 2500), None
            else:
                require("fare_per_seat_inr" not in data, "Cabs use fare_total_inr only.")
                per_seat_fare, total_fare = None, integer(data.get("fare_total_inr"), "fare_total_inr", 100, 10000)
            fields(data["vehicle"], ("make", "model", "color", "plate"), ("make", "model", "color", "plate"))
            vehicle = {key: string(value, "vehicle." + key, 1, 30) for key, value in data["vehicle"].items()}
            active = conn.execute("SELECT COUNT(*) FROM rides WHERE driver_id=? AND status IN ('scheduled','in_progress')", (user["id"],)).fetchone()[0]
            require(active < 20, "Limit of 20 active demo rides reached.", "limit_reached", 409)
            ride_id = identifier("ride")
            conn.execute("INSERT INTO rides VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (ride_id, user["id"], origin, destination,
                         iso(departure), seats, seats, per_seat_fare, total_fare, service, "scheduled", json.dumps(vehicle), iso(utcnow())))
            return 201, {"ride": ride_json(conn, conn.execute("SELECT * FROM rides WHERE id=?", (ride_id,)).fetchone())}
        if method == "PATCH" and re.fullmatch(r"/v1/rides/ride_[a-f0-9]{32}", path):
            query_fields(query, ())
            ride_id = path.rsplit("/", 1)[1]
            row = conn.execute("SELECT * FROM rides WHERE id=? AND driver_id=?", (ride_id, user["id"])).fetchone()
            require(row is not None, "Your ride was not found.", "not_found", 404)
            data = self.read_body()
            fields(data, ("status",), ("status",))
            target = data["status"]
            require(target in ("in_progress", "completed", "cancelled"), "Unknown ride status.")
            transitions = {"scheduled": ("in_progress", "cancelled"), "in_progress": ("completed", "cancelled"), "completed": (), "cancelled": ()}
            require(target in transitions[row["status"]], "This ride status transition is not allowed.", "invalid_transition", 409)
            conn.execute("UPDATE rides SET status=? WHERE id=?", (target, ride_id))
            if target in ("completed", "cancelled"):
                conn.execute("UPDATE bookings SET status=?,updated_at=? WHERE ride_id=? AND status='confirmed'", (target, iso(utcnow()), ride_id))
            if target == "cancelled":
                conn.execute("UPDATE rides SET seats_available=seats_total WHERE id=?", (ride_id,))
            return 200, {"ride": ride_json(conn, conn.execute("SELECT * FROM rides WHERE id=?", (ride_id,)).fetchone())}
        if method == "POST" and path == "/v1/bookings":
            query_fields(query, ())
            data = self.read_body()
            fields(data, ("ride_id", "seats"), ("ride_id", "seats"))
            ride_id = string(data["ride_id"], "ride_id", 1, 50)
            seats = integer(data["seats"], "seats", 1, 6)
            row = conn.execute("SELECT * FROM rides WHERE id=?", (ride_id,)).fetchone()
            require(row is not None, "Ride not found.", "not_found", 404)
            require(row["driver_id"] != user["id"], "You cannot book your own ride.", "own_ride", 409)
            require(row["status"] == "scheduled" and row["departure_at"] > iso(utcnow()), "This ride is no longer open for booking.", "ride_unavailable", 409)
            require(conn.execute("SELECT id FROM bookings WHERE user_id=? AND ride_id=? AND status='confirmed'", (user["id"], ride_id)).fetchone() is None,
                    "You already have a booking for this ride.", "duplicate_booking", 409)
            require(seats <= row["seats_total"], "Passenger count exceeds vehicle capacity.", "insufficient_seats", 409)
            reserved = row["seats_total"] if row["service"] == "cab" else seats
            total = row["fare_total_inr"] if row["service"] == "cab" else seats * row["fare_per_seat_inr"]
            updated = conn.execute("UPDATE rides SET seats_available=seats_available-? WHERE id=? AND seats_available>=?", (reserved, ride_id, reserved))
            require(updated.rowcount == 1, "There are not enough seats remaining.", "insufficient_seats", 409)
            booking_id, now = identifier("booking"), iso(utcnow())
            conn.execute("INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?,?)", (booking_id, user["id"], ride_id, seats, reserved, total, "confirmed", now, now))
            return 201, {"booking": booking_json(conn, conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone())}
        if method == "GET" and path in ("/v1/bookings", "/v1/history"):
            params = query_fields(query, ("limit", "offset"))
            limit = query_integer(params.get("limit", "50"), "limit", 1, 100)
            offset = query_integer(params.get("offset", "0"), "offset", 0, 10000)
            extra = " AND status IN ('completed','cancelled')" if path == "/v1/history" else ""
            rows = conn.execute("SELECT * FROM bookings WHERE user_id=?" + extra + " ORDER BY created_at DESC,id LIMIT ? OFFSET ?", (user["id"], limit, offset)).fetchall()
            return 200, {"bookings": [booking_json(conn, row) for row in rows], "limit": limit, "offset": offset, "demo": True}
        if method == "POST" and re.fullmatch(r"/v1/bookings/booking_[a-f0-9]{32}/cancel", path):
            query_fields(query, ())
            data = self.read_body()
            fields(data, ())
            booking_id = path.split("/")[3]
            row = conn.execute("SELECT * FROM bookings WHERE id=? AND user_id=?", (booking_id, user["id"])).fetchone()
            require(row is not None, "Your booking was not found.", "not_found", 404)
            if row["status"] == "cancelled":
                return 200, {"booking": booking_json(conn, row)}
            ride = conn.execute("SELECT * FROM rides WHERE id=?", (row["ride_id"],)).fetchone()
            require(row["status"] == "confirmed" and ride["status"] == "scheduled", "Only a booking on a scheduled ride may be cancelled.", "invalid_transition", 409)
            conn.execute("UPDATE bookings SET status='cancelled',updated_at=? WHERE id=?", (iso(utcnow()), booking_id))
            conn.execute("UPDATE rides SET seats_available=seats_available+? WHERE id=?", (row["seats_reserved"], row["ride_id"]))
            return 200, {"booking": booking_json(conn, conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone())}
        raise ApiError(404, "not_found", "Endpoint not found.")

    def handle_request(self):
        try:
            self.dispatch()
        except ApiError as error:
            self.json_response(error.status, {"error": {"code": error.code, "message": error.message}})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True
        except sqlite3.OperationalError:
            self.json_response(503, {"error": {"code": "database_unavailable", "message": "Database is temporarily unavailable. Please retry."}})
        except Exception:
            self.json_response(500, {"error": {"code": "internal_error", "message": "The development server could not process the request."}})

    do_GET = handle_request
    do_POST = handle_request
    do_PATCH = handle_request
    do_DELETE = handle_request
    do_OPTIONS = handle_request


def is_loopback(host):
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_origin(origin, allow_lan=False):
    parsed = urlsplit(origin)
    try:
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        return False
    if port is not None and not 1 <= port <= 65535:
        return False
    if is_loopback(parsed.hostname):
        return True
    if allow_lan:
        try:
            address = ipaddress.ip_address(parsed.hostname)
            return address.is_private and not address.is_unspecified and not address.is_multicast
        except ValueError:
            return False
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plato-Ride local development API — demo accounts only")
    parser.add_argument("command", nargs="?", choices=("serve",), default="serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--db", default=str(Path(__file__).parent / "data" / "platoride.sqlite3"))
    parser.add_argument("--allow-demo-lan", action="store_true", help="Explicitly expose demo identities to a trusted private LAN for device testing")
    parser.add_argument("--origin", action="append", help="Allowed exact local browser origin, e.g. http://localhost:8081; repeatable")
    parser.add_argument("--no-seed", action="store_true")
    parser.add_argument("--production", action="store_true", help="Refuse startup: production identity and operational adapters are not implemented")
    args = parser.parse_args(argv)
    if args.production:
        parser.error("Production mode is unavailable. Implement and review real identity, transport, safety, payment and operational adapters first.")
    if not is_loopback(args.host) and not args.allow_demo_lan:
        parser.error("Non-loopback binding requires --allow-demo-lan. This API provides unverified demo identities only.")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be 1–65535.")
    origins = args.origin or DEFAULT_ORIGINS
    if any(not validate_origin(origin, args.allow_demo_lan) for origin in origins):
        parser.error("Origins must be exact HTTP loopback URLs without paths; --allow-demo-lan also permits explicit private IP origins.")
    database = Database(args.db, seed=not args.no_seed)
    server = PlatoRideServer((args.host, args.port), database, origins)
    print(f"Plato-Ride DEMO API: http://{args.host}:{args.port} — fictitious rides, unverified identities, no payments", flush=True)
    print(f"Database: {database.path}", flush=True)
    if args.allow_demo_lan:
        print("DEMO LAN enabled. Use only on a trusted private network with test data; never expose this server to the internet.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
