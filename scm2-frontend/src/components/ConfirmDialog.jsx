import { useEffect, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'

/**
 * Usage:
 *   const [confirm, setConfirm] = useState(null)
 *   // to trigger: setConfirm({ message: '삭제할까요?', onConfirm: () => deleteMutation.mutate(id) })
 *   // with comment: setConfirm({ message: '반려 사유를 입력하세요', inputLabel: '반려 사유', inputRequired: true, onConfirm: (comment) => rejectMutation.mutate({ id, comment }) })
 *   // in JSX: <ConfirmDialog config={confirm} onClose={() => setConfirm(null)} />
 */
export default function ConfirmDialog({ config, onClose }) {
  const cancelRef = useRef(null)
  const [inputValue, setInputValue] = useState('')

  useEffect(() => {
    if (config) {
      setInputValue('')
      cancelRef.current?.focus()
    }
  }, [config])

  if (!config) return null

  const {
    message = '계속 진행하시겠습니까?',
    confirmLabel = '확인',
    danger = true,
    onConfirm,
    inputLabel = null,
    inputRequired = false,
  } = config

  function handleConfirm() {
    if (inputRequired && !inputValue.trim()) return
    onConfirm?.(inputValue.trim())
    onClose()
  }

  const confirmDisabled = inputRequired && !inputValue.trim()

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-message"
    >
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
        <div className="flex items-start gap-3 mb-4">
          {danger && <AlertTriangle size={20} className="text-red-500 mt-0.5 shrink-0" aria-hidden="true" />}
          <p id="confirm-dialog-message" className="text-sm text-gray-700 leading-relaxed">{message}</p>
        </div>

        {inputLabel && (
          <div className="mb-4">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {inputLabel}{inputRequired && <span className="text-red-500 ml-0.5">*</span>}
            </label>
            <textarea
              rows={3}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder={`${inputLabel}을(를) 입력하세요`}
              aria-label={inputLabel}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50"
          >
            취소
          </button>
          <button
            onClick={handleConfirm}
            disabled={confirmDisabled}
            className={`px-4 py-2 text-sm rounded-lg text-white font-medium ${
              danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
