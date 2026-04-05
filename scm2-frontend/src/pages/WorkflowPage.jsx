import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, Clock, GitMerge, Plus, ChevronDown } from 'lucide-react'
import client from '../api/client'
import { useFormError } from '../hooks/useFormError'
import { GlobalError, SuccessMessage } from '../components/FormFeedback'
import { useConfirm } from '../hooks/useConfirm'
import ConfirmDialog from '../components/ConfirmDialog'
import Pagination from '../components/Pagination'

const STATUS_LABEL = {
  pending:   { label: '대기', color: 'bg-amber-100 text-amber-700' },
  approved:  { label: '승인', color: 'bg-green-100 text-green-700' },
  rejected:  { label: '반려', color: 'bg-red-100 text-red-700' },
  cancelled: { label: '취소', color: 'bg-gray-100 text-gray-500' },
}

function StatusBadge({ status }) {
  const s = STATUS_LABEL[status] || { label: status, color: 'bg-gray-100 text-gray-500' }
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${s.color}`}>{s.label}</span>
}

const INIT_FORM = { template: '', title: '', content: '', ref_module: '', ref_id: '' }

export default function WorkflowPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [filterStatus, setFilterStatus] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(INIT_FORM)
  const [expandedId, setExpandedId] = useState(null)

  const { globalError, handleApiError, clearErrors, setGlobalError } = useFormError()
  const [successMsg, setSuccessMsg] = useState('')
  const { confirmConfig, requestConfirm, closeConfirm } = useConfirm()

  // Queries
  const { data: requestsData, isLoading } = useQuery({
    queryKey: ['workflow-requests', page, filterStatus],
    queryFn: () => client.get(`/workflow/requests/?page=${page}${filterStatus ? `&status=${filterStatus}` : ''}`).then(r => r.data),
    placeholderData: prev => prev,
  })
  const requests = requestsData?.results ?? requestsData ?? []

  const { data: templatesData } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: () => client.get('/workflow/templates/').then(r => r.data),
  })
  const templates = templatesData?.results ?? templatesData ?? []

  // Mutations
  const createMutation = useMutation({
    mutationFn: data => client.post('/workflow/requests/', data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflow-requests'] })
      setSuccessMsg('결재 요청이 등록되었습니다.')
      setShowForm(false)
      setForm(INIT_FORM)
    },
    onError: err => handleApiError(err),
  })

  const approveMutation = useMutation({
    mutationFn: ({ id, comment }) => client.post(`/workflow/requests/${id}/approve/`, { comment }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflow-requests'] })
      setSuccessMsg('승인 처리되었습니다.')
    },
    onError: err => handleApiError(err),
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, comment }) => client.post(`/workflow/requests/${id}/reject/`, { comment }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflow-requests'] })
      setSuccessMsg('반려 처리되었습니다.')
    },
    onError: err => handleApiError(err),
  })

  function handleSubmit(e) {
    e.preventDefault()
    clearErrors()
    createMutation.mutate(form)
  }

  return (
    <div className="p-3 sm:p-6 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">결재 워크플로우</h1>
          <p className="text-sm text-gray-500 mt-1">전자 결재 요청 및 처리</p>
        </div>
        <button
          onClick={() => { setShowForm(s => !s); clearErrors(); setSuccessMsg('') }}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg"
        >
          <Plus size={16} /> 결재 요청
        </button>
      </div>

      <GlobalError message={globalError} onClose={() => setGlobalError('')} />
      <SuccessMessage message={successMsg} onClose={() => setSuccessMsg('')} />

      {/* New Request Form */}
      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6 shadow-sm">
          <h2 className="font-semibold text-gray-700 mb-4 text-sm">새 결재 요청</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label htmlFor="wf-request-template" className="block text-xs text-gray-500 mb-1">결재 템플릿</label>
                <select
                  id="wf-request-template"
                  name="template"
                  value={form.template}
                  onChange={e => setForm(f => ({ ...f, template: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">템플릿 선택 (선택사항)</option>
                  {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="wf-request-title" className="block text-xs text-gray-500 mb-1">제목 *</label>
                <input
                  id="wf-request-title"
                  name="title"
                  required
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="결재 제목"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label htmlFor="wf-request-content" className="block text-xs text-gray-500 mb-1">내용</label>
              <textarea
                id="wf-request-content"
                name="content"
                value={form.content}
                onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                rows={3}
                placeholder="결재 내용을 입력하세요"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
                취소
              </button>
              <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-60">
                {createMutation.isPending ? '등록 중...' : '요청 등록'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filter */}
      <div className="overflow-x-auto mb-4">
      <div className="flex items-center gap-3 min-w-max pb-1">
        <span className="text-sm text-gray-500">상태 필터:</span>
        {['', 'pending', 'approved', 'rejected'].map(s => (
          <button
            key={s}
            onClick={() => { setFilterStatus(s); setPage(1) }}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              filterStatus === s
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {s === '' ? '전체' : STATUS_LABEL[s]?.label}
          </button>
        ))}
      </div>
      </div>

      {/* Request List */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-32 text-gray-400 text-sm">로딩 중...</div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400">
            <GitMerge size={32} className="mb-2 opacity-30" />
            <p className="text-sm">결재 요청이 없습니다</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['제목', '요청자', '상태', '요청일', '액션'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {requests.map(req => (
                <>
                  <tr
                    key={req.id}
                    className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => setExpandedId(expandedId === req.id ? null : req.id)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <ChevronDown size={14} className={`text-gray-400 transition-transform ${expandedId === req.id ? 'rotate-180' : ''}`} />
                        <span className="font-medium text-gray-800">{req.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{req.requester_name || req.requester}</td>
                    <td className="px-4 py-3"><StatusBadge status={req.status} /></td>
                    <td className="px-4 py-3 text-gray-400">{req.created_at?.slice(0, 10)}</td>
                    <td className="px-4 py-3">
                      {req.status === 'pending' && (
                        <div className="flex gap-2" onClick={e => e.stopPropagation()}>
                          <button
                            onClick={() => requestConfirm({
                              message: `"${req.title}" 결재를 승인하시겠습니까?`,
                              confirmLabel: '승인',
                              danger: false,
                              inputLabel: '승인 의견 (선택)',
                              inputRequired: false,
                              onConfirm: (comment) => approveMutation.mutate({ id: req.id, comment }),
                            })}
                            className="flex items-center gap-1 text-xs px-3 py-1.5 bg-green-50 text-green-700 hover:bg-green-100 rounded-lg border border-green-200"
                          >
                            <CheckCircle size={12} /> 승인
                          </button>
                          <button
                            onClick={() => requestConfirm({
                              message: `"${req.title}" 결재를 반려합니다. 반려 사유를 입력하세요.`,
                              confirmLabel: '반려',
                              danger: true,
                              inputLabel: '반려 사유',
                              inputRequired: true,
                              onConfirm: (comment) => rejectMutation.mutate({ id: req.id, comment }),
                            })}
                            className="flex items-center gap-1 text-xs px-3 py-1.5 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg border border-red-200"
                          >
                            <XCircle size={12} /> 반려
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                  {expandedId === req.id && (
                    <tr key={`${req.id}-detail`} className="bg-blue-50 border-b border-gray-100">
                      <td colSpan={5} className="px-8 py-4">
                        <p className="text-xs text-gray-500 mb-1">내용</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{req.content || '(내용 없음)'}</p>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
          </div>
        )}
        <Pagination currentPage={page} totalPages={requestsData?.total_pages} onPageChange={setPage} />
      </div>

      <ConfirmDialog config={confirmConfig} onClose={closeConfirm} />
    </div>
  )
}
