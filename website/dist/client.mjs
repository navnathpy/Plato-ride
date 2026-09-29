export const SERVICES={shared:{label:'Shared',capacity:6},cab:{label:'Car',capacity:4},bike:{label:'Bike',capacity:1}};
export function totalFare(ride,seats){if(!Number.isInteger(seats)||seats<1||seats>ride.capacity)throw Error('Invalid passenger count');return ride.price*(ride.service==='shared'?seats:1);}
export function createApi(base,fetcher=fetch){
 let token='';base=base.replace(/\/$/,'');
 return {setToken(value){token=value;},async request(path,method='GET',body){
  if(!base)throw Error('Booking service is not connected yet. No booking or payment has been made.');
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),25000);
  try{const response=await fetcher(base+path,{method,headers:{Accept:'application/json',...(body!==undefined?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Please check your details and try again.');return data;}catch(e){if(e.name==='AbortError')throw Error('The service took too long to respond. Refresh your trips before retrying a booking.');throw e;}finally{clearTimeout(timer);}
 }};
}
export async function cashfreeCheckout(payment){
 if(!window.Cashfree){await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://sdk.cashfree.com/js/v3/cashfree.js';s.onload=resolve;s.onerror=()=>reject(Error('Cashfree checkout could not load.'));document.head.append(s);});}
 return window.Cashfree({mode:payment.mode}).checkout({paymentSessionId:payment.payment_session_id,redirectTarget:'_modal'});
}
