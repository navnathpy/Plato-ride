export const LOCATIONS = ['Baner','Hinjewadi','Wakad','Shivajinagar','Kothrud','Viman Nagar','Kalyani Nagar','Magarpatta'];
export const STATUSES = ['confirmed','arriving','in_progress','completed'];
export const money = n => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n);
export function localDate(date){return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;}
export function tomorrow(now=new Date()){const d=new Date(now);d.setDate(d.getDate()+1);return localDate(d);}
export function initialState(now=new Date()){
 const day=tomorrow(now);const rides=[];
 const routes=[['Baner','Hinjewadi',90],['Wakad','Hinjewadi',65],['Kothrud','Shivajinagar',80],['Viman Nagar','Magarpatta',120],['Kalyani Nagar','Viman Nagar',75],['Hinjewadi','Baner',90]];
 routes.forEach(([from,to,price],i)=>{
  rides.push({id:`shared-${i}-a`,service:'shared',from,to,host:['Aditi K.','Rahul S.','Sneha P.'][i%3],vehicle:'Hatchback',departure:`${day}T09:15`,price,seats:3,capacity:3,owned:false});
  rides.push({id:`shared-${i}-b`,service:'shared',from,to,host:['Rohan M.','Priya D.','Amit J.'][i%3],vehicle:'Sedan',departure:`${day}T09:45`,price:price+15,seats:2,capacity:2,owned:false});
  rides.push({id:`cab-${i}-a`,service:'cab',from,to,host:'Sample cab partner',vehicle:'Plato Compact',departure:`${day}T09:00`,price:price*3+49,seats:4,capacity:4,owned:false});
  rides.push({id:`cab-${i}-b`,service:'cab',from,to,host:'Sample cab partner',vehicle:'Plato Sedan',departure:`${day}T09:30`,price:price*4+49,seats:4,capacity:4,owned:false});
 });return {version:1,rides,bookings:[]};
}
function fail(condition,message){if(condition)throw new Error(message);}
export function validateSearch(q){fail(!LOCATIONS.includes(q.from)||!LOCATIONS.includes(q.to),'Choose pickup and destination areas.');fail(q.from===q.to,'Pickup and destination must be different.');fail(!/^\d{4}-\d{2}-\d{2}$/.test(q.date)||!Number.isFinite(Date.parse(q.date)),'Choose a valid travel date.');fail(!Number.isInteger(q.seats)||q.seats<1||q.seats>4,'Choose between 1 and 4 passengers.');fail(!['shared','cab'].includes(q.service),'Choose a ride type.');}
export function searchRides(state,q,now=new Date()){validateSearch(q);return state.rides.filter(r=>r.from===q.from&&r.to===q.to&&r.service===q.service&&r.departure.slice(0,10)===q.date&&r.seats>=q.seats&&new Date(r.departure)>now).sort((a,b)=>a.price-b.price);}
export function bookRide(state,id,seats,now=new Date()){
 const ride=state.rides.find(r=>r.id===id);fail(!ride,'This ride is no longer available.');fail(ride.owned,'You cannot book your own offered ride.');fail(!Number.isInteger(seats)||seats<1||seats>4,'Choose between 1 and 4 passengers.');fail(ride.seats<seats,'There are not enough seats. Please search again.');fail(new Date(ride.departure)<=now,'This departure has already passed.');fail(state.bookings.some(b=>b.rideId===id&&!['cancelled','completed'].includes(b.status)),'You already have an active booking on this ride.');
 const reserved=ride.service==='cab'?ride.seats:seats;ride.seats-=reserved;
 const booking={id:`PR-${globalThis.crypto.randomUUID().slice(0,8).toUpperCase()}`,rideId:id,service:ride.service,from:ride.from,to:ride.to,host:ride.host,vehicle:ride.vehicle,departure:ride.departure,passengers:seats,reserved,total:ride.service==='cab'?ride.price:ride.price*seats,status:'confirmed',createdAt:now.toISOString()};state.bookings.unshift(booking);return booking;
}
export function cancelBooking(state,id){const b=state.bookings.find(b=>b.id===id);fail(!b,'Booking not found.');fail(!['confirmed','arriving'].includes(b.status),'Only a trip that has not started can be cancelled.');const r=state.rides.find(r=>r.id===b.rideId);if(r)r.seats=Math.min(r.capacity,r.seats+b.reserved);b.status='cancelled';return b;}
export function advanceBooking(state,id){const b=state.bookings.find(b=>b.id===id);fail(!b,'Booking not found.');const n=STATUSES.indexOf(b.status);fail(n<0||n>=STATUSES.length-1,'This trip cannot move to another stage.');b.status=STATUSES[n+1];return b;}
export function offerRide(state,offer,now=new Date()){
 fail(!LOCATIONS.includes(offer.from)||!LOCATIONS.includes(offer.to)||offer.from===offer.to,'Choose different pickup and destination areas.');
 const departure=new Date(offer.departure);fail(!Number.isFinite(departure.getTime())||departure<=now,'Choose a future departure time.');fail(departure-now>90*86400000,'Choose a departure within the next 90 days.');fail(!Number.isInteger(offer.seats)||offer.seats<1||offer.seats>4,'Offer between 1 and 4 seats.');fail(!Number.isInteger(offer.price)||offer.price<1||offer.price>5000,'Price must be a whole number from ₹1 to ₹5,000.');fail(typeof offer.vehicle!=='string'||offer.vehicle.trim().length<2||offer.vehicle.trim().length>50,'Enter a vehicle description between 2 and 50 characters.');
 const ride={id:`offer-${globalThis.crypto.randomUUID()}`,service:'shared',from:offer.from,to:offer.to,host:'You',vehicle:offer.vehicle.trim(),departure:offer.departure,price:offer.price,seats:offer.seats,capacity:offer.seats,owned:true};state.rides.push(ride);return ride;
}
export function removeOffer(state,id){const r=state.rides.find(r=>r.id===id&&r.owned);fail(!r,'Your offer could not be found.');fail(state.bookings.some(b=>b.rideId===id&&!['cancelled','completed'].includes(b.status)),'This offer has an active booking.');state.rides=state.rides.filter(r=>r.id!==id);}
