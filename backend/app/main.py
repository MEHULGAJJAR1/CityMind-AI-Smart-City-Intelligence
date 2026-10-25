from datetime import datetime, timezone
from pathlib import Path
import csv, io, os, hashlib, secrets, math
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Float, DateTime, Integer, Text, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DB_URL=os.getenv('DATABASE_URL','sqlite:///./citymind.db')
engine=create_engine(DB_URL, connect_args={'check_same_thread':False} if DB_URL.startswith('sqlite') else {})
SessionLocal=sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); email:Mapped[str]=mapped_column(String,unique=True); password_hash:Mapped[str]=mapped_column(String); role:Mapped[str]=mapped_column(String,default='analyst')
class LoginSession(Base):
 __tablename__='login_sessions'; id:Mapped[int]=mapped_column(primary_key=True); token:Mapped[str]=mapped_column(String,unique=True,index=True); user_id:Mapped[int]=mapped_column(Integer,index=True)
class Observation(Base):
 __tablename__='observations'; id:Mapped[int]=mapped_column(primary_key=True); city:Mapped[str]=mapped_column(String,index=True); category:Mapped[str]=mapped_column(String,index=True); metric:Mapped[str]=mapped_column(String); value:Mapped[float]=mapped_column(Float); unit:Mapped[str]=mapped_column(String,default=''); lat:Mapped[float|None]=mapped_column(Float,nullable=True); lon:Mapped[float|None]=mapped_column(Float,nullable=True); observed_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc)); source:Mapped[str]=mapped_column(String,default='imported')
class Alert(Base):
 __tablename__='alerts'; id:Mapped[int]=mapped_column(primary_key=True); title:Mapped[str]=mapped_column(String); severity:Mapped[str]=mapped_column(String); region:Mapped[str]=mapped_column(String); status:Mapped[str]=mapped_column(String,default='open'); details:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Audit(Base):
 __tablename__='audit_logs'; id:Mapped[int]=mapped_column(primary_key=True); actor:Mapped[str]=mapped_column(String); action:Mapped[str]=mapped_column(String); at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
Base.metadata.create_all(engine)
def db():
 s=SessionLocal()
 try: yield s
 finally: s.close()
def hashpw(p): return hashlib.pbkdf2_hmac('sha256',p.encode(),b'citymind-local-v1',180000).hex()
class Credentials(BaseModel): email:str; password:str=Field(min_length=10); role:str='analyst'
class AlertIn(BaseModel): title:str; severity:str='medium'; region:str='Unspecified'; details:str=''
class Scenario(BaseModel): demand_change_pct:float=Field(ge=-80,le=200); capacity_change_pct:float=Field(ge=-80,le=200)
app=FastAPI(title='CityMind AI API',version='1.0.0',description='Smart-city intelligence APIs. Measurements are stored with source and timestamp; demo sample records are labeled.')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','),allow_methods=['*'],allow_headers=['*'])
def auth(authorization:str|None=Header(default=None),s:Session=Depends(db)):
 if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Authentication required')
 token=authorization[7:]; session=s.scalar(select(LoginSession).where(LoginSession.token==token))
 user=s.get(User,session.user_id) if session else None
 if not user: raise HTTPException(401,'Invalid session')
 return user
@app.get('/health')
def health(): return {'status':'ok','database':'configured','time':datetime.now(timezone.utc).isoformat()}
@app.get('/ready')
def ready(s:Session=Depends(db)): s.execute(select(Observation.id).limit(1)); return {'ready':True}
@app.post('/api/v1/auth/register')
def register(data:Credentials,s:Session=Depends(db)):
 if data.role not in ('viewer','analyst','administrator'): raise HTTPException(422,'Invalid role')
 if s.scalar(select(User).where(User.email==data.email)): raise HTTPException(409,'Email already registered')
 u=User(email=data.email,password_hash=hashpw(data.password),role=data.role); s.add(u); s.commit(); return {'message':'Account created; sign in to continue'}
@app.post('/api/v1/auth/login')
def login(data:Credentials,s:Session=Depends(db)):
 u=s.scalar(select(User).where(User.email==data.email))
 if not u or u.password_hash!=hashpw(data.password): raise HTTPException(401,'Invalid credentials')
 # Opaque local bearer token; production must add expiry/revocation lifecycle.
 token=secrets.token_urlsafe(32); s.add(LoginSession(token=token,user_id=u.id)); s.commit(); return {'access_token':token,'token_type':'bearer','user':{'email':u.email,'role':u.role}}
@app.get('/api/v1/cities')
def cities(s:Session=Depends(db)): return sorted({x[0] for x in s.execute(select(Observation.city)).all()})
@app.get('/api/v1/traffic/observations')
def traffic(city:str='Ahmedabad',limit:int=500,s:Session=Depends(db),u=Depends(auth)):
 rows=s.scalars(select(Observation).where(Observation.city==city,Observation.category=='traffic').order_by(Observation.observed_at.desc()).limit(min(limit,1000))).all(); return [obs(x) for x in rows]
@app.get('/api/v1/environment/observations')
def environment(city:str='Ahmedabad',limit:int=500,s:Session=Depends(db),u=Depends(auth)):
 rows=s.scalars(select(Observation).where(Observation.city==city,Observation.category=='environment').order_by(Observation.observed_at.desc()).limit(min(limit,1000))).all(); return [obs(x) for x in rows]
def obs(x): return {'id':x.id,'city':x.city,'category':x.category,'metric':x.metric,'value':x.value,'unit':x.unit,'lat':x.lat,'lon':x.lon,'observed_at':x.observed_at.isoformat(),'source':x.source}
@app.get('/api/v1/dashboard/summary')
def summary(city:str='Ahmedabad',s:Session=Depends(db),u=Depends(auth)):
 rows=s.scalars(select(Observation).where(Observation.city==city).order_by(Observation.observed_at.desc()).limit(1000)).all()
 traffic=[r.value for r in rows if r.category=='traffic' and r.metric=='congestion_index']; pm=[r.value for r in rows if r.metric=='pm25']; incidents=s.scalar(select(func.count(Alert.id)).where(Alert.status=='open')) or 0
 return {'city':city,'traffic_index':round(sum(traffic)/len(traffic),1) if traffic else None,'pm25':round(sum(pm)/len(pm),1) if pm else None,'open_alerts':incidents,'observation_count':len(rows),'data_status':'imported historical data' if rows else 'no observations','updated_at':max([r.observed_at for r in rows]).isoformat() if rows else None}
@app.get('/api/v1/alerts')
def alerts(status:str|None=None,s:Session=Depends(db),u=Depends(auth)):
 q=select(Alert).order_by(Alert.created_at.desc());
 if status:q=q.where(Alert.status==status)
 return [{'id':a.id,'title':a.title,'severity':a.severity,'region':a.region,'status':a.status,'details':a.details,'created_at':a.created_at.isoformat()} for a in s.scalars(q.limit(200)).all()]
@app.post('/api/v1/alerts')
def create_alert(data:AlertIn,s:Session=Depends(db),u=Depends(auth)):
 a=Alert(**data.model_dump());s.add(a);s.add(Audit(actor=u.email,action='alert.created'));s.commit();return {'id':a.id,'status':a.status}
@app.patch('/api/v1/alerts/{alert_id}/{action}')
def update_alert(alert_id:int,action:str,s:Session=Depends(db),u=Depends(auth)):
 if action not in ('acknowledge','resolve'):raise HTTPException(400,'Action must be acknowledge or resolve')
 a=s.get(Alert,alert_id)
 if not a:raise HTTPException(404,'Alert not found')
 a.status='acknowledged' if action=='acknowledge' else 'resolved';s.add(Audit(actor=u.email,action=f'alert.{action}:{alert_id}'));s.commit();return {'id':a.id,'status':a.status}
@app.post('/api/v1/scenarios')
def scenario(x:Scenario,u=Depends(auth)):
 # Transparent illustrative index relation, not a causal forecast.
 baseline=100.0; ratio=(1+x.demand_change_pct/100)/(1+x.capacity_change_pct/100) if x.capacity_change_pct>-100 else 10
 return {'baseline_index':baseline,'scenario_index':round(max(0,min(300,baseline*ratio)),1),'assumptions':x.model_dump(),'method':'Illustrative proportional demand/capacity index; not calibrated to observed outcomes.','limitation':'Directional what-if only; does not establish causality.'}
@app.post('/api/v1/imports/csv')
async def import_csv(file:UploadFile=File(...),s:Session=Depends(db),u=Depends(auth)):
 if not file.filename.lower().endswith('.csv'):raise HTTPException(400,'CSV required')
 raw=await file.read(5_000_001)
 if len(raw)>5_000_000:raise HTTPException(413,'File exceeds 5 MB limit')
 try:
  reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))); required={'city','category','metric','value'}
  if not required.issubset(reader.fieldnames or []):raise ValueError('Required columns: city,category,metric,value')
  count=0
  for r in reader:
   v=float(r['value']); lat=float(r['lat']) if r.get('lat') else None;lon=float(r['lon']) if r.get('lon') else None
   s.add(Observation(city=r['city'][:100],category=r['category'][:40],metric=r['metric'][:80],value=v,unit=r.get('unit','')[:30],lat=lat,lon=lon,source='user_csv')) ;count+=1
  s.commit();return {'imported':count,'source':'user_csv','note':'Timestamps omitted from CSV use ingestion time; imported data is not live.'}
 except Exception as e:s.rollback();raise HTTPException(422,f'Invalid CSV: {e}')
