import sys; sys.path.insert(0,__import__("os").environ["CCN_WORK"] + '/D')
import numpy as np, pandas as pd, itertools
from model import *
data=load(); p=build_parcels(2025,data)
print(len(p), p.p_test_imputed.mean().round(3), p.n_surplus.describe().round(1).to_dict())
dev=pd.read_csv(ROOT/'tasks/dev/D1_dev_catchments_2025.csv').set_index('catchment_id')
def evalL(Lp,Ln,kr=1.0):
    s=catchment_sums(p,field_losses(p,Lp,Ln,kr)).join(dev,how='inner')
    out={}
    for a,b in (('P','apetit_p_to_water_kg'),('N','apetit_n_to_water_kg')):
        lr=np.log10(s[b]/s[a]); 
        loo=[abs(lr.iloc[i]-lr.drop(lr.index[i]).mean()) for i in range(len(lr))]
        out[a]=(np.mean(loo), lr.std(), 10**lr.mean())
    return out
for Lp in [150,250,400,700,1500,1e9]:
    for Ln in [300,700,1500,1e9]:
        r=evalL(Lp,Ln); print(Lp,Ln, 'P loo %.3f'%r['P'][0],'N loo %.3f'%r['N'][0])
print('---')
for Ln in [100,200,300,450]:
    print(Ln, evalL(400,Ln))
s=catchment_sums(p,field_losses(p,400,300)).join(dev,how='inner')
print(np.log10(s.apetit_p_to_water_kg/s.P).round(3).to_dict(), np.log10(s.apetit_n_to_water_kg/s.N).round(3).to_dict())
