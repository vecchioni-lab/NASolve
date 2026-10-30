"""Phenix 2.2.1 phase-restrained XYZ/isotropic-ADP worker with passive audits.

Executed only by configured phenix.python. No captured script is replayed by
verification. The full-precision state is retained separately from PDB rounding.
"""
import hashlib
import gzip
import json
from pathlib import Path
import sys


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def reflection_signature(fmodel):
    f=fmodel.f_obs();flags=fmodel.r_free_flags()
    if list(f.indices())!=list(flags.indices()):raise ValueError('Native observation/flag indices differ')
    rows=sorted((list(h),float(v),float(s),bool(q)) for h,v,s,q in zip(f.indices(),f.data(),f.sigmas(),flags.data()))
    return dict(hash=hashlib.sha256(canonical(rows).encode()).hexdigest(),count=len(rows),
                anomalous=bool(f.anomalous_flag()),free_count=sum(row[-1] for row in rows),rows=rows)


def policy(params,dm,has_phases,weight_controls=False):
    data=dm.data_manager.fmodel.xray_data
    result=dict(strategy=list(params.refine.strategy),target=params.main.target,cycles=params.main.number_of_macro_cycles,
                minimizer_cycles=params.group_anomalous.number_of_minimizer_cycles,
                max_iterations=params.group_anomalous.lbfgs_max_iterations,random_seed=params.main.random_seed,
                nproc=params.main.nproc,apply_overall_isotropic_scale_to_adp=params.main.apply_overall_isotropic_scale_to_adp,
                apply_back_trace=params.bulk_solvent_and_scale.apply_back_trace,update_f_part1=params.main.update_f_part1,
                nqh_flips=params.main.nqh_flips,ordered_solvent=params.main.ordered_solvent,
                find_and_add_hydrogens=params.main.find_and_add_hydrogens,
                find_anomalous_automatically=params.group_anomalous.find_automatically,
                outliers_rejection=data.outliers_rejection,bulk_solvent_and_scale=params.main.bulk_solvent_and_scale,
                experimental_phases=has_phases,free_r_test_value=data.r_free_flags.test_flag_value,
                anomalous_observations=data.force_anomalous_flag_to_be_equal_to,
                isotropic_selection=params.refine.adp.individual.isotropic,
                anisotropic_selection=params.refine.adp.individual.anisotropic,
                automatic_metal_linking=params.pdb_interpretation.automatic_linking.link_metals,
                optimize_xyz_weight=params.target_weights.optimize_xyz_weight,
                optimize_adp_weight=params.target_weights.optimize_adp_weight)
    if weight_controls:
        result['weight_controls']={name:getattr(params.target_weights,name)
            for name in ('wxc_scale','wxu_scale','wc','wu','fix_wxc','fix_wxu')}
    return result


def symmetry_signature(symmetry):
    return dict(unit_cell=list(symmetry.unit_cell().parameters()),
                space_group_number=symmetry.space_group().type().number())


def phase_signature(array):
    if array is None:raise ValueError('Experimental phase coefficients missing')
    rows=sorted((list(h),list(v)) for h,v in zip(array.indices(),array.data()))
    return dict(hash=hashlib.sha256(canonical(rows).encode()).hexdigest(),count=len(rows),rows=rows)


def native_source_hashes():
    import phenix.refinement.fp_fdp as fp_fdp
    import phenix.refinement.bulk_solvent_and_scaling as scaling
    import mmtbx.refinement.anomalous_scatterer_groups as groups
    import cctbx_xray_ext
    import scitbx_lbfgs_ext
    return {name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name,module in [('fp_fdp',fp_fdp),('bulk_scaling',scaling),('anomalous_minimizer',groups),
                                ('xray_kernel',cctbx_xray_ext),('lbfgs_kernel',scitbx_lbfgs_ext)]}


def run(filename):
    from iotbx.cli_parser import run_program
    from phenix.programs.phenix_refine import Program,PhenixRefineParser,custom_process_arguments
    from phenix import phenix_info
    request=json.loads(Path(filename).read_text());plan=request['plan']
    version='-'.join(str(v) for v in phenix_info.version_and_release_tag() if v)
    if version!='2.2.1-6174':raise ValueError('Unsupported native version: '+version)

    class AuditedProgram(Program):
        def validate(self):
            super().validate()
            actual=policy(self.params.refinement,self.data_manager.export_phil_scope().extract(),self.fmodel.hl_coeffs() is not None,weight_controls='weight_controls' in plan['policy'])
            if canonical(actual)!=canonical(plan['policy']):
                raise ValueError('Preflight native parameter mismatch: '+canonical(actual))
            from iotbx import pdb
            self.input_symmetry=symmetry_signature(pdb.input(file_name='input.pdb').crystal_symmetry())
            self.before_symmetry=symmetry_signature(self.fmodel.xray_structure)
            if (self.input_symmetry['space_group_number']!=self.before_symmetry['space_group_number']
                    or any(abs(a-b)>(.000501 if i<3 else .005001) for i,(a,b) in enumerate(zip(
                        self.input_symmetry['unit_cell'],self.before_symmetry['unit_cell'])))):
                raise ValueError('Input crystal symmetry changed beyond PDB precision')
            self.before=reflection_signature(self.fmodel)
            self.phases_before=phase_signature(self.fmodel.hl_coeffs())
            from iotbx import reflection_file_reader
            arrays=reflection_file_reader.any_reflection_file('phases.mtz').as_miller_arrays()
            matches=[a for a in arrays if a.info().labels==plan['phases']['labels']]
            if len(matches)!=1 or matches[0].anomalous_flag():raise ValueError('Require one mean HL source array')
            selected=self.data_manager.get_miller_array_user_selected_labels('phases.mtz')
            if selected!=[','.join(plan['phases']['labels'])]:raise ValueError('Native phase array selection changed')
            self.phase_labels=matches[0].info().labels
            source=matches[0].map_to_asu().merge_equivalents().array()
            self.phase_source=phase_signature(source)
            lookup={tuple(h):list(v) for h,v in zip(source.indices(),source.data())}
            if any(lookup.get(tuple(h))!=v for h,v in self.phases_before['rows']):
                raise ValueError('Active phase coefficients differ from selected source array')
            self.scattering_before=[s.scattering_type for s in self.model.get_xray_structure().scatterers()]
            scopes=[g for g in self.params.refinement.refine.anomalous_scatterers.group if g.selection is not None]
            if len(scopes)!=len(plan['groups']):raise ValueError('Native group scopes changed')
            for g,expected in zip(scopes,plan['groups']):
                wanted=['f_double_prime'] if expected['refine_fdp'] else []
                if (g.selection!=expected['selection'] or g.f_prime!=expected['f_prime']
                        or g.f_double_prime!=expected['f_double_prime_start'] or list(g.refine)!=wanted):
                    raise ValueError('Initial native anomalous parameter mismatch')

        def get_results(self):
            r=super().get_results();x=r.fmodel.xray_structure;h=r.model.get_hierarchy()
            model_x=r.model.get_xray_structure()
            if len(x.scatterers())!=len(model_x.scatterers()):raise ValueError('Model and active fmodel atom counts differ')
            for a,b in zip(x.scatterers(),model_x.scatterers()):
                state=lambda s:(s.label,s.scattering_type,tuple(s.site),s.occupancy,s.u_iso,tuple(s.u_star),s.fp,s.fdp)
                if state(a)!=state(b):raise ValueError('Active fmodel differs from model atomic state')
            from cctbx import adptbx
            sites=x.sites_cart()
            u_cart=x.scatterers().extract_u_cart(x.unit_cell());rows=[]
            for i,(a,s) in enumerate(zip(h.atoms(),x.scatterers())):
                label=a.fetch_labels()
                key=dict(model_id=label.model_id.strip() or '1',chain_id=label.chain_id.strip(),
                         residue_id=label.resseq.strip(),insertion_code=label.icode.strip(),
                         component_id=label.resname.strip(),atom_name=label.name.strip(),
                         altloc=label.altloc.strip(),segment_id=a.segid.strip(),symmetry='x,y,z')
                rows.append(dict(key=key,element=a.element.strip().capitalize(),xyz=list(sites[i]),
                                 occupancy=s.occupancy,b_iso=a.b if s.flags.use_u_aniso() else adptbx.u_as_b(s.u_iso),charge=a.charge.strip(),normal_scattering_type=s.scattering_type,u_cart=list(u_cart[i]) if s.flags.use_u_aniso() else None,
                                 fp=s.fp,fdp=s.fdp))
            groups=[]
            actual_groups=r.model.get_anomalous_scatterer_groups()
            if len(actual_groups)!=len(plan['groups']):raise ValueError('Final native group count changed')
            for actual,expected in zip(actual_groups,plan['groups']):
                group=dict(expected,selection=actual.selection_string,indices=list(actual.iselection),
                           f_prime=actual.f_prime,f_double_prime=actual.f_double_prime,
                           refine_fp=actual.refine_f_prime,refine_fdp=actual.refine_f_double_prime)
                groups.append(group)
            result=dict(protocol=plan['protocol'],completed=True,execution='complete',native_version=version,
                        atoms=rows,groups=groups,input_symmetry=self.input_symmetry,
                        symmetry_before=self.before_symmetry,symmetry_after=symmetry_signature(x),policy=policy(r.params,r.dm_working_phil.extract(),r.fmodel.hl_coeffs() is not None,weight_controls='weight_controls' in plan['policy']),
                        reflection_before=self.before,reflection_after=reflection_signature(r.fmodel),
                        phase_labels=self.phase_labels,phase_source=self.phase_source,
                        phases_before=self.phases_before,phases_after=phase_signature(r.fmodel.hl_coeffs()),
                        normal_scattering_before=self.scattering_before,
                        native_source_hashes=native_source_hashes(),
                        r_work=r.fmodel.r_work(),r_free=r.fmodel.r_free(),convergence='NOT_INDEPENDENTLY_ASSESSED')
            from fit_diagnostics import capture
            result['fit_diagnostics']=capture(r.fmodel)
            if 'map_capture' in plan:
                from map_diagnostics import capture as capture_maps
                result['map_diagnostics']=capture_maps(r.fmodel,result,plan['sites'],plan['map_capture'])
            Path('native-result.json.gz').write_bytes(gzip.compress(canonical(result).encode(),mtime=0))
            Path('final.pdb').write_text(r.model.model_as_pdb(output_cs=True))
            Path('effective-final.phil').write_text(r.master_params.format(python_object=r.iparams).as_str())
            return result

    run_program(program_class=AuditedProgram,parser_class=PhenixRefineParser,
                custom_process_arguments=custom_process_arguments,unused_phil_raises_sorry=False,args=request['args'])


if __name__=='__main__':
    run(sys.argv[1])
