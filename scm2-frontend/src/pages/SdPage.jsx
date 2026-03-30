import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['고객 관리', '판매주문', '출하 처리', '송장 관리']

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
  confirmed: { label: '확정',    bg: '#e8f5e9', color: '#2e7d32' },
  shipped:   { label: '출하완료', bg: '#e3f2fd', color: '#1565c0' },
  delivered: { label: '배송완료', bg: '#e0f2f1', color: '#00695c' },
  cancelled: { label: '취소',    bg: '#fdecea', color: '#d44c47' },
  partial:   { label: '부분출하', bg: '#f3e5f5', color: '#6a1b9a' },
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
function Field({ label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{ fontSize: 12, color: '#6b6b6b', display: 'block', marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  )
}

// ─── 우측 테이블 패널 ─────────────────────────────────────────
function TablePanel({ isLoading, isError, rows, columns, renderActions, hasActions }) {
  return (
    <div style={{ flex: 1, minWidth: 0, overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} style={{
                background: '#f5f5f3', padding: '10px 12px',
                textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap',
              }}>
                {col.label}
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
// 고객 탭
// ─────────────────────────────────────────────────────────────
const CUSTOMER_INIT = {
  customer_code: '', customer_name: '', contact: '',
  email: '', credit_limit: '', payment_terms: '',
}

function CustomerTab() {
  const qc = useQueryClient()
  const [form, setForm]     = useState(CUSTOMER_INIT)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sd-customers', page],
    queryFn: () => api.get(`/sd/customers/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['sd-customers'] })

  const createMut = useMutation({
    mutationFn: body => api.post('/sd/customers/', body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(CUSTOMER_INIT); setEditId(null); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, body }) => api.put(`/sd/customers/${id}/`, body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(CUSTOMER_INIT); setEditId(null); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/sd/customers/${id}/`),
    onSuccess: () => invalidate(),
    onError: (err) => handleApiError(err),
  })

  function handleEdit(row) {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      customer_code:  row.customer_code ?? row.code ?? '',
      customer_name:  row.customer_name ?? row.name ?? '',
      contact:        row.contact ?? '',
      email:          row.email ?? '',
      credit_limit:   row.credit_limit ?? '',
      payment_terms:  row.payment_terms ?? '',
    })
    setEditId(row.id)
  }
  function handleCancel() {
    setForm(CUSTOMER_INIT)
    setEditId(null)
  }
  function handleSubmit() {
    if (!form.customer_code.trim()) { setGlobalError('고객코드는 필수입니다.'); return }
    if (!form.customer_name.trim()) { setGlobalError('고객명은 필수입니다.'); return }
    const body = {
      ...form,
      credit_limit: form.credit_limit !== '' ? Number(form.credit_limit) : null,
    }
    if (editId) {
      updateMut.mutate({ id: editId, body })
    } else {
      createMut.mutate(body)
    }
  }
  function handleDelete(row) {
    requestConfirm({ message: `"${row.customer_name ?? row.name}" 고객을 삭제하시겠습니까?`, onConfirm: () => deleteMut.mutate(row.id) })
  }

  const isPending = createMut.isPending || updateMut.isPending

  const columns = [
    { key: 'customer_code', label: '고객코드',  render: (v, row) => v ?? row.code ?? '-' },
    { key: 'customer_name', label: '고객명',    render: (v, row) => v ?? row.name ?? '-' },
    { key: 'contact',       label: '연락처' },
    { key: 'credit_limit',  label: '여신한도', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'payment_terms', label: '결제조건' },
    { key: 'is_active',     label: '상태', render: v => (v ? '활성' : '비활성') },
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
          <Field label="고객코드 *">
            <input
              style={inputStyle}
              value={form.customer_code}
              onChange={e => setForm(f => ({ ...f, customer_code: e.target.value }))}
              placeholder="예: CUST-001"
            />
          </Field>
          <Field label="고객명 *">
            <input
              style={inputStyle}
              value={form.customer_name}
              onChange={e => setForm(f => ({ ...f, customer_name: e.target.value }))}
              placeholder="고객 회사명"
            />
          </Field>
          <Field label="연락처">
            <input
              style={inputStyle}
              value={form.contact}
              onChange={e => setForm(f => ({ ...f, contact: e.target.value }))}
              placeholder="연락처를 입력하세요"
            />
          </Field>
          <Field label="이메일">
            <input
              style={inputStyle}
              type="email"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="이메일을 입력하세요"
            />
          </Field>
          <Field label="여신한도 (원)">
            <input
              style={inputStyle}
              type="number"
              value={form.credit_limit}
              onChange={e => setForm(f => ({ ...f, credit_limit: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="결제조건">
            <select
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
// 품목 라인 헬퍼
// ─────────────────────────────────────────────────────────────
const EMPTY_LINE = { item_name: '', quantity: '', unit_price: '', discount_rate: '', expected_date: '' }

function calcLineSubtotal(line) {
  const qty   = Number(line.quantity)   || 0
  const price = Number(line.unit_price) || 0
  const disc  = Number(line.discount_rate) || 0
  return qty * price * (1 - disc / 100)
}

// ─────────────────────────────────────────────────────────────
// 판매주문 탭 (등록만, draft 상태 시 [확정][삭제]) + 다품목 라인
// ─────────────────────────────────────────────────────────────
const SALES_ORDER_INIT = {
  customer: '', item_name: '', quantity: '',
  unit_price: '', discount_rate: '', expected_date: '',
}

function SalesOrderTab() {
  const qc = useQueryClient()
  const [form, setForm]           = useState(SALES_ORDER_INIT)
  const [showLines, setShowLines] = useState(false)
  const [lines, setLines]         = useState([{ ...EMPTY_LINE }])
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sd-orders', page],
    queryFn: () => api.get(`/sd/orders/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const { data: customersData } = useQuery({
    queryKey: ['sd-customers'],
    queryFn: () => api.get('/sd/customers/').then(r => r.data),
  })

  const rows      = getList(data)
  const customers = getList(customersData)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['sd-orders'] })

  const createMut = useMutation({
    mutationFn: body => api.post('/sd/orders/', body).then(r => r.data),
    onSuccess: async createdOrder => {
      // 다품목 라인 저장 (선택적)
      if (showLines) {
        const validLines = lines.filter(l => l.item_name.trim())
        for (const line of validLines) {
          try {
            await api.post(`/sd/orders/${createdOrder.id}/lines/`, {
              item_name:     line.item_name,
              quantity:      line.quantity      !== '' ? Number(line.quantity)      : null,
              unit_price:    line.unit_price    !== '' ? Number(line.unit_price)    : null,
              discount_rate: line.discount_rate !== '' ? Number(line.discount_rate) : null,
              expected_date: line.expected_date || null,
            })
          } catch {
            // 라인 저장 실패 시 개별 경고 없이 계속 진행
          }
        }
      }
      invalidate()
      setForm(SALES_ORDER_INIT)
      setLines([{ ...EMPTY_LINE }])
      setShowLines(false)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })
  const confirmMut = useMutation({
    mutationFn: id => api.post(`/sd/orders/${id}/confirm/`).then(r => r.data),
    onSuccess: () => { invalidate(); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/sd/orders/${id}/`),
    onSuccess: () => invalidate(),
    onError: (err) => handleApiError(err),
  })

  function handleSubmit() {
    if (!form.customer)         { setGlobalError('고객을 선택하세요.'); return }
    if (!form.item_name.trim()) { setGlobalError('품목명은 필수입니다.'); return }
    if (!form.quantity)         { setGlobalError('수량은 필수입니다.'); return }
    createMut.mutate({
      ...form,
      quantity:      Number(form.quantity),
      unit_price:    form.unit_price    !== '' ? Number(form.unit_price)    : null,
      discount_rate: form.discount_rate !== '' ? Number(form.discount_rate) : null,
    })
  }
  function handleConfirm(row) {
    requestConfirm({ message: `주문 "${row.order_number}"를 확정하시겠습니까?`, confirmLabel: '확정', danger: false, onConfirm: () => confirmMut.mutate(row.id) })
  }
  function handleDelete(row) {
    requestConfirm({ message: `수주 "${row.order_number}"를 삭제하시겠습니까?`, onConfirm: () => deleteMut.mutate(row.id) })
  }

  // 라인 핸들러
  function handleLineChange(idx, field, value) {
    setLines(prev => prev.map((l, i) => i === idx ? { ...l, [field]: value } : l))
  }
  function handleAddLine() {
    setLines(prev => [...prev, { ...EMPTY_LINE }])
  }
  function handleRemoveLine(idx) {
    setLines(prev => prev.length === 1 ? [{ ...EMPTY_LINE }] : prev.filter((_, i) => i !== idx))
  }

  const linesTotal = showLines
    ? lines.reduce((sum, l) => sum + calcLineSubtotal(l), 0)
    : 0

  const columns = [
    { key: 'order_number',  label: '주문번호' },
    { key: 'customer_name', label: '고객',  render: (v, row) => v ?? row.customer?.name ?? '-' },
    { key: 'item_name',     label: '품목' },
    { key: 'quantity',      label: '수량' },
    { key: 'unit_price',    label: '단가',  render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'status',        label: '상태',  render: v => <StatusBadge status={v} /> },
  ]

  const lineInputSm = {
    ...inputStyle,
    padding: '5px 7px',
    fontSize: 12,
  }

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
          <Field label="고객 *">
            <select
              style={selectStyle}
              value={form.customer}
              onChange={e => setForm(f => ({ ...f, customer: e.target.value }))}
            >
              <option value="">고객 선택</option>
              {customers.map(c => (
                <option key={c.id} value={c.id}>
                  {c.customer_name ?? c.name}
                  {(c.customer_code ?? c.code) ? ` (${c.customer_code ?? c.code})` : ''}
                </option>
              ))}
            </select>
          </Field>
          <Field label="품목명 *">
            <input
              style={inputStyle}
              value={form.item_name}
              onChange={e => setForm(f => ({ ...f, item_name: e.target.value }))}
              placeholder="품목명을 입력하세요"
            />
          </Field>
          <Field label="수량 *">
            <input
              style={inputStyle}
              type="number"
              value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="단가 (원)">
            <input
              style={inputStyle}
              type="number"
              value={form.unit_price}
              onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="할인율 (0~100%)">
            <input
              style={inputStyle}
              type="number"
              min="0"
              max="100"
              value={form.discount_rate}
              onChange={e => setForm(f => ({ ...f, discount_rate: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="납기일">
            <input
              style={inputStyle}
              type="date"
              value={form.expected_date}
              onChange={e => setForm(f => ({ ...f, expected_date: e.target.value }))}
            />
          </Field>

          {/* ─── 품목 라인 섹션 ─────────────────────────── */}
          <div style={{
            borderTop: '1px solid #e9e9e7',
            paddingTop: 12,
            marginTop: 4,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>품목 라인 (선택)</span>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6b6b6b', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={showLines}
                  onChange={e => setShowLines(e.target.checked)}
                />
                다품목 추가
              </label>
            </div>

            {showLines && (
              <div>
                {lines.map((line, idx) => {
                  const subtotal = calcLineSubtotal(line)
                  return (
                    <div key={idx} style={{
                      border: '1px solid #e9e9e7', borderRadius: 6,
                      padding: 10, marginBottom: 8,
                      background: '#fafaf8',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#6b6b6b' }}>라인 {idx + 1}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveLine(idx)}
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#cc3333', fontSize: 12, padding: '0 2px',
                          }}
                        >
                          X
                        </button>
                      </div>
                      <div style={{ marginBottom: 6 }}>
                        <label style={{ display: 'block', fontSize: 11, color: '#9b9b9b', marginBottom: 2 }}>품목명</label>
                        <input
                          style={lineInputSm}
                          value={line.item_name}
                          onChange={e => handleLineChange(idx, 'item_name', e.target.value)}
                          placeholder="품목명"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-1.5 mb-1.5">
                        <div>
                          <label style={{ display: 'block', fontSize: 11, color: '#9b9b9b', marginBottom: 2 }}>수량</label>
                          <input
                            style={lineInputSm}
                            type="number"
                            min={0}
                            value={line.quantity}
                            onChange={e => handleLineChange(idx, 'quantity', e.target.value)}
                            placeholder="0"
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: 11, color: '#9b9b9b', marginBottom: 2 }}>단가 (원)</label>
                          <input
                            style={lineInputSm}
                            type="number"
                            min={0}
                            value={line.unit_price}
                            onChange={e => handleLineChange(idx, 'unit_price', e.target.value)}
                            placeholder="0"
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: 11, color: '#9b9b9b', marginBottom: 2 }}>할인율 (%)</label>
                          <input
                            style={lineInputSm}
                            type="number"
                            min={0}
                            max={100}
                            value={line.discount_rate}
                            onChange={e => handleLineChange(idx, 'discount_rate', e.target.value)}
                            placeholder="0"
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: 11, color: '#9b9b9b', marginBottom: 2 }}>납기일</label>
                          <input
                            style={lineInputSm}
                            type="date"
                            value={line.expected_date}
                            onChange={e => handleLineChange(idx, 'expected_date', e.target.value)}
                          />
                        </div>
                      </div>
                      {subtotal > 0 && (
                        <div style={{
                          textAlign: 'right', fontSize: 11,
                          color: '#1a1a2e', fontWeight: 600,
                        }}>
                          소계: {subtotal.toLocaleString()}원
                        </div>
                      )}
                    </div>
                  )
                })}

                <button
                  type="button"
                  onClick={handleAddLine}
                  style={{
                    width: '100%', padding: '7px', fontSize: 12,
                    background: '#f0f4ff', color: '#3366cc',
                    border: '1px dashed #c5d5f5', borderRadius: 6,
                    cursor: 'pointer', fontWeight: 500,
                  }}
                >
                  + 라인 추가
                </button>

                {linesTotal > 0 && (
                  <div style={{
                    marginTop: 10, padding: '8px 10px',
                    background: '#e8f5e9', borderRadius: 6,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span style={{ fontSize: 12, color: '#2e7d32', fontWeight: 600 }}>라인 합계</span>
                    <span style={{ fontSize: 13, color: '#2e7d32', fontWeight: 700 }}>
                      {linesTotal.toLocaleString()}원
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
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
              row.status === 'draft'
                ? (
                  <>
                    <ActionBtn variant="success" onClick={() => handleConfirm(row)}>확정</ActionBtn>
                    <DeleteBtn onClick={() => handleDelete(row)} />
                  </>
                )
                : null
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
// 출하 탭 (등록만, 미완료 시 [출하확정])
// ─────────────────────────────────────────────────────────────
const DELIVERY_INIT = {
  order: '', delivery_qty: '', carrier: '', tracking_number: '', delivery_date: '',
}

function DeliveryTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(DELIVERY_INIT)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sd-deliveries', page],
    queryFn: () => api.get(`/sd/deliveries/?page=${page}`).then(r => r.data),
    placeholderData: (prev) => prev,
  })
  const { data: confirmedOrdersData } = useQuery({
    queryKey: ['sd-orders-confirmed'],
    queryFn: () => api.get('/sd/orders/?status=confirmed').then(r => r.data),
  })

  const rows            = getList(data)
  const confirmedOrders = getList(confirmedOrdersData)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['sd-deliveries'] })
    qc.invalidateQueries({ queryKey: ['sd-orders'] })
    qc.invalidateQueries({ queryKey: ['sd-orders-confirmed'] })
  }

  const createMut = useMutation({
    mutationFn: body => api.post('/sd/deliveries/', body).then(r => r.data),
    onSuccess: () => { invalidate(); setForm(DELIVERY_INIT); setSuccessMsg('저장되었습니다.') },
    onError: (err) => handleApiError(err),
  })
  const deliverMut = useMutation({
    mutationFn: id => api.post(`/sd/deliveries/${id}/confirm/`).then(r => r.data),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['sd-invoices'] })
      setSuccessMsg('배송이 확정되고 송장이 생성되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  function handleSubmit() {
    if (!form.order)        { setGlobalError('수주를 선택하세요.'); return }
    if (!form.delivery_qty) { setGlobalError('출하수량은 필수입니다.'); return }
    createMut.mutate({
      ...form,
      delivery_qty: Number(form.delivery_qty),
    })
  }
  function handleDeliver(row) {
    requestConfirm({ message: `출하 "${row.delivery_number}"를 출하 확정 처리하시겠습니까?`, confirmLabel: '출하확정', danger: false, onConfirm: () => deliverMut.mutate(row.id) })
  }

  const columns = [
    { key: 'delivery_number', label: '출하번호' },
    { key: 'order_number',    label: '주문번호', render: (v, row) => v ?? row.order?.order_number ?? '-' },
    { key: 'delivery_qty',    label: '수량',    render: (v, row) => v ?? row.shipped_qty ?? '-' },
    { key: 'carrier',         label: '운송사' },
    { key: 'tracking_number', label: '운송장' },
    { key: 'delivery_date',   label: '출하일',  render: (v, row) => v ?? row.ship_date ?? '-' },
    { key: 'status',          label: '상태',   render: v => <StatusBadge status={v} /> },
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
          <Field label="수주 선택 * (confirmed 주문)">
            <select
              style={selectStyle}
              value={form.order}
              onChange={e => setForm(f => ({ ...f, order: e.target.value }))}
            >
              <option value="">수주 선택</option>
              {confirmedOrders.map(o => (
                <option key={o.id} value={o.id}>
                  {o.order_number} — {o.item_name ?? ''}{o.customer_name ? ` (${o.customer_name})` : ''}
                </option>
              ))}
            </select>
          </Field>
          <Field label="출하수량 *">
            <input
              style={inputStyle}
              type="number"
              value={form.delivery_qty}
              onChange={e => setForm(f => ({ ...f, delivery_qty: e.target.value }))}
              placeholder="0"
            />
          </Field>
          <Field label="운송사">
            <input
              style={inputStyle}
              value={form.carrier}
              onChange={e => setForm(f => ({ ...f, carrier: e.target.value }))}
              placeholder="운송사명"
            />
          </Field>
          <Field label="운송장 번호">
            <input
              style={inputStyle}
              value={form.tracking_number}
              onChange={e => setForm(f => ({ ...f, tracking_number: e.target.value }))}
              placeholder="운송장 번호"
            />
          </Field>
          <Field label="출하일">
            <input
              style={inputStyle}
              type="date"
              value={form.delivery_date}
              onChange={e => setForm(f => ({ ...f, delivery_date: e.target.value }))}
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
              (row.status !== 'shipped' && row.status !== 'delivered')
                ? <ActionBtn variant="primary" onClick={() => handleDeliver(row)}>출하확정</ActionBtn>
                : null
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
// 송장 탭
// ─────────────────────────────────────────────────────────────
function InvoiceTab() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const { globalError, handleApiError, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()

  const { data, isLoading } = useQuery({
    queryKey: ['sd-invoices', page],
    queryFn: () => api.get(`/sd/invoices/?page=${page}`).then(r => r.data),
    placeholderData: prev => prev,
  })
  const invoices = data?.results ?? (Array.isArray(data) ? data : [])

  const issueMutation = useMutation({
    mutationFn: id => api.post(`/sd/invoices/${id}/issue/`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sd-invoices'] }); setSuccessMsg('송장이 발행되었습니다.') },
    onError: err => handleApiError(err),
  })

  const paidMutation = useMutation({
    mutationFn: id => api.post(`/sd/invoices/${id}/mark-paid/`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sd-invoices'] }); setSuccessMsg('수금 처리되었습니다.') },
    onError: err => handleApiError(err),
  })

  const STATUS_COLOR = {
    draft:     'bg-gray-100 text-gray-600',
    issued:    'bg-blue-100 text-blue-700',
    paid:      'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-600',
  }
  const STATUS_LABEL = { draft: '임시', issued: '발행', paid: '수금완료', cancelled: '취소' }

  return (
    <div className="p-3 md:p-5">
      <GlobalError message={globalError} onClose={() => setGlobalError('')} />
      <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              {['송장번호', '주문번호', '고객', '송장일', '공급가액', '부가세', '합계', '상태', '액션'].map(h => (
                <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={9} className="text-center py-8 text-gray-400 text-sm">로딩 중...</td></tr>
            ) : invoices.length === 0 ? (
              <tr><td colSpan={9} className="text-center py-8 text-gray-400 text-sm">데이터가 없습니다</td></tr>
            ) : invoices.map(inv => (
              <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2.5 font-mono text-xs text-gray-700">{inv.invoice_number}</td>
                <td className="px-3 py-2.5 text-xs text-gray-600">{inv.order_number ?? '-'}</td>
                <td className="px-3 py-2.5 text-sm">{inv.customer_name ?? '-'}</td>
                <td className="px-3 py-2.5 text-xs text-gray-500">{inv.invoice_date}</td>
                <td className="px-3 py-2.5 text-sm text-right">{Number(inv.supply_amount).toLocaleString()}</td>
                <td className="px-3 py-2.5 text-sm text-right">{Number(inv.vat_amount).toLocaleString()}</td>
                <td className="px-3 py-2.5 text-sm text-right font-semibold">{Number(inv.total_amount).toLocaleString()}</td>
                <td className="px-3 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[inv.status] ?? 'bg-gray-100 text-gray-500'}`}>
                    {STATUS_LABEL[inv.status] ?? inv.status}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex gap-1.5">
                    {inv.status === 'draft' && (
                      <button
                        onClick={() => requestConfirm({
                          message: '송장을 발행하시겠습니까?',
                          confirmLabel: '발행',
                          danger: false,
                          onConfirm: () => issueMutation.mutate(inv.id),
                        })}
                        className="text-xs px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100"
                      >
                        발행
                      </button>
                    )}
                    {inv.status === 'issued' && (
                      <button
                        onClick={() => requestConfirm({
                          message: '수금 처리하시겠습니까?',
                          confirmLabel: '수금',
                          danger: false,
                          onConfirm: () => paidMutation.mutate(inv.id),
                        })}
                        className="text-xs px-2 py-1 bg-green-50 text-green-700 border border-green-200 rounded hover:bg-green-100"
                      >
                        수금
                      </button>
                    )}
                    <a
                      href={`/api/reports/invoice/${inv.id}/pdf/`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs px-2 py-1 bg-gray-50 text-gray-700 border border-gray-200 rounded hover:bg-gray-100 inline-flex items-center gap-1"
                    >
                      PDF
                    </a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function SdPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: ordersData } = useQuery({
    queryKey: ['sd-orders'],
    queryFn: () => api.get('/sd/orders/').then(r => r.data),
  })
  const { data: deliveriesData } = useQuery({
    queryKey: ['sd-deliveries'],
    queryFn: () => api.get('/sd/deliveries/').then(r => r.data),
  })

  const orders     = getList(ordersData)
  const deliveries = getList(deliveriesData)

  const now         = new Date()
  const thisMonth   = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const monthOrders = orders.filter(o => (o.order_date ?? '').startsWith(thisMonth))
  const shipped     = deliveries.filter(d =>
    (d.status === 'shipped' || d.status === 'delivered') &&
    (d.ship_date ?? d.delivery_date ?? '').startsWith(thisMonth)
  )
  const monthRevenue = monthOrders.reduce((sum, o) => sum + (Number(o.total_amount) || 0), 0)

  const TAB_COMPONENTS = [CustomerTab, SalesOrderTab, DeliveryTab, InvoiceTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🛍️</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>SD 판매출하</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Sales & Distribution — 고객·수주·출하를 통합 관리합니다.</div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="이번달 수주" value={ordersData ? monthOrders.length             : '-'} unit="건" />
        <KpiCard label="출하 완료"   value={deliveriesData ? shipped.length              : '-'} unit="건" />
        <KpiCard label="매출 금액"   value={ordersData ? monthRevenue.toLocaleString()   : '-'} unit="원" />
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
