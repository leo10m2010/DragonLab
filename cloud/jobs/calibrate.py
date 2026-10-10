"""Generate reviewable candidates from multiple users. Never publishes automatically."""
import collections,hashlib,json,math,os,pathlib,sys,urllib.request
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from calibration_validation import validated_fit

def candidates(rows):
    groups=collections.defaultdict(list)
    for row in rows:
        s=row['sample']
        # A zero-wind regime is identifiable without guessing the wind response.
        if s['wind']!=0:continue
        ratio=math.hypot(s['vx'],s['vy'])/s['power']
        regime=f"g{s['ay']:g}-p{round(ratio/.025)*.025:.3f}"
        groups[(row['clone'],row['mobile'],row['shot'],regime)].append(row)
    output=[]
    for (clone,mobile,shot,regime),values in groups.items():
        users=collections.defaultdict(list)
        for row in values:users[row['user_id']].append(row['sample'])
        # Cap each contributor so one account cannot overwhelm the fit.
        eligible=[s[-12:] for s in users.values() if len(s)>=6 and len({x['power'] for x in s})>=3 and max(x['power'] for x in s)-min(x['power'] for x in s)>=60]
        if len(eligible)<3:continue
        samples=[s for user_samples in eligible for s in user_samples]
        try:
            fit=validated_fit(samples)
            errors=[]
            for i,user_samples in enumerate(eligible):
                training=[s for j,u in enumerate(eligible) if j!=i for s in u];trial=validated_fit(training)
                errors.extend(abs(math.hypot(s['vx'],s['vy'])-(trial['power_scale']*s['power']+trial['speed_offset'])) for s in user_samples)
            if max(errors)>5:continue
        except (ValueError,KeyError,TypeError):continue
        fingerprint=hashlib.sha256(json.dumps([clone,mobile,shot,regime,fit],sort_keys=True).encode()).hexdigest()
        output.append({'clone':clone,'mobile':mobile,'shot':shot,'regime':regime,'fit':fit,'contributors':len(eligible),'source_count':len(samples),'evidence':{'held_out_contributor_max_speed_error':max(errors),'wind_scope':'zero','limit_per_contributor':12},'fingerprint':fingerprint})
    return output

def run():
    url=os.environ.get('SUPABASE_URL');key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:print('Cloud calibration skipped: server not configured.');return
    def request(path,body=None,method='GET'):
        req=urllib.request.Request(url+'/rest/v1/'+path,data=json.dumps(body).encode() if body is not None else None,headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':'resolution=ignore-duplicates'},method=method)
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r) if method=='GET' else None
    rows=[]
    for offset in range(0,10000,1000):
        page=request(f'measurements?select=clone,mobile,shot,sample,user_id&order=created_at.desc&limit=1000&offset={offset}');rows.extend(page)
        if len(page)<1000:break
    proposed=candidates(rows)
    if proposed:request('calibration_candidates?on_conflict=fingerprint',proposed,'POST')
    print(f'{len(rows)} measurements checked; {len(proposed)} candidates proposed. No profiles published.')
if __name__=='__main__':run()
