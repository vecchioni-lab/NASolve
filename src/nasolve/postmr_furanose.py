"""One source-qualified internal sugar substitution after ordinary scaffold construction."""
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_acquisition_preparation import _freeze
from .cif_attachment_profiles import inspect_attachment_profile
from .cif_attachment_sites import _site
from .cif_base_displacement import POLICY_ID as BASE_B_POLICY
from .cif_dictionary_sites import _SNAPSHOT_FILES, _need, _read
from .cif_dictionary_store import resolve_dictionary_snapshot
from .cif_fana_component import _load
from .cif_furanose_bridge import prepare_furanose_bridge_seed, read_furanose_bridge_seed
from .cif_repair_attempt import _root
from .cif_whole_furanose import prepare_base_anchored_furanose_from_model
from .phenix_runtime import PhenixInstallation

DIRECTORY = 'PostMR/Coot/furanose'
_LOCKED = 'two-o-four-c-methylene-furanose-phosphate-v1'
_FIT = dict(endpoint_weight=1000.0, max_base_displacement=2.0)


@dataclass(frozen=True)
class CatalogueSubstitution:
    site: str
    code: str
    source: Path
    source_bytes: bytes
    source_authority: str
    host: Path
    host_bytes: bytes
    workbook: Path
    workbook_bytes: bytes
    store: Path
    phenix: PhenixInstallation
    consumer: dict
    generation: dict
    native_seconds: int
    acquisition_seconds: int

    def verify_source(self, path, authority):
        _need(authority == self.source_authority and _read(path) == self.source_bytes,
              'Locked-sugar source or its authority changed after planning')

    def acquire(self, directory):
        """Use the ordinary isolated-dictionary owner after PostMR reserves its directory."""
        from .cif_acquisition_attempt import acquire_dictionary_attempt, read_acquisition_result

        self.verify_source(self.source, self.source_authority)
        _need(_read(self.host) == self.host_bytes and _read(self.workbook) == self.workbook_bytes,
              'Locked-sugar host dictionary or workbook changed before acquisition')
        result = acquire_dictionary_attempt(self.source, self.code, self.store, directory,
            source_authority=self.source_authority, consumer=self.consumer, generation=self.generation,
            phenix=self.phenix, native_timeout_seconds=self.native_seconds,
            total_timeout_seconds=self.acquisition_seconds, max_attempts=1)
        saved = read_acquisition_result(directory, result['attempt_number'])
        self.verify_source(saved['source'], saved['manifest']['request']['source_authority'])
        choice = capture_substitution(dict(site=self.site, snapshot=saved['directory'].parent,
                                           host_dictionary=self.host, workbook=self.workbook), self.consumer)
        _need(choice.entry_id == saved['entry_id'] and choice.host_bytes == self.host_bytes
              and choice.workbook_bytes == self.workbook_bytes, 'Locked-sugar inputs changed during acquisition')
        return choice


def plan_catalogue_substitution(run_directory, site, configured, phenix, store, data_root, limits):
    """Read the frozen mutation, ordinary chemical sources and the installed restraint workbook."""
    from restraints import residue_library
    from .cif_generation_input import POLICY_ID as SOURCE_READER, source_selected_generation
    from .component_normalization import preparation_targets
    from .curated_ligands import ligand_source, validate_ligand_dictionary
    from .postmr import _read_report, _solution_model, _target_sites, residue_name

    site = _site(site)
    run, report = _read_report(run_directory)
    model = _solution_model(run, report)
    targets = preparation_targets(_target_sites(report, model, run_directory=run), model)
    code = targets.get(site)
    _need(code is not None, 'Locked-sugar site must occur in the frozen mutation or sequence')
    host_code = residue_name(model, site)
    sources = [ligand_source(c, data_root, ready_set_executable=configured.ready_set_executable)
               for c in (code, host_code)]
    for component, source in zip((code, host_code), sources, strict=True):
        validate_ligand_dictionary(component, source.path)
    target, host = sources
    workbook = Path(residue_library.__file__).parent/'data/Ligands.xlsx'
    original, host_bytes, workbook_bytes = (_read(p) for p in (target.path,host.path,workbook))
    profile = inspect_attachment_profile(target.path, code, workbook=workbook)
    _need(profile['topology_status'] == 'MATCH' and profile['matched_profile'] == _LOCKED,
          'Selected mutation lacks a source-declared 2′-O,4′-C bridged furanose')
    generation = dict(configured.generation)
    generation.setdefault('source_input_policy', SOURCE_READER)
    if 'bond_representation_policy' not in generation:
        generation = source_selected_generation(target.path, code, generation)
    return CatalogueSubstitution(site,code,target.path,original,target.authority,host.path,host_bytes,
        workbook,workbook_bytes,Path(store),phenix,configured.consumer,generation,
        limits.get('native_timeout_seconds',90),limits.get('component_timeout_seconds',600))


@dataclass(frozen=True)
class FuranoseInput:
    site: str
    code: str
    entry_id: str
    source_authority: str
    snapshot: Path
    files: dict[str, bytes]
    host: Path
    host_bytes: bytes
    workbook: Path
    workbook_bytes: bytes

    def verify_source(self, path, authority):
        _need(authority == self.source_authority and _read(path) == self.files['entry/source.cif'],
              'Furanose construction differs from the selected chemical source or its authority')

    def verify(self):
        _need(all(_read(self.snapshot/name) == data for name, data in self.files.items())
              and _read(self.host) == self.host_bytes and _read(self.workbook) == self.workbook_bytes,
              'Selected furanose construction inputs changed')


def capture_substitution(selection, consumer):
    """Read only the declared qualified snapshot, host dictionary and NARestraints workbook."""
    _need(isinstance(selection, dict) and set(selection) == {'site','snapshot','host_dictionary','workbook'},
          'A furanose substitution needs a site, qualified snapshot, host dictionary and workbook')
    site = _site(selection['site'])
    directory = _root(selection['snapshot'])
    saved = resolve_dictionary_snapshot(directory)
    _need(saved['qualification_current'] and saved['manifest']['consumer'] == consumer,
          'Furanose construction requires a dictionary qualified for the selected consumer')
    code = saved['manifest']['request']['component']
    host, workbook = (Path(selection[k]).absolute() for k in ('host_dictionary','workbook'))
    choice = FuranoseInput(site, code, saved['entry_id'], saved['manifest']['request']['source_authority'],
                          directory, {n:_read(directory/n) for n in _SNAPSHOT_FILES},
                          host, _read(host), workbook, _read(workbook))
    profile = inspect_attachment_profile(saved['source'], code, workbook=workbook)
    _need(profile['topology_status'] == 'MATCH' and profile['matched_profile'] == _LOCKED,
          'This construction requires the source-declared 2′-O,4′-C bridged furanose')
    _need(resolve_dictionary_snapshot(directory)['manifest'] == saved['manifest'],
          'Qualified furanose dictionary changed during selection')
    choice.verify()
    return choice


def build_substitution(choice, frame, prepared, run, report):
    """Install the verified base-anchored seed on the phosphate-prepared Coot frame."""
    choice.verify()
    root = run/DIRECTORY
    root.mkdir(exist_ok=False)
    _freeze(root/'snapshot', choice.files, ['entry'])
    saved = resolve_dictionary_snapshot(root/'snapshot')
    with TemporaryDirectory(prefix='furanose-placement-', dir=root) as temporary:
        temp = Path(temporary)
        host, workbook = temp/'host.cif', temp/'Ligands.xlsx'
        host.write_bytes(choice.host_bytes)
        workbook.write_bytes(choice.workbook_bytes)
        prepare_base_anchored_furanose_from_model(
            saved['source'], saved['dictionary'], host, workbook, frame, temp/'placement',
            code=choice.code, site=choice.site, postmr_report=report, canonical_at_edge=False)
        prepare_furanose_bridge_seed(temp/'placement', root/'seed', **_FIT, inherit_equivalent_base_b=True)
    choice.verify()
    with prepared.open('xb') as handle:
        handle.write(_read(root/'seed/model.pdb'))


def read_substitution(root):
    """Recover the original qualified component and the exact two ports used in the model."""
    root = _root(root)
    _need({p.name for p in root.iterdir()} == {'snapshot','seed'}, 'Unexpected furanose construction members')
    _need({p.name for p in (root/'snapshot').iterdir()} == {'resolution.json','entry'},
          'Unexpected furanose dictionary snapshot members')
    original = resolve_dictionary_snapshot(root/'snapshot')
    seed = read_furanose_bridge_seed(root/'seed')
    placement = root/'seed/placement'
    placed = _load(placement/'placement.json')
    code = original['manifest']['request']['component']
    _need(original['qualification_current'] and seed['component'] == placed['component'] == code
          and _read(placement/'source.cif') == _read(original['source'])
          and _read(placement/'numerical.cif') == _read(original['dictionary'])
          and placed['source_profile'] == _LOCKED and 'ordinary_backbone' in placed
          and 'phosphate_leaving_atom' in placed and 'base_frame_source' in placed,
          'Furanose seed differs from the qualified source, ordinary partners or mapped base')
    _need(seed['config'] == dict(_FIT, base_b_policy=BASE_B_POLICY),
          'Furanose seed differs from the supported fit and displacement policy')
    return dict(snapshot=original, model=root/'seed/model.pdb', host_frame=placement/'frame.pdb',
                context=placed['context'], workbook=placement/'Ligands.xlsx', code=code)
