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
  // atmosfera
  let g=ctx.createRadialGradient(cx,cy,R*.92,cx,cy,R*1.25);g.addColorStop(0,'rgba(91,143,217,.16)');g.addColorStop(1,'rgba(91,143,217,0)');
  ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,R*1.25,0,7);ctx.fill();
  // esfera
  g=ctx.createRadialGradient(cx-R*.35,cy-R*.4,R*.1,cx,cy,R);g.addColorStop(0,'#16294A');g.addColorStop(1,'#0A1426');
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
  desenhar(t);requestAnimationFrame(loop);
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
  return s+'.';
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
  else if(d.defasagem!=null){contar(n1,'d',d.defasagem,v=>{v=Math.round(v);return v===0?'0':(v>0?'+':'−')+Math.abs(v)});m1.querySelector('.u').textContent=d.defasagem!==0?(p.tri?' trim.':' meses'):'';}
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
