import React from 'react';
import { Pressable, StyleProp, StyleSheet, Text, TextStyle, View, ViewStyle } from 'react-native';
import Svg, { Circle, Path, Rect, G, Line } from 'react-native-svg';

export const C = { ink: '#103D2E', forest: '#123D2D', green: '#356A49', lime: '#D5F46B', bg: '#F6F7F1', white: '#FFFFFF', text: '#1E362B', muted: '#65736B', line: '#E1E7DE', pale: '#EAF0E2', red: '#9C3A2A' };
export type IconName = 'leaf' | 'car' | 'arrow' | 'pin' | 'clock' | 'people' | 'trips' | 'profile' | 'close' | 'chevron' | 'check' | 'swap' | 'plus' | 'minus' | 'back' | 'spark';

export function Icon({ name, size = 22, color = C.ink }: { name: IconName; size?: number; color?: string }) {
  const paths: Record<IconName, React.ReactNode> = {
    leaf: <><Path d="M19 4C8 2 3 8 6 15c3 6 12 3 13-11Z" /><Path d="m5 21 10-12M9 15v-5M10 15h5" /></>,
    car: <><Path d="m4 10 2-6h12l2 6M3 10h18v9H3zM6 19v2m12-2v2" /><Path d="M6 14h2m8 0h2" /></>,
    arrow: <><Path d="M4 12h16m-6-6 6 6-6 6" /></>,
    pin: <><Path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z" /><Circle cx="12" cy="10" r="2" /></>,
    clock: <><Circle cx="12" cy="12" r="9" /><Path d="M12 7v5l3 2" /></>,
    people: <><Circle cx="9" cy="8" r="3" /><Path d="M3 20v-2a6 6 0 0 1 12 0v2m1-16a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 4v2" /></>,
    trips: <><Rect x="5" y="4" width="14" height="17" rx="3" /><Path d="M9 3h6v3H9zM9 11h6m-6 5h6" /></>,
    profile: <><Circle cx="12" cy="8" r="4" /><Path d="M4 22v-2a8 8 0 0 1 16 0v2" /></>,
    close: <Path d="m6 6 12 12M6 18 18 6" />,
    chevron: <Path d="m9 5 7 7-7 7" />,
    check: <Path d="m5 12 4 4L19 6" />,
    swap: <><Path d="M8 3v17m-4-4 4 4 4-4M16 21V4m-4 4 4-4 4 4" /></>,
    plus: <Path d="M12 5v14M5 12h14" />,
    minus: <Path d="M5 12h14" />,
    back: <Path d="M20 12H4m6-6-6 6 6 6" />,
    spark: <Path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5Z" />,
  };
  return <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">{paths[name]}</Svg>;
}
export function Button({ children, onPress, variant = 'primary', disabled = false, icon, style, accessibilityLabel }: {
  children: React.ReactNode; onPress: () => void; variant?: 'primary' | 'secondary' | 'lime' | 'danger';
  disabled?: boolean; icon?: IconName; style?: StyleProp<ViewStyle>; accessibilityLabel?: string;
}) {
  const colors = { primary: [C.forest, C.white], secondary: [C.pale, C.ink], lime: [C.lime, C.ink], danger: ['#F7EAE5', C.red] };
  return <Pressable accessibilityRole="button" accessibilityLabel={accessibilityLabel} accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [u.button, { backgroundColor: colors[variant][0], opacity: disabled ? 0.42 : pressed ? 0.8 : 1 }, style]}>
    <Text style={[u.buttonText, { color: colors[variant][1] }]}>{children}</Text>{icon && <Icon name={icon} color={colors[variant][1]} size={20} />}
  </Pressable>;
}
export function Chip({ children, active, onPress }: { children: React.ReactNode; active?: boolean; onPress?: () => void }) {
  const content = <Text style={[u.chipText, active && { color: C.white }]}>{children}</Text>;
  return onPress ? <Pressable accessibilityRole="button" accessibilityState={{ selected: !!active }} onPress={onPress} style={[u.chip, active && { backgroundColor: C.forest }]}>{content}</Pressable> : <View style={[u.chip, active && { backgroundColor: C.forest }]}>{content}</View>;
}
export function Eyebrow({ children, color = C.muted }: { children: React.ReactNode; color?: string }) { return <Text style={[u.eyebrow, { color }]}>{children}</Text>; }
export function Body({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) { return <Text style={[u.body, style]}>{children}</Text>; }
export function Card({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) { return <View style={[u.card, style]}>{children}</View>; }
export function Stepper({ value, onChange, label = 'Seats' }: { value: number; onChange: (value: number) => void; label?: string }) {
  return <View style={u.row}><View style={{ flex: 1 }}><Text style={u.label}>{label}</Text><Body style={{ fontSize: 12 }}>{label === 'Seats to offer' ? 'Passenger seats, excluding driver' : 'Including your seat'}</Body></View><Pressable accessibilityRole="button" accessibilityLabel={`Decrease ${label.toLowerCase()}`} accessibilityState={{ disabled: value <= 1 }} disabled={value <= 1} onPress={() => onChange(value - 1)} style={[u.step, value <= 1 && { opacity: 0.35 }]}><Icon name="minus" size={18} /></Pressable><Text accessibilityLiveRegion="polite" style={u.stepValue}>{value}</Text><Pressable accessibilityRole="button" accessibilityLabel={`Increase ${label.toLowerCase()}`} accessibilityState={{ disabled: value >= 4 }} disabled={value >= 4} onPress={() => onChange(value + 1)} style={[u.step, value >= 4 && { opacity: 0.35 }]}><Icon name="plus" size={18} /></Pressable></View>;
}
export function RouteIllustration({ compact = false }: { compact?: boolean }) {
  return <Svg width="100%" height={compact ? 126 : 172} viewBox="0 0 330 172" accessibilityLabel="Illustration of a shared car passing city trees, not a live map" role="img">
    <G opacity="0.16" stroke="#A7C098" fill="none" strokeWidth="1"><Path d="M0 25h330M0 65h330M0 105h330M0 145h330M25 0v172M65 0v172M105 0v172M145 0v172M185 0v172M225 0v172M265 0v172M305 0v172" /></G>
    <Path d="M25 133h65c32 0 20-92 54-92h90c39 0 30 93 73 93" stroke="#719165" strokeWidth="18" fill="none" />
    <Path d="M25 133h65c32 0 20-92 54-92h90c39 0 30 93 73 93" stroke="#D5F46B" strokeWidth="2" strokeDasharray="5 6" fill="none" />
    <Circle cx="26" cy="133" r="9" fill="#D5F46B" /><Circle cx="26" cy="133" r="4" fill="#123D2D" /><Circle cx="306" cy="133" r="9" fill="#FFF" />
    <G transform="translate(150 20)"><Rect x="0" y="0" width="52" height="29" rx="9" fill="#D5F46B" /><Path d="M10 5h31l5 6H6z" fill="#123D2D" /><Rect x="-3" y="8" width="5" height="10" rx="2" fill="#B9D25E" /><Rect x="50" y="8" width="5" height="10" rx="2" fill="#B9D25E" /><Path d="M8 23h6m24 0h6" stroke="#123D2D" strokeWidth="3" /></G>
    <G fill="#5E8E61"><Circle cx="56" cy="46" r="21" /><Circle cx="280" cy="36" r="17" /><Circle cx="182" cy="128" r="25" /></G>
    <G stroke="#D5F46B" strokeWidth="2" fill="none"><Path d="M56 73V34m0 14-9-6m9 16 9-7M280 59V26m0 17-8-7M182 161v-46m0 16-11-8m11 20 12-9" /></G>
  </Svg>;
}
export const u = StyleSheet.create({
  button: { minHeight: 54, borderRadius: 17, paddingHorizontal: 20, paddingVertical: 14, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 10 },
  buttonText: { fontSize: 15, fontWeight: '700', letterSpacing: 0.1 },
  chip: { paddingHorizontal: 15, paddingVertical: 11, borderRadius: 30, backgroundColor: C.pale, minHeight: 44, justifyContent: 'center' },
  chipText: { fontSize: 12, fontWeight: '600', color: C.ink },
  eyebrow: { fontSize: 10, letterSpacing: 1.7, fontWeight: '700', textTransform: 'uppercase' },
  body: { fontSize: 14, lineHeight: 21, color: C.muted },
  card: { backgroundColor: C.white, borderRadius: 24, borderWidth: 1, borderColor: C.line, padding: 20, gap: 14 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  label: { fontSize: 15, color: C.ink, fontWeight: '600' },
  step: { width: 44, height: 44, borderRadius: 14, borderColor: C.line, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  stepValue: { minWidth: 22, textAlign: 'center', fontSize: 18, fontWeight: '700', color: C.ink },
});
