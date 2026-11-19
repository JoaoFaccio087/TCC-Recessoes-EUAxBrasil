"""Gera dados.json a partir de uma edição publicada pela pipeline (contrato v1).
Uso: python dados.py <pasta da edição>"""
import duckdb, json, math, sys
ED=sys.argv[1]
q=lambda s: duckdb.sql(s.replace('@',ED+'/')).df()
nn=lambda v: None if v is None or (isinstance(v,float) and math.isnan(v)) or str(v) in ('NaT','<NA>','nan','None') else v
ds=q("select * from '@dim_serie.parquet'").set_index('id_serie')
ep=q("select * from '@dim_episodio.parquet' order by pico_mensal")
po=q("select * from '@ponte_serie_br_eua.parquet'")
res=q("select * from '@fato_resumo_episodio.parquet'")
cm=q("select * from '@fato_comparacao.parquet'")
am=q("select * from '@fato_serie_alinhada_mensal.parquet'")
at=q("select * from '@fato_serie_alinhada_trimestral.parquet'")
edi=q("select * from '@dim_edicao.parquet'").iloc[0]
EPI=[]
for r in ep.itertuples():
    p,v=r.pico_mensal,r.vale_mensal; d=(v.year-p.year)*12+v.month-p.month
    EPI.append({'id':r.id_episodio,'pico':str(p)[:7],'vale':str(v)[:7],'meses':d})
ORD=['producao_industrial','desemprego','juros','inflacao','pib','acoes','exportacoes_total','exportacoes_eua']
NOME={'producao_industrial':'Produção industrial','desemprego':'Desemprego','juros':'Juros','inflacao':'Inflação','pib':'PIB',
      'acoes':'Bolsa de valores','exportacoes_total':'Exportações totais','exportacoes_eua':'Exportações para os EUA','cambio':'Câmbio real'}
def serie(i):
    s=ds.loc[i]; return {'id':i,'nome':s.nome,'fonte':s.fonte,'codigo':str(s.codigo_origem),'unidade':s.unidade,'produtor':str(s.produtor)}
def pts(i,e,tri):
    t=(at if tri else am); t=t[(t.id_serie==i)&(t.id_episodio==e)].sort_values('t_rel')
    lim=(-8,16) if tri else (-24,48)
    return [[int(r.t_rel)*(3 if tri else 1), None if nn(r.valor_painel) is None else round(float(r.valor_painel),3), str(r.data_ref)[:7]] for r in t.itertuples() if lim[0]<=r.t_rel<=lim[1]]
def resumo(i,e):
    r=res[(res.id_serie==i)&(res.id_episodio==e)]
    if r.empty: return None
    r=r.iloc[0]; f=lambda x: None if nn(x) is None else (int(x) if isinstance(x,(int,)) or float(x).is_integer() else round(float(x),2))
    return {'reacao':f(r.t_reacao),'extremo':f(r.t_extremo),'amplitude':None if nn(r.amplitude) is None else round(float(r.amplitude),2),
            'recup':f(r.t_recuperacao),'st_reacao':r.status_reacao,'st_recup':r.status_recuperacao}
PARES=[]
for pid in ORD:
    linhas=po[po.id_par==pid]; tri=pid=='pib'; tipo=ds.loc[linhas.iloc[0].id_serie_eua].tipo_medida
    item={'id':pid,'nome':NOME[pid],'tri':tri,'tipo':tipo,'grupo':linhas.iloc[0].grupo,'eps':{}}
    for e in EPI:
        l=linhas[linhas.id_episodio==e['id']].iloc[0]; c=cm[(cm.id_par==pid)&(cm.id_episodio==e['id'])].iloc[0]
        br=nn(l.id_serie_br); ue=l.id_serie_eua
        item['eps'][e['id']]={'eua':serie(ue),'br':serie(br) if br else None,'pts_eua':pts(ue,e['id'],tri),'pts_br':pts(br,e['id'],tri) if br else [],
            'res_eua':resumo(ue,e['id']),'res_br':resumo(br,e['id']) if br else None,
            'defasagem':None if nn(c.defasagem) is None else int(c.defasagem),'status':c.status,'motivo':nn(c.motivo),
            'difmet':nn(l.diferencas_metodologicas)}
    PARES.append(item)
# câmbio sem par
cam={'id':'cambio','nome':'Câmbio real','tri':False,'tipo':'nivel','grupo':'Câmbio real','sem_par':True,'eps':{}}
for e in EPI:
    cam['eps'][e['id']]={'eua':None,'br':serie('br_cambio_real'),'pts_eua':[],'pts_br':pts('br_cambio_real',e['id'],False),'res_eua':None,
        'res_br':resumo('br_cambio_real',e['id']),'defasagem':None,'status':'SEM_PAR','motivo':'sem série equivalente nos EUA','difmet':None}
PARES.append(cam)
out={'edicao':{'id':edi.id_edicao,'corte':str(edi.data_corte)[:10]},'episodios':EPI,'pares':PARES}
from pathlib import Path
json.dump(out,open(Path(__file__).parent/'dados.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(len(json.dumps(out)), EPI)
for p in PARES: print(p['id'],p['tipo'],[ (k,v['defasagem'],v['status']) for k,v in p['eps'].items()])
