"""First-pass scientific diagnostics, exclusively generated with matplotlib.
AI-assisted: OpenAI Codex/OpenAI, 2026-09-24; exact model/release unverified.
Figure contract: reports/figure_contracts.md. All test rows are plotted.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import OUTPUT, output_dir, configure_stdout

plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
                     'font.size':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,
                     'axes.titlesize':8,'legend.fontsize':7,'axes.spines.right':False,
                     'axes.spines.top':False,'axes.linewidth':.8,'svg.fonttype':'none','pdf.fonttype':42,
                     'savefig.facecolor':'white'})

def save(fig,path):
    fig.savefig(str(path)+'.svg',bbox_inches='tight')
    fig.savefig(str(path)+'.pdf',bbox_inches='tight')
    fig.savefig(path.with_suffix('.png'),dpi=300,bbox_inches='tight')
    plt.close(fig)

def main():
    configure_stdout();out=output_dir('figures')
    data=pd.read_csv(OUTPUT/'mixture/aggregate_predictions.csv')
    metrics=pd.read_csv(OUTPUT/'mixture/metrics.csv')
    colors={'linear':'#336E9C','quadratic':'#CB8247'}
    fig,axes=plt.subplots(1,2,figsize=(183/25.4,86/25.4),gridspec_kw={'width_ratios':[1.2,1]},layout='constrained')
    a,b=axes
    hold=data[data['set'].eq('test_1m')]
    lo=min(hold.observed_or_estimated_mean_loss.min(),hold.predicted_mean_loss.min())-.08
    hi=max(hold.observed_or_estimated_mean_loss.max(),hold.predicted_mean_loss.max())+.08
    a.plot([lo,hi],[lo,hi],color='#888888',linestyle='--',linewidth=.8,zorder=0)
    for family in colors:
        d=hold[hold.model.eq(family)]
        a.scatter(d.observed_or_estimated_mean_loss,d.predicted_mean_loss,s=10,alpha=.5,color=colors[family],label=family.capitalize(),edgecolors='none')
    a.set(xlim=(lo,hi),ylim=(lo,hi),xlabel='Observed mean validation loss',ylabel='Predicted mean validation loss',title='1M held-out recipes (n = 256)')
    a.legend(loc='upper left')
    names=['test_1m','test_60m','test_1B','est_10b','est_70b']
    b.axhline(0,color='#999999',lw=.6)
    b.axvspan(2.6,4.45,color='#EEEEEE',zorder=0)
    for j,family in enumerate(colors):
        d=metrics[metrics.model.eq(family)].set_index('set').loc[names]
        x=np.arange(5)+(j-.5)*.14;rho=d.spearman_equal_domain_mean.to_numpy()
        b.plot(x[:3],rho[:3],marker='o',markersize=4,lw=1,color=colors[family])
        b.scatter(x[3:],rho[3:],marker='o',s=22,facecolor='white',edgecolor=colors[family],linewidth=1)
    b.set(xticks=np.arange(5),xticklabels=['1M\n256','60M\n256','1B\n64','10B\n63','70B\n63'],ylim=(-1,1),ylabel='Spearman rank correlation',xlabel='Model scale / recipe count',title='Observed tests and estimated targets')
    b.text(3.5,.86,'Estimated',ha='center',fontsize=7,color='#666666')
    for tag,ax in zip('ab',axes):ax.text(-.12,1.06,tag,transform=ax.transAxes,fontweight='bold',fontsize=9)
    save(fig,out/'mixture_baseline_diagnostics')
    hold.to_csv(out/'mixture_scatter_source.csv',index=False)
    metrics[metrics.model.isin(colors)&metrics['set'].isin(names)].to_csv(out/'mixture_rank_source.csv',index=False)
    print('Generated mixture_baseline_diagnostics.svg/pdf/png')

if __name__=='__main__':main()
