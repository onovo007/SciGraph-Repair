# SciGraph Repair

SciGraph Repair investigates how coding agents can locate relevant Python code and check that a proposed repair preserves the scientific meaning of its outputs. A patch can run successfully while returning the wrong quantity. This synthetic pilot tests code localization and the ability of different checks to detect deliberately seeded errors.

## Approach

The retriever indexes Python definitions and call relationships using the abstract syntax tree. It compares lexical retrieval with graph-guided retrieval under the same character budgets. Graph traversal can bring related functions into a compact, read-only context package alongside candidate verification checks. Scanning source does not execute it.

The benchmark executes controlled synthetic fixtures and compares three levels of verification. Smoke checks test basic execution, invariants check properties such as plausible bounds, and semantic checks compare calculations against numerical expectations. All fixtures are synthetic and require no external data.

## Reproduce the pilot

Start with [Kaggle_Reproducible_Pilot.ipynb](Kaggle_Reproducible_Pilot.ipynb). Run all cells with a Python kernel from a fresh scratch directory because the notebook writes the embedded source files and results to its working directory. To run locally, use Python 3.12 and install the notebook interface with `python -m pip install -r requirements.txt`. Then start `jupyter notebook`. Kaggle provides a notebook interface.

The extracted benchmark uses the Python standard library and can also run directly from the repository root:

```sh
python -m unittest discover -s tests -v
python -m benchmark.evaluate
python -m scigraph.cli benchmark/fixture_repo --issue "immunization dashboard shows coverage above 100 percent" --mode graph --chars 1500
```

The evaluator writes `results/pilot_results.json`.

## Findings and limitations

Four unit tests passed. Smoke checks detected 0 of 24 seeded mutations, scientific invariants detected 18 of 24, and semantic checks detected 24 of 24. The retrieval benchmark measured whether the relevant function appeared anywhere in the returned context.

| Character budget | Lexical retrieval | Graph-guided retrieval |
| --- | ---: | ---: |
| 600 | 2/8 | 3/8 |
| 1,200 | 4/8 | 5/8 |
| 2,400 | 8/8 | 8/8 |

Top-ranked localization was 0 of 8 for both methods at every budget. The tasks are few, and test authors knew the mutation types, which can make detection rates optimistic. Static analysis has limited visibility into Python aliases, inheritance, and dynamic dispatch. This experiment did not evaluate Gemma 4, generate patches, or measure real-world repair performance.

## Exploratory extensions

Bayesian behavioral monitoring is a proposed way to track uncertainty about agent behavior across a sequence of observations. Estimating and assessing calibration would require independently labeled traces and held-out evaluation.

Quantum optimization is an exploratory feasibility question for selecting code context under a budget. A meaningful test would compare the same small instances and objective with classical baselines. The reproducible pilot supplies no evidence of quantum advantage.
