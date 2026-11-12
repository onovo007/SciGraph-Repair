"""A minimal dependent analytics pipeline to illustrate graph-guided issue context."""
from epi_analytics import (vaccine_coverage, dropout_rate, incidence_per_100k,
                           rolling_mean_past, weighted_rate, deduplicate_records,
                           positivity_rate, cumulative_cases)

def immunization_dashboard(vaccinated, eligible, first_dose, final_dose):
    return {'coverage':vaccine_coverage(vaccinated, eligible),
            'dropout':dropout_rate(first_dose,final_dose)}

def outbreak_dashboard(cases, population, observations):
    return {'incidence': incidence_per_100k(cases, population),
            'trend': rolling_mean_past(observations,3),
            'cumulative': cumulative_cases(observations)}

def laboratory_dashboard(positive, tested, records):
    deduped = deduplicate_records(records)
    return {'positivity':positivity_rate(positive,tested), 'patients':len(deduped)}

def equity_dashboard(groups):
    return {'pooled_rate':weighted_rate(groups)}
