"""Project the specified weight/cut contrast into the declared magnitude strata."""
from decimal import Decimal

from weight_contrasts import case_arrays, classify, pct, put_csv, read_csv, read_json

def main(workspace, output):
    from weight_contrasts import CATALOG_SUBPATH

    HERE = output
    RUN = workspace / 'expected' / CATALOG_SUBPATH / 'runs/run_01'
    receipt = read_json(HERE / 'RESULTS.json')
    assert receipt['status']=='PASS_RETAINED_RECLASSIFICATION_AND_RECALCULATED_STRATA'
    pairs = read_csv(RUN / 'PAIRED_ENDPOINTS.csv')
    results = []
    for row in receipt['sweep']:
        weight = row['weight']
        if weight not in (1.,1.2,1.3):
            continue
        tag = format(weight,'.17g').replace('.','p')
        data = {source: case_arrays(RUN/f'cases/{source}_w{tag}') for source in ('ssn','usgs')}
        indices = {source:{rid:j for j,rid in enumerate(case['ids'])} for source,case in data.items()}
        labels = {source:classify(case,row[source+'_threshold'])['roles'] for source,case in data.items()}
        tally = {}
        for pair in pairs:
            ssn_id,usgs_id = pair['ssn_record_id'],pair['usgs_record_id']
            i,j = indices['ssn'][ssn_id], indices['usgs'][usgs_id]
            m_a = Decimal(data['ssn']['rows'][i]['magnitude'])
            m_b = Decimal(data['usgs']['rows'][j]['magnitude'])
            agree = labels['ssn'][i]==labels['usgs'][j]
            low_a,low_b = m_a<=Decimal('5.2'),m_b<=Decimal('5.2')
            stratum = 'SSN M≤5.2' if low_a else 'SSN M>5.2'
            strata = [stratum] + (['Opposite sides of 5.2'] if low_a!=low_b else [])
            periods = ['all'] + (['evaluation'] if pair['year']>='2021' else [])
            for label in strata:
                for period in periods:
                    n,equal = tally.get((label,period),(0,0))
                    tally[label,period] = (n+1,equal+int(agree))
        for (label,period),(n,equal) in sorted(tally.items()):
            results.append(dict(weight=weight,cut_mode=row['cut_mode'],stratum=label,period=period,n=n,agree=equal,percent=pct(equal,n)))
        assert sum(n for (label,period),(n,equal) in tally.items() if label.startswith('SSN') and period=='all')==889
        assert sum(equal for (label,period),(n,equal) in tally.items() if label.startswith('SSN') and period=='all')==row['full_matches']
        assert sum(equal for (label,period),(n,equal) in tally.items() if label.startswith('SSN') and period=='evaluation')==row['evaluation_matches']
    put_csv(HERE / 'WEIGHT_STRATA_ROLES.csv',results)
