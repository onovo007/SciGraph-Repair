import unittest
from pathlib import Path
from scigraph.graph import inspect_repository,build_context
from benchmark.evaluate import MUTANTS, SOURCE, load_source, invariant_ok, semantic_ok

ROOT=Path(__file__).resolve().parents[1]
class TestGraph(unittest.TestCase):
    def test_graph_call_edge(self):
        g=inspect_repository(ROOT/'benchmark'/'fixture_repo')
        self.assertTrue(any('immunization_dashboard' in e['source'] and 'vaccine_coverage' in e['target'] for e in g['edges']))
    def test_read_only_context(self):
        obj=build_context(ROOT/'benchmark'/'fixture_repo','vaccine coverage dashboard error',budget_chars=1600)
        self.assertTrue(obj['selected_symbols'])
        self.assertEqual(obj['mode'],'graph')
    def test_mutation_reference(self):
        m=load_source(SOURCE)
        self.assertTrue(all(semantic_ok(m,f) for f in MUTANTS))
    def test_detect_swap(self):
        bad=SOURCE.replace('return vaccinated / eligible','return eligible / vaccinated',1)
        self.assertFalse(semantic_ok(load_source(bad),'vaccine_coverage'))
if __name__=='__main__':unittest.main()
