import os, re, glob

TARGETS = {
    '1___MM_자재관리.py': [('goods_receipt', 'item_name', 'df_gr')],
    '2____SD_판매출하.py': [('customers', 'customer_name', 'df_cust')],
    '9_관리자.py': [('user_permissions', 'page_key', 'df_perm'), ('allowed_domains', 'domain', 'df_dom')]
}

def get_edit_block(table, col, indent, df_var):
    return f'''
{indent}            # ── 행 수정/삭제 버튼 ({table}) ──────────────────────────
{indent}            if not {df_var}.empty if hasattr({df_var}, 'empty') else {df_var} is not None:
{indent}                _row_opts_{table} = {{}}
{indent}                try:
{indent}                    _cx_opt = get_db()
{indent}                    _opt_rs = [dict(r) for r in _cx_opt.execute(
{indent}                        "SELECT id, * FROM {table} ORDER BY id DESC LIMIT 300"
{indent}                    ).fetchall()]
{indent}                    _cx_opt.close()
{indent}                    for _r in _opt_rs:
{indent}                        _k = f"{{_r['id']}} | {{_r.get('{col}','')}}"
{indent}                        _row_opts_{table}[_k] = _r['id']
{indent}                except Exception:
{indent}                    pass
{indent}
{indent}                if _row_opts_{table}:
{indent}                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
{indent}                    _rb_sel_{table} = _rb_sel_col.selectbox(
{indent}                        "행 선택", list(_row_opts_{table}.keys()),
{indent}                        key="_rbsel_{table}", label_visibility="collapsed"
{indent}                    )
{indent}                    _rb_id_{table} = _row_opts_{table}[_rb_sel_{table}]
{indent}
{indent}                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_{table}"):
{indent}                        st.session_state[f"_edit_{table}"] = _rb_id_{table}
{indent}                        st.session_state[f"_del_{table}"]  = None
{indent}
{indent}                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_{table}"):
{indent}                        st.session_state[f"_del_{table}"]  = _rb_id_{table}
{indent}                        st.session_state[f"_edit_{table}"] = None
{indent}
{indent}                # ── 삭제 확인 ──────────────────────────────────────────
{indent}                if st.session_state.get(f"_del_{table}"):
{indent}                    _del_id_{table} = st.session_state[f"_del_{table}"]
{indent}                    st.warning(f"⚠️ ID **{{_del_id_{table}}}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
{indent}                    _dc1, _dc2 = st.columns(2)
{indent}                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_{table}"):
{indent}                        _cx_d = get_db()
{indent}                        _cx_d.execute("DELETE FROM {table} WHERE id = ?", (_del_id_{table},))
{indent}                        _cx_d.commit(); _cx_d.close()
{indent}                        st.session_state[f"_del_{table}"] = None
{indent}                        st.success("✅ 삭제 완료!"); st.rerun()
{indent}                    if _dc2.button("취소", use_container_width=True, key="_delcancel_{table}"):
{indent}                        st.session_state[f"_del_{table}"] = None; st.rerun()
{indent}
{indent}                # ── 수정 인라인 폼 ─────────────────────────────────────
{indent}                if st.session_state.get(f"_edit_{table}"):
{indent}                    _edit_id_{table} = st.session_state[f"_edit_{table}"]
{indent}                    try:
{indent}                        _cx_e = get_db()
{indent}                        _edit_row_{table} = dict(_cx_e.execute(
{indent}                            "SELECT * FROM {table} WHERE id=?", (_edit_id_{table},)
{indent}                        ).fetchone() or {{}})
{indent}                        _cx_e.close()
{indent}                    except Exception:
{indent}                        _edit_row_{table} = {{}}
{indent}                    with st.expander(f"✏️ 정보 수정 — ID {{_edit_id_{table}}}", expanded=True):
{indent}                        if not _edit_row_{table}:
{indent}                            st.warning("데이터를 불러올 수 없습니다.")
{indent}                        else:
{indent}                            _skip_cols = {{'id','created_at','updated_at','ordered_at'}}
{indent}                            _edit_fields_{table} = [c for c in _edit_row_{table} if c not in _skip_cols]
{indent}                            _ncols = min(3, max(1, len(_edit_fields_{table})))
{indent}                            _ecols = st.columns(_ncols)
{indent}                            _new_vals_{table} = {{}}
{indent}                            for _i, _fc in enumerate(_edit_fields_{table}):
{indent}                                _cv = _edit_row_{table}[_fc]
{indent}                                _ec = _ecols[_i % _ncols]
{indent}                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
{indent}                                    _new_vals_{table}[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{{_edit_id_{table}}}_{{_fc}}_{table}")
{indent}                                else:
{indent}                                    _new_vals_{table}[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{{_edit_id_{table}}}_{{_fc}}_{table}")
{indent}                            _s1, _s2 = st.columns(2)
{indent}                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_{table}"):
{indent}                                _set_sql = ", ".join([f"{{c}}=?" for c in _new_vals_{table}])
{indent}                                _set_params = list(_new_vals_{table}.values()) + [_edit_id_{table}]
{indent}                                _cx_s = get_db()
{indent}                                _cx_s.execute(f"UPDATE {table} SET {{_set_sql}} WHERE id=?", _set_params)
{indent}                                _cx_s.commit(); _cx_s.close()
{indent}                                st.session_state[f"_edit_{table}"] = None
{indent}                                st.success("✅ 수정 저장 완료!"); st.rerun()
{indent}                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_{table}"):
{indent}                                st.session_state[f"_edit_{table}"] = None; st.rerun()
'''[1:]

for fname, tables in TARGETS.items():
    fpath = f"../pages/{fname}"
    if not os.path.exists(fpath): continue

    with open(fpath, "r", encoding="utf-8") as f: content = f.read()

    for table, col, df_var in tables:
        if f"_rbed_{table}" in content: continue
        
        # 정규표현식으로 df 출력부 아래에 붙임
        m = re.search(r"^[ \t]*st\.dataframe\(" + df_var + r".*?\)\s*\n", content, flags=re.MULTILINE)
        if m:
            print(f"Patched {table} in {fname}")
            block = get_edit_block(table, col, "            ", df_var)
            content = content[:m.end()] + "\n" + block + content[m.end():]
        else:
            print(f"Could not find dataframe print for {table} in {fname}")

    with open(fpath, "w", encoding="utf-8") as f: f.write(content)
