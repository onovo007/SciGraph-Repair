"""Human-authored scientific contracts for optional code-review assistance.

These assertions are suggestions, not a proof of correctness and not universally valid
for all public health datasets. Apply only after validating the statistical definitions.
"""
CONTRACTS={
 'vaccine_coverage': {
    'meaning':'Vaccinated / eligible, represented as a proportion',
    'checks':['Check numerator and denominator represent the same cohort and period',
              'Under ideal consistent counts, 0 <= coverage <= 1; values over 1 can also reflect reporting artifacts',
              'Joint multiplication of counts should preserve the proportion'],
    'example':'assert abs(vaccine_coverage(40,80) - 0.5) < 1e-10'},
 'dropout_rate': {
    'meaning':'(First dose - final dose) / first dose',
    'checks':['Check dose order and denominator','Negative dropout can occur in reported aggregate data',
              'Scaling dose counts together should preserve dropout'],
    'example':'assert abs(dropout_rate(80,60) - 0.25) < 1e-10'},
 'incidence_per_100k': {
    'meaning':'Case count / population * 100,000',
    'checks':['Confirm the scale is per 100,000','Verify person-time or population denominator is appropriate',
              'Joint multiplication of counts and population should preserve rate'],
    'example':'assert abs(incidence_per_100k(5,10000) - 50) < 1e-10'},
 'rolling_mean_past': {
    'meaning':'Trailing window average without future information',
    'checks':['Prefix outputs should not change after future values are appended',
              'Constant inputs should yield constant outputs','Check first-window convention'],
    'example':'assert rolling_mean_past([1,3,9,2],2) == [1,2,6,5.5]'},
 'weighted_rate': {
    'meaning':'Pooled rate equals total events / total denominator',
    'checks':['Do not substitute unweighted mean of stratum rates',
              'Shuffling strata should not change the pooled rate',
              'Joint rescaling of all strata should not change the pooled rate'],
    'example':'assert abs(weighted_rate([(1,10),(80,100)]) - 81/110) < 1e-10'},
 'deduplicate_records': {
    'meaning':'Retain first instance per person identifier',
    'checks':['Check unique identifier semantics across sites',
              'Verify retained-record precedence is as specified',
              'Confirm de-duplication does not silently discard records with incomplete IDs'],
    'example':"assert len(deduplicate_records([{'id':'A'},{'id':'A'}])) == 1"},
 'positivity_rate': {
    'meaning':'Positive test results / number tested',
    'checks':['Numerator should not exceed denominator for coherent linked person counts',
              'Zero positives should produce zero when denominator positive',
              'Counts must refer to the same interval and test-definition'],
    'example':'assert abs(positivity_rate(10,40) - .25) < 1e-10'},
 'cumulative_cases': {
    'meaning':'Running sum of incident counts in chronological order',
    'checks':['For nonnegative incident counts, cumulative output should not decrease',
              'Appending new observations should not change earlier cumulative totals',
              'A zero-case period should preserve the previous cumulative total'],
    'example':'assert cumulative_cases([2,3,1]) == [2,5,6]'},
}

def select_contracts(context, max_contracts=8):
    out=[]
    for n in context.get('selected_symbols',[]):
        name=n['name'].split('.')[-1]
        if name in CONTRACTS:
            out.append({'symbol':n['id'],'line':n['line'],**CONTRACTS[name]})
    return out[:max_contracts]
