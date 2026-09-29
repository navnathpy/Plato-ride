export type Service='shared'|'cab'|'bike';
export const capacities:Record<Service,number>={shared:6,cab:4,bike:1};
export type User={id:string;name:string;phone:string;role:'rider'|'driver';gender:string;approved:number;woman_verified:number;contact:string};
export type Ride={id:string;driver_id:string;driver:string;origin:string;destination:string;departure:string;service:Service;ladies:boolean;capacity:number;available:number;price:number;vehicle:string;plate:string;status:string};
export type Booking={id:string;seats:number;total:number;status:string;paid:boolean;pin?:string;rider_name:string;ride:Ride;location:null|{lat:number;lng:number;updated_at:number}};
export function fare(ride:Ride,seats:number){if(!Number.isInteger(seats)||seats<1||seats>ride.capacity)throw Error('Invalid passenger count');return ride.price*(ride.service==='shared'?seats:1);}
export function createApi(base:string){
 let token='';base=base.replace(/\/$/,'');
 return {setToken(value:string){token=value;},async request<T=any>(path:string,method='GET',body?:unknown):Promise<T>{
  if(!base)throw Error('Booking service is not connected yet. No booking or payment has been made.');
  const control=new AbortController(),timer=setTimeout(()=>control.abort(),25000);
  try{const r=await fetch(base+path,{method,headers:{Accept:'application/json',...(body!==undefined?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:control.signal});const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Check your details and try again.');return data;}finally{clearTimeout(timer);}
 }};
}
