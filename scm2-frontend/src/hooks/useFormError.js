import { useState, useCallback } from 'react'

export function useFormError() {
  const [errors, setErrors] = useState({})
  const [globalError, setGlobalError] = useState('')

  const handleApiError = useCallback((err) => {
    const data = err?.response?.data
    if (!data) { setGlobalError('서버 오류가 발생했습니다.'); return }
    if (typeof data === 'string') { setGlobalError(data); return }
    if (data.detail) { setGlobalError(data.detail); return }
    // DRF field errors: { field: ["message"] }
    const fieldErrors = {}
    for (const [key, val] of Object.entries(data)) {
      fieldErrors[key] = Array.isArray(val) ? val[0] : String(val)
    }
    if (Object.keys(fieldErrors).length > 0) setErrors(fieldErrors)
    else setGlobalError(JSON.stringify(data))
  }, [])

  const clearErrors = useCallback(() => { setErrors({}); setGlobalError('') }, [])
  const setFieldError = useCallback((field, msg) => setErrors(e => ({...e, [field]: msg})), [])

  return { errors, globalError, handleApiError, clearErrors, setFieldError, setErrors, setGlobalError }
}
