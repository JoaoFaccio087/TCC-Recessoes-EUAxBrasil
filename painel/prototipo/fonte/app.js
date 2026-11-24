(function(){
'use strict';
const COR={eua:'#5B8FD9',br:'#2FA06E'};
const MOV=!matchMedia('(prefers-reduced-motion: reduce)').matches;
const fmt=(v,c=1)=>v==null?'—':v.toLocaleString('pt-BR',{minimumFractionDigits:c,maximumFractionDigits:c});
const sinal=(v,c=1)=>v==null?'—':(v>0?'+':v<0?'−':'')+fmt(Math.abs(v),c);
const MES=['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
const mesTxt=s=>{if(!s)return'';const [a,m]=s.split('-');return MES[+m-1]+'/'+a};

/* =================== conteúdo histórico =================== */
const HIST={
 eua:{nome:'Estados Unidos',sub:'Três recessões datadas pelo NBER',paginas:[
  {aba:'1981–82',dur:'16 meses',ano:'1981–1982',titulo:'O remédio amargo contra a inflação',periodo:'De julho de 1981 a novembro de 1982.',
   p:[['O estopim','No fim dos anos 1970, a inflação americana passava de 10% ao ano. O Federal Reserve, sob o comando de Paul Volcker, decidiu enfrentá-la de frente e levou os juros a perto de 20% ao ano.'],
      ['O impacto','Com o dinheiro caro, famílias e empresas pararam de comprar e de investir. A indústria e a construção encolheram, e o desemprego chegou perto de 11%.'],
      ['A saída','Quando a inflação cedeu, o Fed passou a cortar os juros, a partir de meados de 1982. A economia retomou com força em 1983 e 1984.']]},
  {aba:'2007–09',dur:'18 meses',ano:'2007–2009',titulo:'Do crédito imobiliário ao sistema financeiro',periodo:'De dezembro de 2007 a junho de 2009.',
   p:[['O estopim','Bancos emprestaram para quem não tinha como pagar e transformaram essas hipotecas de alto risco, as subprime, em títulos vendidos no mundo todo. Quando os calotes cresceram, esses títulos perderam valor.'],
      ['O impacto','A quebra do banco Lehman Brothers, em setembro de 2008, paralisou o crédito e levou a crise a outros países. Foi a recessão mais longa desde a Segunda Guerra Mundial, e o desemprego chegou a 10%.'],
      ['A saída','O Fed levou os juros para perto de zero e passou a comprar títulos em grande volume. O governo socorreu bancos e aprovou um pacote de estímulo. A retomada veio, mas devagar.']]},
  {aba:'2020',dur:'2 meses',ano:'2020',titulo:'Uma parada súbita',periodo:'De fevereiro a abril de 2020.',
   p:[['O estopim','Para conter a covid-19, os estados americanos fecharam comércio, escritórios e fábricas em poucas semanas.'],
      ['O impacto','Foi a recessão mais curta já registrada, com apenas dois meses, e uma das mais profundas. Em abril de 2020, o desemprego chegou perto de 15%.'],
      ['A saída','O Fed zerou os juros e o Congresso aprovou pacotes trilionários de ajuda a famílias e empresas. A atividade voltou rápido, mas não da mesma forma em todos os setores.']]}]},
 br:{nome:'Brasil',sub:'Como cada crise americana chegou aqui',paginas:[
  {aba:'1981–83',dur:'cerca de 3 anos',ano:'1981–1983',titulo:'A conta da dívida externa',periodo:'A recessão brasileira foi de 1981 a 1983.',
   p:[['O estopim','O Brasil havia crescido nos anos 1970 com dinheiro emprestado do exterior, a juros flutuantes. Quando os juros americanos dispararam, a conta da dívida disparou junto.'],
      ['O impacto','Em 1982, a moratória do México fez os bancos fecharem o crédito para a América Latina. O país recorreu ao FMI e fez um ajuste duro, que derrubou a produção e a renda.'],
      ['A saída','As exportações puxaram a retomada a partir de 1984. A dívida e a inflação alta, porém, marcaram o período que ficou conhecido como década perdida.']]},
  {aba:'2008–09',dur:'alguns meses',ano:'2008–2009',titulo:'A crise que chegou de fora',periodo:'Recessão curta, do fim de 2008 ao início de 2009.',
   p:[['O estopim','O Brasil não vivia uma bolha imobiliária. A crise chegou de fora: investidores tiraram dinheiro do país, o real se desvalorizou, o crédito externo secou e as exportações caíram.'],
      ['O impacto','A produção industrial despencou nos últimos meses de 2008. No balanço de 2009, o PIB ficou praticamente parado, com variação de −0,1%.'],
      ['A saída','O governo cortou o IPI de carros e eletrodomésticos e ampliou o crédito dos bancos públicos, e o Banco Central baixou os juros. Em 2010, o PIB cresceu 7,5%.']]},
  {aba:'2020',dur:'1º e 2º tri.',ano:'2020',titulo:'O choque duplo',periodo:'Segundo o Comitê de Datação de Ciclos Econômicos (CODACE/FGV), a recessão começou no 1º trimestre de 2020.',
   p:[['O estopim','O isolamento contra a covid-19 parou o comércio e os serviços no mesmo momento em que o resto do mundo também parava.'],
      ['O impacto','O pior momento foi o 2º trimestre de 2020. No ano, o PIB caiu 3,3%, segundo o IBGE.'],
      ['A saída','O auxílio emergencial sustentou a renda de milhões de famílias, e o Banco Central levou a Selic a 2% ao ano, a menor da história. A economia voltou ao nível de antes da pandemia no início de 2021.']]}]}
};

/* =================== globo =================== */
const cv=document.getElementById('globo'), ctx=cv.getContext('2d');
const LUGAR={eua:{c:[-98.5,39],nome:'Estados Unidos'},br:{c:[-52,-11],nome:'Brasil'}};
const FEAT={eua:ALVOS.features.find(f=>f.id==='840'),br:ALVOS.features.find(f=>f.id==='076')};
let W=0,R=0,dpr=1;
const proj=d3.geoOrthographic().rotate([78,-12]).clipAngle(90);
const caminho=d3.geoPath(proj,ctx);
const grat=d3.geoGraticule10();
const arco=d3.geoInterpolate(LUGAR.eua.c,LUGAR.br.c);
let hover=null, selecionado=null, t0=performance.now();
function medir(){const r=cv.getBoundingClientRect();dpr=Math.min(2,devicePixelRatio||1);W=r.width;cv.width=W*dpr;cv.height=W*dpr;R=W*.43;proj.scale(R).translate([W/2,W/2]);}
function visivel(c){const r=proj.rotate();return d3.geoDistance(c,[-r[0],-r[1]])<Math.PI/2-.02}
function desenhar(t){
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,W);
  const cx=W/2,cy=W/2;
  // esfera (a atmosfera é desenhada no céu, sem o limite do canvas do globo)
  let g=ctx.createRadialGradient(cx-R*.35,cy-R*.4,R*.1,cx,cy,R);g.addColorStop(0,'#16294A');g.addColorStop(1,'#0A1426');
  ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,R,0,7);ctx.fill();
  ctx.strokeStyle='rgba(120,150,200,.07)';ctx.lineWidth=.6;ctx.beginPath();caminho(grat);ctx.stroke();
  // pontos de terra
  const r=proj.rotate(), centro=[-r[0],-r[1]];
  const base=Math.max(1,R/260);
  for(const p of PONTOS){
    const d=d3.geoDistance([p[0],p[1]],centro); if(d>Math.PI/2) continue;
    const xy=proj([p[0],p[1]]); const luz=Math.cos(d);
    if(p[2]===0){ctx.fillStyle=`rgba(148,168,200,${.12+.42*luz})`;ctx.fillRect(xy[0]-base*.55,xy[1]-base*.55,base*1.1,base*1.1);}
  }
  for(const k of ['eua','br']){
    const id=k==='eua'?1:2, ativo=hover===k||selecionado===k;
    ctx.fillStyle=COR[k];
    for(const p of PONTOS){ if(p[2]!==id) continue;
      const d=d3.geoDistance([p[0],p[1]],centro); if(d>Math.PI/2) continue;
      const xy=proj([p[0],p[1]]); ctx.globalAlpha=(ativo?.75:.5)+.45*Math.cos(d);
      ctx.beginPath();ctx.arc(xy[0],xy[1],base*(ativo?1.05:.9),0,7);ctx.fill();}
    ctx.globalAlpha=1;
    ctx.strokeStyle=COR[k];ctx.globalAlpha=ativo?.9:.45;ctx.lineWidth=ativo?1.4:1;ctx.beginPath();caminho(FEAT[k]);ctx.stroke();ctx.globalAlpha=1;
  }
  // arco de transmissão: ponto elevado acima da superfície (altitude em frações do raio)
  ctx.save();ctx.beginPath();let ini=false;
  for(let i=0;i<=80;i++){const k=i/80, c=arco(k), alt=Math.sin(Math.PI*k)*.16;
    const z=Math.cos(d3.geoDistance(c,centro)), pr=proj(c), dx=pr[0]-cx, dy=pr[1]-cy;
    const x=cx+dx*(1+alt), y=cy+dy*(1+alt);
    const vis=z>0||Math.hypot(x-cx,y-cy)>R;
    if(!vis){ini=false;continue}
    if(!ini){ctx.moveTo(x,y);ini=true}else ctx.lineTo(x,y);}
  ctx.strokeStyle='rgba(231,194,125,.8)';ctx.lineWidth=1.4;ctx.lineCap='round';ctx.lineJoin='round';ctx.setLineDash([3,6]);ctx.lineDashOffset=MOV?-(t/60):0;ctx.stroke();ctx.restore();
  // marcadores e rótulos
  ctx.font=`500 ${Math.max(12,R/26)}px Plex, system-ui, sans-serif`;
  for(const k of ['eua','br']){const c=LUGAR[k].c; if(!visivel(c)) continue; const [x,y]=proj(c);
    const fase=MOV?((t/1600)%1):.4;
    ctx.strokeStyle=COR[k];ctx.globalAlpha=(1-fase)*.8;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,6+fase*18,0,7);ctx.stroke();ctx.globalAlpha=1;
    ctx.fillStyle=COR[k];ctx.beginPath();ctx.arc(x,y,5.5,0,7);ctx.fill();ctx.strokeStyle='#070D18';ctx.lineWidth=2;ctx.stroke();
    const txt=LUGAR[k].nome, tw=ctx.measureText(txt).width, px=x+14, py=y-14;
    ctx.fillStyle='rgba(7,13,24,.82)';ctx.beginPath();ctx.roundRect(px-8,py-15,tw+16,24,6);ctx.fill();
    ctx.fillStyle='#EAF0F7';ctx.fillText(txt,px,py+2);}
}
// rotação
let alvoRot=null, vel=[0,0], arrastando=false, ocioso=true;
function loop(t){
  if(alvoRot){const k=Math.min(1,(t-alvoRot.t)/900),e=d3.easeCubicInOut(k);proj.rotate(alvoRot.i(e));if(k>=1)alvoRot=null;}
  else if(!arrastando&&(Math.abs(vel[0])>.01||Math.abs(vel[1])>.01)){const r=proj.rotate();proj.rotate([r[0]+vel[0],Math.max(-60,Math.min(60,r[1]+vel[1])),0]);vel=[vel[0]*.94,vel[1]*.94];}
  else if(ocioso&&MOV){const r=proj.rotate();proj.rotate([r[0]+.035,r[1],0]);}
  desenhar(t);desenharEspaco(t);requestAnimationFrame(loop);
}
function girarPara(k){const c=LUGAR[k].c;const de=proj.rotate();let alvo=[-c[0],-c[1]*.6,0];
  let dl=alvo[0]-de[0];dl=((dl+540)%360)-180;alvo[0]=de[0]+dl;
  if(!MOV){proj.rotate(alvo);return}alvoRot={i:d3.interpolate(de,alvo),t:performance.now()};}
function paisEm(ev){const b=cv.getBoundingClientRect();const p=proj.invert([ev.clientX-b.left,ev.clientY-b.top]);
  if(!p||d3.geoDistance(p,[-proj.rotate()[0],-proj.rotate()[1]])>Math.PI/2)return null;
  for(const k of ['eua','br']){if(d3.geoContains(FEAT[k],p))return k;const xy=proj(LUGAR[k].c);if(Math.hypot(xy[0]-(ev.clientX-b.left),xy[1]-(ev.clientY-b.top))<16&&visivel(LUGAR[k].c))return k;}
  return null;}
let movido=0, ult=null;
cv.addEventListener('pointerdown',e=>{arrastando=true;ocioso=false;alvoRot=null;movido=0;ult=[e.clientX,e.clientY];vel=[0,0];cv.setPointerCapture(e.pointerId);cv.classList.add('arrasto');});
cv.addEventListener('pointermove',e=>{
  if(arrastando){const dx=e.clientX-ult[0],dy=e.clientY-ult[1];ult=[e.clientX,e.clientY];movido+=Math.abs(dx)+Math.abs(dy);
    const s=75/R;const r=proj.rotate();vel=[dx*s,-dy*s];proj.rotate([r[0]+dx*s,Math.max(-60,Math.min(60,r[1]-dy*s)),0]);return;}
  const k=paisEm(e);if(k!==hover){hover=k;cv.classList.toggle('alvo',!!k);}});
cv.addEventListener('pointerup',e=>{arrastando=false;cv.classList.remove('arrasto');if(movido<5){const k=paisEm(e);if(k)abrir(k);}});
cv.addEventListener('pointerleave',()=>{hover=null;cv.classList.remove('alvo')});
new ResizeObserver(medir).observe(cv);medir();requestAnimationFrame(loop);

/* =================== espaço =================== */
// Céu da capa: estrelas, Via Láctea, atmosfera do globo e objetos em órbita (ilustrativos, fora de escala).
// Duas camadas: #ceu fica atrás do globo (a esfera opaca esconde o que passa por trás) e #frente fica na frente.
const capa=document.getElementById('capa');
const ceu=document.getElementById('ceu'), cc=ceu.getContext('2d');
const frente=document.getElementById('frente'), fc=frente.getContext('2d');
const ESP_ITENS=['estrelas','lua','iss','satelites'];
const esp={estrelas:true,lua:true,iss:true,satelites:true};
try{const s=JSON.parse(localStorage.getItem('tcc-espaco')||'{}');for(const k of ESP_ITENS)if(typeof s[k]==='boolean')esp[k]=s[k];}catch(e){}
function salvarEsp(){try{localStorage.setItem('tcc-espaco',JSON.stringify(esp))}catch(e){}}
let CW=0,CH=0,estrelas=[],via=null,capaVisivel=true;
function medirCeu(){
  const b=capa.getBoundingClientRect();CW=b.width;CH=b.height;const d=Math.min(2,devicePixelRatio||1);
  for(const c of [ceu,frente]){c.width=Math.round(CW*d);c.height=Math.round(CH*d);c.getContext('2d').setTransform(d,0,0,d,0,0);}
  const rnd=d3.randomLcg(11);
  estrelas=Array.from({length:Math.round(CW*CH/3600)},()=>{const q=rnd();
    return {x:rnd()*CW,y:rnd()*CH,r:.35+Math.pow(rnd(),4)*1.4,a:.18+rnd()*.6,f:rnd()*6.28,v:.4+rnd()*1.6,p:.15+rnd()*.85,
      cor:q<.1?'201,216,255':q<.16?'255,226,190':'255,255,255'};});
  // Via Láctea: faixa diagonal pré-desenhada uma vez
  via=document.createElement('canvas');via.width=Math.round(CW*d);via.height=Math.round(CH*d);
  const vc=via.getContext('2d');vc.setTransform(d,0,0,d,0,0);
  vc.translate(CW*.42,CH*.5);vc.rotate(-.42);
  const L=Math.hypot(CW,CH);
  for(const [w,a] of [[CH*.34,.035],[CH*.16,.04],[CH*.06,.03]]){
    const g=vc.createLinearGradient(0,-w,0,w);g.addColorStop(0,'rgba(120,150,220,0)');g.addColorStop(.5,`rgba(150,170,230,${a})`);g.addColorStop(1,'rgba(120,150,220,0)');
    vc.fillStyle=g;vc.fillRect(-L,-w,L*2,w*2);}
  const nrnd=d3.randomNormal.source(d3.randomLcg(5))(0,CH*.07);
  for(let i=0;i<Math.round(CW*1.4);i++){const x=(rnd()-.5)*L,y=nrnd();vc.fillStyle=`rgba(220,230,255,${.05+rnd()*.22})`;vc.fillRect(x,y,.7,.7);}
}
new ResizeObserver(medirCeu).observe(capa);medirCeu();
new IntersectionObserver(e=>{capaVisivel=e[0].isIntersecting}).observe(capa);

// órbitas em unidades do raio do globo: a = semieixo, b = achatamento (inclinação vista), tilt = giro no plano da tela
const ORB={
  lua:{a:1.62,b:1.12,tilt:-.22,per:52,fase:.3},
  iss:{a:1.14,b:.42,tilt:.42,per:15,fase:2.4},
  sats:[{a:1.3,b:.62,tilt:-.75,per:24,fase:1.1},{a:1.42,b:.16,tilt:.08,per:31,fase:4.2},{a:1.24,b:.9,tilt:1.25,per:21,fase:5.3}]
};
function posOrb(o,t,cx,cy){
  const th=o.fase+(o.desl||0)+(MOV?t/1000:0)*2*Math.PI/o.per, x=Math.cos(th)*o.a*R, y=Math.sin(th)*o.b*R, c=Math.cos(o.tilt), s=Math.sin(o.tilt);
  return {x:cx+x*c-y*s, y:cy+x*s+y*c, z:Math.sin(th), ang:o.tilt+Math.atan2(Math.cos(th)*o.b,-Math.sin(th)*o.a)};
}
// Objetos pré-renderizados uma vez em canvas fora da tela, com luz vinda do alto à esquerda (a mesma do globo).
const SOL=(()=>{const v=[-.55,-.6,.58],n=Math.hypot(...v);return v.map(x=>x/n)})();
function ruido2(seed){ // value noise suave, determinístico
  const rnd=d3.randomLcg(seed),N=256,perm=new Uint8Array(N*2),val=new Float32Array(N);
  for(let i=0;i<N;i++){perm[i]=i;val[i]=rnd();}
  for(let i=N-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[perm[i],perm[j]]=[perm[j],perm[i]];}
  for(let i=0;i<N;i++)perm[N+i]=perm[i];
  const sm=t=>t*t*(3-2*t), h=(x,y,z)=>val[perm[perm[perm[x&255]+(y&255)]+(z&255)]];
  return (x,y,z)=>{const X=Math.floor(x),Y=Math.floor(y),Z=Math.floor(z),fx=sm(x-X),fy=sm(y-Y),fz=sm(z-Z);
    const l=(a,b,t)=>a+(b-a)*t;
    return l(l(l(h(X,Y,Z),h(X+1,Y,Z),fx),l(h(X,Y+1,Z),h(X+1,Y+1,Z),fx),fy),
             l(l(h(X,Y,Z+1),h(X+1,Y,Z+1),fx),l(h(X,Y+1,Z+1),h(X+1,Y+1,Z+1),fx),fy),fz);};
}
function fbm(n,x,y,z,o){let s=0,a=.5,f=1;for(let i=0;i<o;i++){s+=a*n(x*f,y*f,z*f);a*=.5;f*=2.03;}return s;}

const SPRITE={};
function renderLua(S){
  const c=document.createElement('canvas');c.width=c.height=S;const k=c.getContext('2d'),img=k.createImageData(S,S),d=img.data;
  const n=ruido2(3), rnd=d3.randomLcg(9), r0=S/2-1;
  // crateras em direções aleatórias da esfera
  const crat=Array.from({length:160},()=>{const u=rnd()*2-1,t=rnd()*6.283,s=Math.sqrt(1-u*u);
    return {v:[s*Math.cos(t),s*Math.sin(t),u],r:.01+Math.pow(rnd(),4)*.08,raio:rnd()<.06}});
  const H=new Float32Array(S*S),A=new Float32Array(S*S),M=new Uint8Array(S*S);
  for(let j=0;j<S;j++)for(let i=0;i<S;i++){
    const x=(i+.5-S/2)/r0,y=(j+.5-S/2)/r0,q=x*x+y*y;if(q>1)continue;const z=Math.sqrt(1-q),o=j*S+i;M[o]=1;
    // mares: manchas escuras de baixa frequência
    const mq=Math.max(0,Math.min(1,(fbm(n,x*1.2+4.3,y*1.2+1.7,z*1.2+.5,5)-.56)/.07)),mar=mq*mq*(3-2*mq);
    let h=fbm(n,x*12,y*12,z*12,4)*.006, alb=.9-.5*mar+(fbm(n,x*18+9,y*18,z*18,4)-.5)*.16;
    for(const cr of crat){const dot=x*cr.v[0]+y*cr.v[1]+z*cr.v[2];if(dot<.7)continue;
      const ang=Math.acos(Math.min(1,dot))/cr.r;
      if(cr.raio&&ang<6)alb+=.1*Math.exp(-ang*.8)*(1-mar*.5);
      if(ang>1.5)continue;
      h+=cr.r*(ang<1?(ang*ang-1)*.22:Math.exp(-((ang-1)*(ang-1))/.03)*.07);
      if(ang<1.2)alb+=.07*(1-mar);}
    H[o]=h;A[o]=alb;}
  for(let j=0;j<S;j++)for(let i=0;i<S;i++){const o=j*S+i;if(!M[o])continue;
    const x=(i+.5-S/2)/r0,y=(j+.5-S/2)/r0,z=Math.sqrt(Math.max(0,1-x*x-y*y));
    const hx=(M[o+1]?H[o+1]:H[o])-(M[o-1]?H[o-1]:H[o]), hy=(M[o+S]?H[o+S]:H[o])-(M[o-S]?H[o-S]:H[o]);
    let nx=x-hx*S*.35,ny=y-hy*S*.35,nz=z;const nl=Math.hypot(nx,ny,nz);nx/=nl;ny/=nl;nz/=nl;
    const lam=Math.max(0,nx*SOL[0]+ny*SOL[1]+nz*SOL[2]);
    const lim=Math.pow(z,.25); // escurece de leve a borda
    const v=Math.min(1,A[o]*(Math.pow(lam,.7)*1.08+.03)*lim);
    const aa=Math.max(0,Math.min(1,(1-Math.hypot(x,y))*r0*1.2)); // borda suavizada
    d[o*4]=v*232;d[o*4+1]=v*229;d[o*4+2]=v*222;d[o*4+3]=255*aa;}
  k.putImageData(img,0,0);return c;
}
function painelSolar(k,x,y,w,h,cor){ // painel com células, reflexo e moldura
  const g=k.createLinearGradient(x,y,x+w,y+h);for(const [o,c] of cor)g.addColorStop(o,c);
  k.fillStyle=g;k.fillRect(x,y,w,h);
  k.strokeStyle='rgba(0,0,0,.35)';k.lineWidth=Math.max(.5,w/60);
  for(let i=1;i<6;i++){k.beginPath();k.moveTo(x+w*i/6,y);k.lineTo(x+w*i/6,y+h);k.stroke();}
  for(let i=1;i<3;i++){k.beginPath();k.moveTo(x,y+h*i/3);k.lineTo(x+w,y+h*i/3);k.stroke();}
  k.strokeStyle='rgba(255,255,255,.18)';k.strokeRect(x,y,w,h);
}
function cilindro(k,x,y,w,h,claro,escuro){const g=k.createLinearGradient(0,y,0,y+h);g.addColorStop(0,escuro);g.addColorStop(.3,claro);g.addColorStop(1,escuro);k.fillStyle=g;k.beginPath();k.roundRect(x,y,w,h,h*.35);k.fill();}
function renderISS(){ // vista de cima, eixo da treliça na horizontal; unidade = 1/100 da largura
  const W=400,H=260,c=document.createElement('canvas');c.width=W;c.height=H;const k=c.getContext('2d');k.translate(W/2,H/2);
  const ouro=[[0,'#1E1712'],[.35,'#5E4630'],[.55,'#A07A4E'],[.75,'#4C3826'],[1,'#1E1712']];
  for(const sx of [-1,1])for(const off of [46,76])for(const sy of [-1,1])
    painelSolar(k,sx*off-13,sy>0?14:-14-88,26,88,ouro);
  // treliça principal
  const gt=k.createLinearGradient(0,-6,0,6);gt.addColorStop(0,'#5E6672');gt.addColorStop(.4,'#E6EAF0');gt.addColorStop(1,'#59606B');
  k.fillStyle=gt;k.fillRect(-170,-5,340,10);
  k.strokeStyle='rgba(40,46,56,.6)';k.lineWidth=1;for(let x=-165;x<170;x+=10){k.beginPath();k.moveTo(x,-5);k.lineTo(x+10,5);k.stroke();}
  // radiadores brancos
  k.fillStyle='rgba(235,240,246,.9)';for(const sx of [-1,1]){k.fillRect(sx*24-6,8,12,40);k.fillRect(sx*24-6,-48,12,40);}
  // módulos pressurizados (eixo vertical)
  cilindro(k,-11,-70,22,140,'#F1F3F6','#7E8693');
  cilindro(k,-30,-40,60,16,'#ECEFF3','#7A828F');cilindro(k,-26,30,52,14,'#ECEFF3','#7A828F');
  const s=document.createElement('canvas');s.width=W;s.height=H;s.getContext('2d').drawImage(c,0,0);return c;
}
function renderSat(){
  const W=200,H=80,c=document.createElement('canvas');c.width=W;c.height=H;const k=c.getContext('2d');k.translate(W/2,H/2);
  const azul=[[0,'#070D1C'],[.45,'#18294A'],[.6,'#3A5584'],[1,'#070D1C']];
  painelSolar(k,-96,-18,70,36,azul);painelSolar(k,26,-18,70,36,azul);
  k.fillStyle='#8A8F98';k.fillRect(-26,-2,52,4);
  const g=k.createLinearGradient(-20,-22,20,22);g.addColorStop(0,'#E9C77E');g.addColorStop(.45,'#A27630');g.addColorStop(.7,'#C99A4A');g.addColorStop(1,'#4A3212');
  k.fillStyle=g;k.beginPath();k.roundRect(-20,-22,40,44,4);k.fill();
  k.fillStyle='rgba(255,255,255,.18)';k.fillRect(-16,-18,8,36);
  k.fillStyle='#D8DDE4';k.beginPath();k.ellipse(0,-26,9,4,0,0,7);k.fill();
  return c;
}
function brilho(k,x,y,r,a){const g=k.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(255,250,235,${a})`);g.addColorStop(.25,`rgba(255,240,210,${a*.35})`);g.addColorStop(1,'rgba(255,240,210,0)');k.fillStyle=g;k.beginPath();k.arc(x,y,r,0,7);k.fill();}
function lua(k,p){
  if(!SPRITE.lua)SPRITE.lua=renderLua(256);
  const r=R*.062*(1+.08*p.z);k.drawImage(SPRITE.lua,p.x-r,p.y-r,r*2,r*2);
}
function reflexo(t,fase,per){return Math.pow(Math.max(0,Math.sin(t/per+fase)),28)}
function estacao(k,p,t){
  if(!SPRITE.iss)SPRITE.iss=renderISS();
  const w=Math.max(40,R*.12)*(1+.12*p.z),h=w*.65;
  k.save();k.translate(p.x,p.y);k.rotate(p.ang+Math.PI/2);k.scale(1,.62);
  k.drawImage(SPRITE.iss,-w/2,-h/2,w,h);k.restore();
  const f=MOV?reflexo(t,.8,1700):0;if(f>.02)brilho(k,p.x,p.y,w*.55,.85*f);
}
function satelite(k,p,t,i){
  if(!SPRITE.sat)SPRITE.sat=renderSat();
  const w=Math.max(16,R*.042)*(1+.12*p.z),h=w*.4;
  k.save();k.translate(p.x,p.y);k.rotate(p.ang);k.scale(1,.7);k.drawImage(SPRITE.sat,-w/2,-h/2,w,h);k.restore();
  const f=MOV?reflexo(t,i*2.1,1300+i*300):0;if(f>.02)brilho(k,p.x,p.y,w*.7,.8*f);
}
function desenharEspaco(t){
  if(!capaVisivel||!CW)return;
  cc.clearRect(0,0,CW,CH);fc.clearRect(0,0,CW,CH);
  const bc=capa.getBoundingClientRect(), bg=cv.getBoundingClientRect();
  const cx=bg.left-bc.left+bg.width/2, cy=bg.top-bc.top+bg.height/2, rot=proj.rotate();
  if(esp.estrelas){
    cc.drawImage(via,0,0,CW,CH);
    for(const e of estrelas){
      const x=((e.x+rot[0]*e.p*1.2)%CW+CW)%CW, y=((e.y-rot[1]*e.p*1.2)%CH+CH)%CH;
      const a=MOV?e.a*(.7+.3*Math.sin(t/1000*e.v+e.f)):e.a;
      cc.fillStyle=`rgba(${e.cor},${a})`;cc.fillRect(x-e.r/2,y-e.r/2,e.r,e.r);}
    // satélite distante cruzando o céu de tempos em tempos
    if(esp.satelites&&MOV){const ciclo=38000,k=(t%ciclo)/ciclo;if(k<.55){const q=k/.55;
      cc.fillStyle=`rgba(230,236,245,${.55*Math.sin(Math.PI*q)})`;cc.fillRect(CW*(-.05+q*.7),CH*(.12+q*.1),1.3,1.3);}}
  }
  // atmosfera (antes cortada pelo canvas do globo)
  const g=cc.createRadialGradient(cx,cy,R*.92,cx,cy,R*1.32);g.addColorStop(0,'rgba(91,143,217,.17)');g.addColorStop(1,'rgba(91,143,217,0)');
  cc.fillStyle=g;cc.beginPath();cc.arc(cx,cy,R*1.32,0,7);cc.fill();
  // inércia depois de soltar um objeto arrastado
  for(const o of [ORB.lua,ORB.iss,...ORB.sats])if(o!==arrasteEsp?.ref&&o.vel){o.desl=(o.desl||0)+o.vel;o.vel*=.955;if(Math.abs(o.vel)<1e-4)o.vel=0;}
  const objs=[];espCentro=[cx,cy];espAlvos=[];
  const alvo=(ref,geo,p,raio,nome)=>{if(!(p.z<0&&Math.hypot(p.x-cx,p.y-cy)<R))espAlvos.push({ref,geo,p,raio,nome});};
  if(esp.lua){// a órbita da Lua encolhe quando não cabe na tela
    const L=ORB.lua, f=Math.max(.62,Math.min(1,((CW-cx)/R-.14)/L.a,((CH-cy)/R-.1)/L.b)), o={...L,a:L.a*f,b:L.b*f}, p=posOrb(o,t,cx,cy);
    objs.push([p,(k,p)=>lua(k,p)]);alvo(L,o,p,R*.062+8,'Lua');}
  if(esp.iss){const p=posOrb(ORB.iss,t,cx,cy);objs.push([p,(k,p)=>estacao(k,p,t)]);alvo(ORB.iss,ORB.iss,p,Math.max(24,R*.06),'Estação Espacial Internacional');}
  if(esp.satelites)ORB.sats.forEach((o,i)=>{const p=posOrb(o,t,cx,cy);objs.push([p,(k,p)=>satelite(k,p,t,i)]);alvo(o,o,p,Math.max(16,R*.03),'Satélite');});
  objs.sort((a,b)=>a[0].z-b[0].z);
  for(const [p,f] of objs)f(p.z>0?fc:cc,p);
  if(arrasteEsp||hoverEsp){const h=arrasteEsp||hoverEsp, a=espAlvos.find(x=>x.ref===h.ref);
    if(a){rotuloEsp.textContent=a.nome;rotuloEsp.style.transform=`translate(${a.p.x+a.raio+6}px,${a.p.y-12}px)`;rotuloEsp.hidden=false;}else rotuloEsp.hidden=true;}
  else rotuloEsp.hidden=true;
}

// arrastar a Lua, a Estação e os satélites ao longo da própria órbita, com inércia ao soltar
let espAlvos=[],espCentro=[0,0],arrasteEsp=null,hoverEsp=null;
const rotuloEsp=document.getElementById('esp-rotulo');
function noCapa(e){const b=capa.getBoundingClientRect();return [e.clientX-b.left,e.clientY-b.top];}
function alvoEm(x,y){let m=null,d=1e9;for(const a of espAlvos){const q=Math.hypot(x-a.p.x,y-a.p.y);if(q<a.raio&&(q<d||(m&&a.p.z>m.p.z))){m=a;d=q;}}return m;}
function anguloNaOrbita(g,x,y){const dx=x-espCentro[0],dy=y-espCentro[1],c=Math.cos(g.tilt),s=Math.sin(g.tilt);
  return Math.atan2((-dx*s+dy*c)/(g.b*R),(dx*c+dy*s)/(g.a*R));}
const giro=d=>Math.atan2(Math.sin(d),Math.cos(d));
capa.addEventListener('pointerdown',e=>{if(e.button!==0)return;const [x,y]=noCapa(e),a=alvoEm(x,y);if(!a)return;
  e.stopPropagation();e.preventDefault();a.ref.vel=0;
  arrasteEsp={ref:a.ref,geo:a.geo,ang:anguloNaOrbita(a.geo,x,y)};capa.setPointerCapture(e.pointerId);capa.classList.add('arrastando-obj');},true);
capa.addEventListener('pointermove',e=>{const [x,y]=noCapa(e);
  if(arrasteEsp){const g=arrasteEsp.geo,n=anguloNaOrbita(g,x,y),d=giro(n-arrasteEsp.ang);arrasteEsp.ang=n;
    arrasteEsp.ref.desl=(arrasteEsp.ref.desl||0)+d;arrasteEsp.ref.vel=d*.5;return;}
  if(e.target.closest('.texto,.esp-menu'))return;
  const a=alvoEm(x,y);hoverEsp=a?{ref:a.ref}:null;capa.classList.toggle('sobre-obj',!!a);},true);
function soltarEsp(){if(!arrasteEsp)return;if(!MOV)arrasteEsp.ref.vel=0;arrasteEsp=null;capa.classList.remove('arrastando-obj');}
capa.addEventListener('pointerup',soltarEsp,true);capa.addEventListener('pointercancel',soltarEsp,true);
capa.addEventListener('pointerleave',()=>{hoverEsp=null;capa.classList.remove('sobre-obj');});

// menu do espaço
const espBotao=document.getElementById('esp-botao'), espPainel=document.getElementById('esp-painel'), espTodos=document.getElementById('esp-todos');
function syncEsp(){
  espPainel.querySelectorAll('input[data-esp]').forEach(i=>{i.checked=esp[i.dataset.esp]});
  const algum=ESP_ITENS.some(k=>esp[k]);espTodos.textContent=algum?'Deixar só o globo':'Mostrar tudo';
  capa.classList.toggle('ceu-limpo',!esp.estrelas);
}
function abrirEsp(on){espPainel.hidden=!on;espBotao.setAttribute('aria-expanded',on);if(on)espPainel.querySelector('input').focus();}
espBotao.addEventListener('click',()=>abrirEsp(espPainel.hidden));
espPainel.addEventListener('change',e=>{const k=e.target.dataset.esp;if(k){esp[k]=e.target.checked;salvarEsp();syncEsp();}});
espTodos.addEventListener('click',()=>{const v=!ESP_ITENS.some(k=>esp[k]);for(const k of ESP_ITENS)esp[k]=v;salvarEsp();syncEsp();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!espPainel.hidden){abrirEsp(false);espBotao.focus();}});
document.addEventListener('pointerdown',e=>{if(!espPainel.hidden&&!e.target.closest('.esp-menu'))abrirEsp(false);});
syncEsp();

/* =================== gaveta =================== */
const gav=document.getElementById('gaveta'), veu=document.getElementById('veu');
let gPais='eua', gPag=0, ultimoFoco=null;
function montarGaveta(troca){
  const h=HIST[gPais], pg=h.paginas[gPag];
  gav.style.setProperty('--cor',COR[gPais]);
  document.getElementById('g-pais').textContent=h.nome;
  document.getElementById('g-sub').textContent=h.sub;
  const lt=gav.querySelector('.linha-tempo');lt.innerHTML='';
  h.paginas.forEach((q,i)=>{const b=document.createElement('button');b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-selected',i===gPag);
    b.innerHTML=`<b>${q.aba}</b><small>${q.dur}</small>`;b.onclick=()=>{if(i!==gPag){gPag=i;montarGaveta(true)}};lt.appendChild(b);});
  const alvo=gav.querySelector('.g-conteudo');
  const html=`<p class="g-ano">${pg.ano}</p><p class="g-titulo">${pg.titulo}</p><p class="g-periodo">${pg.periodo}</p>`+pg.p.map(([t,x])=>`<div class="g-parte"><h3>${t}</h3><p>${x}</p></div>`).join('');
  if(troca&&MOV){alvo.classList.add('saindo');setTimeout(()=>{alvo.innerHTML=html;gav.querySelector('.g-corpo').scrollTop=0;alvo.classList.remove('saindo')},170);}
  else{alvo.innerHTML=html;gav.querySelector('.g-corpo').scrollTop=0;}
}
function abrir(k){gPais=k;gPag=0;selecionado=k;ultimoFoco=document.activeElement;montarGaveta(false);girarPara(k);ocioso=false;
  gav.classList.add('on');veu.classList.add('on');document.body.classList.add('com-gaveta');gav.setAttribute('aria-hidden','false');setTimeout(()=>gav.focus({preventScroll:true}),60);}
function fechar(){gav.classList.remove('on');veu.classList.remove('on');document.body.classList.remove('com-gaveta');gav.setAttribute('aria-hidden','true');selecionado=null;if(ultimoFoco)ultimoFoco.focus();}
gav.querySelector('.fechar').onclick=fechar;veu.onclick=fechar;
document.addEventListener('keydown',e=>{if(!gav.classList.contains('on'))return;
  if(e.key==='Escape')fechar();
  const n=HIST[gPais].paginas.length;
  if(e.key==='ArrowRight'&&gPag<n-1){gPag++;montarGaveta(true);gav.querySelector('.linha-tempo [aria-selected=true]').focus()}
  if(e.key==='ArrowLeft'&&gPag>0){gPag--;montarGaveta(true);gav.querySelector('.linha-tempo [aria-selected=true]').focus()}
  if(e.key==='Tab'){const f=[...gav.querySelectorAll('button')];const a=f[0],z=f[f.length-1];
    if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus()}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus()}}});
document.querySelectorAll('.escolha button').forEach(b=>b.onclick=()=>abrir(b.dataset.pais));
document.getElementById('g-dados').onclick=()=>{const EPMAP=['1981-1982','2007-2009','2020'];estado.ep=EPMAP[gPag];atualizar();fechar();document.getElementById('explorar').scrollIntoView({behavior:MOV?'smooth':'auto'});};

/* =================== explorar =================== */
const D=window.DADOS, EPS=D.episodios;
const ROT={'1981-1982':'1981–82','2007-2009':'2007–09','2020':'2020'};
const estado={par:'producao_industrial',ep:'2007-2009'};
const parDe=id=>D.pares.find(p=>p.id===id);
const unid=p=>p.tipo==='nivel'?'%':' p.p.';
const tempo=(n,p)=>{if(n==null)return'—';const a=Math.abs(n);return p.tri?`${a} ${a===1?'trimestre':'trimestres'}`:`${a} ${a===1?'mês':'meses'}`};
const xT=(v,p)=>v==null?null:(p.tri?v*3:v);
document.getElementById('rod-edicao').innerHTML=`<b>Edição dos dados:</b> ${D.edicao.id}, com dados coletados até ${D.edicao.corte.split('-').reverse().join('/')}.`;

// trilho
const trilho=document.querySelector('.trilho');
D.pares.forEach(p=>{const b=document.createElement('button');b.type='button';b.dataset.par=p.id;
  b.innerHTML=`<span>${p.nome}</span><small>${p.sem_par?'só Brasil':p.tri?'trimestral':''}</small>`;
  b.onclick=()=>{estado.par=p.id;atualizar()};trilho.appendChild(b);});
const seg=document.getElementById('seg-ep');
EPS.forEach(e=>{const b=document.createElement('button');b.type='button';b.dataset.ep=e.id;b.textContent=ROT[e.id];b.onclick=()=>{estado.ep=e.id;atualizar()};seg.appendChild(b);});

const EM={producao_industrial:'na produção industrial',desemprego:'no desemprego',juros:'nos juros',inflacao:'na inflação',pib:'no PIB',acoes:'na bolsa de valores',exportacoes_total:'nas exportações totais',exportacoes_eua:'nas exportações para os EUA'};
function textoManchete(p,e,d){
  const crise=`Na crise de ${ROT[e]}`, em=EM[p.id];
  if(p.sem_par){const r=d.res_br;return r&&r.amplitude!=null?`${crise}, o câmbio real brasileiro chegou a <b>${sinal(r.amplitude)}%</b> em relação ao pico${r.amplitude<0?', sinal de desvalorização do real':''}.`:`${crise}, não há medidas para o câmbio real.`}
  if(!d.br)return `${crise}, não existe série brasileira para comparar ${em}.`;
  const rb=d.res_br; let s;
  if(d.defasagem!=null)s=d.defasagem===0?`${crise}, Brasil e EUA reagiram <b>no mesmo ${p.tri?'trimestre':'mês'}</b> ${em}`:`${crise}, o Brasil reagiu <b>${tempo(Math.abs(d.defasagem),p)} ${d.defasagem>0?'depois':'antes'}</b> dos EUA ${em}`;
  else if(rb&&rb.st_reacao!=='OK')s=`${crise}, o Brasil <b>não chegou a reagir</b> ${em}, pelo critério do estudo`;
  else s=`${crise}, os EUA não chegaram a reagir ${em}, e por isso não há defasagem`;
  if(rb&&rb.amplitude!=null&&p.tipo==='nivel'&&rb.amplitude<0)s+=`; no pior momento, a queda brasileira foi de <b>${fmt(Math.abs(rb.amplitude))}%</b>`;
  else if(rb&&rb.amplitude!=null&&p.tipo==='taxa')s+=`; no pior momento, a variação brasileira foi de <b>${sinal(rb.amplitude)} p.p.</b>`;
  return s+(s.endsWith('.</b>')?'':'.');
}
const graf=document.getElementById('graf'), dica=document.getElementById('dica');
function escalaY(p,eps){const vals=[];eps.forEach(e=>{const d=p.eps[e];[d.pts_eua,d.pts_br].forEach(a=>a.forEach(q=>{if(q[1]!=null)vals.push(q[1])}))});
  const ref=p.tipo==='nivel'?100:0;let lo=Math.min(ref,...vals),hi=Math.max(ref,...vals);const pad=(hi-lo)*.08||1;return [lo-pad,hi+pad];}

const DUR=MOV?700:0, EASE=d3.easeCubicInOut;
const val=(a,t)=>{const q=a.find(q=>q[0]===t);return q?q[1]:null};
const linhaPx=d3.line().defined(q=>q[1]!=null).x(q=>q[0]).y(q=>q[1]);

/* anima um caminho entre a posição anterior e a nova, ponto a ponto */
function animarCaminho(sel,pts,x,y,refPx,dur){
  const node=sel.node(), antes=node.__px||new Map();
  const alvo=pts.map(([t,v])=>[t,v==null?null:y(v)]);
  const novo=new Map(alvo.filter(q=>q[1]!=null));
  node.__px=novo;
  if(!dur){sel.attr('d',linhaPx(alvo.map(([t,py])=>[x(t),py])));return sel;}
  return sel.transition().duration(dur).ease(EASE).attrTween('d',()=>k=>linhaPx(alvo.map(([t,py])=>{
    if(py==null)return[x(t),null];const de=antes.has(t)?antes.get(t):refPx;return[x(t),de+(py-de)*k];})));
}

/* ---------- gráfico principal (persistente) ---------- */
let G=null;
function criarGrafico(){
  graf.querySelectorAll('svg').forEach(s=>s.remove());
  const Wg=graf.clientWidth-16, H=Math.max(300,Math.min(440,Wg*.48)), m={t:34,r:20,b:40,l:48};
  const svg=d3.select(graf).insert('svg','#dica').attr('viewBox',`0 0 ${Wg} ${H}`).attr('role','img');
  const x=d3.scaleLinear().domain([-24,48]).range([m.l,Wg-m.r]);
  G={svg,Wg,H,m,x,y:null};
  G.faixa=svg.append('rect').attr('y',m.t).attr('height',H-m.b-m.t).attr('fill','rgba(170,190,220,.07)').attr('x',x(0)).attr('width',2);
  G.grade=svg.append('g').attr('class','eixo');
  G.ref=svg.append('line').attr('x1',m.l).attr('x2',Wg-m.r).attr('stroke','#3A4E70');
  G.refTxt=svg.append('text').attr('x',Wg-m.r).attr('text-anchor','end').attr('fill','#8796AD').attr('paint-order','stroke').attr('stroke','#0E1828').attr('stroke-width',5).attr('font-size',12);
  const gx=svg.append('g').attr('class','eixo');
  for(let t=-24;t<=48;t+=12)gx.append('text').attr('x',x(t)).attr('y',H-14).attr('text-anchor','middle').text(t===0?'pico':(t>0?'+':'−')+Math.abs(t)+' meses');
  svg.append('line').attr('x1',x(0)).attr('x2',x(0)).attr('y1',m.t-26).attr('y2',H-m.b).attr('stroke','#8796AD').attr('stroke-dasharray','3 4');
  G.faixaTxt=svg.append('text').attr('x',x(0)+8).attr('y',m.t-14).attr('fill','#8796AD').attr('font-size',12);
  G.linhas={eua:svg.append('path').attr('fill','none').attr('stroke',COR.eua).attr('stroke-width',2).attr('stroke-linejoin','round').attr('opacity',.9),
            br:svg.append('path').attr('fill','none').attr('stroke',COR.br).attr('stroke-width',2.5).attr('stroke-linejoin','round')};
  G.pontos=svg.append('g');
  G.notas=svg.append('g');
  G.cross=svg.append('line').attr('y1',m.t).attr('y2',H-m.b).attr('stroke','#A9B6C8').attr('opacity',0);
  G.dots={eua:svg.append('circle').attr('r',4.5).attr('fill',COR.eua).attr('stroke','#0E1828').attr('stroke-width',2).attr('opacity',0),
          br:svg.append('circle').attr('r',4.5).attr('fill',COR.br).attr('stroke','#0E1828').attr('stroke-width',2).attr('opacity',0)};
  svg.append('rect').attr('x',m.l).attr('y',m.t).attr('width',Wg-m.l-m.r).attr('height',H-m.t-m.b).attr('fill','transparent')
   .on('pointermove',ev=>{if(!G.atual)return;const {p,series}=G.atual, y=G.y;const [mx]=d3.pointer(ev);let t=Math.round(x.invert(mx));if(p.tri)t=Math.round(t/3)*3;t=Math.max(-24,Math.min(48,t));
     G.cross.attr('x1',x(t)).attr('x2',x(t)).attr('opacity',.5);
     let html=`<b>${t===0?'Mês do pico':(t>0?'+':'−')+Math.abs(t)+' meses'}</b>`;
     ['eua','br'].forEach(k=>{const a=series[k];const q=a&&a.find(q=>q[0]===t);
       if(q&&q[1]!=null){G.dots[k].attr('cx',x(t)).attr('cy',y(q[1])).attr('opacity',1);
         html+=`<div class="l"><span><i style="background:${COR[k]}"></i>${k==='eua'?'EUA':'Brasil'} <span style="color:#728199">${mesTxt(q[2])}</span></span><b class="num">${p.tipo==='nivel'?fmt(q[1]):sinal(q[1],2)}</b></div>`;}
       else G.dots[k].attr('opacity',0);});
     dica.innerHTML=html;dica.style.opacity=1;const bw=graf.clientWidth;const px=x(t)/G.Wg*bw;
     dica.style.left=Math.min(bw-190,Math.max(8,px+14))+'px';dica.style.top='20px';})
   .on('pointerleave',()=>{G.cross.attr('opacity',0);G.dots.eua.attr('opacity',0);G.dots.br.attr('opacity',0);dica.style.opacity=0;});
}

function desenharPrincipal(animar=true){
  if(!G)criarGrafico();
  const dur=animar?DUR:0;
  const p=parDe(estado.par), e=estado.ep, d=p.eps[e], epi=EPS.find(z=>z.id===e);
  const {svg,Wg,H,m,x}=G;
  const [lo,hi]=escalaY(p,[e]);const y=d3.scaleLinear().domain([lo,hi]).nice(6).range([H-m.b,m.t]);
  const yAntes=G.y||y; G.y=y;
  const series={eua:d.pts_eua.length?d.pts_eua:null,br:d.pts_br.length?d.pts_br:null};
  G.atual={p,series};
  svg.attr('aria-label',`${p.nome}: Estados Unidos e Brasil na crise de ${ROT[e]}, alinhados ao pico`);
  const tr=()=>svg.transition().duration(dur).ease(EASE);
  // faixa
  G.faixa.transition(tr()).attr('x',x(0)).attr('width',Math.max(2,x(epi.meses)-x(0)));
  G.faixaTxt.text(`recessão nos EUA: ${epi.meses} ${epi.meses===1?'mês':'meses'}`);
  // grade com entrada e saída
  const ticks=y.ticks(6), rot=v=>p.tipo==='nivel'?fmt(v,0):sinal(v,0);
  G.grade.selectAll('g.tk').data(ticks,v=>p.tipo+v).join(
    en=>{const g=en.append('g').attr('class','tk').attr('opacity',0).attr('transform',v=>`translate(0,${yAntes(v)})`);
      g.append('line').attr('x1',m.l).attr('x2',Wg-m.r).attr('stroke','#16233A');
      g.append('text').attr('x',m.l-10).attr('y',4).attr('text-anchor','end');return g;},
    up=>up,
    ex=>ex.transition(tr()).attr('opacity',0).attr('transform',v=>`translate(0,${y(v)})`).remove())
   .call(g=>g.select('text').text(rot))
   .transition(tr()).attr('opacity',1).attr('transform',v=>`translate(0,${y(v)})`);
  const ref=p.tipo==='nivel'?100:0;
  G.ref.transition(tr()).attr('y1',y(ref)).attr('y2',y(ref));
  G.refTxt.text(p.tipo==='nivel'?'nível do pico = 100':'nível do pico').transition(tr()).attr('y',y(ref)-8);
  // linhas
  ['eua','br'].forEach(k=>{const a=series[k], el=G.linhas[k];
    if(a){el.interrupt();el.attr('opacity',k==='br'?1:.9);animarCaminho(el,a,x,y,y(ref),dur);}
    else el.transition(tr()).attr('opacity',0);});
  // pontos trimestrais
  G.pontos.selectAll('*').remove();
  if(p.tri)['eua','br'].forEach(k=>{if(!series[k])return;G.pontos.append('g').selectAll('circle').data(series[k].filter(q=>q[1]!=null)).join('circle')
    .attr('cx',q=>x(q[0])).attr('cy',q=>y(q[1])).attr('r',3).attr('fill',COR[k]).attr('opacity',0).transition().delay(dur*.6).duration(dur?300:0).attr('opacity',1);});
  // anotações: saem, e as novas entram depois das linhas
  G.notas.selectAll('g.n').transition().duration(dur?180:0).attr('opacity',0).remove();
  const n=G.notas.append('g').attr('class','n').attr('opacity',0);
  [['eua',d.res_eua,d.pts_eua],['br',d.res_br,d.pts_br]].forEach(([k,r,a])=>{if(!r||r.reacao==null)return;const t=xT(r.reacao,p),v=val(a,t);if(v==null)return;
    n.append('circle').attr('cx',x(t)).attr('cy',y(v)).attr('r',6.5).attr('fill','#0E1828').attr('stroke',COR[k]).attr('stroke-width',2.5);});
  if(d.defasagem!=null&&d.res_eua&&d.res_br&&d.res_eua.reacao!=null&&d.res_br.reacao!=null){
    const a=x(xT(d.res_eua.reacao,p)), b=x(xT(d.res_br.reacao,p)), yy=m.t+16;
    const gd=n.append('g').attr('stroke','#E7C27D').attr('fill','none').attr('stroke-width',1.6);
    gd.append('path').attr('d',`M${a} ${yy-6}V${yy+6}`);
    gd.append('path').attr('d',`M${a} ${yy}H${a}`).transition().delay(dur*.9).duration(dur?450:0).attr('d',`M${a} ${yy}H${b}`);
    gd.append('path').attr('d',`M${b} ${yy-6}V${yy+6}`).attr('opacity',0).transition().delay(dur*.9+(dur?400:0)).duration(dur?150:0).attr('opacity',1);
    n.append('text').attr('x',Math.max(a,b)+8).attr('y',yy+4).attr('fill','#E7C27D').attr('font-size',12.5).attr('font-weight',500)
      .text(d.defasagem===0?'reagiram juntos':`defasagem: ${d.defasagem>0?'+':'−'}${tempo(Math.abs(d.defasagem),p)}`);
  }
  const rb=d.res_br, ab=d.pts_br;
  if(rb&&rb.extremo!=null&&rb.amplitude!=null){const t=xT(rb.extremo,p),v=val(ab,t);if(v!=null){
    n.append('circle').attr('cx',x(t)).attr('cy',y(v)).attr('r',6).attr('fill',COR.br).attr('stroke','#0E1828').attr('stroke-width',2);
    const cabe=y(v)+26<H-m.b-18;n.append('text').attr('x',x(t)).attr('y',cabe?y(v)+24:y(v)-14).attr('text-anchor','middle').attr('paint-order','stroke').attr('stroke','#0E1828').attr('stroke-width',5).attr('fill','#EAF0F7').attr('font-size',12.5).text(`pior momento: ${sinal(rb.amplitude)}${unid(p)}`);}}
  if(rb&&rb.recup!=null){const t=xT(rb.recup,p);if(t<=48){const v=val(ab,t);if(v!=null)
    n.append('rect').attr('x',x(t)-5).attr('y',y(v)-5).attr('width',10).attr('height',10).attr('transform',`rotate(45 ${x(t)} ${y(v)})`).attr('fill',COR.br).attr('stroke','#0E1828').attr('stroke-width',2);}}
  if(!series.br&&!p.sem_par)n.append('text').attr('x',(m.l+Wg-m.r)/2+60).attr('y',y(ref)+40).attr('text-anchor','middle').attr('fill','#A9B6C8').attr('font-size',14).text('Brasil: sem série para este período');
  n.transition().delay(dur*.75).duration(dur?350:0).attr('opacity',1);
}

/* ---------- números que contam ---------- */
const antigo={};
function contar(el,chave,para,formata){
  const de=antigo[chave]; antigo[chave]=para;
  if(para==null||de==null||!MOV||de===para){el.textContent=formata(para);return;}
  d3.select(el).interrupt().transition().duration(650).ease(EASE).tween('text',()=>{const i=d3.interpolateNumber(de,para);return k=>{el.textContent=formata(i(k))}});
}
function desenharMedidas(){
  const p=parDe(estado.par), d=p.eps[estado.ep], rb=d.res_br, re=d.res_eua, el=document.getElementById('medidas');
  const linhaComp=(k,txt)=>`<div class="comp"><i style="background:${COR[k]}"></i>${txt}</div>`;
  let defc='Sem defasagem calculada.';
  if(p.sem_par)defc='Não há série equivalente nos EUA para comparar.';
  else if(d.defasagem!=null)defc=d.defasagem===0?`Brasil e EUA reagiram no mesmo ${p.tri?'trimestre':'mês'}.`:`${p.tri?'Trimestres':'Meses'} entre a reação dos EUA e a do Brasil. O Brasil reagiu ${d.defasagem>0?'depois':'antes'}.`;
  else if(d.status==='SEM_DADOS')defc='Não há série brasileira neste período.';
  else if(rb&&rb.st_reacao!=='OK')defc='A série brasileira não passou do limite de reação.';
  else if(re&&re.st_reacao!=='OK')defc='A série americana não passou do limite de reação.';
  const nap=r=>r&&r.st_recup==='NAO_APLICAVEL';
  const pior=r=>r&&r.amplitude!=null?`${sinal(r.amplitude)}${unid(p)}`:(nap(r)?'não se aplica':'—');
  const rec=r=>!r?'—':nap(r)?'não se aplica':r.recup!=null?tempo(r.recup,p):(r.st_recup==='RECUPERACAO_NAO_OBSERVADA'?'não voltou em 60 meses':'—');
  if(!el.dataset.pronto){el.dataset.pronto=1;el.innerHTML=[1,2,3].map(i=>`<div class="medida"><h4></h4><div class="valor num"><span class="n"></span><span class="u" style="font-size:.45em;color:var(--texto2)"></span></div><div class="cmp"></div></div>`).join('');}
  const [m1,m2,m3]=el.querySelectorAll('.medida');
  m1.querySelector('h4').textContent='Defasagem da reação';
  m2.querySelector('h4').textContent='Pior momento, em relação ao pico';
  m3.querySelector('h4').textContent='Volta ao nível do pico';
  // defasagem
  const n1=m1.querySelector('.n');
  if(p.sem_par){antigo.d=null;n1.textContent='sem par';m1.querySelector('.u').textContent='';}
  else if(d.defasagem!=null){contar(n1,'d',d.defasagem,v=>{v=Math.round(v);return v===0?'0':(v>0?'+':'−')+Math.abs(v)});m1.querySelector('.u').textContent=d.defasagem!==0?(p.tri?' trim.':(Math.abs(d.defasagem)===1?' mês':' meses')):'';}
  else{antigo.d=null;n1.textContent='—';m1.querySelector('.u').textContent='';}
  m1.querySelector('.cmp').innerHTML=`<div class="comp">${defc}</div>`;
  // pior momento
  const n2=m2.querySelector('.n');
  if(rb&&rb.amplitude!=null)contar(n2,'p',rb.amplitude,v=>`${sinal(v)}${unid(p)}`);else{antigo.p=null;n2.textContent=rb?pior(rb):'—';}
  m2.querySelector('.cmp').innerHTML=linhaComp('br','Brasil')+(re?linhaComp('eua','EUA: '+pior(re)):'');
  // recuperação
  const n3=m3.querySelector('.n'), u3=m3.querySelector('.u');
  if(rb&&rb.recup!=null){contar(n3,'r',rb.recup,v=>String(Math.round(v)));u3.textContent=' '+(p.tri?(rb.recup===1?'trimestre':'trimestres'):(rb.recup===1?'mês':'meses'));n3.parentElement.style.fontSize='';}
  else{antigo.r=null;const t=rb?rec(rb):'—';n3.textContent=t;u3.textContent='';n3.parentElement.style.fontSize=t.length>12?'26px':'';}
  m3.querySelector('.cmp').innerHTML=linhaComp('br','Brasil')+(re?linhaComp('eua','EUA: '+rec(re)):'');
  const av=[];
  if(['juros','inflacao'].includes(p.id))av.push('Juros e inflação podem subir ou cair numa recessão, conforme a política de cada banco central. Por isso, para eles, o estudo mede só a reação e a defasagem.');
  if(p.id.startsWith('export'))av.push('As exportações brasileiras são comparadas à produção industrial americana, que representa a demanda dos EUA pelos produtos de outros países.');
  if(p.sem_par)av.push('Câmbio real efetivo calculado pela OCDE. Queda do índice indica desvalorização do real.');
  if(p.tri)av.push('O PIB é trimestral: cada ponto representa um trimestre, e as medidas são contadas em trimestres.');
  if(d.difmet)av.push('Diferenças entre as séries: '+d.difmet.replace(/\.?$/,'.'));
  const fonte=[d.eua&&`EUA: ${d.eua.nome} (${d.eua.fonte}, ${d.eua.codigo})`,d.br&&`Brasil: ${d.br.nome} (${d.br.fonte}, ${d.br.codigo})`].filter(Boolean).join('. ');
  document.getElementById('aviso').innerHTML=av.join(' ')+(fonte?`<br><span style="font-size:13px">${fonte}.</span>`:'');
}

/* ---------- três crises (persistente) ---------- */
let T=null;
function desenharTres(){
  const p=parDe(estado.par), el=document.getElementById('tres');
  const Wm=300,Hm=150,m={t:8,r:6,b:18,l:6};
  const x=d3.scaleLinear().domain([-24,48]).range([m.l,Wm-m.r]);
  const [lo,hi]=escalaY(p,EPS.map(e=>e.id)); const y=d3.scaleLinear().domain([lo,hi]).range([Hm-m.b,m.t]);
  const ref=p.tipo==='nivel'?100:0, trocouPar=!T||T.par!==p.id;
  if(!T){T={cards:{}};el.innerHTML='';
    EPS.forEach(epi=>{const b=document.createElement('button');b.type='button';b.className='mini';
      b.innerHTML=`<h5>${ROT[epi.id]}</h5><p></p>`;
      const s=d3.select(b).append('svg').attr('viewBox',`0 0 ${Wm} ${Hm}`).attr('aria-hidden','true');
      s.append('rect').attr('x',x(0)).attr('y',m.t).attr('width',Math.max(1.5,x(epi.meses)-x(0))).attr('height',Hm-m.b-m.t).attr('fill','rgba(170,190,220,.08)');
      const rl=s.append('line').attr('x1',m.l).attr('x2',Wm-m.r).attr('stroke','#2A3C5C');
      s.append('line').attr('x1',x(0)).attr('x2',x(0)).attr('y1',m.t).attr('y2',Hm-m.b).attr('stroke','#5A6B86').attr('stroke-dasharray','2 3');
      const li={eua:s.append('path').attr('fill','none').attr('stroke',COR.eua).attr('stroke-width',1.6),br:s.append('path').attr('fill','none').attr('stroke',COR.br).attr('stroke-width',2)};
      s.append('text').attr('x',x(0)).attr('y',Hm-4).attr('text-anchor','middle').attr('fill','#728199').attr('font-size',11).text('pico');
      const sd=s.append('text').attr('x',Wm/2+40).attr('y',Hm/2+30).attr('text-anchor','middle').attr('fill','#A9B6C8').attr('font-size',12).attr('opacity',0).text('Brasil: sem dados');
      b.onclick=()=>{estado.ep=epi.id;atualizar();};
      el.appendChild(b);T.cards[epi.id]={b,rl,li,sd};});}
  T.par=p.id;
  EPS.forEach(epi=>{const d=p.eps[epi.id], c=T.cards[epi.id];
    c.b.setAttribute('aria-pressed',epi.id===estado.ep);
    if(!trocouPar)return;
    const def=p.sem_par?'Só Brasil':d.defasagem!=null?(d.defasagem===0?`Reagiram no mesmo ${p.tri?'trimestre':'mês'}`:`Defasagem: ${d.defasagem>0?'+':'−'}${tempo(Math.abs(d.defasagem),p)}`):(d.status==='SEM_DADOS'?'Sem série brasileira':'Sem defasagem calculada');
    c.b.querySelector('p').textContent=def;
    c.rl.transition().duration(DUR).ease(EASE).attr('y1',y(ref)).attr('y2',y(ref));
    [['eua',d.pts_eua],['br',d.pts_br]].forEach(([k,a])=>{const el=c.li[k];
      if(a.length){el.interrupt().attr('opacity',1);animarCaminho(el,a,x,y,y(ref),DUR);}else el.transition().duration(DUR).attr('opacity',0);});
    c.sd.transition().duration(DUR).attr('opacity',!d.pts_br.length&&!p.sem_par?1:0);});
}

function desenharMapa(){
  const t=document.getElementById('mapa');
  const max=15;
  let h=`<thead><tr><th>Indicador</th>${EPS.map(e=>`<th>${ROT[e.id]}</th>`).join('')}</tr></thead><tbody>`;
  D.pares.filter(p=>!p.sem_par).forEach(p=>{
    h+=`<tr data-par="${p.id}"><td>${p.nome}</td>`;
    EPS.forEach(e=>{const d=p.eps[e.id];
      if(d.defasagem==null){const motivo=d.status==='SEM_DADOS'?'sem série brasileira':(d.res_br&&d.res_br.st_reacao!=='OK'?'Brasil não reagiu':'EUA não reagiram');h+=`<td data-ep="${e.id}"><div class="cel"><span class="vazio">${motivo}</span></div></td>`;return;}
      const v=d.defasagem, w=96, c=w/2, px=Math.max(-1,Math.min(1,v/max))*c;
      const svg=`<svg width="${w}" height="14" aria-hidden="true"><line x1="0" x2="${w}" y1="7" y2="7" stroke="#1C2B42"/><line x1="${c}" x2="${c}" y1="0" y2="14" stroke="#4A5F84"/><rect x="${Math.min(c,c+px)}" y="3" width="${Math.max(3,Math.abs(px))}" height="8" rx="2" fill="#C9D3E0"/></svg>`;
      h+=`<td data-ep="${e.id}"><div class="cel">${svg}<span class="v">${v===0?'mesmo '+(p.tri?'trim.':'mês'):(v>0?'+':'−')+Math.abs(v)+(p.tri?' trim.':' m')}</span></div></td>`;});
    h+='</tr>';});
  t.innerHTML=h+'</tbody>';
  t.querySelectorAll('tbody td[data-ep]').forEach(td=>td.onclick=()=>{estado.par=td.parentElement.dataset.par;estado.ep=td.dataset.ep;atualizar();document.getElementById('manchete').scrollIntoView({behavior:MOV?'smooth':'auto',block:'center'})});
  t.querySelectorAll('tbody td:first-child').forEach(td=>td.onclick=()=>{estado.par=td.parentElement.dataset.par;atualizar();document.getElementById('manchete').scrollIntoView({behavior:MOV?'smooth':'auto',block:'center'})});
}

/* ---------- seletor com marcador deslizante ---------- */
function moverPilula(){const b=seg.querySelector('[aria-pressed=true]');if(!b)return;const pl=seg.querySelector('.pilula');pl.style.width=b.offsetWidth+'px';pl.style.transform=`translateX(${b.offsetLeft-4}px)`;}
seg.insertAdjacentHTML('afterbegin','<span class="pilula" aria-hidden="true"></span>');
function alinharPilula(){const pl=seg.querySelector('.pilula');pl.style.transition='none';moverPilula();pl.offsetWidth;pl.style.transition='';}
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(alinharPilula);
new ResizeObserver(alinharPilula).observe(seg);

function trocarTexto(el,html){
  if(!MOV||el.innerHTML===html){el.innerHTML=html;return;}
  el.classList.add('trocando');setTimeout(()=>{el.innerHTML=html;el.classList.remove('trocando')},160);
}
function atualizar(animar=true){
  trilho.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.par===estado.par));
  seg.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.ep===estado.ep));
  moverPilula();
  const p=parDe(estado.par), d=p.eps[estado.ep];
  trocarTexto(document.getElementById('manchete'),textoManchete(p,estado.ep,d));
  document.getElementById('submanchete').textContent=p.tipo==='nivel'?'Índice com o mês de pico igual a 100. Círculos vazios marcam a reação de cada país; o losango, a volta do Brasil ao nível do pico.':'Diferença em pontos percentuais em relação ao mês de pico. Círculos vazios marcam a reação de cada país.';
  document.querySelectorAll('#mapa tbody tr').forEach(r=>r.classList.toggle('ativo',r.dataset.par===estado.par));
  document.querySelectorAll('#mapa tbody td[data-ep]').forEach(td=>td.classList.toggle('ativo',td.parentElement.dataset.par===estado.par&&td.dataset.ep===estado.ep));
  desenharPrincipal(animar);desenharMedidas();desenharTres();
}
desenharMapa();atualizar(false);
let rz,larg=graf.clientWidth;new ResizeObserver(()=>{if(graf.clientWidth===larg)return;larg=graf.clientWidth;clearTimeout(rz);rz=setTimeout(()=>{G=null;desenharPrincipal(false);moverPilula()},80)}).observe(graf);
})();
