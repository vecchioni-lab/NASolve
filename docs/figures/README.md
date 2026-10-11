# Editable feature figures

`cif-doctor-overview.svg` is the human/manuscript figure accompanying
[`cif-doctor-human-overview.md`](../cif-doctor-human-overview.md). It uses real
text, named SVG groups and vector shapes; a vector editor can change labels,
colors or placement without reconstructing the feature from development notes.

The standard-library generator is the editable layout source. From the checkout:

```bash
python3 docs/figures/build_cif_doctor_overview.py
```

Edit its labels/layout and regenerate both source-controlled files together.
For one-off manuscript edits in a vector editor, save a separate derivative and
record the source commit; coordinate changes in the figure do not establish a
new runtime capability. Match each paper's actual software version and workflow.

The SVG is 180 mm × 172.5 mm with a white background and legible text at that
width. Export PDF from a vector editor for submission and retain the SVG as
the editable master. Raster previews and PDF exports can be regenerated and
need not be source-controlled. Update the caption and overview whenever the
feature, figure or interpretation changes.
