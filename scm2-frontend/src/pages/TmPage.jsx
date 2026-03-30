import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['운송 계획', '운송사 관리', '운송 추적']

// ─── 공통 헬퍼 ────────────────────────────────────────────────
function getList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
}

function nowDateTimeLocal() {
  const d = new Date()
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
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
  btnActionWarn: {
    background: '#fff8e1', color: '#b45309',
    border: '1px solid #f5dfa0', borderRadius: 4,
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
  DRAFT:      { label: '초안',   bg: '#f5f5f3', color: '#6b6b6b' },
  planned:    { label: '계획',   bg: '#f5f5f3', color: '#6b6b6b' },
  in_transit: { label: '운송중', bg: '#e3f2fd', color: '#1565c0' },
  delivered:  { label: '완료',   bg: '#e8f5e9', color: '#2e7d32' },
  cancelled:  { label: '취소',   bg: '#fdecea', color: '#d44c47' },
  pending:    { label: '대기',   bg: '#fff8e1', color: '#b45309' },
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

// ─── 운송계획 탭 (2컬럼, 등록만) ─────────────────────────────
const initialOrderForm = {
  carrier: '', origin: '', destination: '', item_description: '',
  weight_kg: '', freight_cost: '', currency: 'KRW', planned_date: '',
}

function TransportOrderTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialOrderForm)
  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data: carriersData } = useQuery({
    queryKey: ['tm-carriers'],
    queryFn: () => api.get('/tm/carriers/').then(r => r.data).catch(() => []),
  })
  const carriers = getList(carriersData)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tm-orders', page],
    queryFn: () => api.get(`/tm/orders/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const mutation = useMutation({
    mutationFn: payload => api.post('/tm/orders/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialOrderForm)
      qc.invalidateQueries({ queryKey: ['tm-orders'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const dispatchMutation = useMutation({
    mutationFn: id => api.post(`/tm/orders/${id}/dispatch/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tm-orders'] }),
  })
  const completeMutation = useMutation({
    mutationFn: id => api.post(`/tm/orders/${id}/complete/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tm-orders'] }),
  })
  const cancelMutation = useMutation({
    mutationFn: id => api.post(`/tm/orders/${id}/cancel/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tm-orders'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/tm/orders/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tm-orders'] }),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.origin.trim() || !form.destination.trim()) {
      setGlobalError('출발지와 도착지는 필수입니다.')
      return
    }
    clearErrors(); setSuccessMsg('')
    mutation.mutate({
      ...form,
      carrier:      form.carrier      ? Number(form.carrier)      : undefined,
      weight_kg:    form.weight_kg    ? Number(form.weight_kg)    : undefined,
      freight_cost: form.freight_cost ? Number(form.freight_cost) : undefined,
    })
  }

  const handleDelete = row => {
    requestConfirm({ message: `운송 "${row.transport_number}"를 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })
  }

  const isDraft     = row => row.status === 'DRAFT'   || row.status === 'planned'
  const isActive    = row => row.status === 'planned' || row.status === 'DRAFT' || row.status === 'pending'
  const isInTransit = row => row.status === 'in_transit'

  const columns = [
    { key: 'transport_number', label: '운송번호' },
    { key: 'carrier',          label: '운송사', render: (v, row) => (typeof v === 'object' ? v?.name : v) ?? row.carrier_name ?? '-' },
    { key: 'origin',           label: '출발지' },
    { key: 'destination',      label: '도착지' },
    { key: 'freight_cost',     label: '운임', render: (v, row) => v != null ? `${Number(v).toLocaleString()} ${row.currency ?? 'KRW'}` : '-' },
    { key: 'planned_date',     label: '계획일' },
    { key: 'status',           label: '상태', render: v => <StatusBadge status={v} /> },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {isActive(row) && (
            <button style={S.btnAction} onClick={() => dispatchMutation.mutate(row.id)}>배차</button>
          )}
          {isInTransit(row) && (
            <button style={S.btnAction} onClick={() => completeMutation.mutate(row.id)}>완료</button>
          )}
          {(isActive(row) || isInTransit(row)) && (
            <button style={S.btnActionWarn} onClick={() => cancelMutation.mutate(row.id)}>취소</button>
          )}
          {isDraft(row) && (
            <button style={S.btnDelete} onClick={() => handleDelete(row)}>삭제</button>
          )}
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
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>신규 등록</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>운송사</label>
            <select style={S.input} value={form.carrier} onChange={e => set('carrier', e.target.value)}>
              <option value="">-- 선택 --</option>
              {carriers.map(c => (
                <option key={c.id} value={c.id}>{c.carrier_code} - {c.carrier_name}</option>
              ))}
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>출발지 *</label>
            <input style={S.input} value={form.origin} onChange={e => set('origin', e.target.value)} placeholder="출발지" />
          </div>
          <div style={S.field}>
            <label style={S.label}>도착지 *</label>
            <input style={S.input} value={form.destination} onChange={e => set('destination', e.target.value)} placeholder="도착지" />
          </div>
          <div style={S.field}>
            <label style={S.label}>화물 설명</label>
            <input style={S.input} value={form.item_description} onChange={e => set('item_description', e.target.value)} placeholder="화물 내용" />
          </div>
          <div style={S.field}>
            <label style={S.label}>중량(kg)</label>
            <input style={S.input} type="number" min="0" step="0.01" value={form.weight_kg} onChange={e => set('weight_kg', e.target.value)} placeholder="0" />
          </div>
          <div style={S.field}>
            <label style={S.label}>운임</label>
            <input style={S.input} type="number" min="0" value={form.freight_cost} onChange={e => set('freight_cost', e.target.value)} placeholder="0" />
          </div>
          <div style={S.field}>
            <label style={S.label}>통화</label>
            <select style={S.input} value={form.currency} onChange={e => set('currency', e.target.value)}>
              <option value="KRW">KRW</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>계획일</label>
            <input style={S.input} type="date" value={form.planned_date} onChange={e => set('planned_date', e.target.value)} />
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

// ─── 운송사 탭 (2컬럼, 등록/수정) ────────────────────────────
const initialCarrierForm = {
  carrier_code: '', carrier_name: '', contact: '',
  phone: '', email: '', vehicle_type: '', is_active: true,
}

function CarrierTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(initialCarrierForm)
  const [editId, setEditId] = useState(null)
  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tm-carriers', page],
    queryFn: () => api.get(`/tm/carriers/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const mutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/tm/carriers/${editId}/`, payload).then(r => r.data)
        : api.post('/tm/carriers/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(initialCarrierForm)
      setEditId(null)
      qc.invalidateQueries({ queryKey: ['tm-carriers'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/tm/carriers/${id}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tm-carriers'] }),
    onError: (err) => handleApiError(err),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      carrier_code: row.carrier_code ?? '',
      carrier_name: row.carrier_name ?? '',
      contact:      row.contact      ?? '',
      phone:        row.phone        ?? '',
      email:        row.email        ?? '',
      vehicle_type: row.vehicle_type ?? '',
      is_active:    row.is_active    ?? true,
    })
    setEditId(row.id)
  }

  const handleCancel = () => {
    setForm(initialCarrierForm)
    setEditId(null)
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.carrier_code.trim() || !form.carrier_name.trim()) {
      setGlobalError('운송사코드와 운송사명은 필수입니다.')
      return
    }
    clearErrors(); setSuccessMsg('')
    mutation.mutate(form)
  }

  const handleDelete = row => {
    requestConfirm({ message: `운송사 "${row.carrier_name}"를 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })
  }

  const columns = [
    { key: 'carrier_code', label: '운송사코드' },
    { key: 'carrier_name', label: '운송사명' },
    { key: 'contact',      label: '연락처' },
    { key: 'phone',        label: '전화' },
    { key: 'vehicle_type', label: '차량유형' },
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
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>{editId ? '수정' : '신규 등록'}</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>운송사코드 *</label>
            <input style={S.input} value={form.carrier_code} onChange={e => set('carrier_code', e.target.value)} placeholder="CAR-001" />
          </div>
          <div style={S.field}>
            <label style={S.label}>운송사명 *</label>
            <input style={S.input} value={form.carrier_name} onChange={e => set('carrier_name', e.target.value)} placeholder="운송사명" />
          </div>
          <div style={S.field}>
            <label style={S.label}>연락처</label>
            <input style={S.input} value={form.contact} onChange={e => set('contact', e.target.value)} placeholder="담당자명" />
          </div>
          <div style={S.field}>
            <label style={S.label}>전화</label>
            <input style={S.input} value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="010-0000-0000" />
          </div>
          <div style={S.field}>
            <label style={S.label}>이메일</label>
            <input style={S.input} type="email" value={form.email} onChange={e => set('email', e.target.value)} placeholder="example@carrier.com" />
          </div>
          <div style={S.field}>
            <label style={S.label}>차량유형</label>
            <select style={S.input} value={form.vehicle_type} onChange={e => set('vehicle_type', e.target.value)}>
              <option value="">-- 선택 --</option>
              <option value="트럭">트럭</option>
              <option value="컨테이너">컨테이너</option>
              <option value="항공">항공</option>
              <option value="해운">해운</option>
              <option value="기타">기타</option>
            </select>
          </div>
          <div style={{ ...S.field, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox" id="carrier_is_active"
              checked={form.is_active}
              onChange={e => set('is_active', e.target.checked)}
              style={{ width: 'auto' }}
            />
            <label htmlFor="carrier_is_active" style={{ ...S.label, margin: 0 }}>활성</label>
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

// ─── 운송추적 탭 (2컬럼, 등록만) ─────────────────────────────
const makeInitialTrackingForm = () => ({
  transport_order: '', location: '', status_note: '', tracked_at: nowDateTimeLocal(),
})

function TrackingTab() {
  const qc = useQueryClient()
  const [form, setForm] = useState(makeInitialTrackingForm)
  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const [page, setPage] = useState(1)

  const { data: ordersData } = useQuery({
    queryKey: ['tm-orders'],
    queryFn: () => api.get('/tm/orders/').then(r => r.data).catch(() => []),
  })
  const orders = getList(ordersData)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tm-tracking', page],
    queryFn: () => api.get(`/tm/tracking/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const mutation = useMutation({
    mutationFn: payload => api.post('/tm/tracking/', payload).then(r => r.data),
    onSuccess: () => {
      setForm(makeInitialTrackingForm())
      qc.invalidateQueries({ queryKey: ['tm-tracking'] })
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.location.trim()) {
      setGlobalError('현재 위치는 필수입니다.')
      return
    }
    clearErrors(); setSuccessMsg('')
    mutation.mutate({
      ...form,
      transport_order: form.transport_order ? Number(form.transport_order) : undefined,
    })
  }

  const columns = [
    { key: 'transport_number', label: '운송번호',  render: (v, row) => v ?? row.transport_order ?? '-' },
    { key: 'location',         label: '현재위치' },
    { key: 'status_note',      label: '상태메모' },
    { key: 'tracked_at',       label: '추적시간', render: v => v?.slice(0, 16) ?? '-' },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5">
      {/* 좌측 폼 */}
      <div style={S.formPanel}>
        <p style={S.formTitle}>추적 등록</p>
        <form onSubmit={handleSubmit}>
          <div style={S.field}>
            <label style={S.label}>운송오더</label>
            <select style={S.input} value={form.transport_order} onChange={e => set('transport_order', e.target.value)}>
              <option value="">-- 선택 --</option>
              {orders.map(o => (
                <option key={o.id} value={o.id}>{o.transport_number} - {o.origin}→{o.destination}</option>
              ))}
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>현재 위치 *</label>
            <input style={S.input} value={form.location} onChange={e => set('location', e.target.value)} placeholder="예: 부산항 대기" />
          </div>
          <div style={S.field}>
            <label style={S.label}>상태 메모</label>
            <input style={S.input} value={form.status_note} onChange={e => set('status_note', e.target.value)} placeholder="상태 설명" />
          </div>
          <div style={S.field}>
            <label style={S.label}>추적 시각</label>
            <input style={S.input} type="datetime-local" value={form.tracked_at} onChange={e => set('tracked_at', e.target.value)} />
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

// ─── 메인 ─────────────────────────────────────────────────────
export default function TmPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: dashboardData } = useQuery({
    queryKey: ['tm-dashboard'],
    queryFn: () => api.get('/tm/orders/dashboard/').then(r => r.data).catch(() => null),
  })
  const { data: ordersData } = useQuery({
    queryKey: ['tm-orders'],
    queryFn: () => api.get('/tm/orders/').then(r => r.data).catch(() => []),
  })

  const orders     = getList(ordersData)
  const inTransit  = dashboardData?.in_progress ?? orders.filter(o => o.status === 'in_transit').length
  const completed  = dashboardData?.completed   ?? orders.filter(o => o.status === 'delivered').length
  const costs      = orders.map(o => Number(o.freight_cost) || 0).filter(v => v > 0)
  const avgFreight = dashboardData?.avg_freight ??
    (costs.length > 0 ? Math.round(costs.reduce((s, v) => s + v, 0) / costs.length) : '-')

  const TAB_COMPONENTS = [TransportOrderTab, CarrierTab, TrackingTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🚢</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>TM 운송관리</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Transportation Management — 운송계획·운송사·운임을 통합 관리합니다.</div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="진행 중 운송" value={ordersData ? inTransit  : '-'} unit="건" />
        <KpiCard label="완료"         value={ordersData ? completed  : '-'} unit="건" />
        <KpiCard label="평균 운임"    value={ordersData ? (typeof avgFreight === 'number' ? avgFreight.toLocaleString() : avgFreight) : '-'} unit="원" />
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
