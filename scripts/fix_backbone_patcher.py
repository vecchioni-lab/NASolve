from pathlib import Path

path = Path(__file__).with_name("apply_backbone_feature.py")
text = path.read_text(encoding="utf-8")

needle = '''    "        phosphate_intent_summary(resolved.allow_op3_sites, resolved.phosphate_intent),\\n",
    "        phosphate_intent_summary(resolved.allow_op3_sites, resolved.phosphate_intent),\\n"
'''
replacement = '''    "        phosphate_intent_summary(resolved.allow_op3_sites, resolved.phosphate_intent),\\n"
    "        f\\"Authoritative space group: {space_group}\\",\\n",
    "        phosphate_intent_summary(resolved.allow_op3_sites, resolved.phosphate_intent),\\n"
'''
if text.count(needle) != 1:
    raise SystemExit(f"Expected one ambiguous AutoMR anchor block, found {text.count(needle)}")
text = text.replace(needle, replacement, 1)

needle = '''    "         )),\\n",
)

# ---- campaigns.py: freeze/validate the new intent without breaking old plans ----
'''
replacement = '''    "         )),\\n"
    "        f\\"Authoritative space group: {space_group}\\",\\n",
)

# ---- campaigns.py: freeze/validate the new intent without breaking old plans ----
'''
if text.count(needle) != 1:
    raise SystemExit(f"Expected one AutoMR replacement tail, found {text.count(needle)}")
text = text.replace(needle, replacement, 1)

path.write_text(text, encoding="utf-8")
print("Disambiguated AutoMR log patch anchor.")
