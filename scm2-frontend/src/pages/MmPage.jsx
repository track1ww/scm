import { useState, Fragment } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage, FieldError } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'
import { useSortedData } from '../hooks/useSortedData'

const TABS = ['공급처 관리', '자재 목록', '발주 관리', '입고 처리', '공급처 비교', '소요량 계획']

// ─── 공통 헬퍼 ────────────────────────────────────────────────
function getList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
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

// ─── 상태 배지 ────────────────────────────────────────────────
const STATUS_MAP = {
  draft:     { label: '초안',    bg: '#f5f5f3', color: '#6b6b6b' },
  pending:   { label: '대기',    bg: '#fff8e1', color: '#b45309' },
  ordered:   { label: '발주완료', bg: '#e8f0fe', color: '#1a56db' },
  confirmed: { label: '확정',    bg: '#e8f5e9', color: '#2e7d32' },
  received:  { label: '입고완료', bg: '#e3f2fd', color: '#1565c0' },
  cancelled: { label: '취소',    bg: '#fdecea', color: '#d44c47' },
  partial:   { label: '부분입고', bg: '#f3e5f5', color: '#6a1b9a' },
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

// ─── 공통 스타일 ───────────────────────────────────────────────
const inputStyle = {
  width: '100%', padding: '8px 10px',
  border: '1px solid #e9e9e7', borderRadius: 6,
  fontSize: 13, outline: 'none', boxSizing: 'border-box',
  fontFamily: "'Inter', 'Noto Sans KR', sans-serif",
}

const selectStyle = { ...inputStyle, background: 'white', cursor: 'pointer' }

// ─── 좌측 폼 패널 ─────────────────────────────────────────────
function FormPanel({ title, onSubmit, onCancel, isEditMode, isPending, children }) {
  return (
    <div style={{
      width: 320, flexShrink: 0,
      background: 'white', border: '1px solid #e9e9e7',
      borderRadius: 10, padding: 20,
      display: 'flex', flexDirection: 'column', gap: 12,
      alignSelf: 'flex-start',
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', marginBottom: 4 }}>
        {isEditMode ? '수정' : title}
      </div>
      {children}
      <button
        onClick={onSubmit}
        disabled={isPending}
        style={{
          width: '100%', background: '#1a1a2e', color: 'white',
          padding: '10px', borderRadius: 6, border: 'none',
          fontSize: 13, cursor: isPending ? 'not-allowed' : 'pointer',
          fontWeight: 500, opacity: isPending ? 0.7 : 1, marginTop: 4,
        }}
      >
        {isPending ? '저장 중...' : (isEditMode ? '수정 완료' : '등록')}
      </button>
      {isEditMode && (
        <button
          onClick={onCancel}
          style={{
            width: '100%', background: '#f5f5f3', color: '#6b6b6b',
            padding: '8px', borderRadius: 6, border: '1px solid #e9e9e7',
            fontSize: 13, cursor: 'pointer', fontWeight: 500,
          }}
        >
          취소
        </button>
      )}
    </div>
  )
}

// ─── 폼 필드 공통 ─────────────────────────────────────────────
function Field({ label, htmlFor, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label htmlFor={htmlFor} style={{ fontSize: 12, color: '#6b6b6b', display: 'block', marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  )
}

// ─── 우측 테이블 패널 ─────────────────────────────────────────
function TablePanel({ isLoading, isError, rows, columns, renderActions, hasActions, sortKey, sortDir, onSort }) {
  return (
    <div style={{ flex: 1, minWidth: 0, overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                onClick={() => onSort?.(col.key)}
                aria-sort={sortKey === col.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                style={{
                  background: '#f5f5f3', padding: '10px 12px',
                  textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                  borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap',
                  cursor: onSort ? 'pointer' : 'default',
                  userSelect: 'none',
                }}
              >
                {col.label}
                {onSort && (
                  <span style={{ marginLeft: 4, opacity: sortKey === col.key ? 1 : 0.3 }}>
                    {sortKey === col.key && sortDir === 'desc' ? '▼' : '▲'}
                  </span>
                )}
              </th>
            ))}
            {hasActions && (
              <th style={{
                background: '#f5f5f3', padding: '10px 12px',
                textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap',
              }}>
                액션
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <tr>
              <td colSpan={columns.length + (hasActions ? 1 : 0)}
                style={{ padding: '40px 0', textAlign: 'center', color: '#9b9b9b' }}>
                데이터를 불러오는 중...
              </td>
            </tr>
          )}
          {isError && (
            <tr>
              <td colSpan={columns.length + (hasActions ? 1 : 0)}
                style={{ padding: '40px 0', textAlign: 'center', color: '#9b9b9b' }}>
                데이터를 불러오지 못했습니다
              </td>
            </tr>
          )}
          {!isLoading && !isError && rows.length === 0 && (
            <tr>
              <td colSpan={columns.length + (hasActions ? 1 : 0)}
                style={{ padding: '40px 0', textAlign: 'center', color: '#9b9b9b' }}>
                데이터가 없습니다
              </td>
            </tr>
          )}
          {rows.map((row, i) => (
            <tr
              key={row.id ?? i}
              style={{ borderBottom: '1px solid #e9e9e7' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#f9f9f7' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
            >
              {columns.map(col => (
                <td key={col.key} style={{ padding: '10px 12px', color: '#1a1a1a' }}>
                  {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '-')}
                </td>
              ))}
              {hasActions && (
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {renderActions && renderActions(row)}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── 테이블 액션 버튼 ─────────────────────────────────────────
function EditBtn({ onClick }) {
  return (
    <button onClick={onClick} style={{
      background: '#f0f4ff', color: '#3366cc',
      border: '1px solid #c5d5f5', borderRadius: 4,
      padding: '4px 10px', fontSize: 11, cursor: 'pointer',
    }}>수정</button>
  )
}

function DeleteBtn({ onClick }) {
  return (
    <button onClick={onClick} style={{
      background: '#fff0f0', color: '#cc3333',
      border: '1px solid #f5c5c5', borderRadius: 4,
      padding: '4px 10px', fontSize: 11, cursor: 'pointer',
    }}>삭제</button>
  )
}

function ActionBtn({ children, onClick, variant = 'default' }) {
  const variants = {
    default: { background: '#f5f5f3', color: '#6b6b6b', border: '1px solid #e9e9e7' },
    danger:  { background: '#fff0f0', color: '#cc3333', border: '1px solid #f5c5c5' },
    primary: { background: '#f0f4ff', color: '#3366cc', border: '1px solid #c5d5f5' },
    success: { background: '#e8f5e9', color: '#2e7d32', border: '1px solid #b2dfdb' },
  }
  const v = variants[variant] ?? variants.default
  return (
    <button onClick={onClick} style={{
      ...v, borderRadius: 4, padding: '4px 10px',
      fontSize: 11, cursor: 'pointer', fontWeight: 500, whiteSpace: 'nowrap',
    }}>{children}</button>
  )
}

// ─── 2컬럼 탭 레이아웃 래퍼 ──────────────────────────────────
function TwoColumnLayout({ formPanel, tablePanel }) {
  return (
    <div className="flex flex-col md:flex-row gap-4 p-3 md:p-4 items-start">
      {formPanel}
      {tablePanel}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// 공급처 탭
// ─────────────────────────────────────────────────────────────
const SUPPLIER_INIT = { supplier_name: '', contact: '', email: '', payment_terms: '' }

function SupplierTab() {
  const qc = useQueryClient()
  const [form, setForm]     = useState(SUPPLIER_INIT)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['mm-suppliers', page],
    queryFn: () => api.get(`/mm/suppliers/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const rawRows = getList(data)
  const { sorted: rows, sortKey, sortDir, toggleSort } = useSortedData(rawRows)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['mm-suppliers'] })

  const createMut = useMutation({
    mutationFn: body => api.post('/mm/suppliers/', body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(SUPPLIER_INIT); setEditId(null); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, body }) => api.put(`/mm/suppliers/${id}/`, body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(SUPPLIER_INIT); setEditId(null); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/mm/suppliers/${id}/`),
    onSuccess: () => invalidate(),
    onError: (err) => handleApiError(err),
  })

  function handleEdit(row) {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      supplier_name: row.supplier_name ?? row.name ?? '',
      contact:       row.contact ?? '',
      email:         row.email ?? '',
      payment_terms: row.payment_terms ?? '',
    })
    setEditId(row.id)
  }
  function handleCancel() {
    setForm(SUPPLIER_INIT)
    setEditId(null)
  }
  function handleSubmit() {
    if (!form.supplier_name.trim()) { setGlobalError('공급처명은 필수입니다.'); return }
    if (editId) {
      updateMut.mutate({ id: editId, body: form })
    } else {
      createMut.mutate(form)
    }
  }
  function handleDelete(row) {
    requestConfirm({ message: `"${row.supplier_name ?? row.name}" 공급처를 삭제하시겠습니까?`, onConfirm: () => deleteMut.mutate(row.id) })
  }

  const isPending = createMut.isPending || updateMut.isPending

  const columns = [
    { key: 'supplier_name', label: '공급처명',  render: (v, row) => v ?? row.name ?? '-' },
    { key: 'contact',       label: '연락처' },
    { key: 'email',         label: '이메일' },
    { key: 'payment_terms', label: '결제조건' },
    { key: 'is_active',     label: '상태', render: v => (v ? '활성' : '비활성') },
  ]

  return (
    <>
    <TwoColumnLayout
      formPanel={
        <FormPanel
          title="신규 등록"
          isEditMode={editId !== null}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          isPending={isPending}
        >
          <GlobalError message={globalError} onClose={() => setGlobalError('')} />
          <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
          <Field label="공급처명 *" htmlFor="sup-supplier-name">
            <input
              id="sup-supplier-name" name="supplier_name"
              style={inputStyle}
              value={form.supplier_name}
              onChange={e => setForm(f => ({ ...f, supplier_name: e.target.value }))}
              placeholder="회사명을 입력하세요"
            />
          </Field>
          <Field label="연락처" htmlFor="sup-contact">
            <input
              id="sup-contact" name="contact"
              style={inputStyle}
              value={form.contact}
              onChange={e => setForm(f => ({ ...f, contact: e.target.value }))}
              placeholder="연락처를 입력하세요"
            />
          </Field>
          <Field label="이메일" htmlFor="sup-email">
            <input
              id="sup-email" name="email"
              style={inputStyle}
              type="email"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="이메일을 입력하세요"
            />
          </Field>
          <Field label="결제조건" htmlFor="sup-payment-terms">
            <select
              id="sup-payment-terms" name="payment_terms"
              style={selectStyle}
              value={form.payment_terms}
              onChange={e => setForm(f => ({ ...f, payment_terms: e.target.value }))}
            >
              <option value="">선택</option>
              <option value="현금">현금</option>
              <option value="30일">30일</option>
              <option value="60일">60일</option>
              <option value="90일">90일</option>
            </select>
          </Field>
        </FormPanel>
      }
      tablePanel={
        <>
          <TablePanel
            isLoading={isLoading}
            isError={isError}
            rows={rows}
            columns={columns}
            hasActions={true}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={toggleSort}
            renderActions={row => (
              <>
                <EditBtn onClick={() => handleEdit(row)} />
                <DeleteBtn onClick={() => handleDelete(row)} />
              </>
            )}
          />
          <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
        </>
      }
    />
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// 자재 탭
// ─────────────────────────────────────────────────────────────
const MATERIAL_INIT = {
  material_code: '', material_name: '', unit: '',
  min_stock: '', lead_time_days: '',
}

function MaterialTab() {
  const qc = useQueryClient()
  const [form, setForm]     = useState(MATERIAL_INIT)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['mm-materials', page],
    queryFn: () => api.get(`/mm/materials/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['mm-materials'] })

  const createMut = useMutation({
    mutationFn: body => api.post('/mm/materials/', body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(MATERIAL_INIT); setEditId(null); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, body }) => api.put(`/mm/materials/${id}/`, body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(MATERIAL_INIT); setEditId(null); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/mm/materials/${id}/`),
    onSuccess: () => invalidate(),
    onError: (err) => handleApiError(err),
  })

  function handleEdit(row) {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      material_code:  row.material_code ?? row.code ?? '',
      material_name:  row.material_name ?? row.name ?? '',
      unit:           row.unit ?? '',
      min_stock:      row.min_stock ?? '',
      lead_time_days: row.lead_time_days ?? '',
    })
    setEditId(row.id)
  }
  function handleCancel() {
    setForm(MATERIAL_INIT)
    setEditId(null)
  }
  function handleSubmit() {
    if (!form.material_code.trim()) { setGlobalError('자재코드는 필수입니다.'); return }
    if (!form.material_name.trim()) { setGlobalError('자재명은 필수입니다.'); return }
    const body = {
      ...form,
      min_stock:      form.min_stock      !== '' ? Number(form.min_stock)      : null,
      lead_time_days: form.lead_time_days !== '' ? Number(form.lead_time_days) : null,
    }
    if (editId) {
      updateMut.mutate({ id: editId, body })
    } else {
      createMut.mutate(body)
    }
  }
  function handleDelete(row) {
    requestConfirm({ message: `"${row.material_name ?? row.name}" 자재를 삭제하시겠습니까?`, onConfirm: () => deleteMut.mutate(row.id) })
  }

  const isPending = createMut.isPending || updateMut.isPending

  const columns = [
    { key: 'material_code', label: '자재코드',  render: (v, row) => v ?? row.code ?? '-' },
    { key: 'material_name', label: '자재명',    render: (v, row) => v ?? row.name ?? '-' },
    { key: 'unit',          label: '단위' },
    { key: 'min_stock',     label: '최소재고' },
    { key: 'lead_time_days', label: '리드타임' },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <TwoColumnLayout
      formPanel={
        <FormPanel
          title="신규 등록"
          isEditMode={editId !== null}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          isPending={isPending}
        >
          <Field label="자재코드 *" htmlFor="mat-material-code">
            <input
              id="mat-material-code" name="material_code"
              style={inputStyle}
              value={form.material_code}
              onChange={e => setForm(f => ({ ...f, material_code: e.target.value }))}
              placeholder="예: MAT-001"
            />
          </Field>
          <Field label="자재명 *" htmlFor="mat-material-name">
            <input
              id="mat-material-name" name="material_name"
              style={inputStyle}
              value={form.material_name}
              onChange={e => setForm(f => ({ ...f, material_name: e.target.value }))}
              placeholder="자재명을 입력하세요"
            />
          </Field>
          <Field label="단위" htmlFor="mat-unit">
            <input
              id="mat-unit" name="unit"
              style={inputStyle}
              value={form.unit}
              onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
              placeholder="예: kg, EA, box"
            />
          </Field>
          <Field label="최소재고" htmlFor="mat-min-stock">
            <input
              id="mat-min-stock" name="min_stock"
              style={inputStyle}
              type="number"
              value={form.min_stock}
              onChange={e => setForm(f => ({ ...f, min_stock: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="리드타임 (일)" htmlFor="mat-lead-time-days">
            <input
              id="mat-lead-time-days" name="lead_time_days"
              style={inputStyle}
              type="number"
              value={form.lead_time_days}
              onChange={e => setForm(f => ({ ...f, lead_time_days: e.target.value }))}
              placeholder="0"
            />
          </Field>
        </FormPanel>
      }
      tablePanel={
        <>
          <TablePanel
            isLoading={isLoading}
            isError={isError}
            rows={rows}
            columns={columns}
            hasActions={true}
            renderActions={row => (
              <>
                <EditBtn onClick={() => handleEdit(row)} />
                <DeleteBtn onClick={() => handleDelete(row)} />
              </>
            )}
          />
          <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
        </>
      }
    />
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// 발주 탭 — 헤더 + 다품목 라인 지원
// ─────────────────────────────────────────────────────────────
const ORDER_INIT = {
  supplier: '', item_name: '', quantity: '1', unit_price: '0', expected_date: '',
}
const EMPTY_LINE = { line_no: 1, item_name: '', quantity: '', unit_price: '', unit: 'EA', material: '' }

function OrderTab() {
  const qc = useQueryClient()
  const [form, setForm]           = useState(ORDER_INIT)
  const [lines, setLines]         = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const { globalError, handleApiError, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['mm-orders', page],
    queryFn: () => api.get(`/mm/orders/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const { data: suppliersData } = useQuery({
    queryKey: ['mm-suppliers'],
    queryFn: () => api.get('/mm/suppliers/').then(r => r.data),
  })
  const { data: materialsData } = useQuery({
    queryKey: ['mm-materials-all'],
    queryFn: () => api.get('/mm/materials/?page_size=500').then(r => r.data),
  })

  const rows      = getList(data)
  const suppliers = getList(suppliersData)
  const materials = getList(materialsData)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['mm-orders'] })

  const createMut = useMutation({
    mutationFn: async body => {
      const po = await api.post('/mm/orders/', body.header).then(r => r.data)
      if (body.lines.length > 0) {
        await Promise.all(body.lines.map((ln, i) =>
          api.post('/mm/po-lines/', {
            po: po.id,
            line_no: i + 1,
            item_name: ln.item_name,
            quantity: Number(ln.quantity),
            unit_price: ln.unit_price !== '' ? Number(ln.unit_price) : 0,
            unit: ln.unit || 'EA',
            ...(ln.material ? { material: Number(ln.material) } : {}),
          })
        ))
      }
      return po
    },
    onSuccess: () => {
      invalidate()
      setForm(ORDER_INIT)
      setLines([])
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })
  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/mm/orders/${id}/`),
    onSuccess: () => invalidate(),
    onError: (err) => handleApiError(err),
  })

  function addLine() {
    setLines(ls => [...ls, { ...EMPTY_LINE, line_no: ls.length + 1 }])
  }
  function removeLine(i) {
    setLines(ls => ls.filter((_, idx) => idx !== i))
  }
  function updateLine(i, key, value) {
    setLines(ls => ls.map((ln, idx) => idx === i ? { ...ln, [key]: value } : ln))
  }

  function handleSubmit() {
    if (!form.supplier) { setGlobalError('공급처를 선택하세요.'); return }
    if (!form.item_name.trim()) { setGlobalError('품목명은 필수입니다.'); return }
    for (const [i, ln] of lines.entries()) {
      if (!ln.item_name.trim()) { setGlobalError(`라인 ${i + 1}: 품목명을 입력하세요.`); return }
      if (!ln.quantity) { setGlobalError(`라인 ${i + 1}: 수량을 입력하세요.`); return }
    }
    createMut.mutate({
      header: {
        ...form,
        quantity:   Number(form.quantity) || 1,
        unit_price: form.unit_price !== '' ? Number(form.unit_price) : 0,
      },
      lines,
    })
  }
  function handleDelete(row) {
    requestConfirm({ message: `발주 "${row.po_number}"를 삭제하시겠습니까?`, onConfirm: () => deleteMut.mutate(row.id) })
  }

  const totalFromLines = (row) => {
    if (!row.lines?.length) return null
    return row.lines.reduce((s, l) => s + (Number(l.quantity) * Number(l.unit_price || 0)), 0)
  }

  const columns = [
    { key: 'po_number',    label: '발주번호' },
    { key: 'supplier_name', label: '공급처', render: (v, row) => v ?? row.supplier?.name ?? '-' },
    { key: 'item_name',    label: '품목 (요약)' },
    { key: 'lines',        label: '라인', render: (v) => v?.length > 0 ? `${v.length}건` : '-' },
    { key: 'total_amount', label: '총금액', render: (v, row) => {
        const t = totalFromLines(row) ?? v
        return t != null ? Number(t).toLocaleString() + '원' : '-'
    }},
    { key: 'delivery_date', label: '납기일' },
    { key: 'status',       label: '상태', render: v => <StatusBadge status={v} /> },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <TwoColumnLayout
        formPanel={
          <FormPanel
            title="신규 발주 등록"
            isEditMode={false}
            onSubmit={handleSubmit}
            isPending={createMut.isPending}
          >
            <Field label="공급처 *" htmlFor="ord-supplier">
              <select id="ord-supplier" name="supplier" style={selectStyle} value={form.supplier}
                onChange={e => setForm(f => ({ ...f, supplier: e.target.value }))}>
                <option value="">공급처 선택</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.supplier_name ?? s.name}</option>
                ))}
              </select>
            </Field>
            <Field label="품목명 (요약) *" htmlFor="ord-item-name">
              <input id="ord-item-name" name="item_name" style={inputStyle} value={form.item_name} placeholder="예: 원자재 일괄 발주"
                onChange={e => setForm(f => ({ ...f, item_name: e.target.value }))} />
            </Field>
            <div style={{ display: 'flex', gap: 8 }}>
              <Field label="수량" htmlFor="ord-quantity">
                <input id="ord-quantity" name="quantity" style={inputStyle} type="number" min="0" value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} />
              </Field>
              <Field label="단가 (원)" htmlFor="ord-unit-price">
                <input id="ord-unit-price" name="unit_price" style={inputStyle} type="number" min="0" value={form.unit_price}
                  onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))} />
              </Field>
            </div>
            <Field label="납기일" htmlFor="ord-expected-date">
              <input id="ord-expected-date" name="expected_date" style={inputStyle} type="date" value={form.expected_date}
                onChange={e => setForm(f => ({ ...f, expected_date: e.target.value }))} />
            </Field>

            {/* 다품목 라인 섹션 */}
            <div style={{ borderTop: '1px solid #e9e9e7', paddingTop: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#6b6b6b' }}>품목 라인 ({lines.length}건)</span>
                <button type="button" onClick={addLine} style={{
                  background: '#f0f4ff', color: '#3366cc', border: '1px solid #c5d5f5',
                  borderRadius: 4, padding: '3px 10px', fontSize: 11, cursor: 'pointer',
                }}>+ 라인 추가</button>
              </div>
              {lines.map((ln, i) => (
                <div key={i} style={{
                  border: '1px solid #e9e9e7', borderRadius: 6, padding: 10,
                  marginBottom: 8, background: '#fafaf8', position: 'relative',
                }}>
                  <button type="button" onClick={() => removeLine(i)} style={{
                    position: 'absolute', top: 6, right: 8,
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: '#cc3333', fontSize: 14, lineHeight: 1,
                  }} aria-label={`라인 ${i + 1} 삭제`}>×</button>
                  <div style={{ fontSize: 11, color: '#9b9b9b', marginBottom: 6 }}>라인 {i + 1}</div>
                  <Field label="자재 (선택)" htmlFor={`ord-line-${i}-material`}>
                    <select id={`ord-line-${i}-material`} name={`line_${i}_material`}
                      style={{ ...selectStyle, fontSize: 12, padding: '6px 8px' }}
                      value={ln.material}
                      onChange={e => {
                        const mat = materials.find(m => String(m.id) === e.target.value)
                        updateLine(i, 'material', e.target.value)
                        if (mat) updateLine(i, 'item_name', mat.material_name)
                      }}>
                      <option value="">자재 선택 (선택사항)</option>
                      {materials.map(m => (
                        <option key={m.id} value={m.id}>{m.material_code} {m.material_name}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="품목명 *" htmlFor={`ord-line-${i}-item-name`}>
                    <input id={`ord-line-${i}-item-name`} name={`line_${i}_item_name`}
                      style={{ ...inputStyle, fontSize: 12, padding: '6px 8px' }}
                      value={ln.item_name} placeholder="품목명"
                      onChange={e => updateLine(i, 'item_name', e.target.value)} />
                  </Field>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Field label="수량 *" htmlFor={`ord-line-${i}-quantity`}>
                      <input id={`ord-line-${i}-quantity`} name={`line_${i}_quantity`}
                        style={{ ...inputStyle, fontSize: 12, padding: '6px 8px' }}
                        type="number" min="0" value={ln.quantity} placeholder="0"
                        onChange={e => updateLine(i, 'quantity', e.target.value)} />
                    </Field>
                    <Field label="단가" htmlFor={`ord-line-${i}-unit-price`}>
                      <input id={`ord-line-${i}-unit-price`} name={`line_${i}_unit_price`}
                        style={{ ...inputStyle, fontSize: 12, padding: '6px 8px' }}
                        type="number" min="0" value={ln.unit_price} placeholder="0"
                        onChange={e => updateLine(i, 'unit_price', e.target.value)} />
                    </Field>
                    <Field label="단위" htmlFor={`ord-line-${i}-unit`}>
                      <input id={`ord-line-${i}-unit`} name={`line_${i}_unit`}
                        style={{ ...inputStyle, fontSize: 12, padding: '6px 8px', width: 60 }}
                        value={ln.unit} placeholder="EA"
                        onChange={e => updateLine(i, 'unit', e.target.value)} />
                    </Field>
                  </div>
                </div>
              ))}
            </div>
          </FormPanel>
        }
        tablePanel={
          <>
            <div style={{ flex: 1, minWidth: 0, overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr>
                    {columns.map(col => (
                      <th key={col.key} style={{
                        background: '#f5f5f3', padding: '10px 12px', textAlign: 'left',
                        fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                        borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap',
                      }}>{col.label}</th>
                    ))}
                    <th style={{
                      background: '#f5f5f3', padding: '10px 12px', textAlign: 'left',
                      fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                      borderBottom: '1px solid #e9e9e7',
                    }}>액션</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading && (
                    <tr><td colSpan={columns.length + 1}
                      style={{ padding: '40px 0', textAlign: 'center', color: '#9b9b9b' }}>
                      데이터를 불러오는 중...
                    </td></tr>
                  )}
                  {isError && (
                    <tr><td colSpan={columns.length + 1}
                      style={{ padding: '40px 0', textAlign: 'center', color: '#9b9b9b' }}>
                      데이터를 불러오지 못했습니다
                    </td></tr>
                  )}
                  {!isLoading && !isError && rows.length === 0 && (
                    <tr><td colSpan={columns.length + 1}
                      style={{ padding: '40px 0', textAlign: 'center', color: '#9b9b9b' }}>
                      데이터가 없습니다
                    </td></tr>
                  )}
                  {rows.map((row, i) => (
                    <Fragment key={row.id ?? i}>
                      <tr
                        style={{ borderBottom: expandedId === row.id ? 'none' : '1px solid #e9e9e7', cursor: 'pointer' }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#f9f9f7' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                      >
                        {columns.map(col => (
                          <td key={col.key} style={{ padding: '10px 12px', color: '#1a1a1a' }}
                            onClick={() => row.lines?.length && setExpandedId(expandedId === row.id ? null : row.id)}>
                            {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '-')}
                          </td>
                        ))}
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                            {row.lines?.length > 0 && (
                              <ActionBtn onClick={() => setExpandedId(expandedId === row.id ? null : row.id)}>
                                {expandedId === row.id ? '접기' : '라인'}
                              </ActionBtn>
                            )}
                            {row.status === '발주확정' && <DeleteBtn onClick={() => handleDelete(row)} />}
                            <a
                              href={`/api/reports/po/${row.id}/pdf/`}
                              target="_blank" rel="noreferrer"
                              style={{ fontSize: 11, padding: '4px 10px', background: '#f8fafc', color: '#374151', border: '1px solid #e2e8f0', borderRadius: 4, textDecoration: 'none' }}
                            >PDF</a>
                          </div>
                        </td>
                      </tr>
                      {expandedId === row.id && row.lines?.length > 0 && (
                        <tr style={{ borderBottom: '1px solid #e9e9e7' }}>
                          <td colSpan={columns.length + 1} style={{ padding: '0 12px 12px 32px', background: '#fafaf8' }}>
                            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                              <thead>
                                <tr style={{ color: '#9b9b9b' }}>
                                  {['#', '자재코드', '품목명', '수량', '단가', '소계'].map(h => (
                                    <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, borderBottom: '1px solid #e9e9e7' }}>{h}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {row.lines.map(ln => (
                                  <tr key={ln.id}>
                                    <td style={{ padding: '6px 8px' }}>{ln.line_no}</td>
                                    <td style={{ padding: '6px 8px', color: '#6b6b6b' }}>{ln.material_name_display ?? '-'}</td>
                                    <td style={{ padding: '6px 8px' }}>{ln.item_name}</td>
                                    <td style={{ padding: '6px 8px' }}>{ln.quantity} {ln.unit}</td>
                                    <td style={{ padding: '6px 8px' }}>{Number(ln.unit_price).toLocaleString()}원</td>
                                    <td style={{ padding: '6px 8px', fontWeight: 600 }}>{Number(ln.line_total ?? 0).toLocaleString()}원</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
          </>
        }
      />
      <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// 입고 탭 (등록만, 수정/삭제 없음)
// ─────────────────────────────────────────────────────────────
const RECEIPT_INIT = {
  order: '', received_qty: '', warehouse: '', inspector_name: '',
}

function ReceiptTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(RECEIPT_INIT)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['mm-receipts', page],
    queryFn: () => api.get(`/mm/receipts/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const { data: orderedData } = useQuery({
    queryKey: ['mm-orders-ordered'],
    queryFn: () => api.get('/mm/orders/?status=발주확정').then(r => r.data),
  })

  const rows          = getList(data)
  const orderedOrders = getList(orderedData)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['mm-receipts'] })
    qc.invalidateQueries({ queryKey: ['mm-orders'] })
    qc.invalidateQueries({ queryKey: ['mm-orders-ordered'] })
  }

  const createMut = useMutation({
    mutationFn: body => api.post('/mm/receipts/', body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(RECEIPT_INIT); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  function handleSubmit() {
    if (!form.order)        { setGlobalError('발주를 선택하세요.'); return }
    if (!form.received_qty) { setGlobalError('입고수량은 필수입니다.'); return }
    createMut.mutate({
      ...form,
      received_qty: Number(form.received_qty),
    })
  }

  const columns = [
    { key: 'receipt_number', label: '입고번호' },
    { key: 'order_number',   label: '발주번호', render: (v, row) => v ?? row.order?.order_number ?? '-' },
    { key: 'received_qty',   label: '수량' },
    { key: 'warehouse',      label: '창고' },
    { key: 'inspector_name', label: '검수자',   render: (v, row) => v ?? row.inspector ?? '-' },
    { key: 'receipt_date',   label: '입고일' },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <TwoColumnLayout
      formPanel={
        <FormPanel
          title="신규 등록"
          isEditMode={false}
          onSubmit={handleSubmit}
          isPending={createMut.isPending}
        >
          <Field label="발주 선택 *" htmlFor="rec-order">
            <select
              id="rec-order" name="order"
              style={selectStyle}
              value={form.order}
              onChange={e => setForm(f => ({ ...f, order: e.target.value }))}
            >
              <option value="">발주 선택 (ordered 상태)</option>
              {orderedOrders.map(o => (
                <option key={o.id} value={o.id}>
                  {o.order_number} — {o.supplier_name ?? o.supplier?.name ?? ''}
                  {o.item_name ? ` / ${o.item_name}` : ''}
                </option>
              ))}
            </select>
          </Field>
          <Field label="입고수량 *" htmlFor="rec-received-qty">
            <input
              id="rec-received-qty" name="received_qty"
              style={inputStyle}
              type="number"
              value={form.received_qty}
              onChange={e => setForm(f => ({ ...f, received_qty: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="창고" htmlFor="rec-warehouse">
            <input
              id="rec-warehouse" name="warehouse"
              style={inputStyle}
              value={form.warehouse}
              onChange={e => setForm(f => ({ ...f, warehouse: e.target.value }))}
              placeholder="창고명을 입력하세요"
            />
          </Field>
          <Field label="검수자" htmlFor="rec-inspector-name">
            <input
              id="rec-inspector-name" name="inspector_name"
              style={inputStyle}
              value={form.inspector_name}
              onChange={e => setForm(f => ({ ...f, inspector_name: e.target.value }))}
              placeholder="검수자 이름"
            />
          </Field>
        </FormPanel>
      }
      tablePanel={
        <>
          <TablePanel
            isLoading={isLoading}
            isError={isError}
            rows={rows}
            columns={columns}
            hasActions={false}
          />
          <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
        </>
      }
    />
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// 공급처 비교 탭
// ─────────────────────────────────────────────────────────────
function SupplierComparisonTab() {
  const { data: materialsData } = useQuery({
    queryKey: ['mm-materials-simple'],
    queryFn: () => api.get('/mm/materials/?page_size=200').then(r => r.data),
  })
  const materials = materialsData?.results ?? materialsData ?? []

  const [selectedMaterial, setSelectedMaterial] = useState('')
  const { data: compData, isLoading } = useQuery({
    queryKey: ['mm-supplier-comparison', selectedMaterial],
    queryFn: () => api.get(`/mm/materials/${selectedMaterial}/supplier-comparison/`).then(r => r.data),
    enabled: !!selectedMaterial,
  })
  const rows = compData ?? []

  return (
    <div className="p-3 md:p-5">
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">자재 선택:</label>
        <select
          value={selectedMaterial}
          onChange={e => setSelectedMaterial(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">자재를 선택하세요</option>
          {materials.map(m => (
            <option key={m.id} value={m.id}>{m.material_code} — {m.material_name}</option>
          ))}
        </select>
      </div>
      {isLoading && <p className="text-sm text-gray-400">로딩 중...</p>}
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {['공급처', '최근단가', '최저단가', '최고단가', '평균단가', '이력건수', '비고'].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className={`border-b border-gray-100 hover:bg-gray-50 ${i === 0 ? 'bg-green-50' : ''}`}>
                  <td className="px-3 py-2.5 font-medium text-gray-800">{r.supplier_name}</td>
                  <td className="px-3 py-2.5 text-right font-semibold text-blue-700">{r.latest_price?.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-right text-green-700">{r.min_price?.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-right text-red-600">{r.max_price?.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-right text-gray-600">{r.avg_price?.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-center text-gray-500">{r.history_count}건</td>
                  <td className="px-3 py-2.5">{i === 0 && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">최저가</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selectedMaterial && !isLoading && rows.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-8">가격이력 데이터가 없습니다.</p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// 소요량 계획 탭
// ─────────────────────────────────────────────────────────────
function RequirementsPlanTab() {
  const { data: materialsData } = useQuery({
    queryKey: ['mm-materials-simple'],
    queryFn: () => api.get('/mm/materials/?page_size=200').then(r => r.data),
  })
  const materials = materialsData?.results ?? materialsData ?? []
  const [selectedMaterial, setSelectedMaterial] = useState('')

  const { data: req, isLoading } = useQuery({
    queryKey: ['mm-requirements', selectedMaterial],
    queryFn: () => api.get(`/mm/materials/${selectedMaterial}/requirements/`).then(r => r.data),
    enabled: !!selectedMaterial,
  })

  return (
    <div className="p-3 md:p-5">
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">자재 선택:</label>
        <select
          value={selectedMaterial}
          onChange={e => setSelectedMaterial(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">자재를 선택하세요</option>
          {materials.map(m => (
            <option key={m.id} value={m.id}>{m.material_code} — {m.material_name}</option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-sm text-gray-400">로딩 중...</p>}
      {req && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-3xl">
          {[
            { label: '현재 재고', value: req.current_stock, unit: req.unit, color: 'text-gray-900' },
            { label: '입고 예정 (발주)', value: req.pending_po_qty, unit: req.unit, color: 'text-green-700' },
            { label: '출고 예정 (수주)', value: req.pending_so_qty, unit: req.unit, color: 'text-red-600' },
            { label: '순가용재고', value: req.net_available, unit: req.unit, color: req.net_available < 0 ? 'text-red-700' : 'text-blue-700' },
            { label: '최소재고', value: req.min_stock, unit: req.unit, color: 'text-gray-600' },
            { label: '부족수량', value: req.shortage, unit: req.unit, color: req.shortage > 0 ? 'text-red-700 font-bold' : 'text-green-700' },
          ].map(({ label, value, unit, color }) => (
            <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className={`text-2xl font-bold ${color}`}>{Number(value).toLocaleString()}</p>
              <p className="text-xs text-gray-400 mt-0.5">{unit}</p>
            </div>
          ))}
          {req.reorder_needed && (
            <div className="sm:col-span-2 lg:col-span-3 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
              <span className="text-amber-600 text-lg">&#9888;</span>
              <p className="text-sm text-amber-700 font-medium">
                재발주가 필요합니다. 부족수량: <strong>{Number(req.shortage).toLocaleString()} {req.unit}</strong>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function MmPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: ordersData } = useQuery({
    queryKey: ['mm-orders'],
    queryFn: () => api.get('/mm/orders/').then(r => r.data),
  })
  const { data: receiptsData } = useQuery({
    queryKey: ['mm-receipts'],
    queryFn: () => api.get('/mm/receipts/').then(r => r.data),
  })

  const orders   = getList(ordersData)
  const receipts = getList(receiptsData)

  const now         = new Date()
  const thisMonth   = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const monthOrders = orders.filter(o => (o.order_date ?? '').startsWith(thisMonth))
  const completed   = receipts.filter(r => r.status === 'received' && (r.receipt_date ?? '').startsWith(thisMonth))
  const pending     = orders.filter(o => o.status === 'pending' || o.status === 'confirmed')

  const TAB_COMPONENTS = [SupplierTab, MaterialTab, OrderTab, ReceiptTab, SupplierComparisonTab, RequirementsPlanTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🛒</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>MM 자재관리</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Materials Management — 공급처·자재·발주·입고를 통합 관리합니다.</div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="이번달 발주" value={ordersData ? monthOrders.length : '-'} unit="건" />
        <KpiCard label="입고 완료"   value={receiptsData ? completed.length   : '-'} unit="건" />
        <KpiCard label="미결 발주"   value={ordersData ? pending.length       : '-'} unit="건" />
      </div>

      {/* 탭 패널 */}
      <div style={{
        background: 'white', border: '1px solid #e9e9e7',
        borderRadius: 10, overflow: 'hidden',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      }}>
        {/* 탭 버튼 */}
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
        {/* 탭 콘텐츠 — 2컬럼 레이아웃 */}
        <ActiveContent />
      </div>
    </div>
  )
}
