import re, glob

# ── 1. 세션 상태 캐시 초기화 버그 패치 (_edit_id_ 방식 추가) ──
files = glob.glob('../pages/*.py')
for f in files:
    with open(f, 'r', encoding='utf-8') as file: content = file.read()
    
    # Text input/Number input 등에서 key=f"_ef_{_fc}_{tableName}" 이었던 것을
    # key=f"_ef_{_edit_id_tableName}_{_fc}_{tableName}" 형태로 바꿈 (캐시 충돌 방지)
    def replacer(match):
        table_name = match.group(1)
        # 이미 _edit_id_ 가 포함되어 있다면 무시
        if f"_edit_id_{table_name}" in match.group(0):
            return match.group(0)
        return f'key=f"_ef_{{_edit_id_{table_name}}}_{{_fc}}_{table_name}"'
        
    new_content = re.sub(r'key=f\"_ef_\{_fc\}_(.*?)(\"|\')', replacer, content)
    
    if new_content != content:
        with open(f, 'w', encoding='utf-8') as file: file.write(new_content)
        print(f"Patched Session State keys in: {f}")

