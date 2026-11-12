"""Deterministic, seeded mutation audit using an original synthetic epidemiology library.

This is an engineering feasibility experiment, NOT an assessment of Gemma 4 patch accuracy.
Every mutated function is executed in an isolated in-memory namespace controlled here.
Never use this pattern to load arbitrary untrusted source code.
"""
from pathlib import Path
import json, math, types, statistics, sys
from scigraph.graph import inspect_repository, rank_nodes

HERE=Path(__file__).resolve().parent
SOURCE=(HERE/'fixture_repo'/'epi_analytics.py').read_text(encoding='utf-8')
MUTANTS={
 'vaccine_coverage':[
  ('reversed_denominator','return vaccinated / eligible','return eligible / vaccinated'),
  ('offset_numerator','return vaccinated / eligible','return (vaccinated + 10) / eligible'),
  ('percent_proportion_mixup','return vaccinated / eligible','return vaccinated / eligible * 100'),
 ],
 'dropout_rate':[
  ('wrong_denominator','return (first_dose - final_dose) / first_dose','return (first_dose - final_dose) / final_dose'),
  ('retention_not_dropout','return (first_dose - final_dose) / first_dose','return final_dose / first_dose'),
  ('negative_values_hidden','return (first_dose - final_dose) / first_dose','return abs(first_dose - final_dose) / first_dose'),
 ],
 'incidence_per_100k':[
  ('per_1000_not_100k','return cases / population * 100000','return cases / population * 1000'),
  ('case_pseudocount','return cases / population * 100000','return (cases + 1) / population * 100000'),
  ('off_by_100_denominator','return cases / population * 100000','return cases / (population - 100) * 100000'),
 ],
 'rolling_mean_past':[
  ('future_window','window_values = values[max(0, i - window + 1):i + 1]','window_values = values[i:min(len(values), i + window)]'),
  ('lookahead_leakage','window_values = values[max(0, i - window + 1):i + 1]','window_values = values[max(0, i - window + 1):i + 2]'),
  ('one_period_too_short','window_values = values[max(0, i - window + 1):i + 1]','window_values = values[max(0, i - window + 2):i + 1]'),
 ],
 'weighted_rate':[
  ('unweighted_group_average','return sum(n for n, d in group_counts) / sum(d for n, d in group_counts)','return sum(n / d for n,d in group_counts) / len(group_counts)'),
  ('numerator_denominator_swapped','return sum(n for n, d in group_counts) / sum(d for n, d in group_counts)','return sum(d for n, d in group_counts) / sum(n for n, d in group_counts)'),
  ('added_denominator_offset','return sum(n for n, d in group_counts) / sum(d for n, d in group_counts)','return sum(n for n, d in group_counts) / (sum(d for n, d in group_counts)+10)'),
 ],
 'deduplicate_records':[
  ('inverted_condition',"if rec['id'] not in seen:","if rec['id'] in seen:"),
  ('compound_person_site_key',"seen.add(rec['id'])","seen.add(rec['id'] + rec['site'])"),
  ('unexpected_reverse_order','output.append(rec)','output.insert(0, rec)'),
 ],
 'positivity_rate':[
  ('reversed_denominator','return positive / tested','return tested / positive'),
  ('numerator_pseudocount','return positive / tested','return (positive + 1) / tested'),
  ('wrong_denominator_offset','return positive / tested','return positive / (tested + 10)'),
 ],
 'cumulative_cases':[
  ('reset_each_period','total += x','total = x'),
  ('count_periods_not_cases','total += x','total += 1'),
  ('subtract_cases','total += x','total -= x'),
 ]
}

ISSUES=[
 ('immunization_dashboard results show vaccine coverage too high for eligible population','vaccine_coverage'),
 ('immunization_dashboard drop-off wrong even when dose counts are inconsistent','dropout_rate'),
 ('outbreak_dashboard reports a suspiciously low disease burden','incidence_per_100k'),
 ('outbreak_dashboard trend changes when newer periods are appended','rolling_mean_past'),
 ('equity_dashboard changes with different population sizes across strata','weighted_rate'),
 ('laboratory_dashboard patient count inflated by cross-site records','deduplicate_records'),
 ('laboratory_dashboard infection positivity appears implausible','positivity_rate'),
 ('outbreak_dashboard running total decreases after reporting new cases','cumulative_cases'),
]

def approx(a,b): return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)

def example_records():
    return [{'id':'A','site':'X','stamp':1},{'id':'B','site':'Y','stamp':2},{'id':'A','site':'Z','stamp':3}]

def smoke_ok(m, fn):
    try:
        args={
            'vaccine_coverage':(40,80), 'dropout_rate':(80,60),
            'incidence_per_100k':(5,10000), 'rolling_mean_past':([1,3,9,2],2),
            'weighted_rate':([(1,10),(80,100)],),
            'deduplicate_records':(example_records(),),
            'positivity_rate':(10,40),'cumulative_cases':([2,3,1],)
        }[fn]
        value=getattr(m,fn)(*args)
        if isinstance(value, list):
            return all(isinstance(x,(int,float,dict)) for x in value)
        return isinstance(value,(int,float)) and math.isfinite(value)
    except Exception: return False

def invariant_ok(m, fn):
    """Non-oracle metamorphic checks; does not supply exact expected clinical values."""
    try:
        f=getattr(m,fn)
        if fn=='vaccine_coverage':
            return approx(f(40,80),f(80,160)) and approx(f(0,80),0) and 0<=f(40,80)<=1
        if fn=='dropout_rate':
            return approx(f(80,60),f(160,120)) and f(80,100)<0 and f(80,60)>0
        if fn=='incidence_per_100k':
            return approx(f(5,10000),f(10,20000)) and approx(f(0,10000),0)
        if fn=='rolling_mean_past':
            a=f([1,3,9,2],2); b=f([1,3,9,2,1000],2)
            return len(a)==4 and all(approx(x,y) for x,y in zip(a,b[:4])) and approx(f([7]*5,3)[-1],7)
        if fn=='weighted_rate':
            pairs=[(1,10),(80,100)]
            return approx(f(pairs),f([(n*2,d*2) for n,d in pairs])) and approx(f(pairs),f(list(reversed(pairs))))
        if fn=='deduplicate_records':
            a=f(example_records())
            return len(a)==2 and len({x['id'] for x in a})==2 and a[0]['stamp']==1
        if fn=='positivity_rate':
            return approx(f(10,40),f(20,80)) and approx(f(0,40),0) and 0<=f(10,40)<=1
        if fn=='cumulative_cases':
            a=f([2,3,1]); b=f([2,3,1,9]);return len(a)==3 and a==b[:3] and a==sorted(a)
    except Exception: return False
    return False

def semantic_ok(m, fn):
    """Domain anchors + invariants. These held-in-code values constitute a seeded test oracle."""
    try:
        f=getattr(m,fn)
        anchors={
         'vaccine_coverage':lambda: approx(f(40,80),.5) and approx(f(75,100),.75),
         'dropout_rate':lambda: approx(f(80,60),.25) and approx(f(80,100),-.25),
         'incidence_per_100k':lambda: approx(f(5,10000),50) and approx(f(0,20000),0),
         'rolling_mean_past':lambda: all(approx(x,y) for x,y in zip(f([1,3,9,2],2),[1,2,6,5.5])),
         'weighted_rate':lambda: approx(f([(1,10),(80,100)]),81/110) and approx(f([(0,100),(2,2)]),2/102),
         'deduplicate_records':lambda: [rec['id'] for rec in f(example_records())]==['A','B'],
         'positivity_rate':lambda: approx(f(10,40),.25) and approx(f(0,40),0),
         'cumulative_cases':lambda: f([2,3,1])==[2,5,6]
        }
        return invariant_ok(m,fn) and anchors[fn]()
    except Exception: return False

def load_source(text):
    m=types.ModuleType('controlled_seeded_epi_analytics')
    exec(compile(text,'controlled_seeded_epi_analytics.py','exec'),m.__dict__)
    return m

def wilson(successes,total,z=1.96):
    if total==0: return [None,None]
    p=successes/total; den=1+z*z/total
    center=(p+z*z/(2*total))/den
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [round(center-half,4),round(center+half,4)]

def main():
    control=load_source(SOURCE)
    control_results={fn:{'smoke_pass':smoke_ok(control,fn),'invariant_pass':invariant_ok(control,fn),'semantic_pass':semantic_ok(control,fn)} for fn in MUTANTS}
    assert all(all(v.values()) for v in control_results.values()),control_results
    records=[]
    for fn, variants in MUTANTS.items():
        for label,old,new in variants:
            assert SOURCE.count(old)==1,(fn,label,SOURCE.count(old))
            mutated=load_source(SOURCE.replace(old,new,1))
            records.append({'function':fn,'mutation':label,
                'smoke_detected':not smoke_ok(mutated,fn),
                'invariant_detected':not invariant_ok(mutated,fn),
                'semantic_detected':not semantic_ok(mutated,fn)})
    graph=inspect_repository(HERE/'fixture_repo')
    retrieval=[]
    for issue,fn in ISSUES:
        for budget in (600,1200,2400):
            row={'issue':issue,'expected_function':fn,'budget_chars':budget}
            for mode in ('lexical','graph'):
                ranked=rank_nodes(graph,issue,mode,budget)
                row[mode+'_top1']=int(bool(ranked) and ranked[0]['name']==fn)
                row[mode+'_hit']=int(any(n['name']==fn for n in ranked))
                row[mode+'_symbols']=[n['name'] for n in ranked]
            retrieval.append(row)
    total=len(records)
    metrics={}
    for mode in ('smoke','invariant','semantic'):
        s=sum(r[mode+'_detected'] for r in records)
        metrics[mode]={'detected':s,'total':total,'rate':round(s/total,4),'wilson_95':wilson(s,total)}
    retrieval_metrics={}
    for budget in (600,1200,2400):
        subset=[r for r in retrieval if r['budget_chars']==budget]
        retrieval_metrics[str(budget)]={mode:{'top1':sum(r[mode+'_top1'] for r in subset),
                                                  'hit':sum(r[mode+'_hit'] for r in subset),
                                                  'tasks':len(subset)} for mode in ('lexical','graph')}
    result={'experiment':'Controlled, purpose-built synthetic audit. NOT a Gemma 4 assessment.',
            'n_original_functions':len(MUTANTS),'n_mutants':total,'n_retrieval_issues':len(ISSUES),
            'control_checks':control_results,'mutation_detection':metrics,
            'localization':retrieval_metrics,'mutants':records,'retrieval_rows':retrieval,
            'limitations':['Mutations are authored with knowledge of the test oracles, so detection estimates are optimistic.',
                'The synthetic benchmark is tiny and not representative of Kaggle hidden issues.',
                'The localizer is heuristic; no language model, Gemma weights, or patch-generation experiment was run.',
                'Static call graph cannot completely resolve Python aliases, inheritance, or dynamic dispatch.']}
    out=HERE.parent/'results'/'pilot_results.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'mutation_detection':metrics,'localization':retrieval_metrics,'result_file':str(out)},indent=2))

if __name__=='__main__':main()
