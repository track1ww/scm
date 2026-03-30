import { useState } from 'react'

export function useConfirm() {
  const [confirmConfig, setConfirmConfig] = useState(null)

  function requestConfirm({ message, confirmLabel = '삭제', danger = true, onConfirm }) {
    setConfirmConfig({ message, confirmLabel, danger, onConfirm })
  }

  function closeConfirm() {
    setConfirmConfig(null)
  }

  return { confirmConfig, requestConfirm, closeConfirm }
}
