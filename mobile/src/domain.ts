export type Location = { id: string; name: string; area: string };
export const LOCATIONS: Location[] = [
  { id: 'hinjawadi', name: 'Hinjawadi Phase 1', area: 'IT Park · West Pune' },
  { id: 'wakad', name: 'Wakad', area: 'Bhumkar Chowk · West Pune' },
  { id: 'baner', name: 'Baner', area: 'High Street · West Pune' },
  { id: 'aundh', name: 'Aundh', area: 'Parihar Chowk · West Pune' },
  { id: 'shivajinagar', name: 'Shivajinagar', area: 'Central Pune' },
  { id: 'pune-station', name: 'Pune Railway Station', area: 'Station Road · Central Pune' },
  { id: 'viman-nagar', name: 'Viman Nagar', area: 'Phoenix Marketcity · East Pune' },
  { id: 'kharadi', name: 'Kharadi', area: 'EON IT Park · East Pune' },
  { id: 'magarpatta', name: 'Magarpatta', area: 'Cybercity · East Pune' },
  { id: 'hadapsar', name: 'Hadapsar', area: 'Gadital · East Pune' },
  { id: 'swargate', name: 'Swargate', area: 'Bus terminal · South Pune' },
  { id: 'kothrud', name: 'Kothrud', area: 'Karve Road · West Pune' },
];
export type Category = 'Economy' | 'Comfort' | 'Electric';
export type Service = 'shared' | 'cab';
export type Ride = {
  id: string; originId: string; destinationId: string; driverName: string;
  vehicle: string; category: Category; farePerSeat: number; fareTotal?: number; service: Service; seatsAvailable: number;
  departureAt: string; owned: boolean; cancelled: boolean;
};
export type TripStatus = 'reserved' | 'arriving' | 'in_progress' | 'completed' | 'cancelled';
export type Booking = {
  id: string; rideId: string; ride: Ride; seats: number; reservedSeats: number; total: number;
  status: TripStatus; createdAt: string;
};
export type DemoState = { version: 1; name: string; rides: Ride[]; bookings: Booking[] };
export type Search = { originId: string; destinationId: string; seats: number; service: Service };
export type OfferInput = Search & { vehicle: string; category: Category; farePerSeat: number; departureMinutes: number };

export const findLocation = (id: string) => LOCATIONS.find(location => location.id === id)!;
export const money = (n: number) => `₹${n.toLocaleString('en-IN')}`;
export const rideTotal = (ride: Ride, passengers: number) => ride.service === 'cab' ? ride.fareTotal! : passengers * ride.farePerSeat;
export const activeBooking = (state: DemoState) => state.bookings.find(b => !['completed', 'cancelled'].includes(b.status));
export const tripLabel: Record<TripStatus, string> = {
  reserved: 'Booking reserved', arriving: 'Driver at pickup', in_progress: 'Trip in progress', completed: 'Completed', cancelled: 'Cancelled',
};
export const nextStatus: Partial<Record<TripStatus, TripStatus>> = { reserved: 'arriving', arriving: 'in_progress', in_progress: 'completed' };
export const nextLabel: Partial<Record<TripStatus, string>> = { reserved: 'Simulate driver arrival', arriving: 'Simulate trip start', in_progress: 'Simulate completion' };

export function seedRides(now = Date.now()): Ride[] {
  const routes = [
    ['hinjawadi', 'shivajinagar'], ['wakad', 'baner'], ['kharadi', 'viman-nagar'],
    ['baner', 'hinjawadi'], ['pune-station', 'kharadi'], ['kothrud', 'shivajinagar'],
    ['shivajinagar', 'hinjawadi'], ['viman-nagar', 'kharadi'],
  ];
  const shared = routes.flatMap(([originId, destinationId], routeIndex) => [
    { driverName: 'Aarav S.', vehicle: 'Maruti Swift · White', category: 'Economy' as const, farePerSeat: 89, seatsAvailable: 3, minutes: 15 },
    { driverName: 'Priya M.', vehicle: 'Tata Nexon EV · Teal', category: 'Electric' as const, farePerSeat: 119, seatsAvailable: 2, minutes: 30 },
    { driverName: 'Sahil K.', vehicle: 'Maruti Ertiga · Silver', category: 'Comfort' as const, farePerSeat: 139, seatsAvailable: 4, minutes: 45 },
  ].map((r, index) => ({
    ...r, id: `sample-${routeIndex}-${index}`, originId, destinationId,
    farePerSeat: r.farePerSeat + routeIndex * 5,
    departureAt: new Date(now + r.minutes * 60_000).toISOString(), owned: false, cancelled: false, service: 'shared' as const,
  })));
  return [...shared, ...shared.map((ride, index) => ({ ...ride, id: ride.id.replace('sample-', 'cab-'), driverName: ['Rohan D.', 'Isha P.', 'Aditya N.'][index % 3], service: 'cab' as const, fareTotal: ride.farePerSeat * 3 + 30, seatsAvailable: 4 }))];
}
export function initialState(now = Date.now()): DemoState {
  return { version: 1, name: 'Navnath', rides: seedRides(now), bookings: [] };
}
export function validateSearch(search: Search) {
  if (!['shared', 'cab'].includes(search.service)) throw new Error('Choose a shared ride or private cab.');
  if (!LOCATIONS.some(l => l.id === search.originId) || !LOCATIONS.some(l => l.id === search.destinationId)) throw new Error('Choose a Pune pickup and destination.');
  if (search.originId === search.destinationId) throw new Error('Choose a destination different from your pickup.');
  if (!Number.isInteger(search.seats) || search.seats < 1 || search.seats > 4) throw new Error('Choose between 1 and 4 seats.');
}
export function searchRides(state: DemoState, search: Search, now = Date.now()): Ride[] {
  validateSearch(search);
  return state.rides.filter(r => !r.cancelled && r.service === search.service && r.originId === search.originId && r.destinationId === search.destinationId && r.seatsAvailable >= search.seats && Date.parse(r.departureAt) > now).sort((a, b) => rideTotal(a, search.seats) - rideTotal(b, search.seats));
}
export function bookRide(state: DemoState, rideId: string, seats: number, now = Date.now()): DemoState {
  if (activeBooking(state)) throw new Error('Finish or cancel your active demo trip before booking another.');
  const ride = state.rides.find(r => r.id === rideId);
  if (!ride || ride.cancelled || Date.parse(ride.departureAt) <= now) throw new Error('This ride is no longer available. Try searching again.');
  if (ride.owned) throw new Error('This is your own ride offer. Choose a sample driver to try booking.');
  if (!Number.isInteger(seats) || seats < 1 || seats > 4 || ride.seatsAvailable < seats) throw new Error('There are not enough available seats.');
  const reservedSeats = ride.service === 'cab' ? ride.seatsAvailable : seats;
  const booking: Booking = { id: `PR-${now.toString(36).toUpperCase()}`, rideId, ride: { ...ride }, seats, reservedSeats, total: rideTotal(ride, seats), status: 'reserved', createdAt: new Date(now).toISOString() };
  return { ...state, rides: state.rides.map(r => r.id === rideId ? { ...r, seatsAvailable: r.seatsAvailable - reservedSeats } : r), bookings: [booking, ...state.bookings] };
}
export function transitionBooking(state: DemoState, id: string, status: TripStatus): DemoState {
  const booking = state.bookings.find(b => b.id === id);
  if (!booking) throw new Error('That trip was not found.');
  if (['completed', 'cancelled'].includes(booking.status)) throw new Error('This trip is already closed.');
  if (status === 'cancelled' && booking.status === 'in_progress') throw new Error('A trip that has started cannot be cancelled in this demo.');
  if (status !== 'cancelled' && nextStatus[booking.status] !== status) throw new Error('Trip steps must happen in order.');
  return {
    ...state,
    bookings: state.bookings.map(b => b.id === id ? { ...b, status } : b),
    rides: status === 'cancelled' ? state.rides.map(r => r.id === booking.rideId ? { ...r, seatsAvailable: r.seatsAvailable + booking.reservedSeats } : r) : state.rides,
  };
}
export function offerRide(state: DemoState, input: OfferInput, now = Date.now()): DemoState {
  validateSearch(input);
  if (!input.vehicle.trim() || input.vehicle.trim().length > 60) throw new Error('Add a vehicle description, up to 60 characters.');
  if (!Number.isInteger(input.farePerSeat) || input.farePerSeat < 20 || input.farePerSeat > 2000) throw new Error('Set a whole-rupee fare from ₹20 to ₹2,000.');
  if (!Number.isInteger(input.departureMinutes) || input.departureMinutes < 5 || input.departureMinutes > 1440) throw new Error('Choose a departure from 5 minutes to 24 hours from now.');
  const ride: Ride = {
    id: `offer-${now}`, originId: input.originId, destinationId: input.destinationId,
    driverName: state.name, vehicle: input.vehicle.trim(), category: input.category,
    farePerSeat: input.farePerSeat, seatsAvailable: input.seats,
    departureAt: new Date(now + input.departureMinutes * 60_000).toISOString(), owned: true, cancelled: false, service: 'shared',
  };
  return { ...state, rides: [ride, ...state.rides] };
}
export function removeOffer(state: DemoState, id: string): DemoState {
  const ride = state.rides.find(r => r.id === id);
  if (!ride?.owned) throw new Error('You can only remove your own offers.');
  return { ...state, rides: state.rides.map(r => r.id === id ? { ...r, cancelled: true } : r) };
}
