import os, json, csv, io, uuid
from datetime import datetime
from flask import Flask, send_from_directory, jsonify, request, send_file
from werkzeug.utils import secure_filename

RATES={"Steam":1400,"Apple / iTunes":1350,"【entity-Google Play¦canonical_name=Google Play】":1320,"【entity-Amazon¦canonical_name=Amazon】":1300,"【entity-Sephora¦canonical_name=Sephora】":1280,"【entity-Nike¦canonical_name=Nike】":1250,"【entity-eBay¦canonical_name=eBay】":1220,"USDT TRC20":1685,"USDT BEP20":1675,"Bitcoin":1620}
app=Flask(__name__, static_folder="../", static_url_path="")
# Vercel is serverless - use /tmp for storage (use Supabase later for permanent)
USERS="/tmp/everx_users.json"; TRADES="/tmp/everx_trades.json"; KYC="/tmp/everx_kyc.json"
for f in [USERS,TRADES,KYC]:
    if not os.path.exists(f): open(f,"w").write("[]")
def load(f):
    try: return json.load(open(f))
    except: return []
def save(f,d): json.dump(d,open(f,"w"),indent=2)

@app.route("/")
def home(): return send_from_directory("../","index.html")
@app.route("/admin")
def admin(): return send_from_directory("../","admin.html")
@app.route("/api/rates")
def rates(): return jsonify(RATES)
@app.route("/api/auth",methods=["POST"])
def auth():
    d=request.json; users=load(USERS); u=next((x for x in users if x["email"]==d["email"]),None)
    if d["mode"]=="signup":
        if u: return jsonify({"ok":False,"error":"Email exists - Login"})
        code="EVERX-"+(d.get("name") or "USER").upper().replace(" ","")[:8]+str(len(users)+1)
        u={"email":d["email"],"password":d["password"],"name":d.get("name",""),"phone":d.get("phone",""),"refCode":code,"referredBy":d.get("referredBy",""),"kyc":"Not Submitted","created":datetime.now().isoformat()}
        users.append(u); save(USERS,users)
        return jsonify({"ok":True,"user":{k:v for k,v in u.items() if k!="password"}})
    if not u or u["password"]!=d["password"]: return jsonify({"ok":False,"error":"Wrong email/password"})
    return jsonify({"ok":True,"user":{k:v for k,v in u.items() if k!="password"}})
@app.route("/api/kyc",methods=["POST"])
def kyc():
    k={"email":request.form.get("email"),"name":request.form.get("name"),"idType":request.form.get("idType"),"idNum":request.form.get("idNum"),"status":"Pending Review","date":datetime.now().isoformat()}
    a=load(KYC); a.append(k); save(KYC,a)
    users=load(USERS)
    for u in users:
        if u["email"]==k["email"]: u["kyc"]="Pending Review"
    save(USERS,users); return jsonify({"ok":True})
@app.route("/api/sell",methods=["POST"])
def sell():
    f=request.form; bal=float(f.get("sBal",0) or 0); card=f.get("sCard","Steam"); rate=RATES.get(card,1400); total=int(bal*rate)
    t={"id":f"D{1000+len(load(TRADES))}","email":f.get("email"),"category":f.get("sCat"),"card":card,"country":f.get("sCountry"),"balance":bal,"cardType":f.get("sType"),"rate":rate,"total":total,"code":(f.get("sCode","")[:4]+"****" if f.get("sCode") else "Image Upload"),"bank":f.get("sBank"),"account":f.get("sAcc"),"accName":f.get("sAccName"),"images":2 if request.files.get("img1") else 0,"status":"Pending","date":datetime.now().isoformat(),"adminNote":""}
    a=load(TRADES); a.append(t); save(TRADES,a); return jsonify({"ok":True,"trade":t})
@app.route("/api/my_orders")
def my_orders():
    e=request.args.get("email"); return jsonify([x for x in load(TRADES) if x["email"]==e])
@app.route("/api/admin_all")
def admin_all(): return jsonify({"trades":load(TRADES),"users":load(USERS),"kyc":load(KYC)})
@app.route("/api/set_status",methods=["POST"])
def set_status():
    d=request.json; a=load(TRADES); idx=d.get("index",0)
    if 0<=idx<len(a): a[idx]["status"]=d.get("status","Paid"); a[idx]["adminNote"]=d.get("note",""); save(TRADES,a)
    return jsonify({"ok":True})
@app.route("/api/approve_kyc",methods=["POST"])
def approve_kyc():
    d=request.json; a=load(KYC); idx=d.get("index",0)
    if 0<=idx<len(a): a[idx]["status"]=d.get("status","Approved"); save(KYC,a)
    return jsonify({"ok":True})
@app.route("/api/update_rates",methods=["POST"])
def update_rates():
    global RATES; RATES.update(request.json); return jsonify({"ok":True,"rates":RATES})
@app.route("/api/export_csv")
def export():
    a=load(TRADES); out=io.StringIO(); w=csv.DictWriter(out,fieldnames=["id","date","email","category","card","country","balance","cardType","rate","total","status","bank","account","accName"]); w.writeheader()
    for r in a: w.writerow({k:r.get(k,"") for k in ["id","date","email","category","card","country","balance","cardType","rate","total","status","bank","account","accName"]})
    m=io.BytesIO(); m.write(out.getvalue().encode()); m.seek(0); return send_file(m,as_attachment=True,download_name="EVERX_ALL_TIME.csv",mimetype="text/csv")
@app.route("/health")
def health(): return f"EVERX VERCEL LIVE Steam 1400=70000 Trades:{len(load(TRADES))}"
