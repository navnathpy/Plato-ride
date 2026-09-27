export const PUNE_EMBED='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d121073.91939539721!2d73.8746239!3d18.5035801!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3bc2bf2e67461101%3A0x828d43bf9d9ee343!2sPune%2C%20Maharashtra!5e0!3m2!1sen!2sin!4v1790465034619!5m2!1sen!2sin';
export function directionsUrl(from,to){return 'https://www.google.com/maps/dir/?'+new URLSearchParams({api:'1',origin:from+', Pune, Maharashtra, India',destination:to+', Pune, Maharashtra, India',travelmode:'driving'});}
export function mapSource(from,to,key=''){return key?'https://www.google.com/maps/embed/v1/directions?'+new URLSearchParams({key,origin:from+', Pune, India',destination:to+', Pune, India',mode:'driving',units:'metric',region:'in'}):PUNE_EMBED;}
export function updateMap(query){
 const frame=document.querySelector('#google-map');if(!frame)return;
 const key=window.PLATO_MAPS?.embedApiKey?.trim()||'';const src=mapSource(query.from,query.to,key);
 if(frame.getAttribute('src')!==src)frame.src=src;
 document.querySelector('#map-directions').href=directionsUrl(query.from,query.to);
 document.querySelector('#map-caption').textContent=key?'Google Maps route preview · No live driver tracking':'Google Maps · Pune overview. Open your selected route for directions.';
 frame.title=key?`Google Maps route from ${query.from} to ${query.to}`:'Google Maps overview of Pune';
}
