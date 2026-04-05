import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['부서', '직원', '급여', '근태 관리', '휴가 관리']

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
  btnApprove: {
    background: '#e8f5e9', color: '#2e7d32', border: '1px solid #b2dfdb',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer', marginRight: 4,
  },
}

// ─── 좌측 폼 래퍼 ─────────────────────────────────────────────
function FormPanel({ children, onSubmit, onCancel, isPending, editMode }) {
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
  active:    { label: '재직',    bg: '#e8f5e9', color: '#2e7d32' },
  inactive:  { label: '퇴직',    bg: '#fdecea', color: '#d44c47' },
  leave:     { label: '휴직',    bg: '#fff8e1', color: '#b45309' },
  draft:     { label: '초안',    bg: '#f5f5f3', color: '#6b6b6b' },
  paid:      { label: '지급완료', bg: '#e3f2fd', color: '#1565c0' },
  pending:   { label: '대기',    bg: '#fff8e1', color: '#b45309' },
  approved:  { label: '승인',    bg: '#e8f5e9', color: '#2e7d32' },
  rejected:  { label: '반려',    bg: '#fdecea', color: '#d44c47' },
  cancelled: { label: '취소',    bg: '#f5f5f3', color: '#6b6b6b' },
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

// ─── 부서 탭 ──────────────────────────────────────────────────
function DepartmentTab() {
  const queryClient = useQueryClient()
  const initialForm = { dept_code: '', dept_name: '', is_active: true }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['hr-departments', page],
    queryFn: () => api.get(`/hr/departments/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const rows = getList(data)

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({ dept_code: row.dept_code ?? '', dept_name: row.dept_name ?? '', is_active: row.is_active ?? true })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/hr/departments/${editId}/`, payload).then(r => r.data)
        : api.post('/hr/departments/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-departments'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/hr/departments/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-departments'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.dept_code.trim()) { setGlobalError('부서코드는 필수입니다.'); return }
    if (!form.dept_name.trim()) { setGlobalError('부서명은 필수입니다.'); return }
    saveMutation.mutate(form)
  }

  const columns = [
    { key: 'dept_code', label: '부서코드' },
    { key: 'dept_name', label: '부서명' },
    { key: 'is_active', label: '활성', render: v => v ? '활성' : '비활성' },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: `부서 "${row.dept_name}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
          <label htmlFor="hr-dept-dept-code" style={S.label}>부서코드 *</label>
          <input id="hr-dept-dept-code" name="dept_code" style={S.input} value={form.dept_code}
            onChange={e => setForm(f => ({ ...f, dept_code: e.target.value }))}
            placeholder="예: D001" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-dept-dept-name" style={S.label}>부서명 *</label>
          <input id="hr-dept-dept-name" name="dept_name" style={S.input} value={form.dept_name}
            onChange={e => setForm(f => ({ ...f, dept_name: e.target.value }))}
            placeholder="예: 개발팀" />
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

// ─── 직원 탭 ──────────────────────────────────────────────────
function EmployeeTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    emp_code: '', name: '', dept: '', position: '',
    employment_type: '정규직', hire_date: '', base_salary: '', email: '', phone: '',
  }
  const [form, setForm] = useState(initialForm)
  const [editId, setEditId] = useState(null)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['hr-employees', page],
    queryFn: () => api.get(`/hr/employees/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: deptData } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: () => api.get('/hr/departments/').then(r => r.data).catch(() => []),
  })
  const rows = getList(data)
  const depts = getList(deptData)

  const handleEdit = row => {
    clearErrors(); setSuccessMsg(''); setGlobalError('')
    setForm({
      emp_code: row.emp_code ?? '',
      name: row.name ?? '',
      dept: (typeof row.dept === 'object' ? row.dept?.id : row.dept) ?? '',
      position: row.position ?? '',
      employment_type: row.employment_type ?? '정규직',
      hire_date: row.hire_date ?? '',
      base_salary: row.base_salary ?? '',
      email: row.email ?? '',
      phone: row.phone ?? '',
    })
    setEditId(row.id)
  }
  const handleCancel = () => { setForm(initialForm); setEditId(null) }

  const saveMutation = useMutation({
    mutationFn: payload =>
      editId
        ? api.put(`/hr/employees/${editId}/`, payload).then(r => r.data)
        : api.post('/hr/employees/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-employees'] })
      setForm(initialForm)
      setEditId(null)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/hr/employees/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-employees'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.emp_code.trim()) { setGlobalError('사원코드는 필수입니다.'); return }
    if (!form.name.trim()) { setGlobalError('이름은 필수입니다.'); return }
    const payload = { ...form }
    if (!payload.dept) delete payload.dept
    if (!payload.base_salary) delete payload.base_salary
    saveMutation.mutate(payload)
  }

  const columns = [
    { key: 'emp_code', label: '사원코드' },
    { key: 'name', label: '이름' },
    { key: 'dept', label: '부서', render: (v, row) => (typeof v === 'object' ? v?.name : v) ?? row.dept_name ?? '-' },
    { key: 'position', label: '직급' },
    { key: 'employment_type', label: '고용형태' },
    { key: 'hire_date', label: '입사일' },
    { key: 'status', label: '상태', render: v => <StatusBadge status={v} /> },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <button style={S.btnEdit} onClick={() => handleEdit(row)}>수정</button>
          <button style={S.btnDel} onClick={() => requestConfirm({ message: `직원 "${row.name}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
          <label htmlFor="hr-emp-emp-code" style={S.label}>사원코드 *</label>
          <input id="hr-emp-emp-code" name="emp_code" style={S.input} value={form.emp_code}
            onChange={e => setForm(f => ({ ...f, emp_code: e.target.value }))}
            placeholder="예: E001" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-name" style={S.label}>이름 *</label>
          <input id="hr-emp-name" name="name" style={S.input} value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="홍길동" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-dept" style={S.label}>부서</label>
          <select id="hr-emp-dept" name="dept" style={S.input} value={form.dept}
            onChange={e => setForm(f => ({ ...f, dept: e.target.value }))}>
            <option value="">-- 선택 --</option>
            {depts.map(d => <option key={d.id} value={d.id}>{d.dept_name}</option>)}
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-position" style={S.label}>직급</label>
          <input id="hr-emp-position" name="position" style={S.input} value={form.position}
            onChange={e => setForm(f => ({ ...f, position: e.target.value }))}
            placeholder="예: 대리" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-employment-type" style={S.label}>고용형태</label>
          <select id="hr-emp-employment-type" name="employment_type" style={S.input} value={form.employment_type}
            onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}>
            <option value="정규직">정규직</option>
            <option value="계약직">계약직</option>
            <option value="파트타임">파트타임</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-hire-date" style={S.label}>입사일</label>
          <input id="hr-emp-hire-date" name="hire_date" style={S.input} type="date" value={form.hire_date}
            onChange={e => setForm(f => ({ ...f, hire_date: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-base-salary" style={S.label}>기본급</label>
          <input id="hr-emp-base-salary" name="base_salary" style={S.input} type="number" value={form.base_salary}
            onChange={e => setForm(f => ({ ...f, base_salary: e.target.value }))}
            placeholder="3000000" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-email" style={S.label}>이메일</label>
          <input id="hr-emp-email" name="email" style={S.input} type="email" value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            placeholder="example@company.com" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-emp-phone" style={S.label}>전화번호</label>
          <input id="hr-emp-phone" name="phone" style={S.input} value={form.phone}
            onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
            placeholder="010-0000-0000" />
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

// ─── 급여 탭 ──────────────────────────────────────────────────
function PayrollTab() {
  const queryClient = useQueryClient()
  const initialForm = {
    employee: '', pay_year: new Date().getFullYear(), pay_month: new Date().getMonth() + 1,
    base_salary: '', overtime_pay: '', bonus: '', income_tax: '', net_pay: '',
  }
  const [form, setForm] = useState(initialForm)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['hr-payrolls', page],
    queryFn: () => api.get(`/hr/payrolls/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: empData } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: () => api.get('/hr/employees/').then(r => r.data).catch(() => []),
  })
  const rows = getList(data)
  const employees = getList(empData)

  const saveMutation = useMutation({
    mutationFn: payload => api.post('/hr/payrolls/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-payrolls'] })
      setForm(initialForm)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/hr/payrolls/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-payrolls'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.employee) { setGlobalError('직원을 선택해주세요.'); return }
    if (!form.pay_year) { setGlobalError('년도는 필수입니다.'); return }
    if (!form.pay_month) { setGlobalError('월은 필수입니다.'); return }
    saveMutation.mutate(form)
  }

  const columns = [
    { key: 'payroll_number', label: '급여번호' },
    { key: 'employee', label: '직원', render: (v, row) => (typeof v === 'object' ? v?.name : v) ?? row.employee_name ?? '-' },
    { key: 'pay_year', label: '년' },
    { key: 'pay_month', label: '월' },
    { key: 'base_salary', label: '기본급', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'net_pay', label: '실지급액', render: v => v != null ? Number(v).toLocaleString() + '원' : '-' },
    { key: 'state', label: '상태', render: v => <StatusBadge status={v} /> },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <button style={S.btnDel} onClick={() => requestConfirm({ message: '이 급여 기록을 삭제하시겠습니까?', onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
        editMode={false}
        onSubmit={handleSubmit}
        isPending={saveMutation.isPending}
      >
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-employee" style={S.label}>직원 *</label>
          <select id="hr-payroll-employee" name="employee" style={S.input} value={form.employee}
            onChange={e => setForm(f => ({ ...f, employee: e.target.value }))}>
            <option value="">-- 선택 --</option>
            {employees.map(e => (
              <option key={e.id} value={e.id}>{e.name} ({e.emp_code})</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-pay-year" style={S.label}>년도 *</label>
          <input id="hr-payroll-pay-year" name="pay_year" style={S.input} type="number" value={form.pay_year} min={2000} max={2099}
            onChange={e => setForm(f => ({ ...f, pay_year: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-pay-month" style={S.label}>월 *</label>
          <input id="hr-payroll-pay-month" name="pay_month" style={S.input} type="number" value={form.pay_month} min={1} max={12}
            onChange={e => setForm(f => ({ ...f, pay_month: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-base-salary" style={S.label}>기본급</label>
          <input id="hr-payroll-base-salary" name="base_salary" style={S.input} type="number" value={form.base_salary}
            onChange={e => setForm(f => ({ ...f, base_salary: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-overtime-pay" style={S.label}>연장근로수당</label>
          <input id="hr-payroll-overtime-pay" name="overtime_pay" style={S.input} type="number" value={form.overtime_pay}
            onChange={e => setForm(f => ({ ...f, overtime_pay: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-bonus" style={S.label}>보너스</label>
          <input id="hr-payroll-bonus" name="bonus" style={S.input} type="number" value={form.bonus}
            onChange={e => setForm(f => ({ ...f, bonus: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-income-tax" style={S.label}>소득세</label>
          <input id="hr-payroll-income-tax" name="income_tax" style={S.input} type="number" value={form.income_tax}
            onChange={e => setForm(f => ({ ...f, income_tax: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-payroll-net-pay" style={S.label}>실지급액</label>
          <input id="hr-payroll-net-pay" name="net_pay" style={S.input} type="number" value={form.net_pay}
            onChange={e => setForm(f => ({ ...f, net_pay: e.target.value }))}
            placeholder="0" />
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

// ─── 근태 관리 탭 ─────────────────────────────────────────────
const ATTENDANCE_WORK_TYPES = ['정상', '지각', '조퇴', '결근', '휴일근무', '야근']

const ATTENDANCE_INIT = {
  employee: '', work_date: '', check_in: '', check_out: '',
  work_type: '정상', overtime_hours: '',
}

function AttendanceTab() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(ATTENDANCE_INIT)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['hr-attendances', page],
    queryFn: () => api.get(`/hr/attendances/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: empData } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: () => api.get('/hr/employees/').then(r => r.data).catch(() => []),
  })

  const rows      = getList(data)
  const employees = getList(empData)

  const saveMutation = useMutation({
    mutationFn: payload => api.post('/hr/attendances/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-attendances'] })
      setForm(ATTENDANCE_INIT)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/hr/attendances/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-attendances'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.employee)   { setGlobalError('직원을 선택해주세요.'); return }
    if (!form.work_date)  { setGlobalError('근무일자는 필수입니다.'); return }
    const payload = {
      ...form,
      overtime_hours: form.overtime_hours !== '' ? Number(form.overtime_hours) : null,
    }
    if (!payload.check_in)  delete payload.check_in
    if (!payload.check_out) delete payload.check_out
    if (payload.overtime_hours == null) delete payload.overtime_hours
    saveMutation.mutate(payload)
  }

  const columns = [
    {
      key: 'employee', label: '직원명',
      render: (v, row) => (typeof v === 'object' ? v?.name : v) ?? row.employee_name ?? '-',
    },
    { key: 'work_date',      label: '근무일' },
    { key: 'work_type',      label: '근무유형' },
    { key: 'check_in',       label: '출근시간', render: v => v ?? '-' },
    { key: 'check_out',      label: '퇴근시간', render: v => v ?? '-' },
    {
      key: 'overtime_hours', label: '초과근무(h)',
      render: v => v != null ? `${v}h` : '-',
    },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <button style={S.btnDel} onClick={() => requestConfirm({ message: '이 근태 기록을 삭제하시겠습니까?', onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
      <FormPanel editMode={false} onSubmit={handleSubmit} isPending={saveMutation.isPending}>
        <div style={S.formRow}>
          <label htmlFor="hr-attend-employee" style={S.label}>직원 *</label>
          <select id="hr-attend-employee" name="employee" style={S.input} value={form.employee}
            onChange={e => setForm(f => ({ ...f, employee: e.target.value }))}>
            <option value="">-- 선택 --</option>
            {employees.map(emp => (
              <option key={emp.id} value={emp.id}>{emp.name} ({emp.emp_code})</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-attend-work-date" style={S.label}>근무일자 *</label>
          <input id="hr-attend-work-date" name="work_date" style={S.input} type="date" value={form.work_date}
            onChange={e => setForm(f => ({ ...f, work_date: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-attend-check-in" style={S.label}>출근시간</label>
          <input id="hr-attend-check-in" name="check_in" style={S.input} type="time" value={form.check_in}
            onChange={e => setForm(f => ({ ...f, check_in: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-attend-check-out" style={S.label}>퇴근시간</label>
          <input id="hr-attend-check-out" name="check_out" style={S.input} type="time" value={form.check_out}
            onChange={e => setForm(f => ({ ...f, check_out: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-attend-work-type" style={S.label}>근무유형</label>
          <select id="hr-attend-work-type" name="work_type" style={S.input} value={form.work_type}
            onChange={e => setForm(f => ({ ...f, work_type: e.target.value }))}>
            {ATTENDANCE_WORK_TYPES.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-attend-overtime-hours" style={S.label}>초과근무시간 (h)</label>
          <input id="hr-attend-overtime-hours" name="overtime_hours" style={S.input} type="number" min={0} step={0.5} value={form.overtime_hours}
            onChange={e => setForm(f => ({ ...f, overtime_hours: e.target.value }))}
            placeholder="0" />
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

// ─── 휴가 관리 탭 ─────────────────────────────────────────────
const LEAVE_TYPES = ['연차', '반차', '병가', '특별휴가', '무급휴가']

const LEAVE_INIT = {
  employee: '', leave_type: '연차', start_date: '', end_date: '', days: '', reason: '',
}

function calcDays(start, end) {
  if (!start || !end) return ''
  const s = new Date(start)
  const e = new Date(end)
  if (isNaN(s) || isNaN(e) || e < s) return ''
  return String(Math.round((e - s) / 86400000) + 1)
}

function LeaveTab() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(LEAVE_INIT)
  const { errors, globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['hr-leaves', page],
    queryFn: () => api.get(`/hr/leaves/?page=${page}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })
  const { data: empData } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: () => api.get('/hr/employees/').then(r => r.data).catch(() => []),
  })

  const rows      = getList(data)
  const employees = getList(empData)

  const handleDateChange = (field, value) => {
    setForm(f => {
      const next = { ...f, [field]: value }
      next.days = calcDays(
        field === 'start_date' ? value : f.start_date,
        field === 'end_date'   ? value : f.end_date,
      )
      return next
    })
  }

  const saveMutation = useMutation({
    mutationFn: payload => api.post('/hr/leaves/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-leaves'] })
      setForm(LEAVE_INIT)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const approveMutation = useMutation({
    mutationFn: id => api.post(`/hr/leaves/${id}/approve/`).then(r => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['hr-leaves'] }); setSuccessMsg('처리되었습니다.') },
    onError: (err) => handleApiError(err),
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/hr/leaves/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-leaves'] }),
    onError: (err) => handleApiError(err),
  })

  const handleSubmit = () => {
    if (!form.employee)   { setGlobalError('직원을 선택해주세요.'); return }
    if (!form.start_date) { setGlobalError('시작일은 필수입니다.'); return }
    if (!form.end_date)   { setGlobalError('종료일은 필수입니다.'); return }
    const payload = {
      ...form,
      days: form.days !== '' ? Number(form.days) : undefined,
    }
    if (!payload.reason) delete payload.reason
    if (payload.days == null) delete payload.days
    saveMutation.mutate(payload)
  }

  const columns = [
    {
      key: 'employee', label: '직원명',
      render: (v, row) => (typeof v === 'object' ? v?.name : v) ?? row.employee_name ?? '-',
    },
    { key: 'leave_type', label: '휴가유형' },
    { key: 'start_date', label: '시작일' },
    { key: 'end_date',   label: '종료일' },
    { key: 'days',       label: '일수', render: v => v != null ? `${v}일` : '-' },
    { key: 'status',     label: '상태', render: v => <StatusBadge status={v} /> },
    {
      key: '_actions', label: '작업',
      render: (_, row) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          {row.status === 'pending' && (
            <button style={S.btnApprove} onClick={() => requestConfirm({ message: `"${row.employee_name ?? row.employee?.name ?? '해당 직원'}"의 휴가를 승인하시겠습니까?`, confirmLabel: '승인', danger: false, onConfirm: () => approveMutation.mutate(row.id) })}>승인</button>
          )}
          <button style={S.btnDel} onClick={() => requestConfirm({ message: '이 휴가 기록을 삭제하시겠습니까?', onConfirm: () => deleteMutation.mutate(row.id) })}>삭제</button>
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
      <FormPanel editMode={false} onSubmit={handleSubmit} isPending={saveMutation.isPending}>
        <div style={S.formRow}>
          <label htmlFor="hr-leave-employee" style={S.label}>직원 *</label>
          <select id="hr-leave-employee" name="employee" style={S.input} value={form.employee}
            onChange={e => setForm(f => ({ ...f, employee: e.target.value }))}>
            <option value="">-- 선택 --</option>
            {employees.map(emp => (
              <option key={emp.id} value={emp.id}>{emp.name} ({emp.emp_code})</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-leave-leave-type" style={S.label}>휴가유형</label>
          <select id="hr-leave-leave-type" name="leave_type" style={S.input} value={form.leave_type}
            onChange={e => setForm(f => ({ ...f, leave_type: e.target.value }))}>
            {LEAVE_TYPES.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-leave-start-date" style={S.label}>시작일 *</label>
          <input id="hr-leave-start-date" name="start_date" style={S.input} type="date" value={form.start_date}
            onChange={e => handleDateChange('start_date', e.target.value)} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-leave-end-date" style={S.label}>종료일 *</label>
          <input id="hr-leave-end-date" name="end_date" style={S.input} type="date" value={form.end_date}
            onChange={e => handleDateChange('end_date', e.target.value)} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-leave-days" style={S.label}>일수 (자동계산)</label>
          <input
            id="hr-leave-days"
            name="days"
            style={{ ...S.input, background: '#f5f5f3', color: '#6b6b6b' }}
            type="number" min={1}
            value={form.days}
            readOnly
            placeholder="시작일·종료일 입력 시 자동계산"
          />
        </div>
        <div style={S.formRow}>
          <label htmlFor="hr-leave-reason" style={S.label}>사유</label>
          <input id="hr-leave-reason" name="reason" style={S.input} value={form.reason}
            onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
            placeholder="휴가 사유를 입력하세요" />
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
export default function HrPage() {
  const [activeTab, setActiveTab] = useState(0)

  const { data: employeesData } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: () => api.get('/hr/employees/').then(r => r.data).catch(() => []),
  })
  const { data: payrollsData } = useQuery({
    queryKey: ['hr-payrolls'],
    queryFn: () => api.get('/hr/payrolls/').then(r => r.data).catch(() => []),
  })

  const employees = getList(employeesData)
  const payrolls  = getList(payrollsData)

  const now       = new Date()
  const thisYear  = now.getFullYear()
  const thisMonth = now.getMonth() + 1
  const active    = employees.filter(e => e.status === 'active')
  const monthPayTotal = payrolls
    .filter(p => Number(p.pay_year) === thisYear && Number(p.pay_month) === thisMonth)
    .reduce((sum, p) => sum + (Number(p.net_pay) || 0), 0)

  const TAB_COMPONENTS = [DepartmentTab, EmployeeTab, PayrollTab, AttendanceTab, LeaveTab]
  const ActiveContent = TAB_COMPONENTS[activeTab]

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: '0 0 6px' }}>HR 인사관리</h1>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Human Resources — 부서·직원·급여를 통합 관리합니다.</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="전체 직원"   value={employeesData ? employees.length               : '-'} unit="명" />
        <KpiCard label="재직 중"     value={employeesData ? active.length                  : '-'} unit="명" />
        <KpiCard label="이번달 급여" value={payrollsData  ? monthPayTotal.toLocaleString() : '-'} unit="원" />
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
