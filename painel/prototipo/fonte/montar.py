"""Monta o index.html autocontido.
Uso: python montar.py [node_modules] [saida]"""
import base64,sys
from pathlib import Path
A=Path(__file__).parent; V=Path(sys.argv[1]) if len(sys.argv)>1 else A/'node_modules'; out=Path(sys.argv[2]) if len(sys.argv)>2 else A.parent/'index.html'
b64=lambda p: base64.b64encode(Path(p).read_bytes()).decode()
h=(A/'pagina.html').read_text(encoding='utf-8')
rep={'/*F_FRAUNCES*/':b64(V/'@fontsource-variable/fraunces/files/fraunces-latin-opsz-normal.woff2'),
 '/*F_PLEX400*/':b64(V/'@fontsource/ibm-plex-sans/files/ibm-plex-sans-latin-400-normal.woff2'),
 '/*F_PLEX500*/':b64(V/'@fontsource/ibm-plex-sans/files/ibm-plex-sans-latin-500-normal.woff2'),
 '/*F_PLEX600*/':b64(V/'@fontsource/ibm-plex-sans/files/ibm-plex-sans-latin-600-normal.woff2'),
 '/*D3*/':(V/'d3/dist/d3.min.js').read_text(),
 '/*PONTOS*/':(A/'pontos.json').read_text(),'/*ALVOS*/':(A/'alvos.json').read_text(),'/*DADOS*/':(A/'dados.json').read_text(encoding='utf-8'),
 '/*APP*/':(A/'app.js').read_text(encoding='utf-8')}
for k,v in rep.items():
    assert h.count(k)==1,k; h=h.replace(k,v)
out.write_text(h,encoding='utf-8'); print(len(h))
