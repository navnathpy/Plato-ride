import {writeFileSync} from 'node:fs';
const key=(process.env.MAPS_EMBED_KEY||'').trim();
// This is a client-visible, domain-restricted Maps Embed key, never a server secret.
writeFileSync(new URL('../dist/maps-config.js',import.meta.url),'window.PLANTO_MAPS = '+JSON.stringify({embedApiKey:key})+';\n');
console.log(key?'Restricted Maps Embed key configured.':'Using the official key-free Pune city embed.');
