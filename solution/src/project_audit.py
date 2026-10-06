"""Record source hashes, runtime and required data registry.
AI-assisted by OpenAI Codex (OpenAI), 2026-09-24; version/date unverified.
"""
import csv, hashlib, importlib, json, platform, sys
from pathlib import Path
from common import DATA, WORKSPACE, output_dir, save_json, extended_path, configure_stdout

def main():
    configure_stdout();out=output_dir('audit')
    versions={m:importlib.import_module(m).__version__ for m in ['numpy','pandas','scipy','sklearn','matplotlib','pyarrow']}
    save_json(out/'environment.json',{'python_executable':sys.executable,'python':sys.version,'platform':platform.platform(),'packages':versions,'matlab_detected':'D:/MATLAB/bin/matlab.exe','matlab_verified_version':'24.2.0.2712019 (R2024b)','seed':20260924})
    base=Path(extended_path(DATA)); records=[]
    for p in sorted(base.rglob('*')):
        if not p.is_file():continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            while chunk:=f.read(1024*1024):h.update(chunk)
        records.append({'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':h.hexdigest()})
    with (out/'raw_source_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);writer.writeheader();writer.writerows(records)
    aa=['slimpajama_quality_signal_sample.jsonl.xz','slimpajama_quality_extended/arxiv_*.jsonl.xz','slimpajama_quality_extended/github_*.jsonl.xz','regmix_tables/train_mixture_1m.csv','regmix_tables/train_pile_loss_1m.csv','regmix_tables/test_mixture_1m.csv','regmix_tables/test_pile_loss_1m.csv','regmix_tables/test_mixture_60m.csv','regmix_tables/test_pile_loss_60m.csv','regmix_tables/test_mixture_1B.csv','regmix_tables/test_pile_loss_1B.csv','regmix_tables/est_mixture_10b.csv','regmix_tables/est_pile_loss_10b.csv','regmix_tables/est_mixture_70b.csv','regmix_tables/est_pile_loss_70b.csv','domain_mapping_guide.csv','regmix_domain_summary.csv','regmix_domain_sample.jsonl.xz']
    bb=['pythia_training_log_existing.csv','cerebras_training_log.csv','training_trajectories/*.csv','scaling_baseline.csv','published_scaling_data.csv','supplementary_NQ_experiment.csv','supplementary_NQ_experiment_expanded.csv','supplementary_NQ_experiment_large.csv','supplementary_large_models.csv','supplementary_large_baseline.csv','open_model_family_metadata.csv','pythia_checkpoint_index.csv']
    cc=['leaderboard_cleaned.csv','leaderboard_enhanced.csv','leaderboard_extended_timeseries.csv','epoch_all_ai_models.csv','loss_benchmark_bridge.csv','loss_benchmark_bridge_expanded.csv','model_architecture_metadata.csv','detailed_results/**/*.json','data/*.parquet','pythia*eval_details/README.md']
    nature_a=['observed','observed','observed']+['observed']*8+['training_subset','estimated','training_subset','estimated','reference_mapping','observed_summary','observed_text']
    nature_b=['observed','semisynthetic','interpolated','published_observed','published_observed','semisynthetic','semisynthetic','semisynthetic_with_extrapolation','reported_metadata','estimated','metadata','metadata']
    nature_c=['observed','observed_plus_metadata_matching','mixed','reported_metadata','mixed_comparability','mixed_comparability','metadata','observed_evaluation','observed_evaluation','documentation_only']
    registry=[]
    for prefix,folder,entries,natures in [('A','A_data_value',aa,nature_a),('B','B_scaling_laws',bb,nature_b),('C','C_efficiency_evolution',cc,nature_c)]:
        assert len(entries)==len(natures)
        for i,(pattern,nature) in enumerate(zip(entries,natures),1):
            paths=list((base/folder).glob(pattern))
            registry.append({'id':f'{prefix}{i}','pattern':f'{folder}/{pattern}','nature_as_documented':nature,'file_count':len(paths),'bytes':sum(p.stat().st_size for p in paths),'question':'1' if prefix=='A' else '2' if prefix=='B' else '3,4' if i==7 else '4','interpretation':'documented provenance; not external authenticity certification'})
    import pandas as pd
    pd.DataFrame(registry).to_csv(out/'dataset_registry.csv',index=False,encoding='utf-8-sig')
    assert len(registry)==40 and all(r['file_count']>0 for r in registry)
    save_json(out/'manifest_summary.json',{'files':len(records),'bytes':sum(r['bytes'] for r in records),'registry_entries':len(registry),'purpose':'baseline hash for subsequent integrity checks; raw files read only'})
    print(json.dumps({'source_files':len(records),'registry_entries':len(registry),'bytes':sum(r['bytes'] for r in records)}))

if __name__=='__main__':main()
