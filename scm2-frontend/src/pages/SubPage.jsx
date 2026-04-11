import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'

const TABS = ['발주 현황', '발주 등록/수정', '사급 자재', '입고 처리']

const STATUS_MAP = {
  draft:       { label: '초안',    bg: '#f5f5f3', color: '#6b6b6b' },
  issued:      { label: '발주확정', bg: '#e8f0fe', color: '#1a56db' },
  in_progress: { label: '작업중',  bg: '#fff8e1', color: '#b45309' },
  completed:   { label: '작업완료', bg: '#e8f5e9', color: '#2e7d32' },
  received:    { label: '입고완료', bg: '#e3f2fd', color: '#1565c0' },
  closed:      { label: '마감',    bg: '#f3e5f5', color: '#6a1b9a' },
  cancelled:   { label: '취소',    bg: '#fdecea', color: '#d44c47' },
}

const NEXT_STATUS = {
  issued:      'in_progress',
  in_progress: 'completed',
  completed:   'received',
  received:    'closed',
}
const NEXT_LABEL = {
  in_progress: '작업 착수',
  completed:   '작업 완료',
  received:    '입고 완료',
  closed:      '마감 처리',
}

// ─── 공통 스타일 ──────────────────────────────────────────────
const S = {
  card: {
    background: 'white', border: '1px solid #e9e9e7',
    borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
  },
  label: { fontSize: 12, color: '#6b6b6b', marginBottom: 4, display: 'block' },
  input: {
    width: '100%', padding: '8px 10px',
    border: '1px solid #e9e9e7', borderRadius: 6,
    fontSize: 13, boxSizing: 'border-box', outline: 'none',
  },
  select: {
    width: '100%', padding: '8px 10px',
    border: '1px solid #e9e9e7', borderRadius: 6,
    fontSize: 13, boxSizing: 'border-box', background: 'white', cursor: 'pointer',
  },
  field: { marginBottom: 12 },
  btn: {
    background: '#1a1a2e', color: 'white',
    padding: '8px 16px', borderRadius: 6, border: 'none',
    cursor: 'pointer', fontSize: 13, fontWeight: 500,
  },
  btnSm: {
    padding: '5px 12px', borderRadius: 5, border: '1px solid #e9e9e7',
    cursor: 'pointer', fontSize: 12, fontWeight: 500, background: 'white',
  },
}

function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || { label: status, bg: '#f5f5f3', color: '#6b6b6b' }
  return (
    <span style={{
      display: 'inline-block', padding: '2px 9px', borderRadius: 99,
      fontSize: 11, fontWeight: 600, background: s.bg, color: s.color,
    }}>{s.label}</span>
  )
}

// ─── 탭1: 발주 현황 ──────────────────────────────────────────
function OrderList({ onEdit }) {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch]             = useState('')
  const [selected, setSelected]         = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['sub-orders', statusFilter, search],
    queryFn: () => api.get('/sub/orders/', {
      params: { status: statusFilter || undefined, search: search || undefined }
    }).then(r => r.data),
    staleTime: 30000,
  })
  const orders = Array.isArray(data) ? data : (data?.results ?? [])

  const issueMutation = useMutation({
    mutationFn: (id) => api.post(`/sub/orders/${id}/issue/`).then(r => r.data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['sub-orders'] })
      if (selected?.id) qc.invalidateQueries({ queryKey: ['sub-order-detail', selected.id] })
      const msg = res.email_sent
        ? `발주가 확정되었습니다. 이메일을 ${res.supplier_email} 으로 발송했습니다.`
        : res.supplier_email
          ? `발주가 확정되었습니다. 이메일 발송 실패: ${res.email_error}`
          : '발주가 확정되었습니다. (공급업체 이메일 없음)'
      alert(msg)
    },
  })

  const transitionMutation = useMutation({
    mutationFn: ({ id, status }) => api.post(`/sub/orders/${id}/transition/`, { status }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sub-orders'] }),
  })

  const cancelMutation = useMutation({
    mutationFn: (id) => api.post(`/sub/orders/${id}/cancel/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sub-orders'] })
      setSelected(null)
    },
  })

  // 선택된 발주 상세
  const { data: detail } = useQuery({
    queryKey: ['sub-order-detail', selected?.id],
    queryFn: () => api.get(`/sub/orders/${selected.id}/`).then(r => r.data),
    enabled: !!selected?.id,
    staleTime: 10000,
  })

  return (
    <div style={{ padding: 20 }}>
      {/* 필터 */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        <select style={{ ...S.select, width: 130 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">전체 상태</option>
          {Object.entries(STATUS_MAP).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <input style={{ ...S.input, width: 200 }} placeholder="발주번호·업체명 검색"
          value={search} onChange={e => setSearch(e.target.value)} />
        <button style={S.btn} onClick={() => onEdit(null)}>+ 신규 발주</button>
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {/* 목록 */}
        <div style={{ flex: '1 1 480px', minWidth: 0 }}>
          <div style={S.card}>
            {isLoading ? (
              <div style={{ padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>불러오는 중...</div>
            ) : orders.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
                외주 발주 내역이 없습니다.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      {['발주번호', '공급업체', '작업내용', '납기일', '상태', '금액'].map(h => (
                        <th key={h} style={{
                          background: '#f5f5f3', padding: '8px 12px', textAlign: 'left',
                          fontWeight: 600, color: '#6b6b6b', borderBottom: '1px solid #e9e9e7',
                          fontSize: 12, whiteSpace: 'nowrap',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map(o => (
                      <tr key={o.id}
                        onClick={() => setSelected(o)}
                        style={{
                          borderBottom: '1px solid #f0f0ee', cursor: 'pointer',
                          background: selected?.id === o.id ? '#f0f7ff' : 'transparent',
                        }}
                        onMouseEnter={e => { if (selected?.id !== o.id) e.currentTarget.style.background = '#f9f9f7' }}
                        onMouseLeave={e => { if (selected?.id !== o.id) e.currentTarget.style.background = 'transparent' }}
                      >
                        <td style={{ padding: '9px 12px', fontWeight: 600, color: '#1a1a2e' }}>{o.order_number}</td>
                        <td style={{ padding: '9px 12px' }}>{o.supplier_name || '-'}</td>
                        <td style={{ padding: '9px 12px', color: '#6b6b6b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {o.work_description || '-'}
                        </td>
                        <td style={{ padding: '9px 12px', color: '#6b6b6b', fontSize: 12 }}>{o.due_date || '-'}</td>
                        <td style={{ padding: '9px 12px' }}><StatusBadge status={o.status} /></td>
                        <td style={{ padding: '9px 12px', textAlign: 'right', fontWeight: 600 }}>
                          {o.total_amount != null ? Number(o.total_amount).toLocaleString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* 상세 패널 */}
        {selected && detail && (
          <div style={{ ...S.card, flex: '0 0 320px', minWidth: 280, alignSelf: 'flex-start' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a2e' }}>{detail.order_number}</div>
              <StatusBadge status={detail.status} />
            </div>

            <div style={{ fontSize: 12, color: '#6b6b6b', lineHeight: 2, marginBottom: 12 }}>
              <div>업체: <strong>{detail.supplier_name || '-'}</strong> {detail.supplier_email && <span style={{ color: '#9b9b9b' }}>({detail.supplier_email})</span>}</div>
              <div>발주일: {detail.order_date}</div>
              <div>납기일: {detail.due_date || '-'}</div>
              <div>작업: {detail.work_description || '-'}</div>
              {detail.note && <div>비고: {detail.note}</div>}
            </div>

            {/* 발주 라인 */}
            {detail.lines?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#9b9b9b', marginBottom: 6 }}>발주 라인</div>
                {detail.lines.map((l, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '3px 0', borderBottom: '1px solid #f5f5f3' }}>
                    <span>{l.item_name}</span>
                    <span style={{ color: '#6b6b6b' }}>{l.quantity}{l.unit} × {Number(l.unit_price).toLocaleString()}원</span>
                  </div>
                ))}
                <div style={{ textAlign: 'right', fontSize: 13, fontWeight: 700, marginTop: 6, color: '#1a1a2e' }}>
                  합계 {Number(detail.total_amount).toLocaleString()}{detail.currency}
                </div>
              </div>
            )}

            {/* 사급 자재 */}
            {detail.materials?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#9b9b9b', marginBottom: 6 }}>사급 자재</div>
                {detail.materials.map((m, i) => (
                  <div key={i} style={{ fontSize: 12, padding: '3px 0', borderBottom: '1px solid #f5f5f3', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{m.material_name}</span>
                    <span style={{ color: '#6b6b6b' }}>지급 {m.quantity}{m.unit} / 출고 {m.issued_qty}</span>
                  </div>
                ))}
              </div>
            )}

            {/* 액션 버튼 */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {detail.status === 'draft' && (
                <>
                  <button style={{ ...S.btn, fontSize: 12, padding: '6px 12px' }}
                    onClick={() => onEdit(detail)}>수정</button>
                  <button style={{
                    ...S.btn, fontSize: 12, padding: '6px 12px',
                    background: '#1a56db',
                  }}
                    disabled={issueMutation.isPending}
                    onClick={() => {
                      if (window.confirm('발주를 확정하고 이메일을 발송하시겠습니까?'))
                        issueMutation.mutate(detail.id)
                    }}>
                    📧 발주 확정
                  </button>
                </>
              )}
              {NEXT_STATUS[detail.status] && (
                <button style={{ ...S.btnSm, color: '#2e7d32', borderColor: '#a5d6a7' }}
                  disabled={transitionMutation.isPending}
                  onClick={() => transitionMutation.mutate({ id: detail.id, status: NEXT_STATUS[detail.status] })}>
                  → {NEXT_LABEL[NEXT_STATUS[detail.status]]}
                </button>
              )}
              {!['received', 'closed', 'cancelled'].includes(detail.status) && (
                <button style={{ ...S.btnSm, color: '#d44c47', borderColor: '#f5c6c6' }}
                  onClick={() => {
                    if (window.confirm('이 발주를 취소하시겠습니까?'))
                      cancelMutation.mutate(detail.id)
                  }}>
                  취소
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── 탭2: 발주 등록/수정 ────────────────────────────────────
function OrderForm({ editOrder, onDone }) {
  const qc = useQueryClient()
  const isEdit = !!editOrder

  const [form, setForm] = useState({
    supplier:         editOrder?.supplier ?? '',
    order_date:       editOrder?.order_date ?? new Date().toISOString().slice(0, 10),
    due_date:         editOrder?.due_date ?? '',
    work_description: editOrder?.work_description ?? '',
    currency:         editOrder?.currency ?? 'KRW',
    note:             editOrder?.note ?? '',
  })
  const [lines, setLines] = useState(
    editOrder?.lines?.length
      ? editOrder.lines.map(l => ({ item_name: l.item_name, quantity: l.quantity, unit: l.unit, unit_price: l.unit_price, note: l.note || '' }))
      : [{ item_name: '', quantity: '', unit: 'EA', unit_price: '', note: '' }]
  )
  const [materials, setMaterials] = useState(
    editOrder?.materials?.length
      ? editOrder.materials.map(m => ({ material: m.material || '', material_name: m.material_name, quantity: m.quantity, unit: m.unit, note: m.note || '' }))
      : []
  )

  const { data: suppData } = useQuery({
    queryKey: ['sub-suppliers'],
    queryFn: () => api.get('/mm/suppliers/').then(r => r.data),
  })
  const suppliers = Array.isArray(suppData) ? suppData : (suppData?.results ?? [])

  const { data: matData } = useQuery({
    queryKey: ['sub-materials-list'],
    queryFn: () => api.get('/mm/materials/').then(r => r.data),
  })
  const materialList = Array.isArray(matData) ? matData : (matData?.results ?? [])

  const saveMutation = useMutation({
    mutationFn: async () => {
      let order
      if (isEdit) {
        order = await api.patch(`/sub/orders/${editOrder.id}/`, form).then(r => r.data)
        // 기존 라인/자재 삭제 후 재생성
        for (const l of editOrder.lines || []) await api.delete(`/sub/lines/${l.id}/`)
        for (const m of editOrder.materials || []) await api.delete(`/sub/materials/${m.id}/`)
      } else {
        order = await api.post('/sub/orders/', form).then(r => r.data)
      }
      // 라인 생성
      for (let i = 0; i < lines.length; i++) {
        const l = lines[i]
        if (!l.item_name) continue
        await api.post('/sub/lines/', { ...l, order: order.id, line_no: i + 1 })
      }
      // 사급 자재 생성
      for (const m of materials) {
        if (!m.material_name) continue
        await api.post('/sub/materials/', { ...m, order: order.id })
      }
      return order
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sub-orders'] })
      alert(isEdit ? '수정되었습니다.' : '발주서가 등록되었습니다.')
      onDone()
    },
    onError: (e) => alert(e.response?.data ? JSON.stringify(e.response.data) : '저장 실패'),
  })

  const f = (key) => ({
    value: form[key],
    onChange: e => setForm(p => ({ ...p, [key]: e.target.value })),
  })

  const updateLine = (i, key, val) => setLines(p => p.map((l, j) => j === i ? { ...l, [key]: val } : l))
  const addLine    = () => setLines(p => [...p, { item_name: '', quantity: '', unit: 'EA', unit_price: '', note: '' }])
  const removeLine = (i) => setLines(p => p.filter((_, j) => j !== i))

  const updateMat = (i, key, val) => setMaterials(p => p.map((m, j) => j === i ? { ...m, [key]: val } : m))
  const addMat    = () => setMaterials(p => [...p, { material: '', material_name: '', quantity: '', unit: 'EA', note: '' }])
  const removeMat = (i) => setMaterials(p => p.filter((_, j) => j !== i))

  return (
    <div style={{ padding: 20, maxWidth: 800 }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a2e', marginBottom: 20 }}>
        {isEdit ? `✏️ 발주서 수정 – ${editOrder.order_number}` : '📋 신규 외주 발주 등록'}
      </div>

      <div style={S.card}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ ...S.field, flex: '1 1 200px' }}>
            <label style={S.label}>외주 업체</label>
            <select style={S.select} {...f('supplier')}>
              <option value="">-- 업체 선택 --</option>
              {suppliers.map(s => (
                <option key={s.id} value={s.id}>{s.name} {s.email ? `(${s.email})` : ''}</option>
              ))}
            </select>
          </div>
          <div style={{ ...S.field, flex: '1 1 140px' }}>
            <label style={S.label}>발주일</label>
            <input style={S.input} type="date" {...f('order_date')} />
          </div>
          <div style={{ ...S.field, flex: '1 1 140px' }}>
            <label style={S.label}>납기일</label>
            <input style={S.input} type="date" {...f('due_date')} />
          </div>
          <div style={{ ...S.field, flex: '1 1 80px' }}>
            <label style={S.label}>통화</label>
            <select style={S.select} {...f('currency')}>
              {['KRW','USD','EUR','JPY','CNY'].map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div style={S.field}>
          <label style={S.label}>작업 내용</label>
          <input style={S.input} placeholder="예: 금속 부품 표면처리 가공" {...f('work_description')} />
        </div>
        <div style={S.field}>
          <label style={S.label}>비고</label>
          <input style={S.input} placeholder="특이사항" {...f('note')} />
        </div>
      </div>

      {/* 발주 라인 */}
      <div style={{ ...S.card, marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 700 }}>📦 발주 라인</div>
          <button style={{ ...S.btnSm, color: '#1a56db' }} onClick={addLine}>+ 라인 추가</button>
        </div>
        {lines.map((l, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: '2 1 160px' }}>
              {i === 0 && <label style={S.label}>작업/품목명</label>}
              <input style={S.input} placeholder="품목명" value={l.item_name}
                onChange={e => updateLine(i, 'item_name', e.target.value)} />
            </div>
            <div style={{ flex: '0 1 80px' }}>
              {i === 0 && <label style={S.label}>수량</label>}
              <input style={S.input} type="number" placeholder="0" value={l.quantity}
                onChange={e => updateLine(i, 'quantity', e.target.value)} />
            </div>
            <div style={{ flex: '0 1 70px' }}>
              {i === 0 && <label style={S.label}>단위</label>}
              <input style={S.input} placeholder="EA" value={l.unit}
                onChange={e => updateLine(i, 'unit', e.target.value)} />
            </div>
            <div style={{ flex: '1 1 100px' }}>
              {i === 0 && <label style={S.label}>단가</label>}
              <input style={S.input} type="number" placeholder="0" value={l.unit_price}
                onChange={e => updateLine(i, 'unit_price', e.target.value)} />
            </div>
            <div style={{ flex: '1 1 120px' }}>
              {i === 0 && <label style={S.label}>비고</label>}
              <input style={S.input} placeholder="라인 비고" value={l.note}
                onChange={e => updateLine(i, 'note', e.target.value)} />
            </div>
            <button onClick={() => removeLine(i)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#d44c47', fontSize: 16, padding: '0 4px', alignSelf: 'center',
            }}>✕</button>
          </div>
        ))}
        {lines.some(l => l.item_name && l.quantity && l.unit_price) && (
          <div style={{ textAlign: 'right', fontSize: 13, fontWeight: 700, color: '#1a1a2e', marginTop: 8 }}>
            소계 {lines.reduce((s, l) => s + (parseFloat(l.quantity || 0) * parseFloat(l.unit_price || 0)), 0).toLocaleString()}원
          </div>
        )}
      </div>

      {/* 사급 자재 */}
      <div style={{ ...S.card, marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 700 }}>🧱 사급 자재 (선택)</div>
          <button style={{ ...S.btnSm, color: '#1a56db' }} onClick={addMat}>+ 자재 추가</button>
        </div>
        {materials.length === 0 && (
          <div style={{ fontSize: 12, color: '#9b9b9b', padding: '8px 0' }}>
            외주업체에 지급할 원자재/반제품이 있으면 추가하세요.
          </div>
        )}
        {materials.map((m, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: '2 1 160px' }}>
              {i === 0 && <label style={S.label}>품목 선택 (선택사항)</label>}
              <select style={S.select} value={m.material}
                onChange={e => {
                  const mat = materialList.find(x => String(x.id) === e.target.value)
                  updateMat(i, 'material', e.target.value)
                  if (mat) updateMat(i, 'material_name', mat.material_name)
                }}>
                <option value="">-- 직접 입력 --</option>
                {materialList.map(x => (
                  <option key={x.id} value={x.id}>{x.material_code} {x.material_name}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: '1 1 140px' }}>
              {i === 0 && <label style={S.label}>자재명</label>}
              <input style={S.input} placeholder="자재명" value={m.material_name}
                onChange={e => updateMat(i, 'material_name', e.target.value)} />
            </div>
            <div style={{ flex: '0 1 80px' }}>
              {i === 0 && <label style={S.label}>수량</label>}
              <input style={S.input} type="number" placeholder="0" value={m.quantity}
                onChange={e => updateMat(i, 'quantity', e.target.value)} />
            </div>
            <div style={{ flex: '0 1 70px' }}>
              {i === 0 && <label style={S.label}>단위</label>}
              <input style={S.input} placeholder="EA" value={m.unit}
                onChange={e => updateMat(i, 'unit', e.target.value)} />
            </div>
            <button onClick={() => removeMat(i)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#d44c47', fontSize: 16, padding: '0 4px', alignSelf: 'center',
            }}>✕</button>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
        <button style={S.btn} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? '저장 중...' : isEdit ? '수정 저장' : '발주 등록'}
        </button>
        <button style={{ ...S.btnSm, padding: '8px 16px' }} onClick={onDone}>취소</button>
      </div>
    </div>
  )
}

// ─── 탭3: 사급 자재 현황 ────────────────────────────────────
function MaterialList() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['sub-materials'],
    queryFn: () => api.get('/sub/materials/').then(r => r.data),
    staleTime: 30000,
  })
  const items = Array.isArray(data) ? data : (data?.results ?? [])

  const [editing, setEditing] = useState(null)

  const updateMutation = useMutation({
    mutationFn: ({ id, issued_qty, returned_qty }) =>
      api.patch(`/sub/materials/${id}/`, { issued_qty, returned_qty }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sub-materials'] })
      setEditing(null)
    },
  })

  if (isLoading) return <div style={{ padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>불러오는 중...</div>

  return (
    <div style={{ padding: 20 }}>
      <div style={{ fontSize: 12, color: '#9b9b9b', marginBottom: 12 }}>
        외주 발주에 지급된 사급 자재 현황입니다. 출고·반납 수량을 업데이트할 수 있습니다.
      </div>
      {items.length === 0 ? (
        <div style={{ ...S.card, padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
          등록된 사급 자재가 없습니다.
        </div>
      ) : (
        <div style={S.card}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  {['발주번호', '자재명', '지급 수량', '출고 수량', '반납 수량', '잔여'].map(h => (
                    <th key={h} style={{
                      background: '#f5f5f3', padding: '8px 12px', textAlign: 'left',
                      fontWeight: 600, color: '#6b6b6b', borderBottom: '1px solid #e9e9e7', fontSize: 12,
                    }}>{h}</th>
                  ))}
                  <th style={{ background: '#f5f5f3', padding: '8px 12px', borderBottom: '1px solid #e9e9e7' }} />
                </tr>
              </thead>
              <tbody>
                {items.map(m => {
                  const isEd = editing?.id === m.id
                  const remain = parseFloat(m.quantity) - parseFloat(m.issued_qty) + parseFloat(m.returned_qty)
                  return (
                    <tr key={m.id} style={{ borderBottom: '1px solid #f0f0ee' }}>
                      <td style={{ padding: '8px 12px', color: '#1a56db', fontWeight: 600 }}>{m.order}</td>
                      <td style={{ padding: '8px 12px' }}>{m.material_name}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right' }}>{m.quantity}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                        {isEd ? (
                          <input style={{ ...S.input, width: 80 }} type="number"
                            value={editing.issued_qty}
                            onChange={e => setEditing(p => ({ ...p, issued_qty: e.target.value }))} />
                        ) : m.issued_qty}
                      </td>
                      <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                        {isEd ? (
                          <input style={{ ...S.input, width: 80 }} type="number"
                            value={editing.returned_qty}
                            onChange={e => setEditing(p => ({ ...p, returned_qty: e.target.value }))} />
                        ) : m.returned_qty}
                      </td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', color: remain < 0 ? '#d44c47' : '#6b6b6b' }}>
                        {remain.toFixed(3)}
                      </td>
                      <td style={{ padding: '8px 12px' }}>
                        {isEd ? (
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button style={{ ...S.btnSm, color: '#2e7d32', borderColor: '#a5d6a7' }}
                              onClick={() => updateMutation.mutate(editing)}>저장</button>
                            <button style={S.btnSm} onClick={() => setEditing(null)}>취소</button>
                          </div>
                        ) : (
                          <button style={{ ...S.btnSm, fontSize: 11 }}
                            onClick={() => setEditing({ id: m.id, issued_qty: m.issued_qty, returned_qty: m.returned_qty })}>
                            수정
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── 탭4: 입고 처리 ──────────────────────────────────────────
function ReceiptTab() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    order: '', receipt_date: new Date().toISOString().slice(0, 10),
    item_name: '', ordered_qty: '', received_qty: '', rejected_qty: '0',
    warehouse: '', receiver: '', note: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['sub-receipts'],
    queryFn: () => api.get('/sub/receipts/').then(r => r.data),
    staleTime: 30000,
  })
  const receipts = Array.isArray(data) ? data : (data?.results ?? [])

  const { data: ordersData } = useQuery({
    queryKey: ['sub-orders-for-receipt'],
    queryFn: () => api.get('/sub/orders/', { params: { status: 'completed' } }).then(r => r.data),
  })
  const completedOrders = Array.isArray(ordersData) ? ordersData : (ordersData?.results ?? [])

  const saveMutation = useMutation({
    mutationFn: () => api.post('/sub/receipts/', form).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sub-receipts'] })
      qc.invalidateQueries({ queryKey: ['sub-orders'] })
      setShowForm(false)
      setForm({
        order: '', receipt_date: new Date().toISOString().slice(0, 10),
        item_name: '', ordered_qty: '', received_qty: '', rejected_qty: '0',
        warehouse: '', receiver: '', note: '',
      })
      alert('입고가 등록되었습니다.')
    },
    onError: (e) => alert(e.response?.data ? JSON.stringify(e.response.data) : '저장 실패'),
  })

  const f = (key) => ({ value: form[key], onChange: e => setForm(p => ({ ...p, [key]: e.target.value })) })

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
        <button style={S.btn} onClick={() => setShowForm(v => !v)}>
          {showForm ? '▲ 입고 폼 닫기' : '+ 입고 등록'}
        </button>
      </div>

      {showForm && (
        <div style={{ ...S.card, marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14, color: '#1a1a2e' }}>📥 외주 입고 등록</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ ...S.field, flex: '1 1 200px' }}>
              <label style={S.label}>외주 발주서 (작업완료 건)</label>
              <select style={S.select} {...f('order')}>
                <option value="">-- 발주서 선택 --</option>
                {completedOrders.map(o => (
                  <option key={o.id} value={o.id}>{o.order_number} – {o.supplier_name}</option>
                ))}
              </select>
            </div>
            <div style={{ ...S.field, flex: '1 1 140px' }}>
              <label style={S.label}>입고일</label>
              <input style={S.input} type="date" {...f('receipt_date')} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ ...S.field, flex: '2 1 200px' }}>
              <label style={S.label}>품목명</label>
              <input style={S.input} placeholder="입고 품목" {...f('item_name')} />
            </div>
            <div style={{ ...S.field, flex: '0 1 90px' }}>
              <label style={S.label}>발주수량</label>
              <input style={S.input} type="number" {...f('ordered_qty')} />
            </div>
            <div style={{ ...S.field, flex: '0 1 90px' }}>
              <label style={S.label}>입고수량</label>
              <input style={S.input} type="number" {...f('received_qty')} />
            </div>
            <div style={{ ...S.field, flex: '0 1 90px' }}>
              <label style={S.label}>불량수량</label>
              <input style={S.input} type="number" {...f('rejected_qty')} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ ...S.field, flex: '1 1 150px' }}>
              <label style={S.label}>입고 창고</label>
              <input style={S.input} placeholder="창고명" {...f('warehouse')} />
            </div>
            <div style={{ ...S.field, flex: '1 1 150px' }}>
              <label style={S.label}>수령 담당자</label>
              <input style={S.input} placeholder="담당자명" {...f('receiver')} />
            </div>
            <div style={{ ...S.field, flex: '2 1 200px' }}>
              <label style={S.label}>비고</label>
              <input style={S.input} placeholder="특이사항" {...f('note')} />
            </div>
          </div>
          <button style={S.btn} onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? '등록 중...' : '입고 등록'}
          </button>
        </div>
      )}

      {isLoading ? (
        <div style={{ padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>불러오는 중...</div>
      ) : receipts.length === 0 ? (
        <div style={{ ...S.card, padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
          입고 기록이 없습니다.
        </div>
      ) : (
        <div style={S.card}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  {['입고번호', '발주번호', '공급업체', '품목명', '발주량', '입고량', '불량량', '입고일', '창고'].map(h => (
                    <th key={h} style={{
                      background: '#f5f5f3', padding: '8px 12px', textAlign: 'left',
                      fontWeight: 600, color: '#6b6b6b', borderBottom: '1px solid #e9e9e7',
                      fontSize: 12, whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {receipts.map(r => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #f0f0ee' }}>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: '#1a1a2e' }}>{r.receipt_number}</td>
                    <td style={{ padding: '8px 12px', color: '#1a56db' }}>{r.order_number || '-'}</td>
                    <td style={{ padding: '8px 12px', color: '#6b6b6b' }}>{r.supplier_name || '-'}</td>
                    <td style={{ padding: '8px 12px' }}>{r.item_name}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>{r.ordered_qty}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#2e7d32', fontWeight: 600 }}>{r.received_qty}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', color: parseFloat(r.rejected_qty) > 0 ? '#d44c47' : '#9b9b9b' }}>{r.rejected_qty}</td>
                    <td style={{ padding: '8px 12px', color: '#6b6b6b', fontSize: 12 }}>{r.receipt_date}</td>
                    <td style={{ padding: '8px 12px', color: '#6b6b6b' }}>{r.warehouse || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function SubPage() {
  const [activeTab, setActiveTab] = useState(0)
  const [editOrder, setEditOrder] = useState(undefined)  // undefined=목록, null=신규, obj=수정

  const handleEdit = (order) => {
    setEditOrder(order)    // null=신규, obj=수정
    setActiveTab(1)
  }
  const handleDone = () => {
    setEditOrder(undefined)
    setActiveTab(0)
  }

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🏭</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>SUB 외주관리</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>
          외주 발주 · 사급 자재 관리 · 입고 처리 · 이메일 발송
        </div>
      </div>

      {/* 탭 패널 */}
      <div style={{
        background: 'white', border: '1px solid #e9e9e7',
        borderRadius: 10, overflow: 'hidden',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      }}>
        <div style={{ borderBottom: '1px solid #e9e9e7', display: 'flex' }}>
          {TABS.map((tab, i) => (
            <button key={tab} onClick={() => setActiveTab(i)} style={{
              padding: '12px 22px', fontSize: 13, fontWeight: 500,
              border: 'none', cursor: 'pointer',
              background: activeTab === i ? '#1a1a2e' : 'transparent',
              color: activeTab === i ? 'white' : '#6b6b6b',
              borderBottom: activeTab === i ? '2px solid #1a1a2e' : '2px solid transparent',
              transition: 'all 0.12s',
            }}>
              {tab}
            </button>
          ))}
        </div>
        {activeTab === 0 && <OrderList onEdit={handleEdit} />}
        {activeTab === 1 && <OrderForm editOrder={editOrder} onDone={handleDone} />}
        {activeTab === 2 && <MaterialList />}
        {activeTab === 3 && <ReceiptTab />}
      </div>
    </div>
  )
}
