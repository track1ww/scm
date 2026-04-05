import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['생산오더', 'BOM 관리', 'MRP 계획']

// ─── 공통 헬퍼 ────────────────────────────────────────────────
function getList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

// ─── 공통 스타일 ──────────────────────────────────────────────
const S = {
  input: {
    width: '100%', padding: '8px 10px',
    border: '1px solid #e9e9e7', borderRadius: 6,
    fontSize: 13, boxSizing: 'border-box', outline: 'none',
  },
  label: { fontSize: 12, color: '#6b6b6b', marginBottom: 4, display: 'block' },
  field: { marginBottom: 12 },
  btnSave: {
    width: '100%', background: '#1a1a2e', color: 'white',
    padding: '10px', borderRadius: 6, border: 'none',
    marginTop: 16, cursor: 'pointer', fontSize: 13,
  },
  btnCancel: {
    width: '100%', background: '#f5f5f3', color: '#6b6b6b',
    marginTop: 6, padding: '8px', borderRadius: 6,
    border: '1px solid #e9e9e7', cursor: 'pointer', fontSize: 13,
  },
  btnEdit: {
    background: '#f0f4ff', color: '#3366cc',
    border: '1px solid #c5d5f5', borderRadius: 4,
    padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
  btnDelete: {
    background: '#fff0f0', color: '#cc3333',
    border: '1px solid #f5c5c5', borderRadius: 4,
    padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
  btnAction: {
    background: '#f0fff4', color: '#2d7a2d',
    border: '1px solid #b5e0b5', borderRadius: 4,
    padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
  formPanel: {
    width: 320, flexShrink: 0,
    background: 'white', border: '1px solid #e9e9e7',
    borderRadius: 10, padding: 20, alignSelf: 'flex-start',
  },
  formTitle: { fontSize: 14, fontWeight: 600, marginBottom: 16, margin: '0 0 16px' },
}

// ─── KPI 카드 ─────────────────────────────────────────────────
function KpiCard({ label, value, unit }) {
  return (
    <div style={{
      background: 'white', border: '1px solid #e9e9e7',
      borderRadius: 10, padding: '18px 20px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    }}>
      <div style={{ fontSize: 11, color: '#9b9b9b', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      {unit && <div style={{ fontSize: 11, color: '#9b9b9b', marginTop: 6 }}>{unit}</div>}
    </div>
  )
}

// ─── 테이블 공통 래퍼 ─────────────────────────────────────────
function DataTable({ isLoading, isError, rows, columns }) {
  if (isLoading) {
    return (
      <div style={{ padding: '48px 0', textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
        데이터를 불러오는 중...
      </div>
    )
  }
  if (isError || rows.length === 0) {
    return (
      <div style={{ padding: '48px 0', textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
        데이터가 없습니다
      </div>
    )
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} style={{
                background: '#f5f5f3', padding: '10px 16px',
                textAlign: 'left', fontWeight: 600, color: '#6b6b6b',
                borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap',
              }}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id ?? i}
              style={{ borderBottom: '1px solid #e9e9e7' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#f9f9f7' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
            >
              {columns.map(col => (
                <td key={col.key} style={{ padding: '10px 16px', color: '#1a1a1a' }}>
                  {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── 상태 배지 ────────────────────────────────────────────────
const STATUS_MAP = {
  DRAFT:       { label: '초안',   bg: '#f5f5f3', color: '#6b6b6b' },
  RELEASED:    { label: '확정',   bg: '#e3f2fd', color: '#1565c0' },
  COMPLETED:   { label: '완료',   bg: '#e8f5e9', color: '#2e7d32' },
  planned:     { label: '계획',   bg: '#f5f5f3', color: '#6b6b6b' },
  in_progress: { label: '진행중', bg: '#e3f2fd', color: '#1565c0' },
  completed:   { label: '완료',   bg: '#e8f5e9', color: '#2e7d32' },
  cancelled:   { label: '취소',   bg: '#fdecea', color: '#d44c47' },
  pending:     { label: '대기',   bg: '#fff8e1', color: '#b45309' },
  shortage:    { label: '부족',   bg: '#fdecea', color: '#d44c47' },
  ok:          { label: '충족',   bg: '#e8f5e9', color: '#2e7d32' },
}

function StatusBadge({ status }) {
  const s = STATUS_MAP[status] ?? { label: status ?? '-', bg: '#f5f5f3', color: '#6b6b6b' }
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px',
      borderRadius: 99, fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.color,
    }}>
      {s.label}
    </span>
  )
}

// ─── 완료 처리 모달 (actual_qty 입력) ────────────────────────
function CompleteOrderModal({ order, onClose }) {
  const [actualQty, setActualQty] = useState(order.planned_qty ?? '')
  const qc = useQueryClient()
  const mutation = useMutation({
    mutationFn: qty => api.post(`/pp/production-orders/${order.id}/complete/`, { actual_qty: Number(qty) }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pp-orders'] })
      onClose()
    },
  })

  const overlayStyle = {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.4)', zIndex: 1000,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  }
  const modalStyle = {
    background: 'white', borderRadius: 12, padding: 28,
    width: 360, maxHeight: '80vh', overflowY: 'auto', margin: 'auto',
  }

  return (
    <div style={overlayStyle} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={modalStyle}>
        <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 700 }}>생산 완료 처리</h3>
        <p style={{ fontSize: 13, color: '#6b6b6b', marginBottom: 16 }}>
          오더번호: <strong>{order.order_number}</strong>
        </p>
        <div style={S.field}>
          <label htmlFor="pp-complete-actual-qty" style={S.label}>실제 생산수량 *</label>
          <input
            id="pp-complete-actual-qty"
            name="actual_qty"
            style={S.input}
            type="number" min="0"
            value={actualQty}
            onChange={e => setActualQty(e.target.value)}
          />
        </div>
        {mutation.isError && (
          <div style={{ color: '#d44c47', fontSize: 12, marginBottom: 12 }}>오류가 발생했습니다.</div>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button
            style={{ background: '#f5f5f3', color: '#6b6b6b', padding: '8px 16px', borderRadius: 6, border: 'none', cursor: 'pointer' }}
            onClick={onClose}
          >
            취소
          </button>
          <button
            style={{ background: '#1a1a2e', color: 'white', padding: '8px 20px', borderRadius: 6, border: 'none', cursor: 'pointer' }}
            disabled={mutation.isPending}
            onClick={() => mutation.mutate(actualQty)}
          >
            {mutation.isPending ? '처리 중...' : '완료 처리'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── 생산오더 탭 (2컬럼) ──────────────────────────────────────
const initialOrderForm = {
  order_number: '', product_name: '', planned_qty: '',
  planned_start: '', planned_end: '', work_center: '', note: '',
}

function ProductionOrderTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialOrderForm)
  const [completeTarget, setCompleteTarget] = useState(null)
  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['pp-orders', page],
    queryFn: () => api.get(`/pp/production-orders/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const createMutation = useMutation({
    mutationFn: payload => api.post('/pp/production-orders/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialOrderForm)
      qc.invalidateQueries({ queryKey: ['pp-orders'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const releaseMutation = useMutation({
    mutationFn: id => api.post(`/pp/production-orders/${id}/release/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pp-orders'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/pp/production-orders/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pp-orders'] }),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.order_number.trim() || !form.product_name.trim() || !form.planned_qty) {
      setGlobalError('오더번호, 제품명, 계획수량은 필수입니다.')
      return
    }
    clearErrors(); setSuccessMsg('')
    createMutation.mutate({ ...form, planned_qty: Number(form.planned_qty) })
  }

  const handleDelete = row => {
    requestConfirm({ message: `오더 "${row.order_number}"를 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })
  }

  const columns = [
    { key: 'order_number',  label: '오더번호' },
    { key: 'product_name',  label: '제품명' },
    { key: 'planned_qty',   label: '계획수량' },
    { key: 'produced_qty',  label: '실적수량' },
    { key: 'status',        label: '상태', render: v => <StatusBadge status={v} /> },
    { key: 'planned_start', label: '계획시작' },
    { key: 'planned_end',   label: '계획종료' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => {
        const isDraft    = row.status === 'DRAFT'    || row.status === 'planned'
        const isReleased = row.status === 'RELEASED' || row.status === 'in_progress'
        return (
          <div style={{ display: 'flex', gap: 4 }}>
            {isDraft && (
              <button style={S.btnAction} onClick={() => releaseMutation.mutate(row.id)}>확정</button>
            )}
            {isReleased && (
              <button style={S.btnAction} onClick={() => setCompleteTarget(row)}>완료</button>
            )}
            {isDraft && (
              <button style={S.btnDelete} onClick={() => handleDelete(row)}>삭제</button>
            )}
          </div>
        )
      },
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-4 p-3 md:p-5 items-start">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>신규 등록</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label htmlFor="pp-order-order-number" style={S.label}>오더번호 *</label>
            <input id="pp-order-order-number" name="order_number" style={S.input} value={form.order_number} onChange={e => set('order_number', e.target.value)} placeholder="PO-2026-001" />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-order-product-name" style={S.label}>제품명 *</label>
            <input id="pp-order-product-name" name="product_name" style={S.input} value={form.product_name} onChange={e => set('product_name', e.target.value)} placeholder="제품명 입력" />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-order-planned-qty" style={S.label}>계획수량 *</label>
            <input id="pp-order-planned-qty" name="planned_qty" style={S.input} type="number" min="1" value={form.planned_qty} onChange={e => set('planned_qty', e.target.value)} placeholder="0" />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-order-planned-start" style={S.label}>계획시작일</label>
            <input id="pp-order-planned-start" name="planned_start" style={S.input} type="date" value={form.planned_start} onChange={e => set('planned_start', e.target.value)} />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-order-planned-end" style={S.label}>계획종료일</label>
            <input id="pp-order-planned-end" name="planned_end" style={S.input} type="date" value={form.planned_end} onChange={e => set('planned_end', e.target.value)} />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-order-work-center" style={S.label}>작업장</label>
            <input id="pp-order-work-center" name="work_center" style={S.input} value={form.work_center} onChange={e => set('work_center', e.target.value)} placeholder="작업장" />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-order-note" style={S.label}>비고</label>
            <textarea
              id="pp-order-note"
              name="note"
              style={{ ...S.input, resize: 'vertical', minHeight: 60 }}
              value={form.note}
              onChange={e => set('note', e.target.value)}
              placeholder="비고"
            />
          </div>
          {createMutation.isError && (
            <div style={{ color: '#d44c47', fontSize: 12, marginBottom: 8 }}>저장 중 오류가 발생했습니다.</div>
          )}
          <button type="submit" style={S.btnSave} disabled={createMutation.isPending}>
            {createMutation.isPending ? '저장 중...' : '등록'}
          </button>
        </form>
      </div>

      {/* 우측 목록 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <DataTable isLoading={isLoading} isError={isError} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>

      {completeTarget && <CompleteOrderModal order={completeTarget} onClose={() => setCompleteTarget(null)} />}
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── BOM 탭 (2컬럼) ───────────────────────────────────────────
const initialBomForm = {
  bom_code: '', product_name: '', version: '', is_active: true,
}
const initialLine = { material_code: '', material_name: '', quantity: '', unit: '' }

function BomTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialBomForm)
  const [editId, setEditId] = useState(null)
  const [lines, setLines] = useState([{ ...initialLine }])
  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['pp-boms', page],
    queryFn: () => api.get(`/pp/boms/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const mutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/pp/boms/${editId}/`, payload).then(r => r.data)
        : api.post('/pp/boms/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialBomForm)
      setEditId(null)
      setLines([{ ...initialLine }])
      qc.invalidateQueries({ queryKey: ['pp-boms'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/pp/boms/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pp-boms'] }),
    onError: (err) => handleApiError(err),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const setLine = (i, k, v) => setLines(ls => ls.map((l, idx) => idx === i ? { ...l, [k]: v } : l))
  const addLine = () => setLines(ls => [...ls, { ...initialLine }])
  const removeLine = i => setLines(ls => ls.filter((_, idx) => idx !== i))

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      bom_code: row.bom_code ?? '',
      product_name: row.product_name ?? '',
      version: row.version ?? '',
      is_active: row.is_active ?? true,
    })
    setEditId(row.id)
    setLines(
      row.bom_lines?.length ? row.bom_lines.map(l => ({
        material_code: l.material_code ?? '',
        material_name: l.material_name ?? '',
        quantity: l.quantity ?? '',
        unit: l.unit ?? '',
      })) : [{ ...initialLine }]
    )
  }

  const handleCancel = () => {
    setForm(initialBomForm)
    setEditId(null)
    setLines([{ ...initialLine }])
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.bom_code.trim() || !form.product_name.trim()) {
      setGlobalError('BOM 코드와 제품명은 필수입니다.')
      return
    }
    clearErrors(); setSuccessMsg('')
    mutation.mutate({
      ...form,
      lines: lines
        .filter(l => l.material_code.trim() || l.material_name.trim())
        .map(l => ({ ...l, quantity: l.quantity ? Number(l.quantity) : null })),
    })
  }

  const handleDelete = row => {
    requestConfirm({ message: `BOM "${row.bom_code}"를 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })
  }

  const columns = [
    { key: 'bom_code',     label: 'BOM코드' },
    { key: 'product_name', label: '제품명' },
    { key: 'version',      label: '버전' },
    { key: 'is_active',    label: '활성', render: v => (v ? '활성' : '비활성') },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDelete} onClick={() => handleDelete(row)}>삭제</button>
        </div>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-4 p-3 md:p-5 items-start">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>{editId ? '수정' : '신규 등록'}</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label htmlFor="pp-bom-bom-code" style={S.label}>BOM 코드 *</label>
            <input id="pp-bom-bom-code" name="bom_code" style={S.input} value={form.bom_code} onChange={e => set('bom_code', e.target.value)} placeholder="BOM-001" />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-bom-product-name" style={S.label}>제품명 *</label>
            <input id="pp-bom-product-name" name="product_name" style={S.input} value={form.product_name} onChange={e => set('product_name', e.target.value)} placeholder="제품명" />
          </div>
          <div style={S.field}>
            <label htmlFor="pp-bom-version" style={S.label}>버전</label>
            <input id="pp-bom-version" name="version" style={S.input} value={form.version} onChange={e => set('version', e.target.value)} placeholder="1.0" />
          </div>
          <div style={{ ...S.field, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox" id="bom_is_active"
              checked={form.is_active}
              onChange={e => set('is_active', e.target.checked)}
              style={{ width: 'auto' }}
            />
            <label htmlFor="bom_is_active" style={{ ...S.label, margin: 0 }}>활성</label>
          </div>

          {/* BOM 라인 */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#3b3b3b' }}>BOM 라인</span>
              <button
                type="button"
                onClick={addLine}
                style={{ background: '#f5f5f3', color: '#3b3b3b', border: '1px solid #e9e9e7', borderRadius: 4, padding: '3px 8px', fontSize: 11, cursor: 'pointer' }}
              >
                + 재료 추가
              </button>
            </div>
            <div className="overflow-x-auto" style={{ border: '1px solid #e9e9e7', borderRadius: 6 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, minWidth: 480 }}>
                <thead>
                  <tr style={{ background: '#f5f5f3' }}>
                    {['자재코드', '자재명', '수량', '단위', ''].map(h => (
                      <th key={h} style={{ padding: '5px 6px', textAlign: 'left', fontWeight: 600, color: '#6b6b6b', borderBottom: '1px solid #e9e9e7' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f0f0ee' }}>
                      <td style={{ padding: '3px 4px' }}>
                        <input style={{ ...S.input, padding: '3px 6px', fontSize: 11 }} value={line.material_code} onChange={e => setLine(i, 'material_code', e.target.value)} placeholder="MAT-001" />
                      </td>
                      <td style={{ padding: '3px 4px' }}>
                        <input style={{ ...S.input, padding: '3px 6px', fontSize: 11 }} value={line.material_name} onChange={e => setLine(i, 'material_name', e.target.value)} placeholder="자재명" />
                      </td>
                      <td style={{ padding: '3px 4px' }}>
                        <input style={{ ...S.input, padding: '3px 6px', fontSize: 11 }} type="number" min="0" value={line.quantity} onChange={e => setLine(i, 'quantity', e.target.value)} placeholder="0" />
                      </td>
                      <td style={{ padding: '3px 4px' }}>
                        <input style={{ ...S.input, padding: '3px 6px', fontSize: 11 }} value={line.unit} onChange={e => setLine(i, 'unit', e.target.value)} placeholder="EA" />
                      </td>
                      <td style={{ padding: '3px 4px', textAlign: 'center' }}>
                        {lines.length > 1 && (
                          <button type="button" onClick={() => removeLine(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#d44c47', fontSize: 13, padding: '0 2px' }}>x</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {mutation.isError && (
            <div style={{ color: '#d44c47', fontSize: 12, marginBottom: 8 }}>저장 중 오류가 발생했습니다.</div>
          )}
          <button type="submit" style={S.btnSave} disabled={mutation.isPending}>
            {mutation.isPending ? '저장 중...' : (editId ? '수정완료' : '등록')}
          </button>
          {editId && (
            <button type="button" style={S.btnCancel} onClick={handleCancel}>취소</button>
          )}
        </form>
      </div>

      {/* 우측 목록 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <DataTable isLoading={isLoading} isError={isError} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── MRP 탭 (폼 없음, 전체 너비) ─────────────────────────────
function MrpTab() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['pp-mrp-plans', page],
    queryFn: () => api.get(`/pp/mrp-plans/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const runMutation = useMutation({
    mutationFn: () => api.post('/pp/mrp-plans/run_mrp/', { plan_date: today() }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pp-mrp-plans'] }),
  })

  const columns = [
    { key: 'material_code',       label: '자재코드' },
    { key: 'material_name',       label: '자재명' },
    { key: 'required_qty',        label: '소요량' },
    { key: 'available_qty',       label: '가용재고' },
    { key: 'shortage_qty',        label: '부족수량' },
    { key: 'suggested_order_qty', label: '발주권장량' },
    { key: 'status',              label: '상태', render: v => <StatusBadge status={v} /> },
  ]

  return (
    <div style={{ padding: 20 }}>
      <div className="flex flex-wrap items-center justify-end gap-3 mb-4">
        {runMutation.isSuccess && <span style={{ fontSize: 12, color: '#2e7d32', marginRight: 12 }}>MRP 실행 완료</span>}
        {runMutation.isError && <span style={{ fontSize: 12, color: '#d44c47', marginRight: 12 }}>MRP 실행 오류</span>}
        <button
          style={{
            background: runMutation.isPending ? '#888' : '#1a1a2e',
            color: 'white', padding: '9px 20px', borderRadius: 6,
            border: 'none', cursor: 'pointer', fontSize: 13,
          }}
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
        >
          {runMutation.isPending ? 'MRP 실행 중...' : 'MRP 실행'}
        </button>
      </div>
      <DataTable isLoading={isLoading} isError={isError} rows={rows} columns={columns} />
      <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function PpPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: dashboardData } = useQuery({
    queryKey: ['pp-dashboard'],
    queryFn: () => api.get('/pp/production-orders/dashboard/').then(r => r.data).catch(() => null),
  })
  const { data: ordersData } = useQuery({
    queryKey: ['pp-orders'],
    queryFn: () => api.get('/pp/production-orders/').then(r => r.data).catch(() => []),
  })

  const orders     = getList(ordersData)
  const inProgress = dashboardData?.in_progress ?? orders.filter(o => o.status === 'in_progress' || o.status === 'RELEASED').length
  const completed  = dashboardData?.completed   ?? orders.filter(o => o.status === 'completed'   || o.status === 'COMPLETED').length

  const totalPlanned  = orders.reduce((s, o) => s + (Number(o.planned_qty)  || 0), 0)
  const totalProduced = orders.reduce((s, o) => s + (Number(o.produced_qty) || 0), 0)
  const achievement   = dashboardData?.achievement ??
    (totalPlanned > 0 ? Math.round((totalProduced / totalPlanned) * 100) : '-')

  const TAB_COMPONENTS = [ProductionOrderTab, BomTab, MrpTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🏭</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>PP 생산계획</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Production Planning — 생산오더·BOM·MRP를 통합 관리합니다.</div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="진행 중 생산"   value={ordersData ? inProgress  : '-'} unit="건" />
        <KpiCard label="완료"           value={ordersData ? completed   : '-'} unit="건" />
        <KpiCard label="계획 대비 실적" value={ordersData ? achievement : '-'} unit="%" />
      </div>

      {/* 탭 패널 */}
      <div style={{
        background: 'white', border: '1px solid #e9e9e7',
        borderRadius: 10, overflow: 'hidden',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      }}>
        <div className="overflow-x-auto" style={{ borderBottom: '1px solid #e9e9e7' }}>
          <div className="flex min-w-max">
            {TABS.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(i)}
                style={{
                  padding: '12px 20px', fontSize: 13, fontWeight: 500,
                  border: 'none', cursor: 'pointer',
                  background: activeTab === i ? '#1a1a2e' : 'transparent',
                  color: activeTab === i ? 'white' : '#6b6b6b',
                  borderBottom: activeTab === i ? '2px solid #1a1a2e' : '2px solid transparent',
                  transition: 'all 0.12s',
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        <ActiveContent />
      </div>
    </div>
  )
}
