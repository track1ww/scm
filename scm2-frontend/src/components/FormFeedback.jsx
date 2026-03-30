// Inline error/success feedback components
export function FieldError({ name, errors }) {
  if (!errors?.[name]) return null
  return <p className="text-red-500 text-xs mt-1" role="alert">{errors[name]}</p>
}

export function GlobalError({ message, onClose }) {
  if (!message) return null
  return (
    <div role="alert" className="bg-red-50 border border-red-300 text-red-700 rounded px-4 py-3 mb-4 flex justify-between items-start text-sm">
      <span>{message}</span>
      {onClose && <button onClick={onClose} aria-label="오류 메시지 닫기" className="ml-4 text-red-500 hover:text-red-700 font-bold">✕</button>}
    </div>
  )
}

export function SuccessMessage({ message, onClose }) {
  if (!message) return null
  return (
    <div role="status" aria-live="polite" className="bg-green-50 border border-green-300 text-green-700 rounded px-4 py-3 mb-4 flex justify-between items-start text-sm">
      <span>{message}</span>
      {onClose && <button onClick={onClose} aria-label="성공 메시지 닫기" className="ml-4 text-green-600 hover:text-green-800 font-bold">✕</button>}
    </div>
  )
}
