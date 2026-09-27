import React from 'react';
import {View,Linking} from 'react-native';
import {Body,Button,Card,C} from './ui';
import {PUNE_EMBED,directionsUrl} from './maps';
export default function MapPreview({from,to}:{from:string;to:string}){
 return <Card style={{padding:0,overflow:'hidden',gap:0}}><iframe title="Google Maps overview of Pune" src={PUNE_EMBED} width="100%" height="230" style={{border:0,background:C.pale}} loading="lazy" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen /><View style={{padding:15,gap:10}}><Body style={{fontSize:12}}>Google Maps · Pune overview. No live driver tracking. Internet required.</Body><Button variant="secondary" onPress={()=>{void Linking.openURL(directionsUrl(from,to));}}>Open selected route in Google Maps</Button></View></Card>;
}
