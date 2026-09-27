import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StatusBar, Text, TextInput, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { activeBooking, Booking, bookRide, Category, DemoState, findLocation, initialState, LOCATIONS, money, nextLabel, nextStatus, offerRide, removeOffer, Ride, rideTotal, Search, searchRides, transitionBooking, tripLabel, validateSearch } from './src/domain';
import { demoRepository } from './src/storage';
import { Body, Button, C, Card, Chip, Eyebrow, Icon, IconName, RouteIllustration, Stepper, u } from './src/ui';
import { s } from './src/styles';
import MapPreview from './src/MapPreview';

type Tab = 'ride' | 'trips' | 'impact' | 'profile';
type Confirm = { title: string; message: string; action: string; run: () => void; destructive?: boolean };
const TABS: { id: Tab; label: string; icon: IconName }[] = [{ id: 'ride', label: 'Ride', icon: 'car' }, { id: 'trips', label: 'Trips', icon: 'trips' }, { id: 'impact', label: 'Impact', icon: 'leaf' }, { id: 'profile', label: 'You', icon: 'profile' }];
const CATEGORIES: Category[] = ['Economy', 'Electric', 'Comfort'];
const DEFAULT_SEARCH: Search = { originId: 'hinjawadi', destinationId: 'shivajinagar', seats: 1, service: 'shared' };

export default function App() { return <SafeAreaProvider><PlatoRide /></SafeAreaProvider>; }
function PlatoRide() {
  const [state, setState] = useState<DemoState>(initialState);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [tab, setTab] = useState<Tab>('ride');
  const [mode, setMode] = useState<'find' | 'offer'>('find');
  const [search, setSearch] = useState<Search>(DEFAULT_SEARCH);
  const [searched, setSearched] = useState(false);
  const [category, setCategory] = useState<'All' | Category>('All');
  const [picker, setPicker] = useState<'originId' | 'destinationId' | null>(null);
  const [locationQuery, setLocationQuery] = useState('');
  const [review, setReview] = useState<Ride | null>(null);
  const [confirm, setConfirm] = useState<Confirm | null>(null);
  const [notice, setNotice] = useState<{ message: string; error?: boolean } | null>(null);
  const [vehicle, setVehicle] = useState('Maruti Swift · White');
  const [fare, setFare] = useState('99');
  const [offerCategory, setOfferCategory] = useState<Category>('Economy');
  const [departureMinutes, setDepartureMinutes] = useState(30);
  const [name, setName] = useState('Navnath');
  const [now, setNow] = useState(Date.now());
  const scrollRef = useRef<ScrollView>(null);
  useEffect(() => {
    demoRepository.load().then(saved => { setState(saved); setName(saved.name); setReady(true); }).catch(error => { setLoadError(error.message); setReady(true); });
    const interval = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => { scrollRef.current?.scrollTo({ y: 0, animated: false }); }, [tab, searched, mode]);
  async function mutate(update: (current: DemoState) => DemoState, success?: string): Promise<boolean> {
    if (lock.current) return false;
    lock.current = true; setBusy(true);
    try { const next = update(state); await demoRepository.save(next); setState(next); if (success) setNotice({ message: success }); return true; }
    catch (error) { setNotice({ message: error instanceof Error ? error.message : 'Could not save demo data. Please try again.', error: true }); return false; }
    finally { lock.current = false; setBusy(false); }
  }
  async function reset() {
    if (lock.current) return;
    lock.current = true; setBusy(true);
    try { const fresh = await demoRepository.reset(); setState(fresh); setName(fresh.name); setSearch(DEFAULT_SEARCH); setSearched(false); setMode('find'); setTab('ride'); setLoadError(''); setNotice({ message: 'Demo reset. Fresh sample rides are ready.' }); }
    catch { setNotice({ message: 'Unable to reset local storage. Please restart and try again.', error: true }); }
    finally { lock.current = false; setBusy(false); }
  }
  function openPicker(which: 'originId' | 'destinationId') { setLocationQuery(''); setPicker(which); }
  function doSearch() { try { validateSearch(search); setCategory('All'); setSearched(true); setNotice(null); } catch (error) { setNotice({ message: (error as Error).message, error: true }); } }
  function useRoute(originId: string, destinationId: string) { setSearch({ ...search, originId, destinationId }); setSearched(false); }
  function changeTab(value: Tab) { setTab(value); setNotice(null); }
  function cancelTrip(booking: Booking) { setConfirm({ title: 'Cancel this demo trip?', message: 'Your reserved seats will be released. No money was charged and no cancellation fee applies in this demo.', action: 'Cancel demo trip', destructive: true, run: () => { void mutate(s => transitionBooking(s, booking.id, 'cancelled'), 'Demo trip cancelled. Seats released.'); } }); }
  const active = activeBooking(state);
  const history = state.bookings.filter(b => ['completed', 'cancelled'].includes(b.status));
  const completed = history.filter(b => b.status === 'completed');
  const offers = state.rides.filter(r => r.owned && !r.cancelled);
  let results: Ride[] = [];
  try { results = searchRides(state, search, now).filter(r => category === 'All' || r.category === category); } catch { /* Shown on submit. */ }

  return <SafeAreaView style={s.safe} edges={['top', 'left', 'right']}>
    <StatusBar barStyle="dark-content" backgroundColor={C.bg} />
    <View style={s.shell}>
      <View style={s.header}><View style={u.row}><View style={s.logo}><Icon name="leaf" size={24} color={C.lime} /></View><Text style={s.wordmark}>Plato<Text style={{ fontWeight: '400' }}>-Ride</Text><Text style={{ color: C.green }}>.</Text></Text></View><View style={s.city}><View style={s.cityDot} /><Text style={s.cityText}>PUNE · DEMO</Text></View></View>
      {!ready ? <View style={s.loading}><ActivityIndicator color={C.green} size="large" /><Body>Getting your demo ready…</Body></View> : loadError ? <View style={s.loading}><Icon name="trips" size={42} /><Text style={s.h2}>Let’s start fresh</Text><Body style={{ textAlign: 'center' }}>{loadError}</Body><Button disabled={busy} onPress={() => void reset()}>Reset local demo data</Button></View> : <>
        {notice && <View accessibilityLiveRegion="polite" style={[s.notice, notice.error && s.noticeError]}><Text style={[s.noticeText, notice.error && { color: C.red }]}>{notice.message}</Text><Pressable accessibilityRole="button" accessibilityLabel="Dismiss message" onPress={() => setNotice(null)} style={s.dismiss}><Icon name="close" color={notice.error ? C.red : C.ink} size={18} /></Pressable></View>}
        <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}><ScrollView ref={scrollRef} style={s.flex} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          {tab === 'ride' && <>
            {!searched && <>
              <View style={s.titleBlock}><Eyebrow>LESS TRAFFIC. MORE LIFE.</Eyebrow><Text style={s.h1}>Where to,{'\n'}{state.name.split(' ')[0]}<Text style={{ color: C.green }}>?</Text></Text><Body>A shared journey. A greener Pune.</Body></View>
              <View style={s.segment}>{(['find', 'offer'] as const).map(item => <Pressable key={item} accessibilityRole="button" accessibilityState={{ selected: mode === item }} onPress={() => { setMode(item); setNotice(null); }} style={[s.segmentItem, mode === item && s.segmentActive]}><Icon name={item === 'find' ? 'car' : 'plus'} size={18} color={mode === item ? C.white : C.muted} /><Text style={[s.segmentText, mode === item && { color: C.white }]}>{item === 'find' ? 'Find a ride' : 'Offer seats'}</Text></Pressable>)}</View>
              {mode === 'find' && <View style={s.serviceRow}>{(['shared', 'cab'] as const).map(service => <Pressable accessibilityRole="button" accessibilityState={{ selected: service === search.service }} key={service} onPress={() => setSearch({ ...search, service })} style={[s.serviceCard, search.service === service && s.serviceSelected]}><Icon name={service === 'shared' ? 'people' : 'car'} size={24} /><Text style={s.serviceTitle}>{service === 'shared' ? 'Shared ride' : 'Private cab'}</Text><Body style={{ fontSize: 11 }}>{service === 'shared' ? 'Pay per seat' : 'One fare, whole car'}</Body></Pressable>)}</View>}
              {mode === 'find' && <MapPreview from={findLocation(search.originId).name} to={findLocation(search.destinationId).name} />}
              <Card style={{ gap: 18 }}>
                <View style={s.routeForm}><View style={s.routeRail}><View style={s.pickupDot} /><View style={s.routeLine} /><View style={s.destinationDot} /></View><View style={s.flex}><Pressable accessibilityRole="button" accessibilityLabel={`Pickup: ${findLocation(search.originId).name}. Change pickup`} onPress={() => openPicker('originId')} style={s.locationField}><Eyebrow>Pickup</Eyebrow><Text style={s.locationName}>{findLocation(search.originId).name}</Text></Pressable><View style={s.hairline} /><Pressable accessibilityRole="button" accessibilityLabel={`Destination: ${findLocation(search.destinationId).name}. Change destination`} onPress={() => openPicker('destinationId')} style={s.locationField}><Eyebrow>Destination</Eyebrow><Text style={s.locationName}>{findLocation(search.destinationId).name}</Text></Pressable></View><Pressable accessibilityRole="button" accessibilityLabel="Swap pickup and destination" onPress={() => setSearch({ ...search, originId: search.destinationId, destinationId: search.originId })} style={s.swap}><Icon name="swap" size={19} /></Pressable></View>
                <View style={s.hairline} /><Stepper value={search.seats} onChange={seats => setSearch({ ...search, seats })} label={mode === 'offer' ? 'Seats to offer' : search.service === 'cab' ? 'Passengers' : 'Seats to book'} />
                {mode === 'find' ? <><View style={s.smallNote}><Icon name="clock" size={16} color={C.muted} /><Body style={{ fontSize: 12 }}>Upcoming rides · Sample fares in INR</Body></View><Button onPress={doSearch} icon="arrow">{search.service === 'shared' ? 'Find shared rides' : 'Find a private cab'}</Button></> : <>
                  <View style={s.hairline} /><Field label="Your vehicle"><TextInput accessibilityLabel="Vehicle model and colour" value={vehicle} onChangeText={setVehicle} maxLength={60} placeholder="Model and colour" placeholderTextColor={C.muted} style={s.input} /></Field>
                  <Field label="Ride type"><View style={s.wrap}>{CATEGORIES.map(c => <Chip key={c} active={c === offerCategory} onPress={() => setOfferCategory(c)}>{c}</Chip>)}</View></Field>
                  <Field label="Departure from now"><View style={s.wrap}>{[15, 30, 60, 120].map(minutes => <Chip key={minutes} active={minutes === departureMinutes} onPress={() => setDepartureMinutes(minutes)}>{minutes < 60 ? `${minutes} min` : `${minutes / 60} hour${minutes > 60 ? 's' : ''}`}</Chip>)}</View></Field>
                  <Field label="Fare per seat (₹)"><TextInput accessibilityLabel="Fare per seat in rupees" value={fare} onChangeText={setFare} keyboardType="number-pad" maxLength={4} style={s.input} /><Body style={{ fontSize: 12 }}>₹20–₹2,000 · For demonstration only</Body></Field>
                  <Button disabled={busy} icon="plus" onPress={async () => { const success = await mutate(s => offerRide(s, { ...search, service: 'shared', vehicle, category: offerCategory, farePerSeat: Number(fare), departureMinutes }), 'Your demo offer is published on this device.'); if (success) setTab('trips'); }}>{busy ? 'Saving…' : 'Publish demo offer'}</Button><Body style={s.finePrint}>Shared seats, visible only on this device. Driver identity, vehicle checks and commercial operations are not active.</Body>
                </>}
              </Card>
              {mode === 'find' && <>{active && <Pressable accessibilityRole="button" onPress={() => setTab('trips')} style={s.activeBanner}><View style={s.activeDot} /><View style={s.flex}><Text style={s.activeTitle}>You have a demo trip</Text><Body style={{ fontSize: 12 }}>{tripLabel[active.status]} · Tap to continue</Body></View><Icon name="chevron" size={18} /></Pressable>}<View style={s.sectionHeading}><Text style={s.h3}>Popular demo routes</Text><Eyebrow>PUNE</Eyebrow></View><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 10 }}>{[['hinjawadi', 'shivajinagar'], ['kharadi', 'viman-nagar'], ['wakad', 'baner']].map(([from, to]) => <Pressable key={from} accessibilityRole="button" accessibilityLabel={`Use route ${findLocation(from).name} to ${findLocation(to).name}`} onPress={() => useRoute(from, to)} style={s.quickRoute}><View style={s.quickIcon}><Icon name="arrow" size={19} /></View><Text style={s.quickFrom}>{findLocation(from).name}</Text><Text style={s.quickTo}>to {findLocation(to).name}</Text></Pressable>)}</ScrollView></>}
              <Pressable accessibilityRole="button" accessibilityLabel="Read our 50 percent profit commitment" onPress={() => setTab('impact')} style={s.missionCard}><View style={s.missionIcon}><Icon name="leaf" color={C.lime} size={28} /></View><View style={s.flex}><Text style={s.missionTitle}>Your commute. A bigger purpose.</Text><Text style={s.missionBody}>50% of future profits pledged to planting and caring for city trees.</Text></View><Icon name="arrow" color={C.lime} size={18} /></Pressable><Body style={s.footerNote}>Working product demo · No real rides or charges</Body>
            </>}
            {searched && <>
              <Pressable accessibilityRole="button" onPress={() => setSearched(false)} style={s.back}><Icon name="back" size={20} /><Text style={s.backText}>Edit journey</Text></Pressable><View style={s.titleBlock}><Eyebrow>{search.service === 'shared' ? 'FIND YOUR PEOPLE. SHARE THE WAY.' : 'YOUR SPACE. YOUR JOURNEY.'}</Eyebrow><Text style={s.h1}>{search.service === 'shared' ? 'Let’s ride\ntogether.' : 'A cab,\njust for you.'}</Text></View>
              <Card><RouteSummary ride={search} /><View style={s.smallNote}><Icon name="people" size={16} color={C.muted} /><Body style={{ fontSize: 12 }}>{search.seats} {search.service === 'cab' ? 'passenger' : 'seat'}{search.seats > 1 ? 's' : ''} · {search.service === 'cab' ? 'Whole-car fare' : 'Shared ride'}</Body></View></Card>
              <MapPreview from={findLocation(search.originId).name} to={findLocation(search.destinationId).name} /><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>{(['All', ...CATEGORIES] as const).map(c => <Chip key={c} active={category === c} onPress={() => setCategory(c)}>{c === 'All' ? 'All rides' : c}</Chip>)}</ScrollView><View style={s.sectionHeading}><Text style={s.h3}>{results.length} ride{results.length !== 1 ? 's' : ''} available</Text><Body style={{ fontSize: 12 }}>Lowest fare first</Body></View>
              {results.length ? results.map(ride => <RideCard key={ride.id} ride={ride} seats={search.seats} now={now} onPress={() => setReview(ride)} />) : <Card style={{ alignItems: 'center', paddingVertical: 30 }}><Icon name="car" size={42} /><Text style={s.h3}>No matching rides yet</Text><Body style={{ textAlign: 'center' }}>Try another route, type or seat count. Sample routes start with Hinjawadi to Shivajinagar. Reset the demo in You if departures have passed.</Body><Button variant="secondary" onPress={() => setSearched(false)}>Change journey</Button></Card>}<Body style={s.footerNote}>Sample people, vehicles and fares. Offers you create are visible only on this device.</Body>
            </>}
          </>}
          {tab === 'trips' && <>
            <View style={s.titleBlock}><Eyebrow>YOUR JOURNEYS, TOGETHER</Eyebrow><Text style={s.h1}>My trips.</Text><Body>Your bookings and offered seats, saved on this device.</Body></View>
            {active ? <Card>
              <View style={s.statusPill}><Text style={s.statusText}>{tripLabel[active.status]} · Demo</Text></View>
              <RouteSummary ride={active.ride} /><Driver ride={active.ride} />
              <View style={s.totalRow}><Body>{active.seats} passenger{active.seats > 1 ? 's' : ''} · {active.ride.service === 'cab' ? 'Private cab' : 'Shared ride'}</Body><Text style={s.price}>{money(active.total)}</Text></View>
              <Body style={{ fontSize: 12 }}>Departure {formatTime(active.ride.departureAt)} · {active.id}</Body>
              <View style={s.progress}>{(['reserved','arriving','in_progress','completed'] as const).map((stage,index) => <View key={stage} style={s.progressItem}><View style={[s.progressBar,index <= ['reserved','arriving','in_progress','completed'].indexOf(active.status) && { backgroundColor:C.green }]} /><Text style={s.progressLabel}>{['Reserved','At pickup','On the way','Complete'][index]}</Text></View>)}</View>
              <Body style={s.finePrint}>Demo only: tap below to move to the next stage. No driver is dispatched and no location is tracked.</Body>
              <Button disabled={busy} onPress={() => { const next=nextStatus[active.status]; if(next) void mutate(current => transitionBooking(current,active.id,next),'Demo trip stage updated.'); }}>{nextLabel[active.status]}</Button>
              {['reserved','arriving'].includes(active.status) && <Button variant="secondary" disabled={busy} onPress={() => cancelTrip(active)}>Cancel demo booking</Button>}
            </Card> : <Card><Icon name="trips" size={32} /><Text style={s.h3}>Your next journey awaits.</Text><Body>Find a shared seat or book a sample private cab.</Body><Button onPress={() => {setTab('ride');setSearched(false);}}>Find a ride</Button></Card>}
            <Text style={s.h3}>Your seat offers</Text>
            {offers.length ? offers.map(ride => <Card key={ride.id}><View style={s.statusPill}><Text style={s.statusText}>Your local offer</Text></View><RouteSummary ride={ride} /><Body>{ride.vehicle} · {ride.seatsAvailable} seats · {money(ride.farePerSeat)} per seat</Body><Body>Departure {formatTime(ride.departureAt)}</Body><Button variant="secondary" disabled={busy} onPress={() => setConfirm({title:'Remove your offer?',message:'This removes your local sample journey. No other person has booked it.',action:'Remove offer',run:()=>{void mutate(current => removeOffer(current,ride.id),'Demo offer removed.');}})}>Remove offer</Button></Card>) : <Body>No offered rides yet. Share spare seats from the Ride tab.</Body>}
            <Text style={s.h3}>Past journeys</Text>
            {history.length ? history.map(booking => <Card key={booking.id}><View style={s.sectionHeading}><View style={s.statusPill}><Text style={s.statusText}>{tripLabel[booking.status]} · Demo</Text></View><Text style={s.driverName}>{money(booking.total)}</Text></View><Text style={s.driverName}>{findLocation(booking.ride.originId).name} → {findLocation(booking.ride.destinationId).name}</Text><Body>{booking.ride.service==='cab'?'Private cab':'Shared ride'} · {booking.seats} passenger{booking.seats>1?'s':''}</Body><Body style={{fontSize:12}}>{booking.id} · No payment taken</Body></Card>) : <Body>Completed and cancelled bookings will appear here.</Body>}
          </>}
          {tab === 'impact' && <>
            <View style={s.titleBlock}><Eyebrow>ROOTED IN RESPONSIBILITY</Eyebrow><Text style={s.h1}>{'A promise\nworth growing.'}</Text><Body>Your everyday journey, with a bigger purpose.</Body></View>
            <View style={s.impactCard}><Eyebrow color={C.lime}>OUR PLANNED COMMITMENT</Eyebrow><Text style={s.impactNumber}>50%</Text><Text style={s.impactTitle}>{'of Plato-Ride’s profits\nfor a greener city.'}</Text><Text style={s.impactText}>Our commitment covers planting, irrigation, and ongoing care for city trees. It applies to profits after expenses, not 50% of each fare.</Text></View>
            <Card><Text style={s.h3}>From promise to proof.</Text>{[['Plant with purpose','Work with local partners on suitable sites and species.'],['Keep caring','Fund irrigation, maintenance, and survival monitoring.'],['Show the evidence','Report allocations and outcomes backed by partner records.']].map(([title,text])=><View key={title} style={{gap:5}}><Text style={s.driverName}>{title}</Text><Body>{text}</Body></View>)}</Card>
            <Card><View style={s.sectionHeading}><Text style={s.h3}>Your demo journeys</Text><Text style={s.price}>{completed.length}</Text></View><Body>Completed sample trips on this device. Demo journeys do not generate real revenue or environmental impact.</Body></Card>
            <Body style={s.finePrint}>Plato-Ride is in development. No profit allocations, planted trees, or emissions savings have been verified.</Body><Body style={{fontStyle:'italic'}}>“Protecting our Mother Earth is our responsibility. Let’s cherish and preserve her beauty together.”</Body><Eyebrow>Navnath Sonawane · IT Engineer, Pune</Eyebrow>
          </>}
          {tab === 'profile' && <>
            <View style={s.titleBlock}><Eyebrow>YOUR PLATO-RIDE SPACE</Eyebrow><Text style={s.h1}>Hello, {state.name.split(' ')[0]}.</Text><Body>Your local demo profile.</Body></View>
            <Card><View style={s.profileAvatar}><Text style={s.profileInitial}>{state.name.slice(0,2).toUpperCase()}</Text></View><Field label="Display name"><TextInput style={s.input} value={name} onChangeText={setName} maxLength={40} accessibilityLabel="Display name" autoCapitalize="words" /></Field><Button disabled={busy} variant="secondary" onPress={() => {if(name.trim().length<2){setNotice({message:'Enter a display name with at least 2 characters.',error:true});return;} void mutate(current=>({...current,name:name.trim()}),'Display name saved on this device.');}}>Save display name</Button>{[['Home city','Pune'],['Account','Local demo · no sign-in'],['Payments','Not connected'],['Services','Shared rides & private cabs']].map(([label,value])=><View key={label} style={s.profileRow}><Text style={s.profileLabel}>{label}</Text><Text style={s.profileValue}>{value}</Text></View>)}</Card>
            <Card><Text style={s.h3}>Made for exploration.</Text><Body>Sample rides, bookings and seat offers stay on this device. No data is sent to a booking service or synced with the website. Google Maps supplies an embedded Pune overview and external route directions. Identity checks, live driver tracking, payments, notifications and emergency support are not connected.</Body><Button variant="danger" disabled={busy} onPress={() => setConfirm({title:'Reset your demo?',message:'This clears your local sample bookings and seat offers, and creates fresh sample departures.',action:'Reset demo',destructive:true,run:()=>{void reset();}})}>Reset demo data</Button></Card>
            <Body style={s.footerNote}>Plato-Ride · Version 0.1.0 · Development demo</Body>
          </>}
          <View style={{ height: 12 }} />
        </ScrollView></KeyboardAvoidingView>
        <SafeAreaView edges={['bottom']} style={s.tabsSafe}><View style={s.tabs} accessibilityRole="tablist">{TABS.map(item => <Pressable key={item.id} accessibilityRole="tab" accessibilityLabel={item.label} accessibilityState={{ selected: tab === item.id }} onPress={() => changeTab(item.id)} style={s.tab}><View style={[s.tabIcon, tab === item.id && s.tabIconActive]}><Icon name={item.icon} size={22} color={tab === item.id ? C.ink : C.muted} />{item.id === 'trips' && active && <View style={s.tabDot} />}</View><Text style={[s.tabLabel, tab === item.id && s.tabLabelActive]}>{item.label}</Text></Pressable>)}</View></SafeAreaView>
      </>}
    </View>
    <Modal visible={picker!==null} transparent animationType="slide" onRequestClose={()=>setPicker(null)}>
      <View style={s.modalOverlay}><SafeAreaView style={s.modalSheet} edges={['bottom']}><View style={s.modalHeader}><Text style={s.h2}>{picker==='originId'?'Choose pickup':'Choose destination'}</Text><Pressable style={s.close} accessibilityRole="button" accessibilityLabel="Close location picker" onPress={()=>setPicker(null)}><Icon name="close" /></Pressable></View><TextInput autoFocus accessibilityLabel="Search Pune areas" placeholder="Search Pune areas" placeholderTextColor={C.muted} value={locationQuery} onChangeText={setLocationQuery} style={s.input} /><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{paddingBottom:20}}>{LOCATIONS.filter(l=>(l.name+' '+l.area).toLowerCase().includes(locationQuery.toLowerCase())).map(location=><Pressable key={location.id} style={s.locationOption} accessibilityRole="button" accessibilityLabel={location.name} onPress={()=>{if(picker)setSearch({...search,[picker]:location.id});setPicker(null);setSearched(false);}}><Text style={s.driverName}>{location.name}</Text><Body style={{fontSize:12}}>{location.area}</Body></Pressable>)}{!LOCATIONS.some(l=>(l.name+' '+l.area).toLowerCase().includes(locationQuery.toLowerCase()))&&<Body>No matching Pune areas. Try a shorter name.</Body>}</ScrollView></SafeAreaView></View>
    </Modal>
    <Modal visible={review!==null} transparent animationType="slide" onRequestClose={()=>setReview(null)}>
      <View style={s.modalOverlay}><SafeAreaView style={s.modalSheet} edges={['bottom']}><View style={s.modalHeader}><Text style={s.h2}>Review your ride</Text><Pressable style={s.close} accessibilityRole="button" accessibilityLabel="Close booking review" onPress={()=>setReview(null)}><Icon name="close" /></Pressable></View>{review&&<ScrollView contentContainerStyle={s.modalScroll}><View style={s.statusPill}><Text style={s.statusText}>{review.service==='cab'?'Private cab':'Shared ride'} · Demo</Text></View><RouteSummary ride={review} /><Driver ride={review} /><Body>Departure {formatTime(review.departureAt)} · {search.seats} passenger{search.seats>1?'s':''}</Body><View style={s.hairline}/><View style={s.totalRow}><Body>{review.service==='cab'?'Whole-car fare':`${money(review.farePerSeat)} × ${search.seats} seats`}</Body><Text style={s.driverName}>{money(rideTotal(review,search.seats))}</Text></View><View style={s.totalRow}><Body>Demo platform fee</Body><Text style={s.driverName}>₹0</Text></View><View style={s.totalRow}><Text style={s.h3}>Sample total</Text><Text style={s.price}>{money(rideTotal(review,search.seats))}</Text></View><Body>No payment will be taken. This is a local sample booking; no real ride or driver is arranged.</Body>{notice?.error&&<Body style={{color:C.red}}>{notice.message}</Body>}<Button disabled={busy} onPress={async()=>{const success=await mutate(current=>bookRide(current,review.id,search.seats),'Demo booking confirmed. No payment taken.');if(success){setReview(null);setTab('trips');}}}>{busy?'Saving…':'Confirm demo booking'}</Button></ScrollView>}</SafeAreaView></View>
    </Modal>
    <Modal visible={confirm!==null} transparent animationType="fade" onRequestClose={()=>setConfirm(null)}><View style={s.modalOverlay}><SafeAreaView style={s.modalSheet} edges={['bottom']}><Text style={s.h2}>{confirm?.title}</Text><Body>{confirm?.message}</Body><Button variant={confirm?.destructive?'danger':'primary'} onPress={()=>{confirm?.run();setConfirm(null);}}>{confirm?.action}</Button><Button variant="secondary" onPress={()=>setConfirm(null)}>Go back</Button></SafeAreaView></View></Modal>
  </SafeAreaView>;
}
function formatTime(value: string) { return new Date(value).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata' }); }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <View style={{ gap: 8 }}><Text style={u.label}>{label}</Text>{children}</View>; }
function RouteSummary({ ride }: { ride: { originId: string; destinationId: string } }) { return <View style={s.summary}><View style={s.summaryRail}><View style={s.pickupDot} /><View style={s.summaryLine} /><View style={s.destinationDot} /></View><View style={{ gap: 20, flex: 1 }}><View><Eyebrow>Pickup</Eyebrow><Text style={s.locationName}>{findLocation(ride.originId).name}</Text></View><View><Eyebrow>Destination</Eyebrow><Text style={s.locationName}>{findLocation(ride.destinationId).name}</Text></View></View></View>; }
function Driver({ ride }: { ride: Ride }) { return <View style={u.row}><View style={[s.avatar, ride.category === 'Electric' && { backgroundColor: '#DDEDD3' }]}><Text style={s.avatarText}>{ride.driverName.split(' ').map(n => n[0]).slice(0, 2).join('')}</Text></View><View style={s.flex}><Text style={s.driverName}>{ride.driverName}</Text><Body style={{ fontSize: 12 }}>{ride.vehicle}</Body></View><View style={s.sampleLabel}><Text style={s.sampleLabelText}>{ride.owned ? 'YOU' : 'SAMPLE'}</Text></View></View>; }
function RideCard({ ride, seats, onPress, now }: { ride: Ride; seats: number; onPress: () => void; now: number }) { return <Card><View style={s.sectionHeading}><View style={s.rideType}><Icon name={ride.category === 'Electric' ? 'leaf' : 'car'} size={18} color={C.green} /><Text style={s.rideTypeText}>{ride.category}</Text></View><View style={s.fareBlock}><Text style={s.price}>{money(rideTotal(ride, seats))}</Text><Text style={s.perSeat}>{ride.service === 'cab' ? 'whole car' : `for ${seats} seat${seats > 1 ? 's' : ''}`}</Text></View></View><Driver ride={ride} /><View style={s.hairline} /><View style={s.rideMeta}><View style={s.smallNote}><Icon name="clock" size={16} color={C.muted} /><Body style={{ fontSize: 12 }}>{Math.max(1, Math.ceil((Date.parse(ride.departureAt) - now) / 60_000))} min to departure</Body></View><View style={s.smallNote}><Icon name="people" size={16} color={C.muted} /><Body style={{ fontSize: 12 }}>{ride.service === 'cab' ? 'Up to ' : ''}{ride.seatsAvailable} seats</Body></View></View><Button disabled={ride.owned} variant="secondary" onPress={onPress} icon={ride.owned ? undefined : 'arrow'}>{ride.owned ? 'Your local offer' : 'Review ride'}</Button></Card>; }
