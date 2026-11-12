"""Standard-library-only repository-graph retrieval. Does not execute target code."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import ast
import json
import math
import re

STOP = set('a an the is are of for in it to with on from and or that this when after before than into by be i we should fix bug incorrect wrong value data code issue error results unexpected function reports report gives returning return'.split())

def tokens(s: str):
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    return [w for w in re.findall(r'[a-z0-9]+', s.lower().replace('_',' ')) if w not in STOP and len(w) >= 2]

def inspect_repository(root: str | Path):
    """Parse .py files in root (read only), returning nodes & static call edges."""
    root = Path(root).resolve()
    nodes = {}; calls = defaultdict(list)
    for path in sorted(root.rglob('*.py')):
        if any(x in path.parts for x in ('.git','.venv','venv','__pycache__')):
            continue
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(path))
        except (UnicodeError, SyntaxError, OSError):
            continue
        rel = path.relative_to(root).as_posix()
        for unit in tree.body:
            funcs = []
            if isinstance(unit, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs = [(unit,unit.name)]
            elif isinstance(unit,ast.ClassDef):
                funcs = [(member, unit.name+'.'+member.name) for member in unit.body if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef))]
            for fn, name in funcs:
                id_ = f'{rel}::{name}'
                snip = ast.get_source_segment(source,fn) or ''
                call_names=[]
                for n in ast.walk(fn):
                    if isinstance(n,ast.Call):
                        if isinstance(n.func,ast.Name): call_names.append(n.func.id)
                        elif isinstance(n.func,ast.Attribute): call_names.append(n.func.attr)
                nodes[id_] = {'id':id_,'file':rel,'name':name,'line':fn.lineno,
                              'source':snip,'doc':ast.get_docstring(fn) or '', 'call_names':call_names}
    by_short=defaultdict(list)
    for nid,n in nodes.items(): by_short[n['name'].split('.')[-1]].append(nid)
    edges=[]
    for nid,n in nodes.items():
        for short in n['call_names']:
            for target in by_short.get(short,[]):
                if target != nid:
                    edges.append({'source':nid,'target':target,'relation':'calls'})
    edges=sorted({(e['source'],e['target']) for e in edges})
    return {'root':str(root),'nodes':list(nodes.values()),
            'edges':[{'source':a,'target':b,'relation':'calls'} for a,b in edges]}

def _idf(n, query_words, document_count):
    return sum((1 + math.log((document_count+1)/(1+n.get(w,0)))) for w in query_words if w in n)

def rank_nodes(graph, issue, mode='graph', budget_chars=4500):
    """Contrast lexical retrieval with local dependency propagation."""
    nodes={n['id']:n for n in graph['nodes']}
    if not nodes: return []
    query=set(tokens(issue)); corpus={}
    for k,node in nodes.items():
        words=tokens(node['file']+' '+node['name']+' '+node['doc']+' '+node['source'])
        corpus[k]=Counter(words)
    df=Counter(w for cnt in corpus.values() for w in cnt)
    N=len(nodes)
    base={}
    for k,cnt in corpus.items():
        # Weighted token relevance plus exact symbol-name cues. Absolute scale non-essential.
        base[k] = sum((1+math.log(cnt[w])) * math.log(1+(N+1)/(df[w]+1)) for w in query if cnt[w] > 0)
        label=set(tokens(nodes[k]['name']+' '+nodes[k]['file']))
        base[k]+=2.2*len(query.intersection(label))
    vals=dict(base)
    if mode=='graph':
        neighborhood=defaultdict(set)
        for edge in graph['edges']:
            u,v=edge['source'],edge['target']; neighborhood[u].add(v); neighborhood[v].add(u)
        for _ in range(2):
            vals={n:0.80*base[n]+0.20*sum(vals.get(nb,0)/max(1,len(neighborhood[nb])) for nb in neighborhood[n]) for n in nodes}
    order=sorted(nodes,key=lambda k:(-vals[k],k))
    chars=0; selected=[]
    for k in order:
        n=nodes[k]; footprint=min(len(n['source']),1100)+len(k)+80
        if selected and chars+footprint>budget_chars: continue
        if footprint>budget_chars and not selected: footprint=budget_chars
        selected.append({**n,'score':round(vals[k],5),'snippet':n['source'][:max(100,min(1100,budget_chars-chars))]})
        chars+=footprint
    return selected

def build_context(root, issue, mode='graph', budget_chars=4500):
    g=inspect_repository(root)
    chosen=rank_nodes(g,issue,mode,budget_chars)
    selected=set(n['id'] for n in chosen)
    relevant_edges=[e for e in g['edges'] if e['source'] in selected and e['target'] in selected]
    result={'issue':issue,'mode':mode,'character_budget':budget_chars,
            'total_symbols':len(g['nodes']),'total_edges':len(g['edges']),
            'selected_symbols':chosen,'selected_edges':relevant_edges,
            'disclaimer':'Static AST edges are approximations; dynamic dispatch and aliasing are not fully resolved. No bug fix is generated.'}
    from .contracts import select_contracts
    result['verification_candidates']=select_contracts(result)
    return result
