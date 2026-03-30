import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

/**
 * WebSocket hook for real-time notifications.
 * Connects to ws://host/ws/notifications/?token=<jwt>
 * On new_notification: invalidates ['notifications'] query
 * On unread_count: updates the cache directly
 */
const MAX_RETRIES = 8
const BASE_DELAY = 3000  // 3s, doubles each retry up to ~6.4min

export function useNotificationSocket() {
  const qc = useQueryClient()
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const retryCount = useRef(0)

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    if (retryCount.current >= MAX_RETRIES) return  // 포기 — 백엔드 미실행 상태

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws/notifications/?token=${token}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      retryCount.current = 0  // 성공 시 재시도 카운터 리셋
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'new_notification' || msg.type === 'unread_count') {
          qc.invalidateQueries({ queryKey: ['notifications'] })
        }
      } catch {}
    }

    ws.onclose = () => {
      retryCount.current += 1
      if (retryCount.current < MAX_RETRIES) {
        // 지수 백오프: 3s → 6s → 12s → ... (최대 ~6.4분)
        const delay = Math.min(BASE_DELAY * 2 ** (retryCount.current - 1), 384000)
        reconnectTimer.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [qc])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null  // cleanup 시 재연결 방지
        wsRef.current.close()
      }
    }
  }, [connect])
}
