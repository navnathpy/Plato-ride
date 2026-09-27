import AsyncStorage from '@react-native-async-storage/async-storage';
import { DemoState, initialState, LOCATIONS } from './domain';

const KEY = '@platoride/demo/v1';
const locationIds = new Set(LOCATIONS.map(l => l.id));

// Boundary check: corrupted or obsolete storage must never become trusted app state.
function isState(value: unknown): value is DemoState {
  if (!value || typeof value !== 'object') return false;
  const s = value as DemoState;
  if (s.version !== 1 || typeof s.name !== 'string' || !Array.isArray(s.rides) || !Array.isArray(s.bookings)) return false;
  return s.rides.every(r => r && typeof r.id === 'string' && locationIds.has(r.originId) && locationIds.has(r.destinationId) && Number.isFinite(r.farePerSeat) && Number.isInteger(r.seatsAvailable) && r.seatsAvailable >= 0 && Number.isFinite(Date.parse(r.departureAt)))
    && s.bookings.every(b => b && typeof b.id === 'string' && b.ride && locationIds.has(b.ride.originId) && locationIds.has(b.ride.destinationId) && Number.isFinite(b.total) && Number.isInteger(b.seats) && ['reserved', 'arriving', 'in_progress', 'completed', 'cancelled'].includes(b.status));
}

export const demoRepository = {
  async load(): Promise<DemoState> {
    const raw = await AsyncStorage.getItem(KEY);
    if (raw === null) return initialState();
    let parsed: unknown;
    try { parsed = JSON.parse(raw); } catch { throw new Error('Saved demo data could not be read. Reset local data to start again.'); }
    if (!isState(parsed)) throw new Error('Saved demo data uses an unsupported format. Reset local data to start again.');
    return parsed;
  },
  async save(state: DemoState): Promise<void> { await AsyncStorage.setItem(KEY, JSON.stringify(state)); },
  async reset(): Promise<DemoState> {
    const fresh = initialState();
    await AsyncStorage.setItem(KEY, JSON.stringify(fresh));
    return fresh;
  },
};
