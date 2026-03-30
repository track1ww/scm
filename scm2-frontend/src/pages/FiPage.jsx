import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import AgingTable from '../components/AgingTable'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['계정과목', '전표', '세금계산서', 'AR/AP 나이분석', '예산 관리', '고정자산']

// ─── 공통 헬퍼 ────────────────────────────────────────────────
function getList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
}

const today = () => new Date().toISOString().slice(0, 10)

// ─── 공통 스타일 ───────────────────────────────────────────────
const S = {
  input: {
    width: '100%', padding: '8px 10px', border: '1px solid #e9e9e7',
    borderRadius: 6, fontSize: 13, boxSizing: 'border-box', outline: 'none',
  },
  label: { display: 'block', fontSize: 12, color: '#6b6b6b', marginBottom: 4 },
  formRow: { marginBottom: 12 },
  btnPrimary: {
    width: '100%', background: '#1a1a2e', color: 'white',
    padding: '10px', borderRadius: 6, border: 'none',
    cursor: 'pointer', fontSize: 13, fontWeight: 600, marginTop: 16,
  },
  btnCancelInline: {
    width: '100%', background: '#f5f5f3', color: '#6b6b6b',
    padding: '8px', borderRadius: 6, border: '1px solid #e9e9e7',
    cursor: 'pointer', fontSize: 13, marginTop: 6,
  },
  btnEdit: {
    background: '#f0f4ff', color: '#3366cc', border: '1px solid #c5d5f5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer', marginRight: 4,
  },
  btnDel: {
    background: '#fff0f0', color: '#cc3333', border: '1px solid #f5c5c5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
  btnAction: {
    background: '#f0fff4', color: '#2d7a2d', border: '1px solid #b5e0b5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer', marginRight: 4,
  },
  btnIssue: {
    background: '#f0fff4', color: '#2d7a2d', border: '1px solid #b5e0b5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
}

// ─── 좌측 폼 래퍼 ─────────────────────────────────────────────
function FormPanel({ title, children, onSubmit, onCancel, isPending, editMode }) {
  return (
    <div style={{
      width: 320, flexShrink: 0,
      background: 'white', border: '1px solid #e9e9e7',
      borderRadius: 10, padding: 20, alignSelf: 'flex-start',
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: '#1a1a1a' }}>
        {editMode ? '수정' : '신규 등록'}
      </div>
      {children}
      <button style={S.btnPrimary} onClick={onSubmit} disabled={isPending}>
        {isPending ? '저장 중...' : (editMode ? '수정 완료' : '등록')}
      </button>
      {editMode && onCancel && (
        <button style={S.btnCancelInline} onClick={onCancel}>취소</button>
      )}
    </div>
  )
}

// ─── 테이블 공통 래퍼 ─────────────────────────────────────────
function DataTable({ isLoading, rows, columns }) {
  return (
    <div style={{ flex: 1, overflowX: 'auto', minWidth: 0 }}>
      {isLoading ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
          데이터를 불러오는 중...
        </div>
      ) : rows.length === 0 ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
          데이터가 없습니다
        </div>
      ) : (
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
      )}
    </div>
  )
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
  draft:     { label: '임시',   bg: '#f5f5f3', color: '#6b6b6b' },
  DRAFT:     { label: '임시',   bg: '#f5f5f3', color: '#6b6b6b' },
  posted:    { label: '확정',   bg: '#e8f5e9', color: '#2e7d32' },
  POSTED:    { label: '확정',   bg: '#e8f5e9', color: '#2e7d32' },
  cancelled: { label: '취소',   bg: '#fdecea', color: '#d44c47' },
  CANCELLED: { label: '취소',   bg: '#fdecea', color: '#d44c47' },
  issued:    { label: '발행',   bg: '#e3f2fd', color: '#1565c0' },
  ISSUED:    { label: '발행',   bg: '#e3f2fd', color: '#1565c0' },
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

// ─── 계정과목 탭 ───────────────────────────────────────────────
function AccountTab() {
  const queryClient = useQueryClient()
  const initialForm = { account_code: '', account_name: '', account_type: 'ASSET', is_active: true }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['fi-accounts', page],
    queryFn: () => api.get(`/fi/accounts/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      account_code: row.account_code ?? '',
      account_name: row.account_name ?? '',
      account_type: row.account_type ?? 'ASSET',
      is_active: row.is_active ?? true,
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/fi/accounts/${editId}/`, payload).then(r => r.data)
        : api.post('/fi/accounts/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fi-accounts'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/fi/accounts/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fi-accounts'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.account_code.trim()) { setGlobalError('계정코드는 필수입니다.'); return }
    if (!form.account_name.trim()) { setGlobalError('계정명은 필수입니다.'); return }
    saveMutation.mutate(form)
  }

  const columns = [
    { key: 'account_code', label: '계정코드' },
    { key: 'account_name', label: '계정명' },
    { key: 'account_type', label: '유형' },
    { key: 'is_active', label: '활성', render: v => v ? '활성' : '비활성' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: `계정 "${row.account_name}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
        </span>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>계정코드 *</label>
          <input style={S.input} value={form.account_code}
            onChange={e => setForm(f => ({ ...f, account_code: e.target.value }))}
            placeholder="예: 1001" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>계정명 *</label>
          <input style={S.input} value={form.account_name}
            onChange={e => setForm(f => ({ ...f, account_name: e.target.value }))}
            placeholder="예: 현금" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>계정유형</label>
          <select style={S.input} value={form.account_type}
            onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))}>
            <option value="ASSET">ASSET (자산)</option>
            <option value="LIABILITY">LIABILITY (부채)</option>
            <option value="EQUITY">EQUITY (자본)</option>
            <option value="REVENUE">REVENUE (수익)</option>
            <option value="EXPENSE">EXPENSE (비용)</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
            <input type="checkbox" checked={form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
            활성 상태
          </label>
        </div>
      </FormPanel>
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 전표 탭 ──────────────────────────────────────────────────
function MoveTab() {
  const queryClient = useQueryClient()
  const blankLine = { account: '', debit_amount: '', credit_amount: '' }
  const initialForm = { move_type: 'GENERAL', posting_date: today(), description: '' }
  const [form, setForm] = useState(initialForm)
  const [lines, setLines] = useState([{ ...blankLine }])
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['fi-moves', page],
    queryFn: () => api.get(`/fi/moves/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: accountData } = useQuery({
    queryKey: ['fi-accounts'],
    queryFn: () => api.get('/fi/accounts/').then(r => r.data).catch(() => []),
  })
  const rows = getList(data)
  const accounts = getList(accountData)

  const createMutation = useMutation({
    mutationFn: payload => api.post('/fi/moves/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fi-moves'] })
      setForm(initialForm)
      setLines([{ ...blankLine }])
    },
  })

  const postMutation = useMutation({
    mutationFn: id => api.post(`/fi/moves/${id}/post/`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fi-moves'] }),
  })

  const cancelMutation = useMutation({
    mutationFn: id => api.post(`/fi/moves/${id}/cancel/`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fi-moves'] }),
  })

  const addLine = () => setLines(ls => [...ls, { ...blankLine }])
  const removeLine = idx => setLines(ls => ls.filter((_, i) => i !== idx))
  const updateLine = (idx, field, value) =>
    setLines(ls => ls.map((l, i) => i === idx ? { ...l, [field]: value } : l))

  const handleSubmit = () => {
    const payload = {
      ...form,
      lines: lines.map(l => ({
        account: l.account || undefined,
        debit_amount: l.debit_amount || 0,
        credit_amount: l.credit_amount || 0,
      })),
    }
    if (!payload.posting_date) delete payload.posting_date
    createMutation.mutate(payload)
  }

  const columns = [
    { key: 'move_number', label: '전표번호' },
    { key: 'move_type', label: '유형' },
    { key: 'posting_date', label: '전기일' },
    { key: 'total_debit', label: '차변합계', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'total_credit', label: '대변합계', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'state', label: '상태', render: v => <StatusBadge status={v} /> },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          {(row.state === 'draft' || row.state === 'DRAFT') && (
            <button style={S.btnAction} onClick={() => postMutation.mutate(row.id)}>확정</button>
          )}
          {(row.state === 'posted' || row.state === 'POSTED') && (
            <button style={S.btnDel} onClick={() => requestConfirm({ message: '이 전표를 취소하시겠습니까?', confirmLabel: '취소', onConfirm: () => cancelMutation.mutate(row.id) })}>취소</button>
          )}
        </span>
      ),
    },
  ]

  return (
    <>
    <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5 items-start">
      <div style={{
        width: 320, flexShrink: 0,
        background: 'white', border: '1px solid #e9e9e7',
        borderRadius: 10, padding: 20,
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: '#1a1a1a' }}>신규 등록</div>
        <div style={S.formRow}>
          <label style={S.label}>전표유형</label>
          <select style={S.input} value={form.move_type}
            onChange={e => setForm(f => ({ ...f, move_type: e.target.value }))}>
            <option value="GENERAL">GENERAL (일반)</option>
            <option value="PURCHASE">PURCHASE (매입)</option>
            <option value="SALE">SALE (매출)</option>
            <option value="PAYMENT">PAYMENT (지급)</option>
            <option value="RECEIPT">RECEIPT (수금)</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>전기일</label>
          <input style={S.input} type="date" value={form.posting_date}
            onChange={e => setForm(f => ({ ...f, posting_date: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>설명</label>
          <input style={S.input} value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="전표 설명" />
        </div>

        {/* 전표 라인 섹션 */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>전표 라인</span>
            <button
              style={{
                background: '#f0fff4', color: '#2d7a2d', border: '1px solid #b5e0b5',
                borderRadius: 4, padding: '3px 8px', fontSize: 11, cursor: 'pointer',
              }}
              onClick={addLine}
            >+ 라인 추가</button>
          </div>
          {lines.map((line, idx) => (
            <div key={idx} style={{
              border: '1px solid #e9e9e7', borderRadius: 6, padding: 8,
              marginBottom: 6, background: '#fafafa',
            }}>
              <div style={{ marginBottom: 4 }}>
                <label style={{ ...S.label, fontSize: 11 }}>계정과목</label>
                <select
                  style={{ ...S.input, fontSize: 12, padding: '5px 8px' }}
                  value={line.account}
                  onChange={e => updateLine(idx, 'account', e.target.value)}
                >
                  <option value="">-- 선택 --</option>
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>{a.account_code} {a.account_name}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 4, alignItems: 'end' }}>
                <div>
                  <label style={{ ...S.label, fontSize: 11 }}>차변</label>
                  <input
                    style={{ ...S.input, fontSize: 12, padding: '5px 8px' }}
                    type="number" value={line.debit_amount} placeholder="0"
                    onChange={e => updateLine(idx, 'debit_amount', e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ ...S.label, fontSize: 11 }}>대변</label>
                  <input
                    style={{ ...S.input, fontSize: 12, padding: '5px 8px' }}
                    type="number" value={line.credit_amount} placeholder="0"
                    onChange={e => updateLine(idx, 'credit_amount', e.target.value)}
                  />
                </div>
                <div>
                  {lines.length > 1 && (
                    <button
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#cc3333', fontSize: 16, padding: '5px 2px' }}
                      onClick={() => removeLine(idx)}
                    >×</button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <button style={S.btnPrimary} onClick={handleSubmit} disabled={createMutation.isPending}>
          {createMutation.isPending ? '저장 중...' : '등록'}
        </button>
      </div>
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 세금계산서 탭 ─────────────────────────────────────────────
function TaxInvoiceTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    invoice_type: 'SALE', invoice_date: today(),
    counterpart_name: '', counterpart_reg_no: '',
    supply_amount: '', tax_amount: '',
  }
  const [form, setForm] = useState(initialForm)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['fi-tax-invoices', page],
    queryFn: () => api.get(`/fi/tax-invoices/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const createMutation = useMutation({
    mutationFn: payload => api.post('/fi/tax-invoices/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fi-tax-invoices'] })
      setForm(initialForm)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const issueMutation = useMutation({
    mutationFn: id => api.post(`/fi/tax-invoices/${id}/issue/`).then(r => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['fi-tax-invoices'] }); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/fi/tax-invoices/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fi-tax-invoices'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSupplyBlur = () => {
    const val = form.supply_amount
    if (val) {
      setForm(f => ({ ...f, tax_amount: String(Math.round(Number(val) * 0.1)) }))
    }
  }

  const handleSubmit = () => {
    if (!form.counterpart_name.trim()) { setGlobalError('거래처명은 필수입니다.'); return }
    if (!form.supply_amount) { setGlobalError('공급가액은 필수입니다.'); return }
    createMutation.mutate(form)
  }

  const columns = [
    { key: 'invoice_number', label: '번호' },
    { key: 'invoice_type', label: '유형' },
    { key: 'counterpart_name', label: '거래처' },
    { key: 'supply_amount', label: '공급가액', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'tax_amount', label: '세액', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'invoice_date', label: '발행일' },
    { key: 'status', label: '상태', render: v => <StatusBadge status={v} /> },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          {(row.status === 'DRAFT' || row.status === 'draft') && (
            <>
              <button style={S.btnIssue} onClick={() => issueMutation.mutate(row.id)}>발행</button>
              {' '}
              <button style={S.btnDel} onClick={() => requestConfirm({ message: '세금계산서를 삭제하시겠습니까?', onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
            </>
          )}
        </span>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5 items-start">
      <FormPanel
        editMode={false}
        onSubmit={handleSubmit}
        isPending={createMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>구분</label>
          <select style={S.input} value={form.invoice_type}
            onChange={e => setForm(f => ({ ...f, invoice_type: e.target.value }))}>
            <option value="SALE">SALE (매출)</option>
            <option value="PURCHASE">PURCHASE (매입)</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>발행일</label>
          <input style={S.input} type="date" value={form.invoice_date}
            onChange={e => setForm(f => ({ ...f, invoice_date: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>거래처명 *</label>
          <input style={S.input} value={form.counterpart_name}
            onChange={e => setForm(f => ({ ...f, counterpart_name: e.target.value }))}
            placeholder="거래처 이름" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>사업자등록번호</label>
          <input style={S.input} value={form.counterpart_reg_no}
            onChange={e => setForm(f => ({ ...f, counterpart_reg_no: e.target.value }))}
            placeholder="000-00-00000" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>공급가액 *</label>
          <input style={S.input} type="number" value={form.supply_amount}
            onChange={e => setForm(f => ({ ...f, supply_amount: e.target.value }))}
            onBlur={handleSupplyBlur}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>세액 (공급가액 × 10% 자동계산)</label>
          <input
            style={{ ...S.input, background: '#f9f9f7', color: '#6b6b6b' }}
            type="number" value={form.tax_amount}
            readOnly placeholder="자동계산" />
        </div>
      </FormPanel>
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── AR/AP 나이분석 탭 ────────────────────────────────────────
function AgingTab() {
  const [agingType, setAgingType] = useState('receivable')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['fi-aging', agingType],
    queryFn: () => api.get(`/fi/moves/aging/?type=${agingType}`).then(r => r.data).catch(() => []),
  })

  const rows = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : [])
  const typeLabel = agingType === 'receivable' ? '매출채권' : '매입채무'

  return (
    <div className="p-3 md:p-5">
      {/* 전환 버튼 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button
          onClick={() => setAgingType('receivable')}
          style={{
            padding: '8px 20px', borderRadius: 6, border: 'none',
            cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: agingType === 'receivable' ? '#1a1a2e' : '#f5f5f3',
            color: agingType === 'receivable' ? 'white' : '#6b6b6b',
            transition: 'all 0.12s',
          }}
        >
          매출채권
        </button>
        <button
          onClick={() => setAgingType('payable')}
          style={{
            padding: '8px 20px', borderRadius: 6, border: 'none',
            cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: agingType === 'payable' ? '#1a1a2e' : '#f5f5f3',
            color: agingType === 'payable' ? 'white' : '#6b6b6b',
            transition: 'all 0.12s',
          }}
        >
          매입채무
        </button>
      </div>

      {/* 범례 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        {[
          { label: '미도래', bg: '#f5f5f3', color: '#6b6b6b' },
          { label: '0–30일', bg: '#f0f4ff', color: '#3366cc' },
          { label: '31–60일 (주의)', bg: '#fff8e1', color: '#e65100' },
          { label: '61–90일 (경고)', bg: '#fdecea', color: '#c62828' },
          { label: '90일 초과 (위험)', bg: '#ffcdd2', color: '#b71c1c' },
        ].map(item => (
          <span key={item.label} style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            fontSize: 11, color: item.color,
          }}>
            <span style={{
              display: 'inline-block', width: 10, height: 10,
              borderRadius: 2, background: item.bg, border: `1px solid ${item.color}`,
            }} />
            {item.label}
          </span>
        ))}
      </div>

      {isLoading ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
          데이터를 불러오는 중...
        </div>
      ) : (
        <AgingTable data={rows} title={`${typeLabel} 나이분석`} />
      )}
    </div>
  )
}

// ─── 예산 관리 탭 ─────────────────────────────────────────────
function BudgetTab() {
  const queryClient = useQueryClient()
  const now = new Date()
  const initialForm = {
    budget_year: String(now.getFullYear()),
    budget_month: String(now.getMonth() + 1).padStart(2, '0'),
    account: '',
    budget_amount: '',
    note: '',
  }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['fi-budgets', page],
    queryFn: () => api.get(`/fi/budgets/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: accountData } = useQuery({
    queryKey: ['fi-accounts'],
    queryFn: () => api.get('/fi/accounts/').then(r => r.data).catch(() => []),
  })
  const rows = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : [])
  const accounts = Array.isArray(accountData) ? accountData : (Array.isArray(accountData?.results) ? accountData.results : [])

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      budget_year: row.budget_year ?? '',
      budget_month: row.budget_month ?? '',
      account: (typeof row.account === 'object' ? row.account?.id : row.account) ?? '',
      budget_amount: row.budget_amount ?? '',
      note: row.note ?? '',
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/fi/budgets/${editId}/`, payload).then(r => r.data)
        : api.post('/fi/budgets/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fi-budgets'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/fi/budgets/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fi-budgets'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.budget_year) { setGlobalError('예산연도는 필수입니다.'); return }
    if (!form.budget_month) { setGlobalError('예산월은 필수입니다.'); return }
    if (!form.account) { setGlobalError('계정을 선택해주세요.'); return }
    if (!form.budget_amount) { setGlobalError('예산금액은 필수입니다.'); return }
    saveMutation.mutate(form)
  }

  const fmtAmt = v => v != null ? Number(v).toLocaleString() + '원' : '-'
  const fmtRate = (actual, budget) => {
    if (!budget || Number(budget) === 0) return '-'
    return (Number(actual) / Number(budget) * 100).toFixed(1) + '%'
  }

  const columns = [
    { key: 'budget_year', label: '연도' },
    { key: 'budget_month', label: '월' },
    {
      key: 'account', label: '계정',
      render: (v, row) => {
        if (typeof v === 'object' && v) return `${v.account_code} ${v.account_name}`
        return row.account_name ?? v ?? '-'
      },
    },
    { key: 'budget_amount', label: '예산금액', render: fmtAmt },
    { key: 'actual_amount', label: '실적금액', render: fmtAmt },
    {
      key: '_diff', label: '차이금액',
      render: (_, row) => {
        const diff = Number(row.budget_amount ?? 0) - Number(row.actual_amount ?? 0)
        const color = diff >= 0 ? '#2e7d32' : '#d44c47'
        return <span style={{ color, fontWeight: 600 }}>{diff.toLocaleString()}원</span>
      },
    },
    {
      key: '_rate', label: '달성률',
      render: (_, row) => {
        const rate = row.budget_amount && Number(row.budget_amount) > 0
          ? Number(row.actual_amount ?? 0) / Number(row.budget_amount) * 100
          : null
        if (rate === null) return '-'
        const color = rate >= 100 ? '#2e7d32' : rate >= 80 ? '#e65100' : '#d44c47'
        return <span style={{ color, fontWeight: 600 }}>{rate.toFixed(1)}%</span>
      },
    },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: '이 예산을 삭제하시겠습니까?', onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
        </span>
      ),
    },
  ]

  const months = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0'))

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>예산연도 *</label>
          <input style={S.input} type="number" value={form.budget_year}
            onChange={e => setForm(f => ({ ...f, budget_year: e.target.value }))}
            placeholder="예: 2026" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>예산월 *</label>
          <select style={S.input} value={form.budget_month}
            onChange={e => setForm(f => ({ ...f, budget_month: e.target.value }))}>
            <option value="">-- 월 선택 --</option>
            {months.map(m => <option key={m} value={m}>{m}월</option>)}
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>계정 *</label>
          <select style={S.input} value={form.account}
            onChange={e => setForm(f => ({ ...f, account: e.target.value }))}>
            <option value="">-- 계정 선택 --</option>
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.account_code} {a.account_name}</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>예산금액 *</label>
          <input style={S.input} type="number" value={form.budget_amount}
            onChange={e => setForm(f => ({ ...f, budget_amount: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>비고</label>
          <input style={S.input} value={form.note}
            onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
            placeholder="메모" />
        </div>
      </FormPanel>
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 고정자산 탭 ───────────────────────────────────────────────
function FixedAssetTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    asset_code: '', asset_name: '',
    category: '기계', acquisition_date: today(),
    acquisition_cost: '', useful_life: '', residual_value: '',
    depreciation_method: 'straight_line',
  }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['fi-fixed-assets', page],
    queryFn: () => api.get(`/fi/fixed-assets/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : [])

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      asset_code: row.asset_code ?? '',
      asset_name: row.asset_name ?? '',
      category: row.category ?? '기계',
      acquisition_date: row.acquisition_date ?? today(),
      acquisition_cost: row.acquisition_cost ?? '',
      useful_life: row.useful_life ?? '',
      residual_value: row.residual_value ?? '',
      depreciation_method: row.depreciation_method ?? 'straight_line',
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/fi/fixed-assets/${editId}/`, payload).then(r => r.data)
        : api.post('/fi/fixed-assets/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fi-fixed-assets'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const depreciateMutation = useMutation({
    mutationFn: id => api.post(`/fi/fixed-assets/${id}/depreciate/`).then(r => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['fi-fixed-assets'] }); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/fi/fixed-assets/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fi-fixed-assets'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.asset_code.trim()) { setGlobalError('자산코드는 필수입니다.'); return }
    if (!form.asset_name.trim()) { setGlobalError('자산명은 필수입니다.'); return }
    if (!form.acquisition_cost) { setGlobalError('취득원가는 필수입니다.'); return }
    if (!form.useful_life) { setGlobalError('내용연수는 필수입니다.'); return }
    saveMutation.mutate(form)
  }

  const fmtAmt = v => v != null ? Number(v).toLocaleString() + '원' : '-'

  const STATUS_FA = {
    active:    { label: '운용중',  bg: '#e8f5e9', color: '#2e7d32' },
    disposed:  { label: '처분완료', bg: '#fdecea', color: '#d44c47' },
    fully_dep: { label: '완전상각', bg: '#f5f5f3', color: '#6b6b6b' },
  }

  const columns = [
    { key: 'asset_code', label: '자산코드' },
    { key: 'asset_name', label: '자산명' },
    { key: 'category', label: '분류' },
    { key: 'acquisition_cost', label: '취득원가', render: fmtAmt },
    { key: 'accumulated_depreciation', label: '누계상각', render: fmtAmt },
    {
      key: 'book_value', label: '장부가액',
      render: (v, row) => {
        const bv = v != null ? v : (Number(row.acquisition_cost ?? 0) - Number(row.accumulated_depreciation ?? 0))
        return fmtAmt(bv)
      },
    },
    {
      key: 'status', label: '상태',
      render: v => {
        const s = STATUS_FA[v] ?? { label: v ?? '-', bg: '#f5f5f3', color: '#6b6b6b' }
        return (
          <span style={{
            display: 'inline-block', padding: '2px 8px',
            borderRadius: 99, fontSize: 11, fontWeight: 600,
            background: s.bg, color: s.color,
          }}>
            {s.label}
          </span>
        )
      },
    },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button
            style={{
              background: '#f0fff4', color: '#2d7a2d', border: '1px solid #b5e0b5',
              borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer', marginRight: 4,
            }}
            onClick={() => requestConfirm({ message: `"${row.asset_name}" 자산의 상각을 실행하시겠습니까?`, confirmLabel: '상각실행', danger: false, onConfirm: () => depreciateMutation.mutate(row.id) })}
            disabled={depreciateMutation.isPending}
          >
            상각 실행
          </button>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: `자산 "${row.asset_name}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
        </span>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>자산코드 *</label>
          <input style={S.input} value={form.asset_code}
            onChange={e => setForm(f => ({ ...f, asset_code: e.target.value }))}
            placeholder="예: FA-001" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>자산명 *</label>
          <input style={S.input} value={form.asset_name}
            onChange={e => setForm(f => ({ ...f, asset_name: e.target.value }))}
            placeholder="예: CNC 가공기" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>분류</label>
          <select style={S.input} value={form.category}
            onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
            <option value="기계">기계</option>
            <option value="차량">차량</option>
            <option value="설비">설비</option>
            <option value="비품">비품</option>
            <option value="무형자산">무형자산</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>취득일</label>
          <input style={S.input} type="date" value={form.acquisition_date}
            onChange={e => setForm(f => ({ ...f, acquisition_date: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>취득원가 *</label>
          <input style={S.input} type="number" value={form.acquisition_cost}
            onChange={e => setForm(f => ({ ...f, acquisition_cost: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>내용연수 (년) *</label>
          <input style={S.input} type="number" value={form.useful_life}
            onChange={e => setForm(f => ({ ...f, useful_life: e.target.value }))}
            placeholder="예: 5" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>잔존가치</label>
          <input style={S.input} type="number" value={form.residual_value}
            onChange={e => setForm(f => ({ ...f, residual_value: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>상각방법</label>
          <select style={S.input} value={form.depreciation_method}
            onChange={e => setForm(f => ({ ...f, depreciation_method: e.target.value }))}>
            <option value="straight_line">정액법</option>
            <option value="declining_balance">정률법</option>
          </select>
        </div>
      </FormPanel>
      <div className="flex-1 min-w-0 overflow-x-auto">
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function FiPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: movesData } = useQuery({
    queryKey: ['fi-moves'],
    queryFn: () => api.get('/fi/moves/').then(r => r.data).catch(() => []),
  })

  const moves = getList(movesData)
  const now = new Date()
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const monthMoves  = moves.filter(m => (m.posting_date ?? '').startsWith(thisMonth))
  const postedMoves = monthMoves.filter(m => m.state === 'posted' || m.state === 'POSTED')
  const draftMoves  = monthMoves.filter(m => m.state === 'draft'  || m.state === 'DRAFT')

  const TAB_COMPONENTS = [AccountTab, MoveTab, TaxInvoiceTab, AgingTab, BudgetTab, FixedAssetTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: '0 0 6px' }}>FI 재무회계</h1>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Financial Accounting — 계정과목·전표·세금계산서를 통합 관리합니다.</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="이번달 전표" value={movesData ? monthMoves.length  : '-'} unit="건" />
        <KpiCard label="확정 전표"   value={movesData ? postedMoves.length : '-'} unit="건" />
        <KpiCard label="임시 전표"   value={movesData ? draftMoves.length  : '-'} unit="건" />
      </div>

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
