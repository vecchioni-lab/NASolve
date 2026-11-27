"""Shared passive diffraction checks for compact native workers.

These are the unchanged public metal audit implementations. Their original
modules re-export them; no source, scaling or phase acceptance rule is added.
"""
import hashlib
import math

from .recipe import RecipeError, canonical, digest, number


def audit_reflections(before, after, *, anomalous=True):
    """Permit only common F/sigma scale; require declared anomalous state.

    Frozen fdp callers retain the strict anomalous=True default. The separate
    MLHL geometry audit explicitly requests merged observations.
    """
    if type(anomalous)is not bool:raise RecipeError("Require explicit anomalous boolean")
    for captured in (before,after):
        rows=captured['rows']
        if (captured.get('anomalous') is not anomalous or type(captured.get('count')) is not int
                or captured['count']!=len(rows) or not rows):
            raise RecipeError('Missing observations with the required anomalous state')
        keys=[]
        for row in rows:
            if (not isinstance(row,list) or len(row)!=4 or not isinstance(row[0],list)
                    or len(row[0])!=3 or any(type(v)is not int for v in row[0]) or type(row[3])is not bool):
                raise RecipeError('Invalid reflection identity/flag evidence')
            number(row[1],'F observation')
            if number(row[2],'sigma observation')<=0:raise RecipeError('Nonpositive observation sigma')
            keys.append(tuple(row[0]))
        if len(set(keys))!=len(keys) or keys!=sorted(keys):raise RecipeError('Duplicate or unsorted reflection evidence')
        free=sum(row[3] for row in rows)
        if free!=captured.get('free_count') or not 0<free<len(rows):raise RecipeError('Invalid Free-R membership')
        if hashlib.sha256(canonical(rows).encode()).hexdigest()!=captured['hash']:
            raise RecipeError('Reflection signature differs from evidence')
    first,last=before['rows'],after['rows']
    if len(first)!=len(last) or any(a[0]!=b[0] or a[3]!=b[3] for a,b in zip(first,last)):
        raise RecipeError('Reflection indices or Free-R assignments changed')
    index=max(range(len(first)),key=lambda i:abs(first[i][1]))
    if first[index][1]==0:raise RecipeError('All amplitudes are zero')
    scale=number(last[index][1]/first[index][1],'native amplitude scale')
    if scale<=0:raise RecipeError('Native amplitude scale is nonpositive')
    absolute=0.;relative=0.
    for a,b in zip(first,last):
        for field in (1,2):
            wanted=a[field]*scale;delta=abs(b[field]-wanted)
            absolute=max(absolute,delta);relative=max(relative,delta/max(1.,abs(wanted)))
            if not math.isclose(b[field],wanted,rel_tol=1e-10,abs_tol=1e-9):
                raise RecipeError('Observations changed beyond a uniform F/sigma scale')
    return dict(input_hash=before['hash'],output_hash=after['hash'],count=len(first),
                anomalous=anomalous,free_count=before['free_count'],uniform_F_sigma_scale=scale,
                maximum_absolute_residual=absolute,maximum_relative_residual=relative,
                relative_tolerance=1e-10,absolute_tolerance=1e-9,indices_and_flags='UNCHANGED')



def audit_phases(before, after, reflection_indices):
    for capture in (before,after):
        rows=capture['rows'];keys=[]
        if not rows or type(capture['count'])is not int or capture['count']!=len(rows):
            raise RecipeError('Missing active phase evidence')
        for key,values in rows:
            if (not isinstance(key,list) or len(key)!=3 or any(type(x)is not int for x in key)
                    or not isinstance(values,list) or len(values)!=4):raise RecipeError('Invalid phase row')
            for v in values:number(v,'HL coefficient')
            keys.append(tuple(key))
        if keys!=sorted(set(keys)) or keys!=reflection_indices:
            raise RecipeError('Active phases must cover exactly the refinement reflection indices')
        if digest(rows)!=capture['hash']:raise RecipeError('Phase signature changed')
    if canonical(before)!=canonical(after):raise RecipeError('Active phase coefficients changed during refinement')
    return dict(status='UNCHANGED',hash=before['hash'],count=before['count'])

