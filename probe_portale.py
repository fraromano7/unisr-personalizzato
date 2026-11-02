import requests, re
from bs4 import BeautifulSoup
from datetime import date
from collections import Counter

BASE="https://orario.unisr.it/default.asp"
S=requests.Session()
S.headers["User-Agent"]="Mozilla/5.0 (compatible; UniSR-diagnostica/1.0)"

def params(day,course="10324",year="2"):
    p={"ext":"ok","data":day.strftime("%d/%m/%Y"),
       "CDS_ID":course,"DAORA":"0","ANNO_CORSO":year,
       "id_palazzo":"0","id_aula":"0","lezioni":"ok"}
    return {k:v for k,v in p.items() if v is not None}

D=[date(2026,10,12),date(2026,10,19),date(2026,10,26),
   date(2026,11,2),date(2026,11,9),date(2026,11,16),
   date(2026,11,23),date(2026,11,30),date(2026,12,7),
   date(2026,12,14)]
try:
    r=S.get(BASE,timeout=20)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    for select in soup.find_all("select"):
        opts=[(o.get("value"),o.get_text(" ",strip=True)) for o in select.select("option")]
        print("SELECT",select.get("name"),select.get("id"),"COUNT",len(opts),
              "EXAMPLE",opts[:6])
        print("MEDICINA-ELETTIVI",[
            x for x in opts if "medicina" in x[1].lower() or "elettiv" in x[1].lower()
        ][:25])
except Exception as e:
    print("FORM ERROR",str(e)[:200])

for name,cid,year in [
    ("med3-y2","10324","2"),
    ("med3-y3","10324","3"),
    ("med3-no-year","10324",None),
    ("med3-year0","10324","0"),
    ("all-courses","0","0"),
    ("no-filters",None,None)]:
    confirmed=0
    found=[]
    samples=[]
    for day in D:
        try:
            r=S.get(BASE,params=params(day,cid,year),timeout=22)
            r.raise_for_status()
            soup=BeautifulSoup(r.text,"html.parser")
            body=soup.get_text(" ",strip=True)
            if day.strftime("%d/%m/%Y") in body:
                confirmed+=1
            if re.search(r"burn[ -]?out",body,re.I):
                rows=[re.sub(r"\s+"," ",x.get_text(" ",strip=True))[:300]
                    for x in soup.find_all("tr")
                    if re.search(r"burn[ -]?out",x.get_text(" ",strip=True),re.I)]
                found.append((day.isoformat(),rows[:4]))
            if len(samples)<2:
                samples.append((day.isoformat(),len(r.content),body[-120:]))
        except Exception as e:
            print("CASE ERROR",name,day,str(e)[:180])
    print("CASE",name,"confirmed",confirmed,"found",found,"samples",samples,flush=True)
