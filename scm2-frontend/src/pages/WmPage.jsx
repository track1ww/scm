import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['창고', '재고', '재고이동이력', 'Bin 관리', '재고실사']

// ─── 공통 헬퍼 ────────────────────────────────────────────────
function getList(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  return []
}

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

// ─── 창고 탭 ──────────────────────────────────────────────────
function WarehouseTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    warehouse_code: '', warehouse_name: '',
    warehouse_type: '원자재', location: '', is_active: true,
  }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['wm-warehouses', page],
    queryFn: () => api.get(`/wm/warehouses/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      warehouse_code: row.warehouse_code ?? '',
      warehouse_name: row.warehouse_name ?? '',
      warehouse_type: row.warehouse_type ?? '원자재',
      location: row.location ?? '',
      is_active: row.is_active ?? true,
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/wm/warehouses/${editId}/`, payload).then(r => r.data)
        : api.post('/wm/warehouses/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wm-warehouses'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/wm/warehouses/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wm-warehouses'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.warehouse_code.trim()) { setGlobalError('창고코드는 필수입니다.'); return }
    if (!form.warehouse_name.trim()) { setGlobalError('창고명은 필수입니다.'); return }
    saveMutation.mutate(form)
  }

  const columns = [
    { key: 'warehouse_code', label: '창고코드' },
    { key: 'warehouse_name', label: '창고명' },
    { key: 'warehouse_type', label: '유형' },
    { key: 'location', label: '위치' },
    { key: 'is_active', label: '활성', render: v => v ? '활성' : '비활성' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: `창고 "${row.warehouse_name}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
      <div className="flex flex-col md:flex-row gap-4 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>창고코드 *</label>
          <input style={S.input} value={form.warehouse_code}
            onChange={e => setForm(f => ({ ...f, warehouse_code: e.target.value }))}
            placeholder="예: WH001" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>창고명 *</label>
          <input style={S.input} value={form.warehouse_name}
            onChange={e => setForm(f => ({ ...f, warehouse_name: e.target.value }))}
            placeholder="예: 원자재 창고" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>창고유형</label>
          <select style={S.input} value={form.warehouse_type}
            onChange={e => setForm(f => ({ ...f, warehouse_type: e.target.value }))}>
            <option value="원자재">원자재</option>
            <option value="완제품">완제품</option>
            <option value="반제품">반제품</option>
            <option value="기타">기타</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>위치</label>
          <input style={S.input} value={form.location}
            onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
            placeholder="예: 경기도 안산시" />
        </div>
        <div style={S.formRow}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
            <input type="checkbox" checked={form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
            활성 상태
          </label>
        </div>
      </FormPanel>
      <div style={{ flex: 1 }}>
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 재고 탭 ──────────────────────────────────────────────────
function InventoryTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    item_code: '', warehouse: '', bin_code: '',
    stock_qty: '', min_stock: '', lot_number: '',
  }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')

  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['wm-inventory', page],
    queryFn: () => api.get(`/wm/inventory/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: whData } = useQuery({
    queryKey: ['wm-warehouses'],
    queryFn: () => api.get('/wm/warehouses/').then(r => r.data).catch(() => []),
  })
  const rows = getList(data)
  const warehouses = getList(whData)

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      item_code: row.item_code ?? '',
      warehouse: (typeof row.warehouse === 'object' ? row.warehouse?.id : row.warehouse) ?? '',
      bin_code: row.bin_code ?? '',
      stock_qty: row.stock_qty ?? '',
      min_stock: row.min_stock ?? '',
      lot_number: row.lot_number ?? '',
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/wm/inventory/${editId}/`, payload).then(r => r.data)
        : api.post('/wm/inventory/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wm-inventory'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.item_code.trim()) { setGlobalError('품목코드는 필수입니다.'); return }
    const payload = {
      ...form,
      stock_qty: form.stock_qty === '' ? 0 : parseInt(form.stock_qty, 10),
      min_stock: form.min_stock === '' ? 0 : parseInt(form.min_stock, 10),
    }
    if (!payload.warehouse) delete payload.warehouse
    if (!payload.bin_code) delete payload.bin_code
    if (!payload.lot_number) delete payload.lot_number
    saveMutation.mutate(payload)
  }

  const columns = [
    { key: 'item_code', label: '품목코드' },
    { key: 'warehouse', label: '창고', render: (v, row) => (typeof v === 'object' ? v?.name : v) ?? row.warehouse_name ?? '-' },
    { key: 'bin_code', label: '빈코드' },
    { key: 'stock_qty', label: '실재고' },
    { key: 'min_stock', label: '최소재고' },
    { key: 'lot_number', label: '로트번호' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-4 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>품목코드 *</label>
          <input style={S.input} value={form.item_code}
            onChange={e => setForm(f => ({ ...f, item_code: e.target.value }))}
            placeholder="예: ITEM-001" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>창고</label>
          <select style={S.input} value={form.warehouse}
            onChange={e => setForm(f => ({ ...f, warehouse: e.target.value }))}>
            <option value="">-- 선택 --</option>
            {warehouses.map(w => (
              <option key={w.id} value={w.id}>{w.warehouse_name} ({w.warehouse_code})</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>빈코드</label>
          <input style={S.input} value={form.bin_code}
            onChange={e => setForm(f => ({ ...f, bin_code: e.target.value }))}
            placeholder="예: A-01-01" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>실재고</label>
          <input style={S.input} type="number" min="0" value={form.stock_qty}
            onChange={e => setForm(f => ({ ...f, stock_qty: e.target.value === '' ? '' : Number(e.target.value) }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>최소재고</label>
          <input style={S.input} type="number" min="0" value={form.min_stock}
            onChange={e => setForm(f => ({ ...f, min_stock: e.target.value === '' ? '' : Number(e.target.value) }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>로트번호</label>
          <input style={S.input} value={form.lot_number}
            onChange={e => setForm(f => ({ ...f, lot_number: e.target.value }))}
            placeholder="예: LOT-20260101" />
        </div>
      </FormPanel>
      <div style={{ flex: 1 }}>
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    </>
  )
}

// ─── 재고이동이력 탭 (읽기전용) ────────────────────────────────
function MovementTab() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['wm-movements', page],
    queryFn: () => api.get(`/wm/movements/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)
  const columns = [
    { key: 'movement_type', label: '이동유형' },
    { key: 'material_code', label: '품목코드' },
    { key: 'quantity', label: '수량' },
    { key: 'reference_document', label: '참조문서' },
    { key: 'source_module', label: '출처모듈' },
    { key: 'created_at', label: '일시' },
  ]

  return (
    <div style={{ padding: 20 }}>
      <DataTable isLoading={isLoading} rows={rows} columns={columns} />
      <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
    </div>
  )
}

// ─── Bin 관리 탭 ──────────────────────────────────────────────
function BinTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    warehouse: '', bin_code: '',
    aisle: '', row: '', column: '',
    max_capacity: '', is_active: true,
  }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['wm-bins', page],
    queryFn: () => api.get(`/wm/bins/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: whData } = useQuery({
    queryKey: ['wm-warehouses'],
    queryFn: () => api.get('/wm/warehouses/').then(r => r.data).catch(() => []),
  })
  const rows = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : [])
  const warehouses = Array.isArray(whData) ? whData : (Array.isArray(whData?.results) ? whData.results : [])

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      warehouse: (typeof row.warehouse === 'object' ? row.warehouse?.id : row.warehouse) ?? '',
      bin_code: row.bin_code ?? '',
      aisle: row.aisle ?? '',
      row: row.row ?? '',
      column: row.column ?? '',
      max_capacity: row.max_capacity ?? '',
      is_active: row.is_active ?? true,
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/wm/bins/${editId}/`, payload).then(r => r.data)
        : api.post('/wm/bins/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wm-bins'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/wm/bins/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wm-bins'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.warehouse) { setGlobalError('창고를 선택해주세요.'); return }
    if (!form.bin_code.trim()) { setGlobalError('Bin 코드는 필수입니다.'); return }
    const payload = { ...form }
    if (!payload.aisle) delete payload.aisle
    if (!payload.row) delete payload.row
    if (!payload.column) delete payload.column
    if (!payload.max_capacity) delete payload.max_capacity
    saveMutation.mutate(payload)
  }

  const columns = [
    { key: 'bin_code', label: 'Bin 코드' },
    {
      key: 'warehouse', label: '창고명',
      render: (v, row) => (typeof v === 'object' && v ? v.warehouse_name : row.warehouse_name ?? v ?? '-'),
    },
    {
      key: '_location', label: '통로-행-열',
      render: (_, row) => {
        const parts = [row.aisle, row.row, row.column].filter(Boolean)
        return parts.length > 0 ? parts.join('-') : '-'
      },
    },
    { key: 'max_capacity', label: '최대용량', render: v => v != null ? Number(v).toLocaleString() : '-' },
    { key: 'is_active', label: '활성', render: v => v ? '활성' : '비활성' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: `Bin "${row.bin_code}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
      <div className="flex flex-col md:flex-row gap-4 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>창고 *</label>
          <select style={S.input} value={form.warehouse}
            onChange={e => setForm(f => ({ ...f, warehouse: e.target.value }))}>
            <option value="">-- 창고 선택 --</option>
            {warehouses.map(w => (
              <option key={w.id} value={w.id}>{w.warehouse_name} ({w.warehouse_code})</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>Bin 코드 *</label>
          <input style={S.input} value={form.bin_code}
            onChange={e => setForm(f => ({ ...f, bin_code: e.target.value }))}
            placeholder="예: A-01-01" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>통로</label>
          <input style={S.input} value={form.aisle}
            onChange={e => setForm(f => ({ ...f, aisle: e.target.value }))}
            placeholder="예: A" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
          <div>
            <label style={S.label}>행</label>
            <input style={S.input} value={form.row}
              onChange={e => setForm(f => ({ ...f, row: e.target.value }))}
              placeholder="예: 01" />
          </div>
          <div>
            <label style={S.label}>열</label>
            <input style={S.input} value={form.column}
              onChange={e => setForm(f => ({ ...f, column: e.target.value }))}
              placeholder="예: 01" />
          </div>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>최대용량</label>
          <input style={S.input} type="number" value={form.max_capacity}
            onChange={e => setForm(f => ({ ...f, max_capacity: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
            <input type="checkbox" checked={form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
            활성 상태
          </label>
        </div>
      </FormPanel>
      <div style={{ flex: 1 }}>
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 재고실사 탭 ───────────────────────────────────────────────
function CycleCountTab() {
  const queryClient = useQueryClient()
  const today = () => new Date().toISOString().slice(0, 10)
  const initialForm = {
    count_number: '', warehouse: '',
    count_date: today(), assigned_to: '',
  }
  const [form, setForm] = useState(initialForm)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const [editId, setEditId] = useState(null)
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['wm-cycle-counts', page],
    queryFn: () => api.get(`/wm/cycle-counts/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: whData } = useQuery({
    queryKey: ['wm-warehouses'],
    queryFn: () => api.get('/wm/warehouses/').then(r => r.data).catch(() => []),
  })
  const rows = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : [])
  const warehouses = Array.isArray(whData) ? whData : (Array.isArray(whData?.results) ? whData.results : [])

  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/wm/cycle-counts/${editId}/`, payload).then(r => r.data)
        : api.post('/wm/cycle-counts/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wm-cycle-counts'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const completeMutation = useMutation({
    mutationFn: id => api.post(`/wm/cycle-counts/${id}/complete/`).then(r => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['wm-cycle-counts'] }); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.warehouse) { setGlobalError('창고를 선택해주세요.'); return }
    if (!form.count_date) { setGlobalError('실사일은 필수입니다.'); return }
    const payload = { ...form }
    if (!payload.count_number) delete payload.count_number
    if (!payload.assigned_to) delete payload.assigned_to
    saveMutation.mutate(payload)
  }

  const STATUS_CC = {
    draft:       { label: '초안',     bg: '#f5f5f3', color: '#6b6b6b' },
    in_progress: { label: '진행중',   bg: '#e3f2fd', color: '#1565c0' },
    completed:   { label: '완료',     bg: '#e8f5e9', color: '#2e7d32' },
    cancelled:   { label: '취소',     bg: '#fdecea', color: '#d44c47' },
  }

  const columns = [
    { key: 'count_number', label: '실사번호' },
    {
      key: 'warehouse', label: '창고',
      render: (v, row) => (typeof v === 'object' && v ? v.warehouse_name : row.warehouse_name ?? v ?? '-'),
    },
    { key: 'count_date', label: '실사일' },
    {
      key: 'status', label: '상태',
      render: v => {
        const s = STATUS_CC[v] ?? { label: v ?? '-', bg: '#f5f5f3', color: '#6b6b6b' }
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
    { key: 'assigned_to', label: '담당자', render: v => v ?? '-' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => {
        const canComplete = row.status === 'draft' || row.status === 'in_progress'
        if (!canComplete) return null
        return (
          <button
            style={{
              background: '#f0fff4', color: '#2d7a2d', border: '1px solid #b5e0b5',
              borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer',
            }}
            onClick={() => requestConfirm({ message: `실사 "${row.count_number || row.id}"을(를) 완료 처리하시겠습니까?`, confirmLabel: '완료처리', danger: false, onConfirm: () => completeMutation.mutate(row.id) })}
            disabled={completeMutation.isPending}
          >
            완료 처리
          </button>
        )
      },
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 20px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-4 p-3 md:p-5 items-start">
      <FormPanel
        editMode={!!editId}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label style={S.label}>실사번호 (자동생성 가능)</label>
          <input style={S.input} value={form.count_number}
            onChange={e => setForm(f => ({ ...f, count_number: e.target.value }))}
            placeholder="예: CC-2026-001" />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>창고 *</label>
          <select style={S.input} value={form.warehouse}
            onChange={e => setForm(f => ({ ...f, warehouse: e.target.value }))}>
            <option value="">-- 창고 선택 --</option>
            {warehouses.map(w => (
              <option key={w.id} value={w.id}>{w.warehouse_name} ({w.warehouse_code})</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label style={S.label}>실사일 *</label>
          <input style={S.input} type="date" value={form.count_date}
            onChange={e => setForm(f => ({ ...f, count_date: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label style={S.label}>담당자</label>
          <input style={S.input} value={form.assigned_to}
            onChange={e => setForm(f => ({ ...f, assigned_to: e.target.value }))}
            placeholder="담당자 이름" />
        </div>
      </FormPanel>
      <div style={{ flex: 1 }}>
        <DataTable isLoading={isLoading} rows={rows} columns={columns} />
        <Pagination currentPage={page} totalPages={data?.total_pages} onPageChange={setPage} />
      </div>
    </div>
    <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function WmPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: warehousesData } = useQuery({
    queryKey: ['wm-warehouses'],
    queryFn: () => api.get('/wm/warehouses/').then(r => r.data).catch(() => []),
  })
  const { data: inventoryData } = useQuery({
    queryKey: ['wm-inventory'],
    queryFn: () => api.get('/wm/inventory/').then(r => r.data).catch(() => []),
  })

  const warehouses = getList(warehousesData)
  const inventory  = getList(inventoryData)
  const shortage   = inventory.filter(i => i.stock_qty != null && i.min_stock != null && Number(i.stock_qty) < Number(i.min_stock))

  const TAB_COMPONENTS = [WarehouseTab, InventoryTab, MovementTab, BinTab, CycleCountTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: '0 0 6px' }}>WM 창고관리</h1>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Warehouse Management — 창고·재고·이동 이력을 통합 관리합니다.</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="전체 창고"  value={warehousesData ? warehouses.length : '-'} unit="개소" />
        <KpiCard label="총 품목 수" value={inventoryData  ? inventory.length  : '-'} unit="종" />
        <KpiCard label="부족 재고"  value={inventoryData  ? shortage.length   : '-'} unit="건" />
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
