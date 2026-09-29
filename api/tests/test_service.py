import base64,hashlib,hmac,json,time
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from fastapi.testclient import TestClient
import app as service

@pytest.fixture
def ctx(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'DB',str(tmp_path/'test.sqlite3'))
    monkeypatch.setenv('CASHFREE_CLIENT_SECRET','test-signing-secret')
    monkeypatch.setenv('CASHFREE_CLIENT_ID','test-client-id')
    service.init()
    with service.db(True) as c:
        for id,role,gender,approved,woman in [('driver','driver','woman',1,1),('rider','rider','woman',1,1),('man','rider','man',1,0),('pending','driver','woman',0,0),('other','rider','woman',1,1)]:
            c.execute('INSERT INTO users(id,name,phone,password,role,gender,approved,woman_verified,created) VALUES(?,?,?,?,?,?,?,?,?)',(id,id,'+91900000000'+str(len(c.execute('SELECT * FROM users').fetchall())),'unused',role,gender,approved,woman,time.time()))
            c.execute('INSERT INTO sessions VALUES(?,?,?)',(service.digest(id+'-token'),id,time.time()+3600))
        c.execute('INSERT INTO vehicles VALUES(?,?,?,?)',('driver','MH 12 AB 1234','Approved vehicle','shared,cab,bike'))
    with TestClient(service.app) as client:yield client

def headers(user='rider'):return {'Authorization':'Bearer '+user+'-token'}
def offer(client,kind='shared',ladies=False,capacity=3,driver='driver',**extra):
    data={'origin':'Baner','destination':'Hinjewadi','departure':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'service':kind,'ladies':ladies,'capacity':capacity,'price':100,'vehicle':'Approved vehicle','plate':'MH 12 AB 1234',**extra}
    return client.post('/v1/rides',headers=headers(driver),json=data)
def reserve(client,ride,user='rider',seats=1,women=True):return client.post('/v1/bookings',headers=headers(user),json={'ride_id':ride,'seats':seats,'women_party':women})
def booking(client,kind='shared',ladies=False,seats=1,capacity=3):
    r=offer(client,kind,ladies,capacity);assert r.status_code==201,r.text
    b=reserve(client,r.json()['ride']['id'],seats=seats);assert b.status_code==201,b.text
    return b.json()['booking']
def finish(client,b):
    assert client.post('/v1/bookings/'+b['id']+'/start',headers=headers('driver'),json={'pin':b['pin']}).status_code==200
    assert client.post('/v1/bookings/'+b['id']+'/complete',headers=headers('driver'),json={}).status_code==200

class FakeCashfree:
    """Stateful provider double: tests never reach a real merchant account."""
    def __init__(self):self.orders={};self.payments={};self.calls=[]
    def __call__(self,method,path,payload=None,idempotency=None):
        self.calls.append((method,path,json.loads(json.dumps(payload)),idempotency))
        if method=='POST':
            assert path=='/orders'
            order_id=payload['order_id']
            if order_id not in self.orders:
                self.orders[order_id]={'order_id':order_id,'order_amount':payload['order_amount'],'order_currency':payload['order_currency'],'order_status':'ACTIVE','payment_session_id':'session-'+order_id}
            return dict(self.orders[order_id])
        assert method=='GET' and path.startswith('/orders/')
        order_id=path.split('/')[2]
        if order_id not in self.orders:raise service.CashfreeOrderNotFound()
        return self.payments.get(order_id,[]) if path.endswith('/payments') else dict(self.orders[order_id])
    @property
    def creates(self):return [call for call in self.calls if call[0]=='POST']

def pay(client,b):return client.post('/v1/bookings/'+b['id']+'/payment',headers=headers(),json={})
def signed_webhook(client,order_id,total,**overrides):
    payment={'payment_status':'SUCCESS','payment_currency':'INR','payment_amount':total,**overrides}
    payload={'data':{'order':{'order_id':order_id,'order_currency':'INR','order_amount':total},'payment':payment}}
    body=json.dumps(payload).encode();ts=str(int(time.time()*1000))
    sig=base64.b64encode(hmac.new(b'test-signing-secret',ts.encode()+body,hashlib.sha256).digest()).decode()
    return client.post('/v1/payments/webhook',content=body,headers={'x-webhook-timestamp':ts,'x-webhook-signature':sig,'content-type':'application/json'})

def test_empty_database_has_no_seeded_inventory(ctx):
    assert ctx.get('/v1/rides').json()=={'rides':[]}
    assert ctx.post('/v1/demo/sessions',json={'name':'x'}).status_code==404
def test_registration_and_password_session(ctx):
    data={'name':'New rider','phone':'+919123456789','password':'long-test-password','role':'rider','gender':'woman'}
    r=ctx.post('/v1/auth/register',json=data);assert r.status_code==201
    u=r.json();assert u['user']['approved']==0 and u['user']['woman_verified']==0
    with service.db() as c:stored=c.execute('SELECT password FROM users WHERE id=?',(u['user']['id'],)).fetchone()[0]
    assert stored!=data['password']
    bad=ctx.post('/v1/auth/login',json={'phone':data['phone'],'password':'wrong-test-password'});assert bad.status_code==401
    login=ctx.post('/v1/auth/login',json={k:data[k] for k in ('phone','password')});assert login.status_code==200
    auth={'Authorization':'Bearer '+login.json()['token']}
    assert ctx.delete('/v1/auth/session',headers=auth).status_code==200
    assert ctx.get('/v1/me',headers=auth).status_code==401
def test_driver_approval_and_vehicle_enforced(ctx):
    assert offer(ctx,driver='pending').status_code==403
    assert offer(ctx,plate='MH 12 ZZ 9999').status_code==403
    assert offer(ctx,vehicle='Unapproved change').status_code==400
def test_vehicle_capacity(ctx):
    assert offer(ctx,'bike',capacity=2).status_code==400
    assert offer(ctx,'auto',capacity=1).status_code==422
    assert ctx.get('/v1/rides?service=auto').status_code==422
    assert offer(ctx,'cab',capacity=5).status_code==400
@pytest.mark.parametrize('kind,capacity,seats,total',[('shared',3,2,200),('cab',4,3,100),('bike',1,1,100)])
def test_fares_and_exclusive_inventory(ctx,kind,capacity,seats,total):
    b=booking(ctx,kind,seats=seats,capacity=capacity);assert b['total']==total
    remaining=ctx.get('/v1/rides',params={'service':kind}).json()['rides']
    assert (remaining[0]['available'] if remaining else 0)==(capacity-seats if kind=='shared' else 0)
    assert ctx.post('/v1/bookings/'+b['id']+'/cancel',headers=headers(),json={}).status_code==200
    assert ctx.post('/v1/bookings/'+b['id']+'/cancel',headers=headers(),json={}).status_code==409
    assert ctx.get('/v1/rides',params={'service':kind}).json()['rides'][0]['available']==capacity

def test_last_shared_cancellation_closes_started_offer_and_removes_location(ctx):
    first=booking(ctx,capacity=2)
    second=reserve(ctx,first['ride']['id'],'other').json()['booking']
    finish(ctx,first)
    assert ctx.post('/v1/rides/'+first['ride']['id']+'/location',headers=headers('driver'),json={'lat':18.5,'lng':73.8}).status_code==200
    assert ctx.post('/v1/bookings/'+second['id']+'/cancel',headers=headers('other'),json={}).status_code==200
    with service.db() as c:r=c.execute('SELECT * FROM rides WHERE id=?',(first['ride']['id'],)).fetchone()
    assert r['status']=='closed' and r['lat'] is None and r['lng'] is None and r['located'] is None
    assert ctx.get('/v1/rides').json()['rides']==[]
def test_ladies_constraints_and_no_fallback(ctx):
    regular=offer(ctx).json()['ride']
    assert ctx.get('/v1/rides?ladies=true').json()['rides']==[]
    r=offer(ctx,ladies=True).json()['ride']
    assert reserve(ctx,r['id'],'man').status_code==403
    assert reserve(ctx,r['id'],women=False).status_code==403
    with service.db(True) as c:c.execute("UPDATE users SET woman_verified=0 WHERE id='rider'")
    assert reserve(ctx,r['id']).status_code==403
    assert all(x['id']!=regular['id'] for x in ctx.get('/v1/rides?ladies=true').json()['rides'])
def test_concurrent_last_seat_cannot_oversell(ctx):
    r=offer(ctx,'bike',capacity=1).json()['ride']
    with ThreadPoolExecutor(2) as ex:results=list(ex.map(lambda u:reserve(ctx,r['id'],u).status_code,['rider','other']))
    assert sorted(results)==[201,409]
def test_pin_only_visible_to_rider_and_role_enforced(ctx):
    b=booking(ctx)
    driver=ctx.get('/v1/bookings',headers=headers('driver')).json()['bookings'][0];assert 'pin' not in driver
    assert ctx.post('/v1/bookings/'+b['id']+'/start',headers=headers(),json={'pin':b['pin']}).status_code==404
    assert ctx.post('/v1/bookings/'+b['id']+'/complete',headers=headers('driver'),json={}).status_code==409
    finish(ctx,b)
    assert ctx.post('/v1/bookings/'+b['id']+'/start',headers=headers('driver'),json={'pin':b['pin']}).status_code==409
    assert ctx.get('/v1/rides').json()['rides']==[]
def test_wrong_pin_lockout_persists(ctx):
    b=booking(ctx);wrong='111111' if b['pin']!='111111' else '222222'
    for _ in range(5):assert ctx.post('/v1/bookings/'+b['id']+'/start',headers=headers('driver'),json={'pin':wrong}).status_code==400
    assert ctx.post('/v1/bookings/'+b['id']+'/start',headers=headers('driver'),json={'pin':b['pin']}).status_code==429
def test_share_location_revocation_and_expiry(ctx):
    b=booking(ctx);link=ctx.post('/v1/bookings/'+b['id']+'/share',headers=headers(),json={}).json()['url'];token=link.split('#')[1]
    path='/v1/shared/'+token
    assert ctx.post('/v1/rides/'+b['ride']['id']+'/location',headers=headers(),json={'lat':18.5,'lng':73.8}).status_code==404
    assert ctx.post('/v1/rides/'+b['ride']['id']+'/location',headers=headers('driver'),json={'lat':18.5,'lng':73.8}).status_code==200
    r=ctx.get(path).json();assert r['location']['lat']==18.5
    assert not any(k in r for k in ('pin','phone','rider_name'))
    with service.db(True) as c:c.execute('UPDATE rides SET located=?',(time.time()-121,))
    assert ctx.get(path).json()['location'] is None
    ctx.delete('/v1/bookings/'+b['id']+'/share',headers=headers());assert ctx.get(path).status_code==404
    link=ctx.post('/v1/bookings/'+b['id']+'/share',headers=headers(),json={}).json()['url']
    finish(ctx,b);assert ctx.get('/v1/shared/'+link.split('#')[1]).status_code==404
def test_payment_server_amount_and_reconciliation(ctx,monkeypatch):
    b=booking(ctx);assert ctx.post('/v1/bookings/'+b['id']+'/payment',headers=headers(),json={}).status_code==409
    finish(ctx,b);cf=FakeCashfree()
    monkeypatch.setattr(service,'cashfree',cf)
    p=pay(ctx,b);assert p.status_code==200
    assert cf.creates[0][2]['order_amount']==b['total']
    cf.orders[p.json()['order_id']]['order_status']='PAID'
    assert ctx.post('/v1/bookings/'+b['id']+'/payment-status',headers=headers('other'),json={}).status_code==404
    assert ctx.post('/v1/bookings/'+b['id']+'/payment-status',headers=headers(),json={}).json()['paid']
    assert pay(ctx,b).status_code==409 and len(cf.creates)==1

def test_active_payment_order_reuses_provider_session_without_create(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    first=pay(ctx,b);assert first.status_code==200
    second=pay(ctx,b);assert second.status_code==200 and second.json()==first.json()
    assert len(cf.creates)==1
    assert ('GET','/orders/'+first.json()['order_id']) in [(x[0],x[1]) for x in cf.calls]

@pytest.mark.parametrize('terminal',['EXPIRED','TERMINATED'])
def test_terminal_unpaid_order_rotates_and_keeps_history(ctx,monkeypatch,terminal):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']=terminal
    response=pay(ctx,b);assert response.status_code==200,response.text
    new=response.json()['order_id'];assert new!=old and len(cf.creates)==2
    with service.db() as c:
        assert c.execute('SELECT order_id FROM bookings WHERE id=?',(b['id'],)).fetchone()[0]==new
        assert {r['order_id'] for r in c.execute('SELECT * FROM payment_orders WHERE booking_id=?',(b['id'],))}=={old,new}
    assert cf.creates[0][3]!=cf.creates[1][3]

def test_provider_paid_before_another_checkout_is_recorded_without_create(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']='PAID'
    assert pay(ctx,b).status_code==409 and len(cf.creates)==1
    assert ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']==1

@pytest.mark.parametrize('accepted',[True,False])
def test_lost_create_response_reconciles_or_retries_same_request(ctx,monkeypatch,accepted):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();first=True
    def lost(method,path,payload=None,idempotency=None):
        nonlocal first
        if method=='POST' and first:
            first=False
            result=cf(method,path,payload,idempotency)
            if not accepted:cf.orders.pop(payload['order_id'])
            raise service.HTTPException(502,'Simulated lost create response')
        return cf(method,path,payload,idempotency)
    monkeypatch.setattr(service,'cashfree',lost)
    assert pay(ctx,b).status_code==502
    with service.db() as c:old=c.execute('SELECT order_id FROM bookings WHERE id=?',(b['id'],)).fetchone()[0]
    # Even if deployment URLs change, the original request body is replayed.
    monkeypatch.setattr(service,'WEB','https://changed.example');service.init()
    retry=pay(ctx,b);assert retry.status_code==200 and retry.json()['order_id']==old
    assert len(cf.creates)==(1 if accepted else 2)
    if not accepted:assert cf.creates[0][2:]==cf.creates[1][2:]
    with service.db() as c:assert c.execute('SELECT count(*) FROM payment_orders WHERE booking_id=?',(b['id'],)).fetchone()[0]==1

def test_unresolved_provider_failure_does_not_replace_existing_order(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id']
    def unavailable(method,path,payload=None,idempotency=None):
        if method=='GET':raise service.HTTPException(502,'Simulated provider timeout')
        return cf(method,path,payload,idempotency)
    monkeypatch.setattr(service,'cashfree',unavailable)
    assert pay(ctx,b).status_code==502 and len(cf.creates)==1
    with service.db() as c:assert c.execute('SELECT order_id FROM bookings WHERE id=?',(b['id'],)).fetchone()[0]==old

def test_expired_order_with_pending_bank_attempt_does_not_rotate(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']='EXPIRED';cf.payments[old]=[{'payment_status':'PENDING'}]
    assert pay(ctx,b).status_code==409 and len(cf.creates)==1
    cf.payments[old]=[{'order_id':old,'payment_status':'SUCCESS','payment_currency':'INR','payment_amount':b['total']}]
    assert pay(ctx,b).status_code==409 and len(cf.creates)==1
    assert ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']==1

def test_historical_paid_order_is_reconciled_before_reusing_current_checkout(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']='EXPIRED'
    new=pay(ctx,b).json()['order_id'];assert new!=old
    cf.orders[old]['order_status']='PAID'
    assert pay(ctx,b).status_code==409 and len(cf.creates)==2
    assert ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']==1

def test_historical_webhook_marks_booking_paid_and_rejects_wrong_amount(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']='EXPIRED'
    new=pay(ctx,b).json()['order_id'];assert new!=old
    assert signed_webhook(ctx,old,b['total'],payment_amount=b['total']+1).status_code==200
    assert not ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']
    assert signed_webhook(ctx,old,b['total']).status_code==200
    assert signed_webhook(ctx,old,b['total']).status_code==200
    assert pay(ctx,b).status_code==409 and len(cf.creates)==2
    with service.db() as c:assert c.execute('SELECT status FROM payment_orders WHERE order_id=?',(old,)).fetchone()[0]=='PAID'

def test_concurrent_expired_order_retry_creates_only_one_replacement(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']='EXPIRED'
    entered=Event();release=Event()
    def blocking(method,path,payload=None,idempotency=None):
        if method=='GET' and path=='/orders/'+old:
            entered.set();assert release.wait(5)
        return cf(method,path,payload,idempotency)
    monkeypatch.setattr(service,'cashfree',blocking)
    with ThreadPoolExecutor(2) as executor:
        first=executor.submit(pay,ctx,b)
        assert entered.wait(5)
        try:second=pay(ctx,b);assert second.status_code==409
        finally:release.set()
        response=first.result();assert response.status_code==200,response.text
    assert response.json()['order_id']!=old and len(cf.creates)==2

@pytest.mark.parametrize('field,value',[('order_id','wrong-order'),('order_currency','USD'),('order_amount',101),('order_amount','NaN')])
def test_payment_reconciliation_rejects_mismatched_provider_values(ctx,monkeypatch,field,value):
    b=booking(ctx);finish(ctx,b);cf=FakeCashfree();monkeypatch.setattr(service,'cashfree',cf)
    old=pay(ctx,b).json()['order_id'];cf.orders[old]['order_status']='PAID';cf.orders[old][field]=value
    assert pay(ctx,b).status_code==502 and len(cf.creates)==1
    assert not ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']
def test_webhook_rejects_forgery_and_mismatched_amount_and_is_idempotent(ctx):
    b=booking(ctx);finish(ctx,b)
    with service.db(True) as c:c.execute('UPDATE bookings SET order_id=? WHERE id=?',('test-order',b['id']))
    payload={'data':{'order':{'order_id':'test-order','order_currency':'INR','order_amount':b['total']},'payment':{'payment_status':'SUCCESS','payment_currency':'INR','payment_amount':b['total']}}}
    def send(data,valid=True):
        body=json.dumps(data).encode();ts=str(int(time.time()*1000));sig=base64.b64encode(hmac.new(b'test-signing-secret',ts.encode()+body,hashlib.sha256).digest()).decode()
        return ctx.post('/v1/payments/webhook',content=body,headers={'x-webhook-timestamp':ts,'x-webhook-signature':sig if valid else 'forged','content-type':'application/json'})
    assert send(payload,False).status_code==401
    payload['data']['payment']['payment_amount']=1;assert send(payload).status_code==200
    assert not ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']
    payload['data']['payment']['payment_amount']=b['total'];assert send(payload).status_code==200;assert send(payload).status_code==200
    assert ctx.get('/v1/bookings',headers=headers()).json()['bookings'][0]['paid']
def test_incident_not_emergency_dispatch(ctx):
    r=ctx.post('/v1/incidents',headers=headers(),json={'kind':'safety','detail':'Test concern for operator review'});assert r.status_code==201
    assert r.json()['emergency_services_notified'] is False
    assert ctx.post('/v1/incidents',headers=headers(),json={'kind':'safety','detail':'test concern','booking_id':'not-mine'}).status_code==404
def test_missing_cashfree_keys_fail_closed(ctx,monkeypatch):
    b=booking(ctx);finish(ctx,b);monkeypatch.delenv('CASHFREE_CLIENT_ID')
    assert ctx.post('/v1/bookings/'+b['id']+'/payment',headers=headers(),json={}).status_code==503
def test_private_account_and_sensitive_payload_boundaries(ctx):
    assert ctx.get('/v1/me').status_code==401
    assert ctx.post('/v1/auth/register',json={'name':'x','phone':'wrong','password':'weak','approved':True}).status_code==422
    assert ctx.post('/v1/incidents',headers=headers(),content=b'x'*17000).status_code==413
