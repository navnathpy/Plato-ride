import test from 'node:test';import assert from 'node:assert/strict';import {capacities,createApi,fare} from './api.ts';import type {Ride} from './api.ts';
test('bike limits bookings to one passenger',()=>{assert.equal(capacities.bike,1);assert.equal(fare({capacity:capacities.bike,price:50,service:'bike'} as Ride,1),50);assert.throws(()=>fare({capacity:capacities.bike,price:50,service:'bike'} as Ride,2));});
test('only shared rides multiply by passenger count',()=>{assert.equal(fare({capacity:4,price:100,service:'shared'} as Ride,3),300);assert.equal(fare({capacity:4,price:100,service:'cab'} as Ride,3),100);});
test('missing backend does not create local bookings',async()=>{await assert.rejects(createApi('').request('/v1/bookings','POST',{}),/not connected/);});
