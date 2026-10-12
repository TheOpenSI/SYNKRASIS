import pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
d = pd.read_csv('df3.csv')
cols = {'score': ['abstract_algebra_score','anatomy_score','astronomy_score'],
        'zscore': ['abstract_algebra_zscore','anatomy_zscore','astronomy_zscore']}
colors = {'abstract_algebra':'#4c78a8','anatomy':'#59a14f','astronomy':'#b07aa1','general':'#e15759'}
fig = plt.figure(figsize=(16,8))
for i,(k,c) in enumerate(cols.items()):
    ax = fig.add_subplot(1,2,i+1,projection='3d')
    for s in ['abstract_algebra','anatomy','astronomy','general']:
        g = d[d.expected_service==s]
        ax.scatter(g[c[0]],g[c[1]],g[c[2]],c=colors[s],label=s,
                   s=28 if s=='general' else 12, alpha=.9 if s=='general' else .35,
                   marker='^' if s=='general' else 'o')
    ax.set_xlabel('abstract_algebra'); ax.set_ylabel('anatomy'); ax.set_zlabel('astronomy')
    ax.set_title(f'{k}s by expected service'); ax.view_init(25,45)
    if i==0: ax.legend()
plt.tight_layout()
plt.savefig('scores_3d.png',dpi=140)
