"""Explicit retained AutoSol rehearsal evidence for a new mixed experiment.

This narrow reader supports the saved NASolve metal-rehearsal receipt dialect.
It preserves EXPERIMENT_ONLY provenance; it never creates ordinary AutoSol
approval, runs a command, places a metal or interprets HA occupancy as fitted Q.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math

from .cif_dictionary_sites import _need, _read
from .metal.context import _reference
from .metal.recipe import element
from .refinement_command_binding import _portable
from .refinement_inputs import _bound_path

POLICY_ID = 'external-autosol-rehearsal-source-v1'
ROLES = ('producer', 'parameters', 'mr_model', 'observations', 'sequence', 'phases', 'heavy_atoms')


def review_external_autosol(run, declaration, *, report, observations, phase_labels):
    """Check exact source roles against the current original MR/data/sequence.

The declaration carries existing checksummed run/dataset/repository references.
Native effective parameters and the recorded command must agree. Historical
command paths are provenance text only, never opened or executed. The caller
separately joins the chosen amplitudes/HL with original Free-R assignments.
"""
    from libtbx import phil
    from iotbx import reflection_file_reader
    from .autosol import _original_phaser_model, _sequence_source, _pdb_atoms, _effective_settings
    _need(isinstance(declaration,dict) and set(declaration)=={
        'policy_id','sources','element','wavelength_A','phase_labels'}, 'Unexpected external AutoSol declaration fields')
    _need(declaration['policy_id']==POLICY_ID, 'Unsupported external AutoSol source policy')
    symbol=element(declaration['element']); wavelength=declaration['wavelength_A']
    _need(type(wavelength) in (int,float) and math.isfinite(wavelength) and wavelength>0,
          'External AutoSol requires an explicit positive wavelength')
    _need(declaration['phase_labels']==phase_labels, 'External AutoSol phase labels differ from request')
    refs=declaration['sources']
    _need(isinstance(refs,dict) and set(refs)==set(ROLES), 'Incomplete external AutoSol source roles')
    paths={}
    for role,ref in refs.items():
        _portable(ref); paths[role]=_bound_path(ref,'external AutoSol '+role,run)
    raw={role:_read(path) for role,path in paths.items()}
    hashes={role:sha256(value).hexdigest() for role,value in raw.items()}
    _need(len(set(paths.values()))==len(ROLES), 'External AutoSol source roles must be distinct')
    _need(_reference(observations,run)==_reference(paths['observations'],run),
          'External AutoSol observations differ from the original parent source')
    mr=_original_phaser_model(run,report)
    _need(_reference(mr,run)==_reference(paths['mr_model'],run), 'External AutoSol MR input differs from the original Phaser model')
    _need(isinstance(report.get('inputs'),dict) and report['inputs'].get('frame_sequence') is not None,
          'External AutoSol requires the frozen frame sequence, not adjacent-file inference')
    sequence,_=_sequence_source(report,run)
    _need(sequence is not None and _reference(sequence,run)==_reference(paths['sequence'],run),
          'External AutoSol sequence differs from the frozen frame input')
    producer=json.loads(raw['producer']); result=producer.get('autosol')
    _need(isinstance(result,dict) and producer.get('status')=='AUTOSOL_OUTPUTS_CAPTURED_NOT_ADOPTED'
          and result.get('adoption')=='EXPERIMENT_ONLY' and type(result.get('exit_code')) is int
          and result['exit_code']==0 and producer.get('production_phase_adoption') is False,
          'Require completed, explicitly unadopted external AutoSol rehearsal evidence')
    _need(result.get('primary_species')==symbol and result.get('additional_species') is None
          and result.get('wavelength')==wavelength and result.get('sites_argument') is None,
          'External AutoSol search identity/wavelength/count policy differs; mixed species need separate support')
    for role,key in [('mr_model','input_model_sha256'),('observations','input_reflections_sha256'),
                     ('sequence','sequence_sha256'),('phases','refinement_data_sha256'),('heavy_atoms','heavy_atom_sha256')]:
        _need(result.get(key)==hashes[role], 'External AutoSol producer differs from '+role)
    version=producer.get('phenix_version_output')
    _need(isinstance(version,str) and bool(version.strip()), 'External AutoSol has no recorded native version')
    command=result.get('command')
    _need(isinstance(command,list) and command and all(isinstance(s,str) and s for s in command),
          'External AutoSol has no recorded native command')
    args={}
    for part in command[1:]:
        _need('=' in part, 'Unsupported external AutoSol command argument')
        key,value=part.split('=',1)
        _need(key not in args, 'Duplicate external AutoSol command argument');args[key]=value
    expected={'autosol.data','autosol.seq_file','autosol.labels','autosol.atom_type','autosol.lambda',
        'autosol.phasing.input_partpdb_file','autosol.model_building.build',
        'autosol.model_building.phase_improve_and_build','autosol.general.nproc'}
    _need(set(args)==expected, 'Unsupported external AutoSol command scope')
    effective=phil.parse(raw['parameters'].decode('utf-8')).extract().autosol
    def scalar(value):
        _need(isinstance(value,list) and len(value)==1 and isinstance(value[0],str),
              'Ambiguous external AutoSol effective scalar')
        return value[0]
    values={'autosol.data':scalar(effective.data),'autosol.seq_file':scalar(effective.seq_file),
        'autosol.labels':scalar(effective.labels),'autosol.atom_type':scalar(effective.atom_type),
        'autosol.phasing.input_partpdb_file':scalar(effective.phasing.input_partpdb_file)}
    _need(all(args[k]==v for k,v in values.items()) and values['autosol.atom_type']==symbol
          and float(args['autosol.lambda'])==float(scalar(getattr(effective,'lambda')))==wavelength
          and effective.sites is None and effective.phasing.mad_ha_add_list is None,
          'External AutoSol command and native effective inputs differ')
    _need(args['autosol.model_building.build']=='False'
          and args['autosol.model_building.phase_improve_and_build']=='False'
          and scalar(effective.model_building.build)=='False'
          and scalar(effective.model_building.phase_improve_and_build)=='False',
          'External AutoSol building scope differs')
    nproc=int(args['autosol.general.nproc'])
    _need(nproc>0 and int(scalar(effective.general.nproc))==nproc
          and _effective_settings(paths['parameters'],nproc)==result.get('effective'),
          'External AutoSol effective controls differ from producer')
    labels=values['autosol.labels'].split()
    _need(labels==result.get('observation_labels'), 'External AutoSol observation labels differ')
    arrays=reflection_file_reader.any_reflection_file(str(observations)).as_miller_arrays()
    chosen=[a for a in arrays if a.info().labels==labels]
    _need(len(chosen)==1 and chosen[0].anomalous_flag() and chosen[0].sigmas() is not None
          and (chosen[0].is_xray_intensity_array() or chosen[0].is_xray_amplitude_array()),
          'External AutoSol lacks its recorded anomalous observations')
    phase_arrays=reflection_file_reader.any_reflection_file(str(paths['phases'])).as_miller_arrays()
    selected=[a for a in phase_arrays if a.info().labels==phase_labels]
    _need(len(selected)==1 and selected[0].is_hendrickson_lattman_array(),
          'External AutoSol lacks the exact requested HL quartet')
    sites=json.loads(json.dumps(_pdb_atoms(paths['heavy_atoms'])))
    _need(sites==result.get('sites') and type(result.get('discovered_site_count')) is int
          and len(sites)==result['discovered_site_count'] and len(sites)>0
          and all(row['element']==symbol.upper() for row in sites),
          'External AutoSol heavy-atom output differs from producer')
    _need(all(all(math.isfinite(v) for v in row['coordinates'])
              and math.isfinite(row['occupancy']) and row['occupancy']>=0 for row in sites),
          'External AutoSol has nonfinite coordinates or invalid discovery occupancy')
    _need(all(_read(paths[role])==value for role,value in raw.items()), 'External AutoSol source changed during read')
    return paths['phases'], dict(policy_id=POLICY_ID,status='EXTERNAL_SOURCE_INPUTS_VERIFIED',
        declaration=deepcopy(declaration),phase_origin='external-declared-autosol',
        producer_scope='EXPERIMENT_ONLY',native_version=version,sites=sites,
        occupancy_interpretation='RAW_DISCOVERY_OUTPUT_NOT_QUANTITATIVE_Q',
        ordinary_autosol_approval=False,scientific_acceptance='NOT_ASSESSED')
