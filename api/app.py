"""Planto-Ride API: real accounts and inventory; never seeds passengers or rides."""
from __future__ import annotations
import argparse, base64, hashlib, hmac, json, os, re, secrets, sqlite3, time, uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

DB = os.getenv('DATABASE_PATH', str(Path(__file__).parent/'data'/'planto.sqlite3'))
WEB = os.getenv('WEB_URL', 'http://127.0.0.1:4173').rstrip('/')
PUBLIC = os.getenv('PUBLIC_API_URL', 'http://127.0.0.1:8788').rstrip('/')
MODE = os.getenv('CASHFREE_MODE', 'sandbox')
SERVICES = {'shared':6, 'cab':4, 'bike':1}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,phone TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,gender TEXT NOT NULL,approved INTEGER NOT NULL DEFAULT 0,woman_verified INTEGER NOT NULL DEFAULT 0,contact TEXT NOT NULL DEFAULT '',created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rides(id TEXT PRIMARY KEY,driver_id TEXT REFERENCES users(id),origin TEXT NOT NULL,destination TEXT NOT NULL,departure TEXT NOT NULL,service TEXT NOT NULL,ladies INTEGER NOT NULL,capacity INTEGER NOT NULL,available INTEGER NOT NULL,price INTEGER NOT NULL,vehicle TEXT NOT NULL,plate TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',lat REAL,lng REAL,located REAL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS bookings(id TEXT PRIMARY KEY,rider_id TEXT REFERENCES users(id),ride_id TEXT REFERENCES rides(id),seats INTEGER NOT NULL,reserved INTEGER NOT NULL,total INTEGER NOT NULL,status TEXT NOT NULL,pin TEXT NOT NULL,pin_attempts INTEGER NOT NULL DEFAULT 0,pin_blocked_until REAL NOT NULL DEFAULT 0,paid INTEGER NOT NULL DEFAULT 0,order_id TEXT UNIQUE,created REAL NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS active_reservation ON bookings(rider_id,ride_id) WHERE status IN ('confirmed','in_progress');
CREATE TABLE IF NOT EXISTS payment_orders(order_id TEXT PRIMARY KEY,booking_id TEXT NOT NULL REFERENCES bookings(id),amount INTEGER NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL,request_json TEXT,created REAL NOT NULL,updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS payment_booking ON payment_orders(booking_id,created);
CREATE TABLE IF NOT EXISTS payment_locks(booking_id TEXT PRIMARY KEY REFERENCES bookings(id),token TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS shares(hash TEXT PRIMARY KEY,booking_id TEXT REFERENCES bookings(id),expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS checkout_links(hash TEXT PRIMARY KEY,booking_id TEXT REFERENCES bookings(id),expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),booking_id TEXT,kind TEXT NOT NULL,detail TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,action TEXT NOT NULL,target TEXT NOT NULL,reference TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vehicles(driver_id TEXT REFERENCES users(id),plate TEXT NOT NULL,vehicle TEXT NOT NULL,services TEXT NOT NULL,PRIMARY KEY(driver_id,plate));
CREATE TABLE IF NOT EXISTS limits(key TEXT NOT NULL,created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS limit_lookup ON limits(key,created);
CREATE INDEX IF NOT EXISTS ride_search ON rides(service,ladies,status,departure);
'''

@contextmanager
def db(write=False):
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB,timeout=15,isolation_level=None); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        if write:c.execute('BEGIN IMMEDIATE')
        yield c
        if write:c.commit()
    except Exception:
        if write:c.rollback()
        raise
    finally:c.close()

def init():
    with db() as c:
        c.execute('PRAGMA journal_mode=WAL'); c.executescript(SCHEMA)
        # Preserve order IDs issued before the order-history table was introduced.
        c.execute("INSERT OR IGNORE INTO payment_orders SELECT order_id,id,total,'INR','UNKNOWN',NULL,created,created FROM bookings WHERE order_id IS NOT NULL")

def fail(ok,message,status=400):
    if not ok:raise HTTPException(status,message)
def uid(prefix):return prefix+'_'+uuid.uuid4().hex
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
def user_json(u):return {k:u[k] for k in ('id','name','phone','role','gender','approved','woman_verified','contact')}
def throttle(key,limit,window=60):
    now=time.time()
    with db(True) as c:
        c.execute('DELETE FROM limits WHERE created<?',(now-3600,))
        count=c.execute('SELECT count(*) FROM limits WHERE key=? AND created>?',(key,now-window)).fetchone()[0]
        fail(count<limit,'Too many attempts. Please try again later.',429)
        c.execute('INSERT INTO limits VALUES(?,?)',(key,now))

app=FastAPI(title='Planto-Ride',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('ALLOWED_ORIGINS',WEB).split(','),allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'],allow_credentials=False)

@app.on_event('startup')
def startup():
    fail(MODE in ('sandbox','production'),'CASHFREE_MODE must be sandbox or production')
    if os.getenv('ENVIRONMENT')=='production':
        fail(WEB.startswith('https://') and PUBLIC.startswith('https://'),'Production requires HTTPS public URLs')
    init()

@app.middleware('http')
async def guard(request:Request,call_next):
    # The deployment proxy must also cap request bodies and rate-limit at the edge.
    raw=await request.body()
    if len(raw)>16384:return JSONResponse({'detail':'Request too large'},413)
    try:
        throttle('ip:'+(request.client.host if request.client else 'unknown'),240)
        response=await call_next(request)
    except HTTPException as e:return JSONResponse({'detail':e.detail},e.status_code)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response

def current(authorization:str=Header(default='')):
    fail(authorization.startswith('Bearer '),'Sign in to continue.',401)
    with db() as c:
        row=c.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.hash=? AND s.expires>?',(digest(authorization[7:]),time.time())).fetchone()
    fail(row is not None,'Your session expired. Sign in again.',401)
    return dict(row)

class Input(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Credentials(Input):
    phone:str=Field(pattern=r'^\+91[6-9][0-9]{9}$')
    password:str=Field(min_length=12,max_length=128)
class Register(Credentials):
    name:str=Field(min_length=2,max_length=80)
    role:Literal['rider','driver']='rider'
    gender:Literal['woman','man','other','undisclosed']='undisclosed'
class Profile(Input):contact:str=Field(default='',pattern=r'^(\+91[6-9][0-9]{9})?$')
class Offer(Input):
    origin:str=Field(min_length=2,max_length=100)
    destination:str=Field(min_length=2,max_length=100)
    departure:datetime
    service:Literal['shared','cab','bike']
    ladies:bool=False
    capacity:int=Field(ge=1,le=6,strict=True)
    price:int=Field(ge=10,le=20000,strict=True)
    vehicle:str=Field(min_length=2,max_length=80)
    plate:str=Field(pattern=r'^[A-Z0-9 -]{6,16}$')
class Reservation(Input):ride_id:str; seats:int=Field(ge=1,le=6,strict=True); women_party:bool=False
class Pin(Input):pin:str=Field(pattern=r'^\d{6}$')
class Location(Input):lat:float=Field(ge=-90,le=90);lng:float=Field(ge=-180,le=180)
class Incident(Input):booking_id:str|None=None;kind:Literal['safety','sos','service']='safety';detail:str=Field(min_length=5,max_length=2000)

def session(c,u):
    token=secrets.token_urlsafe(32)
    c.execute('INSERT INTO sessions VALUES(?,?,?)',(digest(token),u['id'],time.time()+12*3600))
    return {'token':token,'user':user_json(u)}

@app.get('/health')
def health():return {'status':'ok','brand':'Planto-Ride','payments_configured':bool(os.getenv('CASHFREE_CLIENT_ID') and os.getenv('CASHFREE_CLIENT_SECRET')),'payment_mode':MODE,'support_monitored':False}
@app.post('/v1/auth/register',status_code=201)
def register(data:Register,request:Request):
    throttle('register:'+request.client.host,10,3600)
    with db(True) as c:
        fail(not c.execute('SELECT id FROM users WHERE phone=?',(data.phone,)).fetchone(),'Unable to register this number. Sign in or contact the operator.',409)
        user_id=uid('user')
        c.execute('INSERT INTO users(id,name,phone,password,role,gender,created) VALUES(?,?,?,?,?,?,?)',(user_id,data.name,data.phone,password_hash(data.password),data.role,data.gender,time.time()))
        return session(c,c.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone())
@app.post('/v1/auth/login')
def login(data:Credentials,request:Request):
    throttle('login:'+data.phone,10,3600);throttle('login-ip:'+request.client.host,30,3600)
    with db(True) as c:
        u=c.execute('SELECT * FROM users WHERE phone=?',(data.phone,)).fetchone()
        encoded=password_hash(data.password,u['password'].split(':')[0] if u else '0'*32)
        fail(u is not None and hmac.compare_digest(encoded,u['password']),'Phone or password is incorrect.',401)
        return session(c,u)
@app.delete('/v1/auth/session')
def logout(u=Depends(current),authorization:str=Header()):
    with db(True) as c:c.execute('DELETE FROM sessions WHERE hash=?',(digest(authorization[7:]),))
    return {'signed_out':True}
@app.get('/v1/me')
def me(u=Depends(current)):return {'user':user_json(u)}
@app.patch('/v1/me')
def profile(data:Profile,u=Depends(current)):
    with db(True) as c:c.execute('UPDATE users SET contact=? WHERE id=?',(data.contact,u['id']))
    return {'saved':True}

def ride_json(c,r):
    d=c.execute('SELECT name,approved,woman_verified FROM users WHERE id=?',(r['driver_id'],)).fetchone()
    return {**{k:r[k] for k in ('id','driver_id','origin','destination','departure','service','ladies','capacity','available','price','vehicle','plate','status')},'driver':d['name'],'driver_approved':bool(d['approved']),'woman_driver_verified':bool(d['woman_verified'])}
def booking_json(c,b,u):
    r=c.execute('SELECT * FROM rides WHERE id=?',(b['ride_id'],)).fetchone()
    result={**{k:b[k] for k in ('id','seats','total','status','paid')},'ride':ride_json(c,r),'rider_name':c.execute('SELECT name FROM users WHERE id=?',(b['rider_id'],)).fetchone()[0]}
    if b['rider_id']==u['id'] and b['status']=='confirmed':result['pin']=b['pin']
    result['location']=location_json(r) if b['status'] in ('confirmed','in_progress') else None
    return result
def location_json(r):
    if not r['located'] or time.time()-r['located']>120:return None
    return {'lat':r['lat'],'lng':r['lng'],'updated_at':r['located']}
def owned_booking(c,id,u,driver=False):
    b=c.execute('SELECT * FROM bookings WHERE id=?',(id,)).fetchone();fail(b is not None,'Booking not found.',404)
    r=c.execute('SELECT * FROM rides WHERE id=?',(b['ride_id'],)).fetchone()
    fail((r['driver_id'] if driver else b['rider_id'])==u['id'],'Booking not found.',404)
    return b,r

@app.get('/v1/rides')
def rides(origin:str='',destination:str='',service:Literal['shared','cab','bike']='shared',ladies:bool=False,seats:int=1,date:str=''):
    fail(1<=seats<=SERVICES[service],'Too many passengers for this vehicle.')
    fail(len(origin)<=100 and len(destination)<=100 and (not date or re.fullmatch(r'\d{4}-\d{2}-\d{2}',date)),'Invalid search.')
    with db() as c:
        rows=c.execute("SELECT r.* FROM rides r JOIN users u ON u.id=r.driver_id WHERE r.status='open' AND u.approved=1 AND (r.ladies=0 OR (u.woman_verified=1 AND u.gender='woman')) AND r.departure>? AND r.service=? AND r.ladies=? AND r.available>=? AND (?='' OR lower(r.origin)=lower(?)) AND (?='' OR lower(r.destination)=lower(?)) ORDER BY r.departure LIMIT 500",(datetime.now(timezone.utc).isoformat(),service,int(ladies),seats,origin,origin,destination,destination)).fetchall()
        return {'rides':[ride_json(c,r) for r in rows if not date or datetime.fromisoformat(r['departure']).astimezone(timezone(timedelta(hours=5,minutes=30))).date().isoformat()==date][:100]}
@app.post('/v1/rides',status_code=201)
def offer(data:Offer,u=Depends(current)):
    fail(u['role']=='driver' and u['approved'],'Driver verification and operator approval are required.',403)
    fail(data.departure.tzinfo is not None and data.departure>datetime.now(timezone.utc),'Choose a future departure with a time zone.')
    fail(data.origin.casefold()!=data.destination.casefold(),'Pickup and destination must differ.')
    fail(data.capacity<=SERVICES[data.service],'Capacity exceeds the vehicle limit.')
    fail(not data.ladies or (u['gender']=='woman' and u['woman_verified']),'Ladies rides require verified women drivers.',403)
    id=uid('ride')
    with db(True) as c:
        approved_vehicle=c.execute('SELECT * FROM vehicles WHERE driver_id=? AND plate=?',(u['id'],data.plate)).fetchone()
        fail(approved_vehicle is not None and data.service in approved_vehicle['services'].split(','),'This vehicle must be approved for the selected service.',403)
        fail(data.vehicle==approved_vehicle['vehicle'],'Vehicle details must match the approved vehicle.')
        c.execute('INSERT INTO rides(id,driver_id,origin,destination,departure,service,ladies,capacity,available,price,vehicle,plate,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(id,u['id'],data.origin,data.destination,data.departure.astimezone(timezone.utc).isoformat(),data.service,int(data.ladies),data.capacity,data.capacity,data.price,data.vehicle,data.plate,time.time()))
        return {'ride':ride_json(c,c.execute('SELECT * FROM rides WHERE id=?',(id,)).fetchone())}
@app.get('/v1/driver/rides')
def driver_rides(u=Depends(current)):
    with db() as c:return {'rides':[ride_json(c,r) for r in c.execute('SELECT * FROM rides WHERE driver_id=? ORDER BY created DESC LIMIT 100',(u['id'],))]}
@app.post('/v1/rides/{id}/close')
def close(id:str,u=Depends(current)):
    with db(True) as c:
        r=c.execute('SELECT * FROM rides WHERE id=? AND driver_id=?',(id,u['id'])).fetchone();fail(r is not None,'Ride not found.',404)
        fail(not c.execute("SELECT 1 FROM bookings WHERE ride_id=? AND status IN ('confirmed','in_progress')",(id,)).fetchone(),'Finish existing bookings before closing this offer.',409)
        c.execute("UPDATE rides SET status='closed',lat=NULL,lng=NULL,located=NULL WHERE id=?",(id,))
    return {'closed':True}
@app.post('/v1/bookings',status_code=201)
def book(data:Reservation,u=Depends(current)):
    fail(u['approved'],'Complete account verification with the operator before booking.',403)
    with db(True) as c:
        r=c.execute('SELECT * FROM rides WHERE id=?',(data.ride_id,)).fetchone();fail(r is not None,'Ride not found.',404)
        fail(r['service'] in SERVICES,'This service is no longer available.',409)
        fail(r['driver_id']!=u['id'],'You cannot book your own ride.')
        d=c.execute('SELECT * FROM users WHERE id=?',(r['driver_id'],)).fetchone()
        fail(d['approved'],'This driver is unavailable.',409)
        fail(r['status']=='open' and r['departure']>datetime.now(timezone.utc).isoformat(),'This ride is no longer available.',409)
        fail(not r['ladies'] or (u['gender']=='woman' and u['woman_verified'] and data.women_party and d['gender']=='woman' and d['woman_verified']),'Ladies rides are for verified women riders and an all-women party with a verified woman driver.',403)
        reserved=data.seats if r['service']=='shared' else r['capacity']
        fail(data.seats<=r['capacity'] and r['available']>=reserved,'There are not enough seats available.',409)
        fail(not c.execute("SELECT 1 FROM bookings WHERE rider_id=? AND status IN ('confirmed','in_progress')",(u['id'],)).fetchone(),'Finish or cancel your active booking first.',409)
        id=uid('booking');pin=f'{secrets.randbelow(1000000):06d}'
        c.execute('UPDATE rides SET available=available-? WHERE id=?',(reserved,r['id']))
        c.execute('INSERT INTO bookings(id,rider_id,ride_id,seats,reserved,total,status,pin,created) VALUES(?,?,?,?,?,?,?,?,?)',(id,u['id'],r['id'],data.seats,reserved,r['price']*(data.seats if r['service']=='shared' else 1),'confirmed',pin,time.time()))
        return {'booking':booking_json(c,c.execute('SELECT * FROM bookings WHERE id=?',(id,)).fetchone(),u)}
@app.get('/v1/bookings')
def bookings(u=Depends(current)):
    with db() as c:
        rows=c.execute('SELECT b.* FROM bookings b JOIN rides r ON r.id=b.ride_id WHERE b.rider_id=? OR r.driver_id=? ORDER BY b.created DESC LIMIT 100',(u['id'],u['id'])).fetchall()
        return {'bookings':[booking_json(c,b,u) for b in rows]}
@app.post('/v1/bookings/{id}/cancel')
def cancel(id:str,u=Depends(current)):
    with db(True) as c:
        b,r=owned_booking(c,id,u);fail(b['status']=='confirmed','Only trips that have not started can be cancelled.',409)
        c.execute("UPDATE bookings SET status='cancelled',pin='' WHERE id=?",(id,));c.execute('UPDATE rides SET available=available+? WHERE id=?',(b['reserved'],r['id']))
        c.execute('DELETE FROM shares WHERE booking_id=?',(id,))
        if r['status']=='in_progress' and not c.execute("SELECT 1 FROM bookings WHERE ride_id=? AND status IN ('confirmed','in_progress')",(r['id'],)).fetchone():
            c.execute("UPDATE rides SET status='closed',lat=NULL,lng=NULL,located=NULL WHERE id=?",(r['id'],))
    return {'cancelled':True}
@app.post('/v1/bookings/{id}/start')
def start(id:str,data:Pin,u=Depends(current)):
    wrong=False
    with db(True) as c:
        b,r=owned_booking(c,id,u,True);fail(u['approved'],'Driver approval required.',403)
        fail(b['status']=='confirmed','This booking cannot be started.',409)
        fail(b['pin_blocked_until']<=time.time(),'PIN attempts temporarily locked. Wait 15 minutes.',429)
        if not hmac.compare_digest(data.pin,b['pin']):
            wrong=True;attempts=b['pin_attempts']+1
            c.execute('UPDATE bookings SET pin_attempts=?,pin_blocked_until=? WHERE id=?',(attempts,time.time()+900 if attempts%5==0 else 0,id))
        else:
            c.execute("UPDATE bookings SET status='in_progress',pin='' WHERE id=?",(id,))
            c.execute("UPDATE rides SET status='in_progress' WHERE id=?",(r['id'],))
    fail(not wrong,'Incorrect trip PIN.',400)
    return {'started':True}
@app.post('/v1/bookings/{id}/complete')
def complete(id:str,u=Depends(current)):
    with db(True) as c:
        b,r=owned_booking(c,id,u,True);fail(u['approved'],'Driver approval required.',403);fail(b['status']=='in_progress','Start the trip with the rider PIN first.',409)
        c.execute("UPDATE bookings SET status='completed' WHERE id=?",(id,));c.execute('DELETE FROM shares WHERE booking_id=?',(id,))
        if not c.execute("SELECT 1 FROM bookings WHERE ride_id=? AND status IN ('confirmed','in_progress')",(r['id'],)).fetchone():c.execute("UPDATE rides SET status='closed',lat=NULL,lng=NULL,located=NULL WHERE id=?",(r['id'],))
    return {'completed':True}
@app.post('/v1/rides/{id}/location')
def location(id:str,data:Location,u=Depends(current)):
    with db(True) as c:
        r=c.execute('SELECT * FROM rides WHERE id=? AND driver_id=?',(id,u['id'])).fetchone();fail(r is not None and u['approved'],'Ride not found.',404)
        fail(c.execute("SELECT 1 FROM bookings WHERE ride_id=? AND status IN ('confirmed','in_progress')",(id,)).fetchone() is not None,'Location sharing is limited to active bookings.',409)
        c.execute('UPDATE rides SET lat=?,lng=?,located=? WHERE id=?',(data.lat,data.lng,time.time(),id))
    return {'updated':True}
@app.delete('/v1/rides/{id}/location')
def stop_location(id:str,u=Depends(current)):
    with db(True) as c:c.execute('UPDATE rides SET lat=NULL,lng=NULL,located=NULL WHERE id=? AND driver_id=?',(id,u['id']))
    return {'stopped':True}
@app.post('/v1/bookings/{id}/share')
def share(id:str,u=Depends(current)):
    with db(True) as c:
        b,r=owned_booking(c,id,u);fail(b['status'] in ('confirmed','in_progress'),'Only active journeys can be shared.',409)
        token=secrets.token_urlsafe(32);c.execute('DELETE FROM shares WHERE booking_id=?',(id,));c.execute('INSERT INTO shares VALUES(?,?,?)',(digest(token),id,time.time()+7200))
    return {'url':WEB+'/track.html#'+token,'expires_in_seconds':7200}
@app.delete('/v1/bookings/{id}/share')
def revoke(id:str,u=Depends(current)):
    with db(True) as c:owned_booking(c,id,u);c.execute('DELETE FROM shares WHERE booking_id=?',(id,))
    return {'revoked':True}
@app.get('/v1/shared/{token}')
def shared(token:str):
    with db() as c:
        b=c.execute("SELECT b.* FROM shares s JOIN bookings b ON b.id=s.booking_id WHERE s.hash=? AND s.expires>? AND b.status IN ('confirmed','in_progress')",(digest(token),time.time())).fetchone();fail(b is not None,'This journey link has expired or been revoked.',404)
        r=c.execute('SELECT * FROM rides WHERE id=?',(b['ride_id'],)).fetchone()
        return {'status':b['status'],'origin':r['origin'],'destination':r['destination'],'vehicle':r['vehicle'],'plate':r['plate'],'location':location_json(r)}
@app.post('/v1/incidents',status_code=201)
def incident(data:Incident,u=Depends(current)):
    with db(True) as c:
        if data.booking_id:
            b=c.execute('SELECT b.id FROM bookings b JOIN rides r ON r.id=b.ride_id WHERE b.id=? AND (b.rider_id=? OR r.driver_id=?)',(data.booking_id,u['id'],u['id'])).fetchone();fail(b is not None,'Booking not found.',404)
        id=uid('incident');c.execute('INSERT INTO incidents VALUES(?,?,?,?,?,?)',(id,u['id'],data.booking_id,data.kind,data.detail,time.time()))
    return {'id':id,'received':True,'emergency_services_notified':False,'message':'Report saved for operator review. This is not a monitored emergency channel. Call 112 for immediate help.'}

class CashfreeOrderNotFound(Exception):pass
class CashfreeOrderExists(Exception):pass

def cashfree(method,path,payload=None,idempotency=None):
    client=os.getenv('CASHFREE_CLIENT_ID');secret=os.getenv('CASHFREE_CLIENT_SECRET')
    fail(client and secret,'Online payments are not configured. No charge was made.',503)
    base='https://api.cashfree.com/pg' if MODE=='production' else 'https://sandbox.cashfree.com/pg'
    headers={'x-client-id':client,'x-client-secret':secret,'x-api-version':'2025-01-01','Content-Type':'application/json'}
    if idempotency:headers['x-idempotency-key']=idempotency
    try:
        response=httpx.request(method,base+path,json=payload,headers=headers,timeout=20)
        response.raise_for_status();return response.json()
    except httpx.HTTPStatusError as e:
        if method=='GET' and e.response.status_code==404:raise CashfreeOrderNotFound() from e
        if method=='POST' and path=='/orders' and e.response.status_code==409:raise CashfreeOrderExists() from e
        raise HTTPException(502,'Payment provider unavailable. Retry safely; your payment status will be checked.') from e
    except (httpx.HTTPError,ValueError):raise HTTPException(502,'Payment provider unavailable. Retry safely; your payment status will be checked.')

def amount_matches(value,expected):
    try:
        amount=Decimal(str(value))
        return amount.is_finite() and amount==Decimal(expected)
    except (InvalidOperation,ValueError,TypeError):return False

def preserve_current_order(c,b):
    if b['order_id']:
        c.execute("INSERT OR IGNORE INTO payment_orders VALUES(?,?,?,'INR','UNKNOWN',NULL,?,?)",(b['order_id'],b['id'],b['total'],b['created'],time.time()))

@contextmanager
def payment_guard(id,u):
    # A durable per-booking lease serializes checkout/status requests without holding
    # SQLite's write lock during network calls. A crashed worker can be retried later.
    token=secrets.token_hex(24);now=time.time()
    with db(True) as c:
        b,r=owned_booking(c,id,u);preserve_current_order(c,b)
        lock=c.execute('SELECT * FROM payment_locks WHERE booking_id=?',(id,)).fetchone()
        fail(lock is None or lock['expires']<=now,'Payment is already being checked. Please retry shortly.',409)
        c.execute('INSERT OR REPLACE INTO payment_locks VALUES(?,?,?)',(id,token,now+120))
    try:yield token
    finally:
        with db(True) as c:c.execute('DELETE FROM payment_locks WHERE booking_id=? AND token=?',(id,token))

def renew_payment_lock(c,id,token):
    now=time.time()
    changed=c.execute('UPDATE payment_locks SET expires=? WHERE booking_id=? AND token=? AND expires>?',(now+120,id,token,now)).rowcount
    fail(changed==1,'Payment check interrupted. Please retry; the existing order will be checked.',409)

def payment_call(id,token,method,path,payload=None,idempotency=None):
    with db(True) as c:
        renew_payment_lock(c,id,token)
        if method=='POST':fail(not c.execute('SELECT paid FROM bookings WHERE id=?',(id,)).fetchone()[0],'This trip is already paid.',409)
    return cashfree(method,path,payload,idempotency)

def validate_order(order,record):
    fail(isinstance(order,dict) and order.get('order_id')==record['order_id'] and order.get('order_currency')==record['currency'] and amount_matches(order.get('order_amount'),record['amount']),'Payment provider returned inconsistent order details. No new checkout was opened.',502)
    fail(order.get('order_status') in ('ACTIVE','PAID','EXPIRED','TERMINATED','TERMINATION_REQUESTED'),'Payment order status could not be confirmed. Retry the status check.',502)

def record_order(id,token,record,order):
    validate_order(order,record)
    with db(True) as c:
        renew_payment_lock(c,id,token)
        # A delayed ACTIVE response must never undo a successful webhook.
        c.execute("UPDATE payment_orders SET status=CASE WHEN status='PAID' THEN status ELSE ? END,updated=? WHERE order_id=?",(order['order_status'],time.time(),record['order_id']))
        if order['order_status']=='PAID':c.execute('UPDATE bookings SET paid=1 WHERE id=? AND total=?',(id,record['amount']))

def terminal_payment_check(id,token,record):
    # An expired order can still have a bank result pending. Do not open another
    # order while such an attempt is unresolved, or if a success arrived first.
    try:payments=payment_call(id,token,'GET','/orders/'+record['order_id']+'/payments')
    except CashfreeOrderNotFound:raise HTTPException(502,'Previous payment attempts could not be verified. Retry the status check.')
    fail(isinstance(payments,list),'Payment attempts could not be verified.',502)
    pending=False
    for payment in payments:
        fail(isinstance(payment,dict),'Payment attempts could not be verified.',502)
        status=payment.get('payment_status')
        if status=='SUCCESS':
            fail(payment.get('order_id')==record['order_id'] and payment.get('payment_currency')==record['currency'] and amount_matches(payment.get('payment_amount'),record['amount']),'Previous payment has inconsistent details. Contact the operator before retrying.',502)
            record_order(id,token,record,{'order_id':record['order_id'],'order_currency':record['currency'],'order_amount':record['amount'],'order_status':'PAID'})
        elif status not in ('FAILED','USER_DROPPED','CANCELLED','VOID'):pending=True
    return pending

def sync_payment_orders(id,token):
    with db() as c:records=[dict(r) for r in c.execute('SELECT * FROM payment_orders WHERE booking_id=? ORDER BY created,order_id',(id,))]
    orders={};errors=[];pending=False
    for record in records:
        try:
            try:order=payment_call(id,token,'GET','/orders/'+record['order_id'])
            except CashfreeOrderNotFound:
                orders[record['order_id']]=None;continue
            record_order(id,token,record,order);orders[record['order_id']]=order
            if order['order_status'] in ('EXPIRED','TERMINATED'):pending=terminal_payment_check(id,token,record) or pending
        except HTTPException as e:errors.append(e)
    with db() as c:paid=bool(c.execute('SELECT paid FROM bookings WHERE id=?',(id,)).fetchone()[0])
    # Still reconcile a known success if a different historical lookup failed.
    if not paid and errors:raise errors[0]
    return orders,paid,pending

def checkout_result(id,token,record,order):
    validate_order(order,record)
    with db(True) as c:
        renew_payment_lock(c,id,token)
        fail(not c.execute('SELECT paid FROM bookings WHERE id=?',(id,)).fetchone()[0],'This trip is already paid. Refresh your trips.',409)
    fail(order['order_status']=='ACTIVE' and isinstance(order.get('payment_session_id'),str) and order['payment_session_id'],'Checkout is not active. Check payment status before retrying.',409)
    return {'payment_session_id':order['payment_session_id'],'mode':MODE,'order_id':record['order_id']}

def create_or_resume_order(id,u,token,previous=None):
    with db(True) as c:
        renew_payment_lock(c,id,token)
        b,r=owned_booking(c,id,u);fail(not b['paid'],'This trip is already paid.',409)
        if previous:
            fail(b['order_id']==previous['order_id'],'Payment order changed. Retry the status check.',409)
            order_id=previous['order_id']
        else:
            order_id='planto_'+uuid.uuid4().hex
            c.execute("INSERT INTO payment_orders VALUES(?,?,?,'INR','CREATING',NULL,?,?)",(order_id,id,b['total'],time.time(),time.time()))
            c.execute('UPDATE bookings SET order_id=? WHERE id=?',(order_id,id))
        record=dict(c.execute('SELECT * FROM payment_orders WHERE order_id=?',(order_id,)).fetchone())
        payload=json.loads(record['request_json']) if record['request_json'] else {'order_id':order_id,'order_amount':record['amount'],'order_currency':record['currency'],'customer_details':{'customer_id':u['id'],'customer_phone':u['phone'],'customer_name':u['name']},'order_meta':{'return_url':WEB+'/app.html?payment_return=1','notify_url':PUBLIC+'/v1/payments/webhook'}}
        # Commit both ID and the immutable body before calling the provider. A lost
        # response is retried with the same ID, body and idempotency key.
        c.execute('UPDATE payment_orders SET request_json=? WHERE order_id=?',(json.dumps(payload,sort_keys=True),order_id))
    try:order=payment_call(id,token,'POST','/orders',payload,str(uuid.uuid5(uuid.NAMESPACE_URL,order_id)))
    except CashfreeOrderExists:
        try:order=payment_call(id,token,'GET','/orders/'+order_id)
        except CashfreeOrderNotFound:raise HTTPException(502,'The existing payment order could not be confirmed. Retry the status check.')
    record_order(id,token,record,order)
    return checkout_result(id,token,record,order)

def payment_order(id,u):
    with payment_guard(id,u) as token:
        with db() as c:
            b,r=owned_booking(c,id,u);fail(b['status']=='completed','Pay after your trip is completed.',409);fail(not b['paid'],'This trip is already paid.',409)
        if not b['order_id']:return create_or_resume_order(id,u,token)
        orders,paid,pending=sync_payment_orders(id,token)
        fail(not paid,'This trip is already paid. Refresh your trips.',409)
        fail(not pending,'A previous payment is still pending. Check payment status before retrying.',409)
        for order_id,order in orders.items():
            if order_id!=b['order_id']:
                fail(order is not None and order['order_status'] in ('EXPIRED','TERMINATED'),'A previous payment order remains unresolved. No new checkout was opened.',409)
        with db() as c:record=dict(c.execute('SELECT * FROM payment_orders WHERE order_id=?',(b['order_id'],)).fetchone())
        order=orders[b['order_id']]
        if order is None:return create_or_resume_order(id,u,token,record)
        if order['order_status']=='ACTIVE':return checkout_result(id,token,record,order)
        fail(order['order_status'] in ('EXPIRED','TERMINATED'),'Previous order is still being terminated. Check payment status before retrying.',409)
        return create_or_resume_order(id,u,token)
@app.post('/v1/bookings/{id}/payment')
def payment(id:str,u=Depends(current)):return payment_order(id,u)
def reconcile(id,u):
    with payment_guard(id,u) as token:
        with db() as c:b,r=owned_booking(c,id,u)
        if b['paid']:return {'paid':True}
        fail(b['order_id'],'No payment order exists yet.',409)
        orders,paid,pending=sync_payment_orders(id,token)
        return {'paid':paid,'pending':pending}
@app.post('/v1/bookings/{id}/payment-status')
def payment_status(id:str,u=Depends(current)):return reconcile(id,u)
@app.post('/v1/bookings/{id}/checkout-link')
def checkout_link(id:str,u=Depends(current)):
    # Native apps open a short-lived hosted page, never put auth tokens in URLs.
    with db(True) as c:
        b,r=owned_booking(c,id,u);fail(b['status']=='completed' and not b['paid'],'No payment due.',409)
        token=secrets.token_urlsafe(32);c.execute('DELETE FROM checkout_links WHERE booking_id=?',(id,));c.execute('INSERT INTO checkout_links VALUES(?,?,?)',(digest(token),id,time.time()+600))
    return {'url':WEB+'/pay.html#'+token}
@app.post('/v1/checkout/{token}')
def checkout(token:str):
    with db() as c:
        row=c.execute('SELECT b.* FROM checkout_links l JOIN bookings b ON b.id=l.booking_id WHERE l.hash=? AND l.expires>?',(digest(token),time.time())).fetchone();fail(row is not None,'Payment link expired. Reopen checkout in the app.',404)
        u=dict(c.execute('SELECT * FROM users WHERE id=?',(row['rider_id'],)).fetchone())
    return payment_order(row['id'],u)
@app.post('/v1/checkout/{token}/status')
def checkout_status(token:str):
    with db() as c:
        row=c.execute('SELECT b.* FROM checkout_links l JOIN bookings b ON b.id=l.booking_id WHERE l.hash=? AND l.expires>?',(digest(token),time.time())).fetchone();fail(row is not None,'Payment link expired.',404)
        u=dict(c.execute('SELECT * FROM users WHERE id=?',(row['rider_id'],)).fetchone())
    return reconcile(row['id'],u)
@app.post('/v1/payments/webhook')
async def webhook(request:Request):
    raw=await request.body();timestamp=request.headers.get('x-webhook-timestamp','');signature=request.headers.get('x-webhook-signature','');secret=os.getenv('CASHFREE_CLIENT_SECRET','')
    expected=base64.b64encode(hmac.new(secret.encode(),timestamp.encode()+raw,hashlib.sha256).digest()).decode()
    fail(secret and timestamp and hmac.compare_digest(expected,signature),'Invalid webhook signature.',401)
    try:
        data=json.loads(raw).get('data',{});order=data.get('order',{});pay=data.get('payment',{})
        fail(isinstance(order,dict) and isinstance(pay,dict),'Invalid webhook body',400)
    except (ValueError,AttributeError):raise HTTPException(400,'Invalid webhook body')
    if pay.get('payment_status')=='SUCCESS':
        with db(True) as c:
            order_id=order.get('order_id')
            fail(isinstance(order_id,str),'Invalid webhook order ID',400)
            record=c.execute('SELECT * FROM payment_orders WHERE order_id=?',(order_id,)).fetchone()
            if record is None:
                legacy=c.execute('SELECT * FROM bookings WHERE order_id=?',(order_id,)).fetchone()
                if legacy:
                    preserve_current_order(c,legacy)
                    record=c.execute('SELECT * FROM payment_orders WHERE order_id=?',(order_id,)).fetchone()
            b=c.execute('SELECT * FROM bookings WHERE id=?',(record['booking_id'],)).fetchone() if record else None
            if b and b['status']=='completed' and record['currency']=='INR' and record['amount']==b['total'] and order.get('order_currency')=='INR' and pay.get('payment_currency')=='INR' and amount_matches(order.get('order_amount'),b['total']) and amount_matches(pay.get('payment_amount'),b['total']):
                c.execute("UPDATE payment_orders SET status='PAID',updated=? WHERE order_id=?",(time.time(),order_id))
                c.execute('UPDATE bookings SET paid=1 WHERE id=?',(b['id'],))
    return {'received':True}

def operator():
    p=argparse.ArgumentParser(description='Local operator administration; run only on the secured API host.')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('approve','suspend'):
        a=sub.add_parser(name);a.add_argument('--phone',required=True);a.add_argument('--reference',required=True)
        if name=='approve':a.add_argument('--woman-verified',action='store_true')
    sub.add_parser('incidents')
    v=sub.add_parser('approve-vehicle');v.add_argument('--phone',required=True);v.add_argument('--plate',required=True);v.add_argument('--vehicle',required=True);v.add_argument('--services',required=True);v.add_argument('--reference',required=True)
    a=p.parse_args();init()
    with db(True) as c:
        if a.command=='incidents':
            for r in c.execute('SELECT * FROM incidents ORDER BY created DESC LIMIT 100'):print(json.dumps(dict(r)))
            return
        u=c.execute('SELECT * FROM users WHERE phone=?',(a.phone,)).fetchone();fail(u is not None,'Account not found.')
        if a.command=='approve-vehicle':
            fail(u['role']=='driver' and u['approved'],'Approve the driver first.')
            fail(set(a.services.split(','))<=set(SERVICES),'Unknown service type.')
            c.execute('INSERT OR REPLACE INTO vehicles VALUES(?,?,?,?)',(u['id'],a.plate,a.vehicle,a.services))
            c.execute('INSERT INTO audit(action,target,reference,created) VALUES(?,?,?,?)',(a.command,u['id']+':'+a.plate,a.reference,time.time()))
            print('Vehicle approved for selected services.');return
        woman=bool(getattr(a,'woman_verified',False));fail(not woman or u['gender']=='woman','Account gender must be woman before verification.')
        c.execute('UPDATE users SET approved=?,woman_verified=? WHERE id=?',(int(a.command=='approve'),int(woman),u['id']))
        if a.command=='suspend':c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
        c.execute('INSERT INTO audit(action,target,reference,created) VALUES(?,?,?,?)',(a.command,u['id'],a.reference,time.time()))
        print('Account updated. Verification evidence must be retained in your secured operations system.')
if __name__=='__main__':operator()
