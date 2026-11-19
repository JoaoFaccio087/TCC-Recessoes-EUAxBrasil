import fs from 'fs';
const V=process.argv[2];
const d3=await import(V+'/d3/src/index.js');
const tj=await import(V+'/topojson-client/src/index.js');
const w=JSON.parse(fs.readFileSync(V+'/world-atlas/countries-50m.json'));
const fs_=tj.feature(w,w.objects.countries).features;
const step=1.1, out=[];
const box=fs_.map(f=>[f,d3.geoBounds(f)]);
for(let lat=-58;lat<=84;lat+=step){const dl=step/Math.max(.2,Math.cos(lat*Math.PI/180));
  for(let lon=-180;lon<180;lon+=dl){const p=[+lon.toFixed(2),+lat.toFixed(2)];
    for(const [f,b] of box){ if(lat<b[0][1]-1||lat>b[1][1]+1) continue;
      const inLon=b[0][0]<=b[1][0]?(lon>=b[0][0]-1&&lon<=b[1][0]+1):true; if(!inLon) continue;
      if(d3.geoContains(f,p)){out.push([p[0],p[1],f.id==='840'?1:f.id==='076'?2:0]);break;}}}}
fs.writeFileSync('pontos.json',JSON.stringify(out));
const c=[0,0,0];out.forEach(o=>c[o[2]]++);console.log(out.length,c);
