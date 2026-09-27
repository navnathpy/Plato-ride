import test from 'node:test';
import assert from 'node:assert/strict';
import {directionsUrl,mapSource,PUNE_EMBED} from '../dist/maps.mjs';
test('route links use official Google Maps URL parameters and selected areas',()=>{const url=new URL(directionsUrl('Baner','Hinjewadi'));assert.equal(url.origin,'https://www.google.com');assert.equal(url.searchParams.get('api'),'1');assert.equal(url.searchParams.get('origin'),'Baner, Pune, Maharashtra, India');assert.equal(url.searchParams.get('destination'),'Hinjewadi, Pune, Maharashtra, India');assert.equal(url.searchParams.get('travelmode'),'driving');});
test('missing key uses the actual city embed, configured key uses route embed',()=>{assert.equal(mapSource('Baner','Hinjewadi'),PUNE_EMBED);const url=new URL(mapSource('A & B','C','test-key'));assert.equal(url.pathname,'/maps/embed/v1/directions');assert.equal(url.searchParams.get('origin'),'A & B, Pune, India');assert.equal(url.searchParams.get('key'),'test-key');});
