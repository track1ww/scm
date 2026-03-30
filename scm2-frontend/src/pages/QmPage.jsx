import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['검사 계획', '검사 결과', '불량 현황', 'SPC 관리도', '불량 통계']

// ─── 공통 헬퍼 ────────────────────────────────────────────────
function getList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
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
  btnActionRed: {
    background: '#fff0f0', color: '#cc3333',
    border: '1px solid #f5c5c5', borderRadius: 4,
    padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
  formPanel: {
    width: 320, flexShrink: 0,
    background: 'white', border: '1px solid #e9e9e7',
    borderRadius: 10, padding: 20, alignSelf: 'flex-start',
  },
  formTitle: { fontSize: 14, fontWeight: 600, margin: '0 0 16px' },
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
  active:      { label: '활성',      bg: '#e8f5e9', color: '#2e7d32' },
  inactive:    { label: '비활성',    bg: '#f5f5f3', color: '#6b6b6b' },
  passed:      { label: '합격',      bg: '#e8f5e9', color: '#2e7d32' },
  '합격':      { label: '합격',      bg: '#e8f5e9', color: '#2e7d32' },
  failed:      { label: '불합격',    bg: '#fdecea', color: '#d44c47' },
  '불합격':    { label: '불합격',    bg: '#fdecea', color: '#d44c47' },
  conditional: { label: '조건부합격', bg: '#fff8e1', color: '#b45309' },
  '조건부합격':{ label: '조건부합격', bg: '#fff8e1', color: '#b45309' },
  pending:     { label: '대기',      bg: '#fff8e1', color: '#b45309' },
  open:        { label: '진행중',    bg: '#e3f2fd', color: '#1565c0' },
  closed:      { label: '완료',      bg: '#e8f5e9', color: '#2e7d32' },
  critical:    { label: '치명',      bg: '#fdecea', color: '#d44c47' },
  '치명':      { label: '치명',      bg: '#fdecea', color: '#d44c47' },
  major:       { label: '주요',      bg: '#fff8e1', color: '#b45309' },
  '심각':      { label: '심각',      bg: '#fff8e1', color: '#b45309' },
  minor:       { label: '경미',      bg: '#f5f5f3', color: '#6b6b6b' },
  '경미':      { label: '경미',      bg: '#f5f5f3', color: '#6b6b6b' },
  '보통':      { label: '보통',      bg: '#e3f2fd', color: '#1565c0' },
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

// ─── 검사계획 탭 (2컬럼) ──────────────────────────────────────
const initialPlanForm = {
  plan_code: '', plan_name: '', inspection_type: '수입검사',
  target_item: '', criteria: '', is_active: true,
}

function InspectionPlanTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialPlanForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['qm-plans', page],
    queryFn: () => api.get(`/qm/inspection-plans/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const mutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/qm/inspection-plans/${editId}/`, payload).then(r => r.data)
        : api.post('/qm/inspection-plans/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialPlanForm)
      setEditId(null)
      qc.invalidateQueries({ queryKey: ['qm-plans'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/qm/inspection-plans/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['qm-plans'] }),
    onError: (err) => handleApiError(err),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      plan_code: row.plan_code ?? '',
      plan_name: row.plan_name ?? '',
      inspection_type: row.inspection_type ?? '수입검사',
      target_item: row.target_item ?? '',
      criteria: row.criteria ?? '',
      is_active: row.is_active ?? true,
    })
    setEditId(row.id)
  }

  const handleCancel = () => {
    setForm(initialPlanForm)
    setEditId(null)
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.plan_code.trim() || !form.plan_name.trim()) {
      setGlobalError('계획코드와 계획명은 필수입니다.')
      return
    }
    mutation.mutate(form)
  }

  const handleDelete = row => {
    requestConfirm({ message: `검사계획 "${row.plan_code}"를 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })
  }

  const columns = [
    { key: 'plan_code',       label: '계획코드' },
    { key: 'plan_name',       label: '계획명' },
    { key: 'inspection_type', label: '검사유형' },
    { key: 'target_item',     label: '대상품목' },
    { key: 'is_active',       label: '활성', render: v => (v ? '활성' : '비활성') },
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
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>{editId ? '수정' : '신규 등록'}</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>계획코드 *</label>
            <input style={S.input} value={form.plan_code} onChange={e => set('plan_code', e.target.value)} placeholder="QP-001" />
          </div>
          <div style={S.field}>
            <label style={S.label}>계획명 *</label>
            <input style={S.input} value={form.plan_name} onChange={e => set('plan_name', e.target.value)} placeholder="계획명" />
          </div>
          <div style={S.field}>
            <label style={S.label}>검사유형</label>
            <select style={S.input} value={form.inspection_type} onChange={e => set('inspection_type', e.target.value)}>
              <option value="수입검사">수입검사</option>
              <option value="공정검사">공정검사</option>
              <option value="출하검사">출하검사</option>
              <option value="정기검사">정기검사</option>
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>대상품목</label>
            <input style={S.input} value={form.target_item} onChange={e => set('target_item', e.target.value)} placeholder="대상품목" />
          </div>
          <div style={S.field}>
            <label style={S.label}>검사기준</label>
            <textarea
              style={{ ...S.input, resize: 'vertical', minHeight: 60 }}
              value={form.criteria}
              onChange={e => set('criteria', e.target.value)}
              placeholder="검사기준 설명"
            />
          </div>
          <div style={{ ...S.field, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox" id="plan_is_active"
              checked={form.is_active}
              onChange={e => set('is_active', e.target.checked)}
              style={{ width: 'auto' }}
            />
            <label htmlFor="plan_is_active" style={{ ...S.label, margin: 0 }}>활성</label>
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
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} isError={isError} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 검사결과 탭 (2컬럼, 등록만) ─────────────────────────────
const initialResultForm = {
  plan: '', item_name: '', lot_number: '',
  inspected_qty: '', passed_qty: '', result: '합격', remarks: '',
}

function InspectionResultTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialResultForm)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const [page, setPage] = useState(1)

  const { data: plansData } = useQuery({
    queryKey: ['qm-plans'],
    queryFn: () => api.get('/qm/inspection-plans/').then(r => r.data).catch(() => []),
  })
  const plans = getList(plansData)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['qm-results', page],
    queryFn: () => api.get(`/qm/inspection-results/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const failedQty = form.inspected_qty && form.passed_qty
    ? Math.max(0, Number(form.inspected_qty) - Number(form.passed_qty))
    : ''

  const mutation = useMutation({
    mutationFn: payload => api.post('/qm/inspection-results/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialResultForm)
      qc.invalidateQueries({ queryKey: ['qm-results'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const approveMutation = useMutation({
    mutationFn: id => api.post(`/qm/inspection-results/${id}/approve/`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['qm-results'] }); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const rejectMutation = useMutation({
    mutationFn: id => api.post(`/qm/inspection-results/${id}/reject/`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['qm-results'] }); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.item_name.trim() || !form.inspected_qty) {
      setGlobalError('품목명과 검사수량은 필수입니다.')
      return
    }
    mutation.mutate({
      ...form,
      plan:          form.plan ? Number(form.plan) : undefined,
      inspected_qty: Number(form.inspected_qty),
      passed_qty:    form.passed_qty ? Number(form.passed_qty) : undefined,
      failed_qty:    failedQty !== '' ? failedQty : undefined,
    })
  }

  const passRate = row => {
    const total = Number(row.inspected_qty)
    const passed = Number(row.passed_qty)
    if (!total) return '-'
    return Math.round((passed / total) * 100) + '%'
  }

  const columns = [
    { key: 'result_number', label: '결과번호' },
    { key: 'item_name',     label: '품목' },
    { key: 'lot_number',    label: '로트' },
    { key: 'inspected_qty', label: '검사수량' },
    { key: 'passed_qty',    label: '합격' },
    { key: 'failed_qty',    label: '불량' },
    { key: 'result',        label: '결과', render: v => <StatusBadge status={v} /> },
    { key: '_rate',         label: '합격률', render: (_, row) => passRate(row) },
    { key: 'inspected_at',  label: '검사일', render: v => v?.slice(0, 10) ?? '-' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <button style={S.btnAction} onClick={() => approveMutation.mutate(row.id)}>합격처리</button>
          <button style={S.btnActionRed} onClick={() => rejectMutation.mutate(row.id)}>불합격처리</button>
          <a
            href={`/api/reports/inspection/${row.id}/pdf/`}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 11, padding: '4px 10px', background: '#f8fafc', color: '#374151', border: '1px solid #e2e8f0', borderRadius: 4, textDecoration: 'none' }}
          >
            PDF
          </a>
        </div>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>신규 등록</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>검사계획</label>
            <select style={S.input} value={form.plan} onChange={e => set('plan', e.target.value)}>
              <option value="">-- 선택 --</option>
              {plans.map(p => (
                <option key={p.id} value={p.id}>{p.plan_code} {p.plan_name}</option>
              ))}
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>품목명 *</label>
            <input style={S.input} value={form.item_name} onChange={e => set('item_name', e.target.value)} placeholder="품목명" />
          </div>
          <div style={S.field}>
            <label style={S.label}>LOT 번호</label>
            <input style={S.input} value={form.lot_number} onChange={e => set('lot_number', e.target.value)} placeholder="LOT-001" />
          </div>
          <div style={S.field}>
            <label style={S.label}>검사수량 *</label>
            <input style={S.input} type="number" min="0" value={form.inspected_qty} onChange={e => set('inspected_qty', e.target.value)} placeholder="0" />
          </div>
          <div style={S.field}>
            <label style={S.label}>합격수량</label>
            <input
              style={S.input}
              type="number" min="0"
              value={form.passed_qty}
              onChange={e => set('passed_qty', e.target.value)}
              placeholder="0"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>불량수량</label>
            <input
              style={{ ...S.input, background: '#f5f5f3', color: '#9b9b9b' }}
              value={failedQty}
              readOnly
              placeholder="자동계산"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>판정</label>
            <select style={S.input} value={form.result} onChange={e => set('result', e.target.value)}>
              <option value="합격">합격</option>
              <option value="불합격">불합격</option>
              <option value="조건부합격">조건부합격</option>
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>비고</label>
            <input style={S.input} value={form.remarks} onChange={e => set('remarks', e.target.value)} placeholder="비고" />
          </div>
          {mutation.isError && (
            <div style={{ color: '#d44c47', fontSize: 12, marginBottom: 8 }}>저장 중 오류가 발생했습니다.</div>
          )}
          <button type="submit" style={S.btnSave} disabled={mutation.isPending}>
            {mutation.isPending ? '저장 중...' : '등록'}
          </button>
        </form>
      </div>

      {/* 우측 목록 */}
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} isError={isError} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    </>
  )
}

// ─── 불량현황 탭 (2컬럼, 등록만) ─────────────────────────────
const initialDefectForm = {
  item_name: '', defect_type: '', severity: '보통', quantity: '', description: '',
}

function DefectTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialDefectForm)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['qm-defects', page],
    queryFn: () => api.get(`/qm/defect-reports/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const mutation = useMutation({
    mutationFn: payload => api.post('/qm/defect-reports/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialDefectForm)
      qc.invalidateQueries({ queryKey: ['qm-defects'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/qm/defect-reports/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['qm-defects'] }),
    onError: (err) => handleApiError(err),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.item_name.trim() || !form.defect_type.trim() || !form.quantity) {
      setGlobalError('품목명, 불량유형, 수량은 필수입니다.')
      return
    }
    mutation.mutate({ ...form, quantity: Number(form.quantity) })
  }

  const handleDelete = row => {
    requestConfirm({ message: `불량 "${row.defect_number ?? row.item_name}"를 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })
  }

  const columns = [
    { key: 'defect_number', label: '불량번호' },
    { key: 'item_name',     label: '품목' },
    { key: 'defect_type',   label: '불량유형' },
    { key: 'severity',      label: '심각도', render: v => <StatusBadge status={v} /> },
    { key: 'quantity',      label: '수량' },
    { key: 'detected_at',   label: '등록일', render: v => v?.slice(0, 10) ?? '-' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <button style={S.btnDelete} onClick={() => handleDelete(row)}>삭제</button>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>신규 등록</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>품목명 *</label>
            <input style={S.input} value={form.item_name} onChange={e => set('item_name', e.target.value)} placeholder="품목명" />
          </div>
          <div style={S.field}>
            <label style={S.label}>불량유형 *</label>
            <input style={S.input} value={form.defect_type} onChange={e => set('defect_type', e.target.value)} placeholder="예: 치수불량, 외관불량" />
          </div>
          <div style={S.field}>
            <label style={S.label}>심각도</label>
            <select style={S.input} value={form.severity} onChange={e => set('severity', e.target.value)}>
              <option value="경미">경미</option>
              <option value="보통">보통</option>
              <option value="심각">심각</option>
              <option value="치명">치명</option>
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>수량 *</label>
            <input style={S.input} type="number" min="1" value={form.quantity} onChange={e => set('quantity', e.target.value)} placeholder="0" />
          </div>
          <div style={S.field}>
            <label style={S.label}>설명</label>
            <textarea
              style={{ ...S.input, resize: 'vertical', minHeight: 60 }}
              value={form.description}
              onChange={e => set('description', e.target.value)}
              placeholder="불량 상세 설명"
            />
          </div>
          {mutation.isError && (
            <div style={{ color: '#d44c47', fontSize: 12, marginBottom: 8 }}>저장 중 오류가 발생했습니다.</div>
          )}
          <button type="submit" style={S.btnSave} disabled={mutation.isPending}>
            {mutation.isPending ? '저장 중...' : '등록'}
          </button>
        </form>
      </div>

      {/* 우측 목록 */}
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} isError={isError} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── SPC 관리도 탭 ────────────────────────────────────────────
const initialSpcForm = {
  measurement_name: '',
  usl: '',
  lsl: '',
  target: '',
  raw_values: '',
}

// SVG control chart: plots each measured value as a dot, draws UCL/CL/LCL lines,
// and highlights out-of-control points in red.
function SpcChart({ values, ucl, cl, lcl, outOfControlIndices }) {
  const W = 600
  const H = 220
  const PAD = { top: 20, right: 20, bottom: 32, left: 52 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom

  const n = values.length
  if (n === 0) return null

  const allY = [
    ...values,
    ucl != null ? ucl : null,
    cl  != null ? cl  : null,
    lcl != null ? lcl : null,
  ].filter(v => v != null)

  const minY = Math.min(...allY)
  const maxY = Math.max(...allY)
  const rangeY = maxY - minY || 1
  const pad = rangeY * 0.15

  const yMin = minY - pad
  const yMax = maxY + pad
  const yRange = yMax - yMin

  const xScale = i => PAD.left + (n <= 1 ? chartW / 2 : (i / (n - 1)) * chartW)
  const yScale = v => PAD.top + chartH - ((v - yMin) / yRange) * chartH

  const hLine = (yVal, color, dash, labelText) => {
    if (yVal == null) return null
    const y = yScale(yVal)
    return (
      <g key={labelText}>
        <line
          x1={PAD.left} y1={y} x2={PAD.left + chartW} y2={y}
          stroke={color} strokeWidth={1.5}
          strokeDasharray={dash}
        />
        <text x={PAD.left - 4} y={y + 4} textAnchor="end" fontSize={9} fill={color}>{labelText}</text>
      </g>
    )
  }

  const outSet = new Set(outOfControlIndices ?? [])

  // polyline path through all points
  const polyPoints = values.map((v, i) => `${xScale(i)},${yScale(v)}`).join(' ')

  // x-axis tick labels (show up to 10 evenly spaced)
  const tickStep = Math.max(1, Math.floor(n / 10))
  const ticks = []
  for (let i = 0; i < n; i += tickStep) {
    ticks.push(
      <text key={i} x={xScale(i)} y={H - PAD.bottom + 14} textAnchor="middle" fontSize={9} fill="#9b9b9b">
        {i + 1}
      </text>
    )
  }

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block', overflow: 'visible' }}>
      {/* axis lines */}
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + chartH} stroke="#e9e9e7" strokeWidth={1} />
      <line x1={PAD.left} y1={PAD.top + chartH} x2={PAD.left + chartW} y2={PAD.top + chartH} stroke="#e9e9e7" strokeWidth={1} />

      {/* limit lines */}
      {hLine(ucl, '#d44c47', '5,3', 'UCL')}
      {hLine(cl,  '#2d7a2d', '',    'CL')}
      {hLine(lcl, '#1565c0', '5,3', 'LCL')}

      {/* data polyline */}
      <polyline points={polyPoints} fill="none" stroke="#9b9b9b" strokeWidth={1} />

      {/* data points */}
      {values.map((v, i) => {
        const isOut = outSet.has(i)
        return (
          <circle
            key={i}
            cx={xScale(i)} cy={yScale(v)} r={isOut ? 5 : 3.5}
            fill={isOut ? '#d44c47' : '#1a1a2e'}
            stroke="white" strokeWidth={1}
          >
            <title>{`[${i + 1}] ${v}`}</title>
          </circle>
        )
      })}

      {/* x-axis ticks */}
      {ticks}

      {/* chart label */}
      <text x={PAD.left + chartW / 2} y={H - 2} textAnchor="middle" fontSize={9} fill="#9b9b9b">
        샘플 번호
      </text>
    </svg>
  )
}

// A single stat row inside the results cards
function StatRow({ label, value, highlight }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '6px 0', borderBottom: '1px solid #f0f0ef',
    }}>
      <span style={{ fontSize: 12, color: '#6b6b6b' }}>{label}</span>
      <span style={{
        fontSize: 13, fontWeight: 600,
        color: highlight === 'bad' ? '#d44c47' : highlight === 'good' ? '#2e7d32' : '#1a1a1a',
      }}>
        {value ?? '-'}
      </span>
    </div>
  )
}

// Result card wrapper
function ResultCard({ title, accent, children }) {
  return (
    <div style={{
      background: 'white', border: `1px solid ${accent ?? '#e9e9e7'}`,
      borderRadius: 10, padding: '16px 20px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    }}>
      <div style={{
        fontSize: 12, fontWeight: 700, color: accent ?? '#6b6b6b',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12,
      }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function SpcTab() {
  const [form, setForm]     = useState(initialSpcForm)
  const [result, setResult] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const parseValues = raw => {
    return raw
      .split(/[\n,]+/)
      .map(s => s.trim())
      .filter(Boolean)
      .map(Number)
      .filter(n => !isNaN(n))
  }

  const mutation = useMutation({
    mutationFn: payload => api.post('/qm/results/spc_analysis/', payload).then(r => r.data),
    onSuccess: data => { setResult(data); setSuccessMsg('분석이 완료되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = e => {
    e.preventDefault()
    const values = parseValues(form.raw_values)
    if (values.length < 2) {
      setGlobalError('측정값을 2개 이상 입력하세요.')
      return
    }
    const toFloat = s => (s === '' || s == null) ? null : parseFloat(s)
    mutation.mutate({
      values,
      usl:           toFloat(form.usl),
      lsl:           toFloat(form.lsl),
      target:        toFloat(form.target),
      subgroup_size: 1,
    })
  }

  const handleReset = () => {
    setForm(initialSpcForm)
    setResult(null)
    mutation.reset()
  }

  // Derive chart data from result
  const chartValues = result?.values ?? parseValues(form.raw_values)
  const ucl = result?.control_limits?.UCL_X ?? null
  const cl  = result?.control_limits?.['X-bar'] ?? result?.control_limits?.CL ?? null
  const lcl = result?.control_limits?.LCL_X ?? null
  const outIdxs = (result?.alerts ?? []).map(a => a.index).filter(i => i != null)

  // Judgment color
  const judgeHighlight = v => {
    if (!v) return null
    const upper = v.toString().toUpperCase()
    if (upper.includes('불합격') || upper.includes('FAIL') || upper.includes('OUT') || upper.includes('부적합')) return 'bad'
    if (upper.includes('합격') || upper.includes('PASS') || upper.includes('OK') || upper.includes('적합')) return 'good'
    return null
  }

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* ── 좌측 입력 폼 ── */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>SPC 분석 입력</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>측정 항목명</label>
            <input
              style={S.input}
              value={form.measurement_name}
              onChange={e => set('measurement_name', e.target.value)}
              placeholder="예: 외경 (mm)"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>USL (상한 규격, 선택)</label>
            <input
              style={S.input}
              type="number" step="any"
              value={form.usl}
              onChange={e => set('usl', e.target.value)}
              placeholder="예: 10.05"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>LSL (하한 규격, 선택)</label>
            <input
              style={S.input}
              type="number" step="any"
              value={form.lsl}
              onChange={e => set('lsl', e.target.value)}
              placeholder="예: 9.95"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>Target (목표값, 선택)</label>
            <input
              style={S.input}
              type="number" step="any"
              value={form.target}
              onChange={e => set('target', e.target.value)}
              placeholder="예: 10.00"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>측정값 * (쉼표 또는 줄바꿈으로 구분)</label>
            <textarea
              style={{ ...S.input, resize: 'vertical', minHeight: 100, fontFamily: 'monospace', fontSize: 12 }}
              value={form.raw_values}
              onChange={e => set('raw_values', e.target.value)}
              placeholder={'10.01, 9.98, 10.03\n또는 한 줄에 하나씩'}
            />
            {form.raw_values && (
              <div style={{ fontSize: 11, color: '#9b9b9b', marginTop: 4 }}>
                인식된 값: {parseValues(form.raw_values).length}개
              </div>
            )}
          </div>
          {mutation.isError && (
            <div style={{ color: '#d44c47', fontSize: 12, marginBottom: 8 }}>
              분석 중 오류가 발생했습니다. API 응답을 확인하세요.
            </div>
          )}
          <button type="submit" style={S.btnSave} disabled={mutation.isPending}>
            {mutation.isPending ? '분석 중...' : 'SPC 분석 실행'}
          </button>
          {result && (
            <button type="button" style={S.btnCancel} onClick={handleReset}>
              초기화
            </button>
          )}
        </form>
      </div>

      {/* ── 우측 결과 영역 ── */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">

        {/* 분석 전 안내 */}
        {!result && !mutation.isPending && (
          <div style={{
            padding: '48px 0', textAlign: 'center',
            color: '#9b9b9b', fontSize: 13,
            background: 'white', border: '1px solid #e9e9e7',
            borderRadius: 10,
          }}>
            좌측에 측정값을 입력하고 분석을 실행하면 SPC 결과가 표시됩니다.
          </div>
        )}

        {/* 로딩 */}
        {mutation.isPending && (
          <div style={{
            padding: '48px 0', textAlign: 'center',
            color: '#9b9b9b', fontSize: 13,
            background: 'white', border: '1px solid #e9e9e7',
            borderRadius: 10,
          }}>
            SPC 분석 중...
          </div>
        )}

        {/* 결과 카드들 */}
        {result && (
          <>
            {/* 측정 항목명 헤더 */}
            {form.measurement_name && (
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>
                {form.measurement_name}
              </div>
            )}

            {/* 상단 3열 카드: 공정능력 / 관리한계 / 경보 */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>

              {/* 공정능력 */}
              {result.process_capability && (
                <ResultCard title="공정 능력 (Capability)" accent="#2e7d32">
                  {result.process_capability.mean != null && (
                    <StatRow label="평균 (Mean)" value={Number(result.process_capability.mean).toFixed(4)} />
                  )}
                  {result.process_capability.std != null && (
                    <StatRow label="표준편차 (Std)" value={Number(result.process_capability.std).toFixed(4)} />
                  )}
                  {result.process_capability.Cp != null && (
                    <StatRow
                      label="Cp"
                      value={Number(result.process_capability.Cp).toFixed(3)}
                      highlight={Number(result.process_capability.Cp) >= 1.33 ? 'good' : Number(result.process_capability.Cp) >= 1.0 ? null : 'bad'}
                    />
                  )}
                  {result.process_capability.Cpk != null && (
                    <StatRow
                      label="Cpk"
                      value={Number(result.process_capability.Cpk).toFixed(3)}
                      highlight={Number(result.process_capability.Cpk) >= 1.33 ? 'good' : Number(result.process_capability.Cpk) >= 1.0 ? null : 'bad'}
                    />
                  )}
                  {result.process_capability.judgment != null && (
                    <StatRow
                      label="판정"
                      value={result.process_capability.judgment}
                      highlight={judgeHighlight(result.process_capability.judgment)}
                    />
                  )}
                </ResultCard>
              )}

              {/* 관리 한계 */}
              {result.control_limits && (
                <ResultCard title="관리 한계 (Control Limits)" accent="#1565c0">
                  {Object.entries(result.control_limits).map(([k, v]) => (
                    <StatRow
                      key={k}
                      label={k}
                      value={v != null ? Number(v).toFixed(4) : '-'}
                      highlight={k.startsWith('UCL') || k.startsWith('LCL') ? null : null}
                    />
                  ))}
                </ResultCard>
              )}

              {/* 경보 요약 */}
              <ResultCard
                title={`이상 점 (${(result.alerts ?? []).length}개)`}
                accent={(result.alerts ?? []).length > 0 ? '#d44c47' : '#2e7d32'}
              >
                {(result.alerts ?? []).length === 0 ? (
                  <div style={{ fontSize: 12, color: '#2e7d32', padding: '8px 0' }}>
                    관리한계 이탈 없음 — 공정이 안정적입니다.
                  </div>
                ) : (
                  <div style={{ maxHeight: 180, overflowY: 'auto' }}>
                    {result.alerts.map((alert, i) => (
                      <div key={i} style={{
                        padding: '6px 8px', marginBottom: 6,
                        background: '#fff5f5', border: '1px solid #fdd',
                        borderRadius: 6, fontSize: 11,
                      }}>
                        <div style={{ fontWeight: 600, color: '#d44c47', marginBottom: 2 }}>
                          샘플 #{(alert.index ?? 0) + 1}
                          {alert.value != null && ` — 값: ${Number(alert.value).toFixed(4)}`}
                        </div>
                        {(alert.rules ?? []).map((rule, j) => (
                          <div key={j} style={{ color: '#8b1c1c' }}>{rule}</div>
                        ))}
                        {typeof alert.rule === 'string' && (
                          <div style={{ color: '#8b1c1c' }}>{alert.rule}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </ResultCard>
            </div>

            {/* 관리도 차트 */}
            <div style={{
              background: 'white', border: '1px solid #e9e9e7',
              borderRadius: 10, padding: '16px 20px',
              boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
            }}>
              <div style={{
                fontSize: 12, fontWeight: 700, color: '#6b6b6b',
                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4,
              }}>
                X 관리도
              </div>

              {/* 범례 */}
              <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#6b6b6b', marginBottom: 10 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ display: 'inline-block', width: 20, height: 2, background: '#d44c47', borderTop: '2px dashed #d44c47' }} />
                  UCL
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ display: 'inline-block', width: 20, height: 2, background: '#2d7a2d' }} />
                  CL
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ display: 'inline-block', width: 20, height: 2, background: '#1565c0', borderTop: '2px dashed #1565c0' }} />
                  LCL
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{
                    display: 'inline-block', width: 10, height: 10,
                    background: '#d44c47', borderRadius: '50%',
                  }} />
                  이상점
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8,
                    background: '#1a1a2e', borderRadius: '50%',
                  }} />
                  정상점
                </span>
              </div>

              <SpcChart
                values={chartValues}
                ucl={ucl}
                cl={cl}
                lcl={lcl}
                outOfControlIndices={outIdxs}
              />
            </div>
          </>
        )}
      </div>
    </div>
    </>
  )
}

// ─── 불량 통계 탭 ─────────────────────────────────────────────
function DefectStatsTab() {
  const { data: defectData } = useQuery({
    queryKey: ['qm-defects-all'],
    queryFn: () => api.get('/qm/defect-reports/?page_size=200').then(r => r.data),
  })
  const defects = defectData?.results ?? (Array.isArray(defectData) ? defectData : [])

  // Build monthly defect count — actual field: detected_at
  const monthlyMap = {}
  defects.forEach(d => {
    const dateStr = d.detected_at || d.detected_date || d.created_at || ''
    if (!dateStr) return
    const month = String(dateStr).slice(0, 7) // YYYY-MM
    if (!monthlyMap[month]) monthlyMap[month] = { month, count: 0, qty: 0 }
    monthlyMap[month].count += 1
    monthlyMap[month].qty += Number(d.quantity || 1)
  })
  const monthlyData = Object.values(monthlyMap)
    .sort((a, b) => a.month.localeCompare(b.month))
    .slice(-12)

  // Build defect type distribution — actual field: defect_type
  const typeMap = {}
  defects.forEach(d => {
    const type = d.defect_type || d.defect_code || d.category || '기타'
    typeMap[type] = (typeMap[type] || 0) + 1
  })
  const typeData = Object.entries(typeMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)

  const PIE_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#65a30d']

  if (defects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-400 p-5">
        <p className="text-sm">불량 데이터가 없습니다</p>
        <p className="text-xs mt-1">불량 현황 탭에서 데이터를 먼저 등록하세요</p>
      </div>
    )
  }

  return (
    <div className="p-3 md:p-5">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: '총 불량 건수', value: `${defects.length}건`, color: 'text-red-600' },
          {
            label: '총 불량 수량',
            value: `${defects.reduce((s, d) => s + Number(d.quantity || 1), 0).toLocaleString()}개`,
            color: 'text-orange-600',
          },
          { label: '불량 유형 수', value: `${Object.keys(typeMap).length}종`, color: 'text-blue-600' },
          {
            label: '이번달 불량',
            value: (() => {
              const thisMonth = new Date().toISOString().slice(0, 7)
              const cnt = defects.filter(d =>
                String(d.detected_at || d.detected_date || d.created_at || '').startsWith(thisMonth)
              ).length
              return `${cnt}건`
            })(),
            color: 'text-purple-600',
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className={`text-xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Monthly trend bar chart */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="font-semibold text-gray-700 text-sm mb-4">월별 불량 발생 추이</h3>
          {monthlyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={monthlyData} margin={{ top: 4, right: 8, bottom: 20, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  formatter={(v, n) => [v, n === 'count' ? '건수' : '수량']}
                  labelFormatter={l => `${l}월`}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} formatter={v => v === 'count' ? '건수' : '수량'} />
                <Bar dataKey="count" name="count" fill="#dc2626" radius={[3, 3, 0, 0]} />
                <Bar dataKey="qty" name="qty" fill="#fca5a5" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">월별 데이터 없음</p>
          )}
        </div>

        {/* Defect type pie chart */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="font-semibold text-gray-700 text-sm mb-4">불량 유형 분포</h3>
          {typeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={typeData}
                  cx="45%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {typeData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v}건`, n]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">유형 데이터 없음</p>
          )}
        </div>
      </div>

      {/* Defect type table */}
      <div className="mt-6 bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
          <h3 className="font-semibold text-gray-700 text-sm">불량 유형별 집계</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">순위</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">불량 유형</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500">건수</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500">비율</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">분포</th>
              </tr>
            </thead>
            <tbody>
              {typeData.map((row, i) => {
                const pct = defects.length > 0 ? (row.value / defects.length * 100).toFixed(1) : 0
                return (
                  <tr key={row.name} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-500">{i + 1}</td>
                    <td className="px-4 py-2.5 font-medium text-gray-800">{row.name}</td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{row.value}건</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{pct}%</td>
                    <td className="px-4 py-2.5 w-32">
                      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function QmPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: dashboardData } = useQuery({
    queryKey: ['qm-dashboard'],
    queryFn: () => api.get('/qm/inspection-results/dashboard/').then(r => r.data).catch(() => null),
  })
  const { data: resultsData } = useQuery({
    queryKey: ['qm-results'],
    queryFn: () => api.get('/qm/inspection-results/').then(r => r.data).catch(() => []),
  })

  const results      = getList(resultsData)
  const now          = new Date()
  const thisMonth    = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const monthResults = results.filter(r => (r.inspected_at ?? '').startsWith(thisMonth))
  const monthPassed  = monthResults.filter(r => r.result === 'passed' || r.result === '합격')
  const monthFailed  = monthResults.filter(r => r.result === 'failed' || r.result === '불합격')

  const kpiTotal  = dashboardData?.total  ?? (resultsData ? monthResults.length : '-')
  const kpiPassed = dashboardData?.passed ?? (resultsData ? monthPassed.length  : '-')
  const kpiFailed = dashboardData?.failed ?? (resultsData ? monthFailed.length  : '-')

  const TAB_COMPONENTS = [InspectionPlanTab, InspectionResultTab, DefectTab, SpcTab, DefectStatsTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🔬</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>QM 품질관리</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Quality Management — 검사·불량·시정조치를 통합 관리합니다.</div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="이번달 검사" value={kpiTotal}  unit="건" />
        <KpiCard label="합격"        value={kpiPassed} unit="건" />
        <KpiCard label="불합격"      value={kpiFailed} unit="건" />
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
