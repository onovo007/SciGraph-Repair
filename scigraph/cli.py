"""CLI for read-only code repository context generation."""
import argparse,json
from .graph import build_context

def main():
    p=argparse.ArgumentParser(description='Build a budgeted code-graph context pack for small offline coding agents')
    p.add_argument('repository',help='Python repository directory (read only)')
    p.add_argument('--issue',required=True,help='Issue description')
    p.add_argument('--mode',choices=['lexical','graph'],default='graph')
    p.add_argument('--chars',type=int,default=4500)
    args=p.parse_args()
    print(json.dumps(build_context(args.repository,args.issue,args.mode,args.chars),indent=2))

if __name__=='__main__':main()
