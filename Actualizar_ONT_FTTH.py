#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Observatorio ONT FTTH Mexico: actualización semanal auditable
No utiliza APIs privadas, no elude bloqueos y NUNCA inventa precios.
Uso: python Actualizar_ONT_FTTH.py
Dependencias: exclusivamente la biblioteca estándar de Python 3.10+.
"""
import argparse, csv, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent
HIST=ROOT/"Historico_ONT_FTTH_2026.csv"
TARGETS=ROOT/"Fuentes_Rastreo_ONT_FTTH.csv"
TEMPLATE=ROOT/"Plantilla_Dashboard_ONT.html"
EXTRA=ROOT/"Fuentes_Sin_Precio_ONT.json"
OUTPUT=ROOT/"Dashboard_ONT_FTTH_Mexico.html"
LOG=ROOT/"Log_Actualizaciones_ONT.csv"
STATE=ROOT/"Estado_Monitoreo_ONT.json"
SITE=ROOT/"sitio"

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data=[]
        self.hide=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript"): self.hide+=1
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript") and self.hide: self.hide-=1
    def handle_data(self, data):
        if not self.hide: self.data.append(data)
    def result(self):
        return re.sub(r"\s+"," "," ".join(self.data)).strip()

def read_csv(p):
    with open(p,"r",newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def write_csv(p,rows,cols):
    with open(p,"w",newline="",encoding="utf-8-sig") as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore");wr.writeheader();wr.writerows(rows)
def download(url,cache):
    if url in cache:
        if isinstance(cache[url],Exception):raise cache[url]
        return cache[url]
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; PriceObserver/1.0; +comercial)", "Accept-Language":"es-MX,es;q=0.9"})
    try:
        with urllib.request.urlopen(req,timeout=12) as f:
            data=f.read(7_000_000)
            charset=f.headers.get_content_charset() or "utf-8"
            content=data.decode(charset,errors="replace")
    except Exception as exc:
        cache[url]=exc
        raise
    cache[url]=content
    time.sleep(.25)
    return content
def extract_catalog(text,sku,vendor,skus):
    # First price linked to the exact SKU: avoid neighbors and unrelated banners.
    pat=re.compile(r"(?<![0-9A-Za-z_-])"+re.escape(sku)+r"(?![0-9A-Za-z_-])",re.I)
    candidates=[]
    for m in pat.finditer(text):
        seg=text[m.end():m.end()+650]
        # Stop if another product SKU is encountered before the price.
        next_positions=[n.start() for other in skus if other!=sku for n in re.finditer(
            r"(?<![0-9A-Za-z_-])"+re.escape(other)+r"(?![0-9A-Za-z_-])",seg,re.I)]
        if next_positions:seg=seg[:min(next_positions)]
        if vendor=="RimeIT":
            cand=re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)\s*MXN\s*IVA\s+incluido",seg,re.I)
            if cand:candidates.append(float(cand.group(1).replace(",","")))
            continue
        if vendor=="Estrategias CTS":
            cand=re.search(r"MXN\s*c\s*/\s*IVA\s*\$\s*([\d,]+(?:\.\d{1,2})?)",seg,re.I)
            if cand:candidates.append(float(cand.group(1).replace(",","")))
            continue
        if vendor=="SolucionesIndustriales":
            cand=re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)\s*MXN\s*IVA\s+incluido",seg,re.I)
            if cand:candidates.append(float(cand.group(1).replace(",","")))
            continue
        if vendor=="La Plaza en Línea":
            cand=re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)\s*incluye\s*IVA",seg,re.I)
            if cand:candidates.append(float(cand.group(1).replace(",","")))
            continue
        # In LM or Reysa the listed amount is the first monetary amount immediately after the SKU.
        cand=re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)",seg,re.I)
        if cand:candidates.append(float(cand.group(1).replace(",","")))
    if not candidates: raise ValueError("no se encontró importe inequívoco al lado del SKU")
    if max(candidates)-min(candidates)>1e-2:
        raise ValueError("precios contradictorios en la misma página; requiere inspección manual")
    return candidates[0]

def scrape(r, cache, skus):
    url=r["URL"]; mode=r["Modo"]
    if mode=="shopify":
        # Shopify exposes the current product price in integer cents in product.js
        raw=download(url.rstrip("/")+".js",cache)
        data=json.loads(raw)
        variants=[v for v in data.get("variants",[]) if v.get("available",True)]
        if not variants: raise ValueError("sin variantes disponibles")
        prices=[int(v["price"])/100 for v in variants if v.get("price") is not None]
        if not prices: raise ValueError("sin precio en el JSON de Shopify")
        return min(prices)
    raw=download(url,cache)
    p=TextExtractor();p.feed(raw)
    text=p.result()
    return extract_catalog(text,r["Modelo"],r["Proveedor"],skus)

def update():
    now = datetime.now(ZoneInfo("America/Mexico_City"))
    today = now.strftime("%Y-%m-%d")
    history=read_csv(HIST);monitors=read_csv(TARGETS)
    if not history or not monitors:
        raise RuntimeError("No se encontró base inicial o fuentes: no se sobrescribirá el histórico")
    cols=list(history[0].keys());skus={x["Modelo"] for x in monitors}
    cache={};logs=[];ok=0;errors=0;skipped=0
    existing={(o["Fecha"],o["Proveedor"],o["Modelo"]) for o in history}
    # Seleccionar siempre el último precio REAL registrado, no el orden físico del CSV.
    by_id={(o["Proveedor"],o["Modelo"]):o for o in sorted(history,key=lambda x:x["Fecha"])}
    for t in monitors:
        key=(t["Proveedor"],t["Modelo"])
        if (today,*key) in existing:
            skipped+=1
            logs.append([today,*key,"OMITIDO","Ya existe captura para esta fecha",t["URL"]])
            continue
        try:
            price=scrape(t,cache,skus)
            if not 100<=price<=20000:raise ValueError(f"precio fuera de límites normales: {price}")
            old=by_id.get(key)
            if old:
                oldprice=float(old["Precio_MXN"])
                if not .4*oldprice<=price<=2.6*oldprice:
                    raise ValueError(f"variación excesiva ({oldprice} → {price}); validación manual")
            if old is None:
                raise ValueError("SKU/proveedor no disponible en histórico inicial")
            new=old.copy();new["Fecha"]=today;new["Precio_MXN"]=f"{price:.2f}"
            new["Estatus"]="Disponibilidad no revalidada"
            new["Tipo_fuente"]="Consulta automática de URL pública"
            new["Observaciones"]=f"Captura automatizada; revisar precio en checkout. Anterior: {old['Precio_MXN']} MXN"
            new["Captura"]="HTML / Shopify reconsultado directamente"
            history.append(new);existing.add((today,*key));ok+=1
            logs.append([today,*key,"OK",f"Precio: {price:.2f}",t["URL"]])
        except Exception as exc:
            errors+=1;logs.append([today,*key,"NO VERIFICABLE",str(exc)[:180],t["URL"]])
    history.sort(key=lambda x:(x["Fecha"],x["Proveedor"],x["Modelo"]))
    write_csv(HIST,history,cols)
    have=LOG.exists()
    with open(LOG,"a",newline="",encoding="utf-8-sig") as f:
        wr=csv.writer(f)
        if not have:wr.writerow(["Fecha","Proveedor","Modelo","Estado","Detalle","URL"])
        wr.writerows(logs)
    state = {
        "fecha_ejecucion":now.isoformat(timespec="seconds"),
        "fecha_base":"2026-11-23",
        "total_fuentes":len(monitors),
        "capturas_nuevas":ok,
        "no_verificables":errors,
        "omitidas_por_duplicado":skipped,
        "observaciones_acumuladas":len(history),
        "estatus":"ACTUALIZADO" if ok else ("SIN_PRECIOS_NUEVOS" if errors else "SIN_CAMBIOS"),
        "nota":"Los precios antiguos pueden estar desactualizados; no se rellenan datos fallidos"
    }
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    build_site(history,state)
    print(f"Actualización {today}: {ok} precios, {errors} fuentes no verificables, {skipped} duplicados omitidos.")
    print(f"Histórico: {HIST.name} | Sitio: {SITE / 'index.html'} | Auditoría: {LOG.name}")
    if not ok:print("AVISO: ningún registro nuevo; NO se han fabricado precios.",file=sys.stderr)


def build_site(history=None,state=None):
    if history is None:history=read_csv(HIST)
    if state is None:
        state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {
          "fecha_ejecucion":None,"fecha_base":"2026-11-23","total_fuentes":75,
          "capturas_nuevas":0,"no_verificables":0,"omitidas_por_duplicado":0,
          "observaciones_acumuladas":len(history),"estatus":"PENDIENTE_PRIMERA_EJECUCION"}
    html=TEMPLATE.read_text(encoding="utf-8")
    extra=json.loads(EXTRA.read_text(encoding="utf-8")) if EXTRA.exists() else []
    for marker,obj in [
        ("/*__DATA_JSON__*/",history),("/*__EXTRA_JSON__*/",extra),
        ("/*__STATUS_JSON__*/",state)]:
        if marker not in html:raise RuntimeError(f"Falta marcador de datos en plantilla: {marker}")
        # No permitir etiquetas de cierre de script aunque una fuente añada texto hostil.
        value=json.dumps(obj,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
        html=html.replace(marker,value)
    SITE.mkdir(exist_ok=True)
    (SITE/"index.html").write_text(html,encoding="utf-8")
    (SITE/"historico_ont_ftth.csv").write_bytes(HIST.read_bytes())
    (SITE/"fuentes_rastreo.csv").write_bytes(TARGETS.read_bytes())
    (SITE/"estado_monitoreo.json").write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if LOG.exists():(SITE/"log_actualizaciones.csv").write_bytes(LOG.read_bytes())
    (SITE/"robots.txt").write_text("User-agent: *\nAllow: /\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description="Actualización ONT FTTH México")
    parser.add_argument("--solo-publicar",action="store_true",help="Crear sitio SIN consultar internet ni añadir registros")
    args=parser.parse_args()
    if args.solo_publicar:
        build_site()
        print("Sitio estático reconstruido sin modificar el histórico")
    else:
        update()
if __name__=="__main__":
    main()
