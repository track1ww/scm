import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import ConfirmDialog from '../components/ConfirmDialog'
import { useConfirm } from '../hooks/useConfirm'
import Pagination from '../components/Pagination'

const TABS = ['작업지시', '작업 실적', '작업자 배정']

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
  btnStart: {
    background: '#f0f4ff', color: '#3366cc', border: '1px solid #c5d5f5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer', marginRight: 4,
  },
  btnComplete: {
    background: '#f0fff4', color: '#2d7a2d', border: '1px solid #b5e0b5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer', marginRight: 4,
  },
  btnDel: {
    background: '#fff0f0', color: '#cc3333', border: '1px solid #f5c5c5',
    borderRadius: 4, padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  },
}

// ─── 좌측 폼 래퍼 ─────────────────────────────────────────────
function FormPanel({ children, onSubmit, isPending }) {
  return (
    <div style={{
      width: 320, flexShrink: 0,
      background: 'white', border: '1px solid #e9e9e7',
      borderRadius: 10, padding: 20, alignSelf: 'flex-start',
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: '#1a1a1a' }}>
        신규 등록
      </div>
      {children}
      <button style={S.btnPrimary} onClick={onSubmit} disabled={isPending}>
        {isPending ? '저장 중...' : '등록'}
      </button>
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
                    {col.render ? col.render(row) : (row[col.key] ?? '-')}
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

const PRIORITY_COLORS = { 높음: '#e53e3e', 보통: '#d69e2e', 낮음: '#38a169' }
const STATUS_COLORS = {
  대기: '#9b9b9b', 진행중: '#3182ce', 완료: '#38a169',
  보류: '#d69e2e', 취소: '#e53e3e',
}

function Badge({ value, colorMap }) {
  const color = colorMap[value] || '#9b9b9b'
  return (
    <span style={{
      background: color + '18', color, border: `1px solid ${color}40`,
      borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600,
    }}>
      {value ?? '-'}
    </span>
  )
}

// ─── 작업지시 탭 ───────────────────────────────────────────────
function InstructionTab({ data, isLoading, page, setPage }) {
  const queryClient = useQueryClient()
  const initialForm = {
    title: '', work_center: '', assigned_to: '', priority: '보통',
    planned_start: '', planned_end: '', planned_qty: '', description: '',
  }
  const [form, setForm] = useState(initialForm)
  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()

  const rows = getList(data)

  const createMutation = useMutation({
    mutationFn: payload => api.post('/wi/work-orders/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wi-instructions'] })
      queryClient.invalidateQueries({ queryKey: ['wi-results'] })
      setForm(initialForm)
      setSuccessMsg('저장되었습니다.')
    },
    onError: (err) => handleApiError(err),
  })

  const patchMutation = useMutation({
    mutationFn: ({ id, payload }) => api.patch(`/wi/work-orders/${id}/`, payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wi-instructions'] })
      queryClient.invalidateQueries({ queryKey: ['wi-results'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: id => api.delete(`/wi/work-orders/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wi-instructions'] })
      queryClient.invalidateQueries({ queryKey: ['wi-results'] })
    },
  })

  const handleSubmit = () => {
    if (!form.title.trim()) {
      setGlobalError('제목은 필수입니다.')
      return
    }
    clearErrors(); setSuccessMsg('')
    const payload = { ...form }
    if (!payload.planned_start) delete payload.planned_start
    if (!payload.planned_end) delete payload.planned_end
    if (!payload.planned_qty) delete payload.planned_qty
    if (!payload.work_center) delete payload.work_center
    if (!payload.assigned_to) delete payload.assigned_to
    createMutation.mutate(payload)
  }

  const columns = [
    { key: 'wi_number', label: '지시번호', render: r => r.wi_number ?? '-' },
    { key: 'title', label: '제목', render: r => r.title ?? '-' },
    { key: 'assigned_to', label: '담당자', render: r => r.assigned_to?.name || r.assigned_to || '-' },
    { key: 'priority', label: '우선순위', render: r => <Badge value={r.priority} colorMap={PRIORITY_COLORS} /> },
    { key: 'status', label: '상태', render: r => <Badge value={r.status} colorMap={STATUS_COLORS} /> },
    { key: 'planned_start', label: '계획시작', render: r => r.planned_start?.slice(0, 10) || '-' },
    { key: 'planned_end', label: '계획종료', render: r => r.planned_end?.slice(0, 10) || '-' },
    {
      key: '_actions', label: '작업',
      render: r => (
        <span style={{ whiteSpace: 'nowrap' }}>
          {r.status === '대기' && (
            <button style={S.btnStart}
              onClick={() => patchMutation.mutate({ id: r.id, payload: { status: '진행중' } })}>
              시작
            </button>
          )}
          {r.status === '진행중' && (
            <button style={S.btnComplete}
              onClick={() => patchMutation.mutate({ id: r.id, payload: { status: '완료' } })}>
              완료
            </button>
          )}
          {r.status === '대기' && (
            <button style={S.btnDel} onClick={() => requestConfirm({ message: `작업지시 "${r.title}"을(를) 삭제하시겠습니까?`, onConfirm: () => deleteMutation.mutate(r.id) })}>삭제</button>
          )}
        </span>
      ),
    },
  ]

  return (
    <>
      <div style={{ padding: '12px 16px 0' }}>
        <GlobalError message={globalError} onClose={() => setGlobalError('')} />
        <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />
      </div>
      <div className="flex flex-col md:flex-row gap-5 p-3 md:p-5 items-start">
      <FormPanel onSubmit={handleSubmit} isPending={createMutation.isPending}>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-title" style={S.label}>제목 *</label>
          <input id="wi-instruction-title" name="title" style={S.input} value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="작업지시 제목" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-work-center" style={S.label}>작업장</label>
          <input id="wi-instruction-work-center" name="work_center" style={S.input} value={form.work_center}
            onChange={e => setForm(f => ({ ...f, work_center: e.target.value }))}
            placeholder="예: 1공장 A라인" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-assigned-to" style={S.label}>담당자</label>
          <input id="wi-instruction-assigned-to" name="assigned_to" style={S.input} value={form.assigned_to}
            onChange={e => setForm(f => ({ ...f, assigned_to: e.target.value }))}
            placeholder="담당자 이름" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-priority" style={S.label}>우선순위</label>
          <select id="wi-instruction-priority" name="priority" style={S.input} value={form.priority}
            onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
            <option value="높음">높음</option>
            <option value="보통">보통</option>
            <option value="낮음">낮음</option>
          </select>
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-planned-start" style={S.label}>계획 시작</label>
          <input id="wi-instruction-planned-start" name="planned_start" style={S.input} type="datetime-local" value={form.planned_start}
            onChange={e => setForm(f => ({ ...f, planned_start: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-planned-end" style={S.label}>계획 종료</label>
          <input id="wi-instruction-planned-end" name="planned_end" style={S.input} type="datetime-local" value={form.planned_end}
            onChange={e => setForm(f => ({ ...f, planned_end: e.target.value }))} />
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-planned-qty" style={S.label}>계획 수량</label>
          <input id="wi-instruction-planned-qty" name="planned_qty" style={S.input} type="number" value={form.planned_qty}
            onChange={e => setForm(f => ({ ...f, planned_qty: e.target.value }))}
            placeholder="0" />
        </div>
        <div style={S.formRow}>
          <label htmlFor="wi-instruction-description" style={S.label}>설명</label>
          <textarea
            id="wi-instruction-description"
            name="description"
            style={{ ...S.input, height: 72, resize: 'vertical' }}
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="작업 내용 설명"
          />
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

// ─── 작업 실적 탭 (읽기전용) ───────────────────────────────────
function ResultTab({ data, isLoading }) {
  const rows = getList(data)
  const columns = [
    { key: 'order_number', label: '작업지시번호', render: r => r.order_number ?? r.wi_number ?? '-' },
    { key: 'title', label: '작업명', render: r => r.title ?? '-' },
    { key: 'assigned_to', label: '작업자', render: r => r.assigned_to?.name || r.assigned_to || '-' },
    { key: 'completed_at', label: '완료일시', render: r => r.completed_at?.slice(0, 10) || '-' },
    { key: 'status', label: '상태', render: r => <Badge value={r.status} colorMap={STATUS_COLORS} /> },
    { key: 'description', label: '비고', render: r => r.description ?? '-' },
  ]
  return (
    <div className="p-3 md:p-5 overflow-x-auto">
      <DataTable isLoading={isLoading} rows={rows} columns={columns} />
    </div>
  )
}

// ─── 작업자 배정 탭 (읽기전용) ─────────────────────────────────
function AssignTab({ data, isLoading }) {
  const rows = getList(data).filter(r => r.status !== '완료' && r.status !== '취소')
  const columns = [
    { key: 'wi_number', label: '작업지시번호', render: r => r.wi_number ?? '-' },
    { key: 'title', label: '작업명', render: r => r.title ?? '-' },
    { key: 'work_center', label: '작업장', render: r => r.work_center ?? '-' },
    { key: 'assigned_to', label: '담당자', render: r => r.assigned_to?.name || r.assigned_to || '미배정' },
    { key: 'priority', label: '우선순위', render: r => <Badge value={r.priority} colorMap={PRIORITY_COLORS} /> },
    { key: 'status', label: '상태', render: r => <Badge value={r.status} colorMap={STATUS_COLORS} /> },
    { key: 'planned_end', label: '납기일', render: r => r.planned_end?.slice(0, 10) || '-' },
  ]
  return (
    <div className="p-3 md:p-5 overflow-x-auto">
      <DataTable isLoading={isLoading} rows={rows} columns={columns} />
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function WiPage() {
  const [activeTab, setActiveTab] = useState(0)
  const [instructionPage, setInstructionPage] = useState(1)

  const { data: instructionData, isLoading: iLoading } = useQuery({
    queryKey: ['wi-instructions', instructionPage],
    queryFn: () => api.get(`/wi/work-orders/?page=${instructionPage}`).then(r => r.data).catch(() => []),
    placeholderData: (prev) => prev,
  })

  const { data: resultData, isLoading: rLoading } = useQuery({
    queryKey: ['wi-results'],
    queryFn: () => api.get('/wi/work-orders/?status=완료').then(r => r.data).catch(() => []),
  })

  const { data: dashboard } = useQuery({
    queryKey: ['wi-dashboard'],
    queryFn: () => api.get('/wi/work-orders/dashboard/').then(r => r.data).catch(() => ({})),
  })

  const instructions = getList(instructionData)
  const inProgress = dashboard?.in_progress ?? instructions.filter(r => r.status === '진행중').length
  const completed  = dashboard?.completed   ?? instructions.filter(r => r.status === '완료').length
  const overdue    = dashboard?.overdue     ?? (() => {
    const todayStr = new Date().toISOString().slice(0, 10)
    return instructions.filter(r =>
      r.status !== '완료' && r.status !== '취소' &&
      r.planned_end && r.planned_end.slice(0, 10) < todayStr
    ).length
  })()

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: '0 0 6px' }}>WI 작업지시서</h1>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>Work Instructions — 작업지시·실적·작업자 배정을 통합 관리합니다.</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <KpiCard label="진행 중 작업" value={inProgress} unit="건" />
        <KpiCard label="완료"         value={completed}  unit="건" />
        <KpiCard label="지연"         value={overdue}    unit="건" />
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
        {activeTab === 0 && <InstructionTab data={instructionData} isLoading={iLoading} page={instructionPage} setPage={setInstructionPage} />}
        {activeTab === 1 && <ResultTab data={resultData} isLoading={rLoading} />}
        {activeTab === 2 && <AssignTab data={instructionData} isLoading={iLoading} />}
      </div>
    </div>
  )
}
