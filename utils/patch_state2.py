import re, glob

files = glob.glob('../pages/*.py')
for f in files:
    with open(f, 'r', encoding='utf-8') as file: content = file.read()

    # Patched!
    new_content = re.sub(r'key=f\"_ef_(\{_edit_id_.*?_\})(_{_fc}_.*?\")+', r'key=f"_ef_\1\2', content)

    if new_content != content:
        with open(f, 'w', encoding='utf-8') as file: file.write(new_content)
