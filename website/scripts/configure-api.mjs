import {writeFileSync} from 'node:fs';
const apiUrl=(process.env.PLANTO_API_URL||'').trim().replace(/\/$/,'');
if(apiUrl){const u=new URL(apiUrl);if(u.username||u.password||u.search||u.hash||(!['127.0.0.1','localhost'].includes(u.hostname)&&u.protocol!=='https:'))throw Error('Use a public HTTPS API URL without credentials, query or fragment.');}
writeFileSync(new URL('../dist/config.js',import.meta.url),'window.PLANTO_CONFIG='+JSON.stringify({apiUrl})+';\n');
