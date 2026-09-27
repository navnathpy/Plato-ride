/** Optional development API adapter. The shipped screens use local demoRepository. */
export type ApiService='shared'|'cab';
export type ApiSession={token:string;expires_at:string;user:{id:string;name:string;role:'rider'|'driver'};demo:true};
export type ApiRide={id:string;service:ApiService;origin:{id:string;name:string};destination:{id:string;name:string};departure_at:string;seats_available:number;seats_total:number;fare_per_seat_inr:number|null;fare_total_inr:number|null;status:string;driver:{id:string;name:string};vehicle:{make:string;model:string;color:string;plate:string};demo:true};
export type ApiBooking={id:string;ride_id:string;seats:number;seats_reserved:number;total_inr:number;status:string;ride:ApiRide;payment_status:'not_collected_demo';demo:true};
export class ApiError extends Error {constructor(public code:string,message:string,public status:number){super(message);}}
export function createDevelopmentApi(baseUrl:string){
 const base=baseUrl.replace(/\/$/,'');let token:string|undefined;
 async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),12000);
  try{const response=await fetch(base+path,{method,headers:{Accept:'application/json',...(body!==undefined?{'Content-Type':'application/json'}:{}),...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{}),signal:controller.signal});const data=await response.json();if(!response.ok)throw new ApiError(data.error?.code||'api_error',data.error?.message||'The development service could not complete this request.',response.status);return data as T;}finally{clearTimeout(timer);}
 }
 return {
  health:()=>request<{status:string;production_ready:false}>('/health'),
  async session(name:string,role:'rider'|'driver'='rider'){const result=await request<ApiSession>('/v1/demo/sessions','POST',{name,role});token=result.token;return result;},
  async signOut(){await request('/v1/demo/sessions/current','DELETE');token=undefined;},
  locations:()=>request<{locations:{id:string;name:string;area:string}[]}>('/v1/locations'),
  rides:(query:{origin_id:string;destination_id:string;seats:number;service:ApiService})=>request<{rides:ApiRide[]}>('/v1/rides?'+new URLSearchParams({...query,seats:String(query.seats)})),
  book:(ride_id:string,seats:number)=>request<{booking:ApiBooking}>('/v1/bookings','POST',{ride_id,seats}),
  bookings:()=>request<{bookings:ApiBooking[]}>('/v1/bookings'),
  cancel:(id:string)=>request<{booking:ApiBooking}>('/v1/bookings/'+encodeURIComponent(id)+'/cancel','POST',{}),
  offer:(input:{service:ApiService;origin_id:string;destination_id:string;departure_at:string;seats:number;fare_per_seat_inr?:number;fare_total_inr?:number;vehicle:ApiRide['vehicle']})=>request<{ride:ApiRide}>('/v1/rides','POST',input),
  transition:(id:string,status:'in_progress'|'completed'|'cancelled')=>request<{ride:ApiRide}>('/v1/rides/'+encodeURIComponent(id),'PATCH',{status}),
 };
}
