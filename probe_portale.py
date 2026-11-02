import requests,re
from bs4 import BeautifulSoup
from datetime import date,timedelta
BASE="https://orario.unisr.it/default.asp"
S=requests.Session()
S.headers["User-Agent"]="Mozilla/5.0 (compatible; UniSR-diagnostica/1.0)"
start=date(2026,10,1);end=date(2027,1,15)
days=[]
while start<=end:
    if start.weekday()<5: days.append(start)
    start+=timedelta(days=1)
def request(day,course,year):
    return {"ext":"ok","data":day.strftime("%d/%m/%Y"),"CDS_ID":course,
            "DAORA":"0","ANNO_CORSO":year,"id_palazzo":"0",
            "id_aula":"0","lezioni":"ok"}
for cid,yr in [("10115","3"),("10311","3"),("10325","3"),("10284","3")]:
    hits,displayed,errors,examples=[],0,0,[]
    print("START",cid,yr,"DAYS",len(days),flush=True)
    for d in days:
        try:
            resp=S.get(BASE,params=request(d,cid,yr),timeout=15)
            resp.raise_for_status()
            soup=BeautifulSoup(resp.text,"html.parser")
            body=soup.get_text(" ",strip=True)
            if d.strftime("%d/%m/%Y") in body: displayed+=1
            if d.isoformat() in ("2026-11-02","2026-11-09") and len(examples)<3:
                snippets=[re.sub(r"\s+"," ",tr.get_text(" ",strip=True))[:210]
                         for tr in soup.select("tr") if "Lezione:" in tr.get_text(" ",strip=True)]
                examples.append((d.isoformat(),len(resp.content),snippets[:5]))
            if re.search(r"burn[\s-]?out|stress lavoro.correlato",body,re.I):
                snippets=[re.sub(r"\s+"," ",tr.get_text(" ",strip=True))[:350]
                         for tr in soup.select("tr")
                         if re.search(r"burn[\s-]?out|stress lavoro.correlato",tr.get_text(" ",strip=True),re.I)]
                hits.append((d.isoformat(),snippets[:5]))
        except Exception as e:
            errors+=1
    print("RESULT",cid,yr,"displayed",displayed,"errors",errors,"matches",hits,"examples",examples,flush=True)
