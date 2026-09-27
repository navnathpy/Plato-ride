// Native implementation. Metro selects MapPreview.web.tsx for browser builds.
import React,{useState} from 'react';
import {View,Linking} from 'react-native';
import {WebView} from 'react-native-webview';
import {Body,Button,Card,C} from './ui';
import {PUNE_EMBED,directionsUrl} from './maps';
export default function MapPreview({from,to}:{from:string;to:string}){
 const [failed,setFailed]=useState(false);
 return <Card style={{padding:0,overflow:'hidden',gap:0}}>
  <View style={{height:230,backgroundColor:C.pale}}>{failed?<View style={{padding:22}}><Body>Google Maps could not load. Check your connection or open directions below.</Body></View>:<WebView accessibilityLabel="Google Maps overview of Pune" source={{uri:PUNE_EMBED}} style={{flex:1,backgroundColor:C.pale}} originWhitelist={['https://*']} geolocationEnabled={false} onError={()=>setFailed(true)} onHttpError={()=>setFailed(true)} setSupportMultipleWindows={false} onShouldStartLoadWithRequest={request=>{if(request.url==='about:blank')return true;try{const host=new URL(request.url).hostname;return host==='www.google.com'||host==='maps.google.com';}catch{return false;}}} />}</View>
  <View style={{padding:15,gap:10}}><Body style={{fontSize:12}}>Google Maps · Pune overview. No live driver tracking. Internet required.</Body><Button variant="secondary" onPress={()=>{void Linking.openURL(directionsUrl(from,to)).catch(()=>setFailed(true));}}>Open selected route in Google Maps</Button></View>
 </Card>;
}
