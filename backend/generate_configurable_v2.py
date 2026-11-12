"""PennyWise deterministic standalone CSV dataset generator.

Usage:
  python generate_configurable.py --users 2 --transactions-per-user 50 --output-dir test_run1
  python generate_configurable.py --users 1000 --transactions-per-user 500 --output-dir full_run1

This is a NEW generator, not an exact reproduction of the existing 500K SQLite dataset.
No existing database is accessed or modified.
"""
import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 20261022
START = date(2025, 11, 10)
END = date(2026, 11, 9)
CENTS = Decimal('0.01')
FIELDS = {
 'user_profiles':['user_id','full_name','email'],
 'accounts':['account_id','user_id','account_name','account_type'],
 'merchants':['merchant_id','merchant_name'],
 'categories':['category_id','category_name','category_type'],
 'transactions':['transaction_id','user_id','account_id','merchant_id','category_id','transaction_date','description','amount','transaction_type','status','original_transaction_id','transfer_group_id'],
 'ground_truth':['transaction_id','expected_category_id','expected_transaction_type','is_intentionally_uncategorized','issue_type','original_transaction_id','transfer_group_id'],
 'budgets':['budget_id','user_id','category_id','budget_amount','period_start','period_end','status'],
 'recurring_series':['series_id','user_id','account_id','merchant_id','category_id','series_name','expected_amount','frequency','last_payment_date','next_payment_date','occurrence_count','status'],
 'recurring_occurrences':['occurrence_id','series_id','transaction_id','occurrence_date','actual_amount','status'],
 'insights':['insight_id','user_id','insight_type','title','description','severity','status','created_date'],
}

def money(v):
 return str(Decimal(str(v)).quantize(CENTS, rounding=ROUND_HALF_UP))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--users',type=int,default=2)
 p.add_argument('--transactions-per-user',type=int,default=50)
 p.add_argument('--seed',type=int,default=SEED)
 p.add_argument('--output-dir',required=True)
 a=p.parse_args()
 if a.users<1 or a.transactions_per_user<1: p.error('counts must be positive')
 out=Path(a.output_dir).resolve()
 if out.exists() and any(out.iterdir()): p.error('output directory must be new or empty: '+str(out))
 out.mkdir(parents=True,exist_ok=True)
 rng=random.Random(a.seed)
 root=Path(__file__).resolve().parent
 master=root/'reproducibility_tests'
 if not master.exists(): master=root
 def read(name):
  with (master/name).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
 merchants=sorted(read('merchants.csv'),key=lambda x:x['merchant_id'])
 categories=sorted(read('categories.csv'),key=lambda x:x['category_id'])
 mapping={r['merchant_id']:r['category_id'] for r in read('merchant_categories.csv')}
 if len(merchants)!=20 or len(categories)!=7 or len(mapping)!=20: raise ValueError('Unexpected master-data counts')
 if set(mapping)!=set(m['merchant_id'] for m in merchants): raise ValueError('Merchant mapping incomplete')
 merchants.append({'merchant_id':'MER-021','merchant_name':'Rent Payment'})
 mapping['MER-021']='CAT-004'
 names={m['merchant_id']:m['merchant_name'] for m in merchants}
 writers={}; handles={}; counts=defaultdict(int)
 try:
  for table,fields in FIELDS.items():
   handle=(out/(table+'.csv')).open('w',encoding='utf-8',newline='')
   handles[table]=handle
   writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore')
   writer.writeheader();writers[table]=writer
  def emit(table,row):
   writers[table].writerow(row);counts[table]+=1
  for row in merchants: emit('merchants',row)
  for row in categories: emit('categories',row)
  for u in range(1,a.users+1):
   uid=f'USR-{u:06d}'
   emit('user_profiles',{'user_id':uid,'full_name':f'Synthetic User {u:06d}','email':f'synthetic{u:06d}@example.invalid'})
   for acct in (1,2):
    emit('accounts',{'account_id':f'ACC-{uid}-{acct:02d}','user_id':uid,'account_name':f'Account {acct}','account_type':'Checking' if acct==1 else 'Savings'})
   for month in range(12):
    year=2025+(11+month-1)//12
    mon=(11+month-1)%12+1
    first=date(year,mon,1)
    next_month=date(year+1,1,1) if mon==12 else date(year,mon+1,1)
    last=next_month-timedelta(days=1)
    for cat in categories:
     if cat['category_type']!='Expense':continue
     cid=cat['category_id']
     emit('budgets',{'budget_id':f'BUD-{uid}-{year}-{mon:02d}-{cid}','user_id':uid,'category_id':cid,'budget_amount':money(3000+rng.randrange(0,12001,500)),'period_start':first.isoformat(),'period_end':last.isoformat(),'status':'Active'})
   expenses=[]; recurring=defaultdict(list); spending=defaultdict(Decimal)
   pending_transfer=None
   scheduled=[]
   for month in range(12):
    year=2025+(11+month-1)//12
    mon=(11+month-1)%12+1
    dt=date(year,mon,15)
    for mid,kind,amount,cat in (
     ('MER-015','Income',Decimal('50000.00'),'CAT-006'),
     ('MER-021','Expense',Decimal('15000.00'),'CAT-004'),
     ('MER-001','Expense',Decimal('499.00'),'CAT-005')
    ):
     scheduled.append((dt,mid,kind,amount,cat))
   scheduled.sort()
   if a.transactions_per_user<36:
    raise ValueError('V2 requires at least 36 transactions per user')
   for j in range(a.transactions_per_user):
    if j < len(scheduled):
     dt,mid,kind,amt,cat=scheduled[j]
     number=(u-1)*a.transactions_per_user+j+1
     tid=f'TXN-2026-{number:08d}'
     acct=f'ACC-{uid}-01'
     cat='CAT-006' if kind=='Income' else mapping[mid]
     emit('transactions',{'transaction_id':tid,'user_id':uid,'account_id':acct,'merchant_id':mid,'category_id':cat,'transaction_date':dt.isoformat(),'description':names[mid],'amount':money(amt if kind=='Income' else -amt),'transaction_type':kind,'status':'Completed','original_transaction_id':'','transfer_group_id':''})
     emit('ground_truth',{'transaction_id':tid,'expected_category_id':cat,'expected_transaction_type':kind,'is_intentionally_uncategorized':0,'issue_type':'','original_transaction_id':'','transfer_group_id':''})
     recurring[(mid,kind)].append((dt,tid,amt,cat,acct))
     if kind=='Expense':
      expenses.append({'id':tid,'merchant':mid,'date':dt,'remaining':amt})
      spending[cat]+=amt
     continue
    if pending_transfer is not None:
     t=pending_transfer
     pending_transfer=None
     number=(u-1)*a.transactions_per_user+j+1
     tid=f'TXN-2026-{number:08d}'
     credit_acct=f'ACC-{uid}-{2 if t["account"].endswith("-01") else 1:02d}'
     emit('transactions',{'transaction_id':tid,'user_id':uid,'account_id':credit_acct,'merchant_id':t['merchant'],'category_id':'CAT-007','transaction_date':t['date'],'description':'Transfer received','amount':money(t['amount']),'transaction_type':'Transfer','status':'Completed','original_transaction_id':'','transfer_group_id':t['group']})
     emit('ground_truth',{'transaction_id':tid,'expected_category_id':'CAT-007','expected_transaction_type':'Transfer','is_intentionally_uncategorized':0,'issue_type':'','original_transaction_id':'','transfer_group_id':t['group']})
     continue
    number=(u-1)*a.transactions_per_user+j+1
    tid=f'TXN-2026-{number:08d}'
    acct=f'ACC-{uid}-{rng.randint(1,2):02d}'
    merchant=rng.choice(merchants);mid=merchant['merchant_id']
    kind=rng.choices(['Expense','Income','Transfer'],weights=[82,11,7])[0]
    if j%30==0:kind='Income';mid='MER-015'
    txdate=START+timedelta(days=rng.randrange(365))
    original='';group='';issue='';uncat=False
    if expenses and rng.random()<0.03:
     eligible=[e for e in expenses if e['date']<END and e['remaining']>=Decimal('0.02')]
     if eligible:
      e=rng.choice(eligible);kind='Refund';mid=e['merchant'];original=e['id']
      maximum=min((END-e['date']).days,30)
      txdate=e['date']+timedelta(days=rng.randint(1,maximum))
      amt=(e['remaining']/2).quantize(CENTS,rounding=ROUND_HALF_UP)
      if amt>e['remaining']:amt=e['remaining']
      e['remaining']-=amt
    if kind!='Refund':
     amt=Decimal(rng.randint(1500000,10000000))/100 if kind=='Income' else Decimal(rng.randint(5000,1000000))/100
     if kind=='Expense' and txdate.month in (10,11,12) and mid in ('MER-002','MER-012','MER-013'):amt=(amt*Decimal('1.30')).quantize(CENTS)
    if kind=='Transfer' and j<a.transactions_per_user-1:
     group=f'TRF-{number:09d}'
     pending_transfer={'account':acct,'merchant':mid,'date':txdate.isoformat(),'amount':amt,'group':group}
    elif kind=='Transfer':
     kind='Expense'
    cat='CAT-006' if kind=='Income' else 'CAT-007' if kind=='Transfer' else mapping[mid]
    if kind=='Expense' and rng.random()<0.05:uncat=True;issue='AMBIGUOUS_CATEGORY'
    desc=names[mid]
    if rng.random()<0.35:desc=rng.choice((desc.upper(),desc+' ONLINE',desc+' PAYMENT'))
    emit('transactions',{'transaction_id':tid,'user_id':uid,'account_id':acct,'merchant_id':mid,'category_id':'' if uncat else cat,'transaction_date':txdate.isoformat(),'description':desc,'amount':money(-amt if kind in ('Expense','Transfer') else amt),'transaction_type':kind,'status':'Completed','original_transaction_id':original,'transfer_group_id':group})
    emit('ground_truth',{'transaction_id':tid,'expected_category_id':cat,'expected_transaction_type':kind,'is_intentionally_uncategorized':int(uncat),'issue_type':issue,'original_transaction_id':original,'transfer_group_id':group})
    if kind=='Expense':
     expenses.append({'id':tid,'merchant':mid,'date':txdate,'remaining':amt})
     spending[cat]+=amt
    elif kind=='Refund':spending[cat]-=amt
   for (mid,kind),events in sorted(recurring.items()):
    events.sort()
    if len(events)<3:continue
    rid=f'REC-{u:06d}-{mid.split("-")[-1]}-{kind[:3].upper()}'
    latest=events[-1][0]
    next_year = latest.year + (1 if latest.month == 12 else 0)
    next_month = 1 if latest.month == 12 else latest.month + 1
    nxt = date(next_year, next_month, 15)
    emit('recurring_series',{'series_id':rid,'user_id':uid,'account_id':events[-1][4],'merchant_id':mid,'category_id':events[-1][3],'series_name':names[mid],'expected_amount':money(sum(x[2] for x in events)/len(events)),'frequency':'Monthly','last_payment_date':latest.isoformat(),'next_payment_date':nxt.isoformat(),'occurrence_count':len(events),'status':'Active'})
    for n,(dt,tx,amt,_,_) in enumerate(events,1):
     emit('recurring_occurrences',{'occurrence_id':f'OCC-{u:06d}-{mid.split("-")[-1]}-{kind[:3].upper()}-{n:04d}','series_id':rid,'transaction_id':tx,'occurrence_date':dt.isoformat(),'actual_amount':money(amt),'status':'Matched'})
   if spending:
    topcat,topamt=max(spending.items(),key=lambda x:x[1])
    emit('insights',{'insight_id':f'INS-{u:06d}-01','user_id':uid,'insight_type':'Spending Summary','title':'Top spending category','description':f'{topcat}: {money(topamt)} net spending','severity':'Info','status':'Active','created_date':END.isoformat()})
   if u%100==0:print(f'Generated {u:,}/{a.users:,} users',flush=True)
 finally:
  for h in handles.values():h.close()
 checksums={}
 for table in FIELDS:
  h=hashlib.sha256()
  with (out/(table+'.csv')).open('rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  checksums[table+'.csv']=h.hexdigest()
 manifest={'generator':'generate_configurable_v2.py','seed':a.seed,'users':a.users,'transactions_per_user':a.transactions_per_user,'date_start':START.isoformat(),'date_end':END.isoformat(),'counts':dict(counts),'sha256':checksums,'note':'New reproducible CSV generator; does not reproduce pre-existing SQLite database byte-for-byte. Ground truth is separate from transactions input.'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print('DONE:',out,'transactions:',counts['transactions'],'ground_truth:',counts['ground_truth'])
 print('Transactions SHA-256:',checksums['transactions.csv'])

if __name__=='__main__':main()
