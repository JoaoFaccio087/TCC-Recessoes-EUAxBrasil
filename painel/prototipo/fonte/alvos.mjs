import fs from 'fs';
const V=process.argv[2];
const tj=await import(V+'/topojson-client/src/index.js');
const w=JSON.parse(fs.readFileSync(V+'/world-atlas/countries-50m.json'));
const f=tj.feature(w,w.objects.countries).features.filter(f=>f.id==='840'||f.id==='076');
// arredonda coordenadas
const r=a=>Array.isArray(a[0])?a.map(r):[+a[0].toFixed(2),+a[1].toFixed(2)];
f.forEach(x=>{x.geometry.coordinates=r(x.geometry.coordinates);x.properties={}});
fs.writeFileSync('alvos.json',JSON.stringify({type:'FeatureCollection',features:f}));
console.log(fs.statSync('alvos.json').size);
