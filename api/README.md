# Planto-Ride API

FastAPI, SQLite transactions and an empty initial database. Start with `pip install -r requirements.txt`, then `uvicorn app:app --host 127.0.0.1 --port 8788 --no-access-log`. Deployment settings are in `../HOSTING.md`. The previous demo server and its seed paths were removed; the new database is `data/planto.sqlite3`.

## Operator workflow

Riders and drivers register with name, Indian mobile number and a password of at least 12 characters. Phone identity is **not SMS-verified**; the operator must verify phone ownership and identity before approval. Passwords are PBKDF2-SHA256 hashes with unique salts and 600,000 iterations. Sessions expire after 12 hours and are revocable. The current release has no self-service password recovery or operational admin web console.

Run the CLI on the secured API host against its production database only after your verification process succeeds:

```sh
python app.py approve --phone +91XXXXXXXXXX --reference YOUR_VERIFICATION_RECORD
python app.py approve --phone +91XXXXXXXXXX --woman-verified --reference YOUR_VERIFICATION_RECORD
python app.py approve-vehicle --phone +91XXXXXXXXXX --plate "MH 12 AB 1234" --vehicle "Maruti Swift" --services shared,cab --reference YOUR_VEHICLE_CHECK_RECORD
python app.py suspend --phone +91XXXXXXXXXX --reference YOUR_CASE_RECORD
python app.py incidents
```

The number plate, make/model and service must match the approved vehicle when publishing a ride. Approve a bike only for its corresponding service. Rider/driver Ladies eligibility is separately recorded; self-declaring woman does not grant verified status. Suspending an account revokes sessions and removes driver offers from search. Operator actions are audited with your reference; do not put identity document numbers or sensitive evidence in the reference.

Read incidents through the restricted operator shell. The app truthfully says reports are saved, not that emergency services were alerted. Establish staffing/escalation and publish support contacts before launch. Account recovery, data deletion/retention, disputes, fleet operations and refunds need an operator process.

## Checks

`python -m pytest tests -q` uses temporary test databases and mocked Cashfree responses. It never creates real rides, calls emergency services or charges a card.

The API is an initial single-instance service, not a completed city-scale dispatch system. Use HTTPS, a persistent volume, rate-limiting proxy, backups, external monitoring and restricted operator access. No real merchant keys or identity records are bundled.
