"""Apply source-qualified phosphate angles and torsions in their declared crystal image."""
from collections import Counter
from contextlib import ExitStack, contextmanager
from functools import wraps
from inspect import signature
from math import fsum
from weakref import WeakKeyDictionary

from .cif_phosphate_restraints import _labels, _undirected
from .topostitch_transport import CartesianImage, IDENTITY_IMAGE


def project_phosphate_terms(inspection, terms, labels):
    """Rebind each complete angle or torsion to the current native selection."""
    lookup = {key: i for i, key in enumerate(labels)}
    if len(lookup) != len(labels):
        raise ValueError("A native selection has ambiguous atom identities")
    endpoint = {"phosphate-site": tuple(inspection["phosphate"][:2]), "o3-site": tuple(inspection["o3"][:2])}
    selected = []
    for term in terms:
        if term["kind"] == "bond_simple":
            continue
        indices = tuple(lookup.get((*endpoint[role], atom)) for role, atom in term["atoms"])
        if None not in indices:
            selected.append((term, indices))
    return selected


class PhosphateImageForces:
    """Native proxy inventory and its local image-coordinate derivative correction."""

    def __init__(self, inspection, terms, labels, cell):
        from cctbx import geometry_restraints as gr, sgtbx
        from cctbx.array_family import flex
        from cctbx.geometry_restraints.linking_class import linking_class
        from .topostitch_pair_coverage import _compiled_fractional_image
        self._gr, self._flex = gr, flex
        self.cell = cell
        self.labels = tuple(labels)
        self.selected = project_phosphate_terms(inspection, terms, self.labels)
        self.indices = sorted({i for _, indices in self.selected for i in indices})
        local = {i: n for n, i in enumerate(self.indices)}
        operator = inspection["o3_image"]
        _, rotation, translation = _compiled_fractional_image(operator, cell.parameters())
        image = CartesianImage(rotation, translation)
        self.transform = [image if self.labels[i][:2] == tuple(inspection["o3"][:2]) else IDENTITY_IMAGE
                          for i in self.indices]
        mate, identity = sgtbx.rt_mx(operator), sgtbx.rt_mx("x,y,z")
        self.origin = linking_class().get_origin_id("edits")
        def arrays():
            return {"angle": gr.shared_angle_proxy(), "dihedral": gr.shared_dihedral_proxy()}
        self.proxies = arrays()       # ASU indices in the actual model
        self._local_native = arrays() # Same native calculation on just the eight local atoms
        self._expanded = arrays()     # Ordinary forces on explicit image coordinates
        for term, indices in self.selected:
            family = term["kind"]
            constructor = getattr(gr, family+"_proxy")
            parameters = dict(term["parameters"], origin_id=self.origin)
            ids = [local[i] for i in indices]
            sym = [mate if role == "o3-site" else identity for role, _ in term["atoms"]]
            self.proxies[family].append(constructor(i_seqs=indices, sym_ops=sym, **parameters))
            self._local_native[family].append(constructor(i_seqs=ids, sym_ops=sym, **parameters))
            self._expanded[family].append(constructor(i_seqs=ids, **parameters))
        self.evaluations = Counter()

    @staticmethod
    def _signature(proxy, family):
        images = tuple(op.as_xyz() for op in (proxy.sym_ops or ()))
        attrs = ("angle_ideal", "weight", "slack", "origin_id")
        if family == "dihedral":
            attrs += ("periodicity", "limit", "top_out")
        return (tuple(proxy.i_seqs), images, *(getattr(proxy, a) for a in attrs),
                tuple(getattr(proxy, "alt_angle_ideals", ()) or ()))

    def check_proxies(self, geometry, *, install=False):
        """Install at the full manager once; selected managers inherit their native proxies."""
        missing = []
        for family, planned in self.proxies.items():
            native = getattr(geometry, family+"_proxies")
            wanted = {_undirected(tuple(p.i_seqs)): self._signature(p, family) for p in planned}
            if len(wanted) != len(planned):
                raise ValueError("Duplicate registered phosphate atom paths")
            actual = [p for p in native or () if _undirected(tuple(p.i_seqs)) in wanted]
            if install:
                if actual or (wanted and native is None):
                    raise ValueError(f"Existing or unavailable native phosphate {family} restraints")
                missing.extend((native, p) for p in planned)
            elif (len(actual) != len(wanted) or
                    {self._signature(p, family) for p in actual} != set(wanted.values())):
                raise ValueError(f"The selected native manager lost or changed phosphate {family} restraints")
        # Check both families before making any change.
        for native, proxy in missing:
            native.append(proxy)

    def release(self, geometry):
        """Remove only these verified image terms from any surviving native manager."""
        self.check_proxies(geometry)
        for family, planned in self.proxies.items():
            if not len(planned):
                continue
            name = family+"_proxies"
            collection = getattr(geometry, name)
            keys = {_undirected(tuple(proxy.i_seqs)) for proxy in planned}
            setattr(geometry, name, type(collection)([p for p in collection if _undirected(tuple(p.i_seqs)) not in keys]))

    def energies_add(self, energies_obj):
        """Replace only the native contribution from the registered local terms.

        Phenix sometimes calls the geometry kernel without the unit cell.
        Its symmetry torsion can also use the wrong Cartesian derivative.
        Explicit image sites with the ordinary native potential give the
        correct energy. A gradient at an image returns through the transposed
        Cartesian rotation to the coordinate that the optimizer can move.
        The real proxies already contributed their counts.
        """
        flex = self._flex
        cell = energies_obj.unit_cell
        if cell is not None and cell.parameters() != self.cell.parameters():
            raise ValueError("Phosphate force called with a different live unit cell")
        if len(energies_obj.sites_cart) != len(self.labels):
            raise ValueError("Phosphate force received coordinates for a different atom selection")
        sites = flex.vec3_double([energies_obj.sites_cart[i] for i in self.indices])
        expanded = flex.vec3_double([op.apply(xyz) for op, xyz in zip(self.transform, sites)])
        grad = energies_obj.gradients
        def zero():
            return flex.vec3_double(len(sites), (0., 0., 0.)) if grad is not None else None
        naive, accurate = zero(), zero()
        for family, proxies in self._local_native.items():
            if getattr(energies_obj, family+"_proxies") is None or not len(proxies):
                continue
            kernel = getattr(self._gr, family + "_residual_sum")
            current = kernel(sites_cart=sites, proxies=proxies, gradient_array=naive,
                             **({"unit_cell": cell} if cell is not None else {}))
            correct = kernel(sites_cart=expanded, proxies=self._expanded[family], gradient_array=accurate)
            change = correct - current
            field = family + "_residual_sum"
            setattr(energies_obj, field, fsum((getattr(energies_obj, field), change)))
            energies_obj.residual_sum = fsum((energies_obj.residual_sum, change))
            self.evaluations[family, grad is not None] += 1
        if grad is not None:
            for i, image, raw, proper in zip(self.indices, self.transform, naive, accurate):
                pulled = image.pullback(proper)
                grad[i] = tuple(fsum((g, b, -a)) for g, a, b in zip(grad[i], raw, pulled))

    def energies_show(self, energies_obj, f, prefix):
        print(prefix + "  NASolve registered crystal-image phosphate restraints", file=f)


class RegisteredPhosphateRuntime:
    """Own an explicitly requested bridge inside one isolated native refinement process."""

    def __init__(self, inspection, model_bytes):
        self.inspection = inspection
        self.model_bytes = model_bytes
        self.live_terms = None
        self.bond = None
        self.full = None
        self.owned = WeakKeyDictionary()
        self.selections = Counter()
        self.calls = Counter()
        self.joint_calls = Counter()
        self.restored = False

    def attach(self, model):
        from .cif_phosphate_restraints import qualify_live_phosphate_sources, verify_phosphate_bond, verify_phosphate_start
        geometry = model.restraints_manager.geometry
        if geometry in self.owned:
            return
        if self.full is not None:
            raise ValueError("Phenix constructed a second full phosphate refinement manager")
        verify_phosphate_start(model, self.model_bytes, self.inspection)
        native = qualify_live_phosphate_sources(model, self.inspection)
        self.bond = verify_phosphate_bond(model, self.inspection, native)
        hierarchy = model.get_hierarchy()
        cell = model.get_xray_structure().unit_cell()
        if geometry.crystal_symmetry.space_group() != model.get_xray_structure().space_group() or (
                geometry.crystal_symmetry.unit_cell().parameters() != cell.parameters()):
            raise ValueError("Native scattering and restraint managers have different phosphate frames")
        self.full = PhosphateImageForces(self.inspection, native, _labels(hierarchy), cell)
        if len(self.full.selected) != 7:
            raise ValueError("The full manager lacks a required phosphate angle or torsion")
        for i in self.full.indices:
            atom = hierarchy.atoms()[i]
            if not 0 < atom.occ <= 1 or atom.element.strip() != self.full.labels[i][-1][0]:
                raise ValueError("Missing occupied atom of the required element at the registered phosphate")
        self.full.check_proxies(geometry, install=True)
        self.owned[geometry] = self.full
        self.full.check_proxies(geometry)
        self.live_terms = native

    def _follow(self, source, child, indices):
        parent = self.owned[source]
        ordered = tuple(parent.labels[i] for i in indices)
        terms = self.full if ordered == self.full.labels else PhosphateImageForces(
            self.inspection, self.live_terms, ordered, self.full.cell)
        terms.check_proxies(child)
        self.owned[child] = terms
        self.selections[len(parent.labels), len(ordered), len(terms.selected)] += 1

    @staticmethod
    def check_group(inspections):
        """Require distinct ester ends on the same explicitly registered crystal copy."""
        if not inspections:
            raise ValueError("At least one registered phosphate is required")
        identifiers, donors, acceptors = [], set(), set()
        first = inspections[0]
        keys = ("copy_id", "registered_graph_sha256", "sources")
        for observation in inspections:
            edge = observation["registered_continuation"]
            if observation["model_sha256"] != first["model_sha256"]:
                raise ValueError("Registered phosphate set spans different model inputs")
            if any(edge[k] != first["registered_continuation"][k] for k in keys):
                raise ValueError("All crystal phosphates must use the same source registration")
            identifier = edge["continuation_id"]
            if type(identifier) is not int or identifier < 1 or identifier in identifiers:
                raise ValueError("A phosphate continuation ID is invalid or appears twice")
            donor = observation["o3"][0]
            acceptor = observation["phosphate"][0]
            if donor in donors:
                raise ValueError(f"Two registered continuations use the same O3′ at {donor}")
            if acceptor in acceptors:
                raise ValueError(f"Two registered continuations use the same phosphorus at {acceptor}")
            identifiers.append(identifier)
            donors.add(donor)
            acceptors.add(acceptor)
        return tuple(identifiers)

    @contextmanager
    def active(self, *additional):
        """Own the native hooks once for all requested links in this Phenix process.

        Each linkage retains its own source, symmetry operator and mapped atom
        selections. A full model and every selected child acquire all applicable
        corrections in the same native evaluation.
        """
        from cctbx.geometry_restraints.manager import manager as Geometry
        from mmtbx.model import manager as Model
        from phenix.refinement.fsr import preprocess
        owners = (self, *additional)
        if additional:
            self.check_group([o.inspection for o in owners])
            if any(o.model_bytes != self.model_bytes for o in additional):
                raise ValueError("Registered phosphate owners received different starting models")
        finalize, process = preprocess.finalize_model, Model.process
        select, energies = Geometry.select, Geometry.energies_sites
        energy_args = signature(energies)
        preparing = False
        if (any(o.restored or o.full is not None for o in owners)
                or any(hasattr(f, "_nasolve_phosphate") for f in (finalize, process, select, energies))):
            raise ValueError("Registered phosphate execution is already owned or finished")

        @wraps(finalize)
        def finalizer(*args, **kwargs):
            nonlocal preparing
            preparing = True
            try:
                return finalize(*args, **kwargs)
            finally:
                preparing = False

        @wraps(process)
        def make_model(model, *args, **kwargs):
            result = process(model, *args, **kwargs)
            if preparing and kwargs.get("make_restraints") is True:
                for owner in owners:
                    owner.attach(model)
            return result

        @wraps(select)
        def selected(geometry, selection=None, iselection=None):
            child = select(geometry, selection=selection, iselection=iselection)
            for owner in owners:
                if geometry in owner.owned:
                    ids = iselection if iselection is not None else selection.iselection()
                    owner._follow(geometry, child, ids)
            return child

        @wraps(energies)
        def score(geometry, *args, **kwargs):
            projections = [owner.owned.get(geometry) for owner in owners]
            if any(projected is None for projected in projections):
                if any(owner.live_terms is not None for owner in owners):
                    raise ValueError("Phenix requested energies from an untracked phosphate manager")
                return energies(geometry, *args, **kwargs)
            bound = energy_args.bind(geometry, *args, **kwargs)
            bound.apply_defaults()
            options = bound.arguments
            extension = options["extension_objects"]
            if any(isinstance(obj, PhosphateImageForces) for obj in extension):
                raise ValueError("A phosphate correction is already attached to this evaluation")
            options["extension_objects"] = [*extension, *(p for p in projections if p.selected)]
            result = energies(*bound.args, **bound.kwargs)
            gradient = bool(options["compute_gradients"])
            counts = tuple(len(projected.selected) for projected in projections)
            for owner, count in zip(owners, counts):
                owner.calls[count, gradient] += 1
            self.joint_calls[counts, gradient] += 1
            return result

        hooks = [(preprocess, "finalize_model", finalize, finalizer), (Model, "process", process, make_model),
                 (Geometry, "select", select, selected), (Geometry, "energies_sites", energies, score)]

        def release(owner):
            for geo, terms in list(owner.owned.items()):
                terms.release(geo)
            owner.restored = all(getattr(host, name) is original for host, name, original, _ in hooks)

        try:
            for host, name, original, wrapped in hooks:
                if getattr(host, name) is not original:
                    raise ValueError("Native phosphate refinement binding changed before attachment")
                wrapped._nasolve_phosphate = True
                setattr(host, name, wrapped)
            yield self
        finally:
            for host, name, original, wrapped in reversed(hooks):
                if getattr(host, name) is wrapped:
                    setattr(host, name, original)
            with ExitStack() as cleanup:
                for owner in owners:
                    cleanup.callback(release, owner)
