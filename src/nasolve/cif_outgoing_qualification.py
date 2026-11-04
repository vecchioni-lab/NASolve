"""Cumulative native gates for explicitly selected outgoing-oxygen candidates."""
from __future__ import annotations

from collections import Counter
import json

from .cif_terminal_qualification import _proxy_subset, qualify_terminal_bundle

OUTGOING_QUALIFICATION_POLICY='cif-native-outgoing-bundle-checks-v1'


def baseline_replay_checks(captured: dict, baseline: dict) -> list[dict]:
    """Require the fresh unchanged baseline to reproduce the captured evidence."""
    checks=[]
    def check(name,passes,**evidence):
        checks.append({'check':'captured-baseline-replay:'+name,'status':'PASS' if passes else 'REVIEW',**evidence})
    check('model',captured.get('atoms')==baseline.get('atoms'))
    def rows(native):
        return Counter(json.dumps(r,sort_keys=True) for r in native['monomer_mappings']['rows'])
    check('site-mappings-and-definitions',rows(captured)==rows(baseline))
    check('custom-requests',captured['geometry'].get('custom_proxy_requests')==baseline['geometry'].get('custom_proxy_requests'))
    kinds=set(captured['geometry'].get('proxy_details',{}))|set(baseline['geometry'].get('proxy_details',{}))
    for kind in sorted(kinds):
        try:
            left,right=_proxy_subset(captured,set(),kind),_proxy_subset(baseline,set(),kind)
            check('proxies:'+kind,left==right,missing=sum((left-right).values()),extra=sum((right-left).values()))
        except (KeyError,TypeError,ValueError) as exc:check('proxies:'+kind,False,error=str(exc))
    return checks


def qualify_outgoing_bundle(baseline: dict, candidate: dict, preparations: list[dict],
        expected_links, free_sites, projections, *, captured_baseline: dict,
        reviewed_torsions=None) -> dict:
    """Keep every terminal/link/proxy/charge gate and add replay/registration."""
    report=qualify_terminal_bundle(baseline,candidate,preparations,expected_links,free_sites,
        projections,reviewed_torsions=reviewed_torsions)
    report['checks'].extend(baseline_replay_checks(captured_baseline,baseline))
    before={r['site']:r.get('chem_mod_ids',{}) for r in baseline['monomer_mappings']['rows']}
    after={r['site']:r.get('chem_mod_ids',{}) for r in candidate['monomer_mappings']['rows']}
    expected={s:set(r.get('ids',[])) for s,r in before.items()}
    failures=[]
    for preparation in preparations:
        for plan in preparation['sites']:
            if not plan.get('outgoing_correction'):continue
            site=plan['site'];prior=set(plan['prior_modification_ids'])
            if before.get(site,{}).get('status')!='RECORDED' or expected.get(site)!=prior:
                failures.append({'site':site,'reason':'Prior native modifier IDs differ from preparation evidence'})
            expected.setdefault(site,set()).add(plan['modification_id'])
    for site,ids in expected.items():
        actual=after.get(site,{})
        if actual.get('status')!='RECORDED' or set(actual.get('ids',[]))!=ids:
            failures.append({'site':site,'expected':sorted(ids),'observed':actual})
    if set(before)!=set(after):failures.append({'reason':'Native site identity inventory changed'})
    report['checks'].append({'check':'exact-native-site-modification-ids',
        'status':'REVIEW' if failures else 'PASS','failures':failures})
    report['audit_kind']='cif_outgoing_native_bundle_qualification'
    report['policy_id']=OUTGOING_QUALIFICATION_POLICY
    report['status']='OUTGOING_BUNDLE_MECHANICS_PASS' if all(c['status']=='PASS' for c in report['checks']) else 'REVIEW'
    return report
