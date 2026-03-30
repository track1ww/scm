import { useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck, X, Info, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import client from '../api/client'

const TYPE_ICON = {
  info:    <Info size={14} className="text-blue-500" />,
  warning: <AlertTriangle size={14} className="text-amber-500" />,
  success: <CheckCircle size={14} className="text-green-500" />,
  error:   <XCircle size={14} className="text-red-500" />,
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60) return '방금'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

function NotificationItem({ item, onRead }) {
  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors ${!item.is_read ? 'bg-blue-50/40' : ''}`}
      onClick={() => !item.is_read && onRead(item.id)}
    >
      <div className="mt-0.5 shrink-0">
        {TYPE_ICON[item.notification_type] || TYPE_ICON.info}
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm leading-snug ${!item.is_read ? 'font-medium text-gray-900' : 'text-gray-600'}`}>
          {item.message}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">{timeAgo(item.created_at)}</p>
      </div>
      {!item.is_read && <span className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />}
    </div>
  )
}

export default function NotificationPanel({ isOpen, onClose }) {
  const panelRef = useRef(null)
  const qc = useQueryClient()

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    function handleClick(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [isOpen, onClose])

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => client.get('/notifications/?page=1&page_size=20').then(r => r.data),
    refetchInterval: 60000,  // fallback polling (WebSocket is primary)
  })

  const notifications = data?.results ?? []
  const unreadCount = data?.unread_count ?? 0

  const readMutation = useMutation({
    mutationFn: id => client.post(`/notifications/${id}/read/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const readAllMutation = useMutation({
    mutationFn: () => client.post('/notifications/read_all/').then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  if (!isOpen) return null

  return (
    <div
      ref={panelRef}
      className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Bell size={16} className="text-gray-600" />
          <span className="font-semibold text-gray-800 text-sm">알림</span>
          {unreadCount > 0 && (
            <span className="text-xs bg-blue-600 text-white rounded-full px-1.5 py-0.5 leading-none">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={() => readAllMutation.mutate()}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
              title="모두 읽음"
            >
              <CheckCheck size={14} /> 모두 읽음
            </button>
          )}
          <button onClick={onClose} aria-label="알림 패널 닫기" className="text-gray-400 hover:text-gray-600">
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="overflow-y-auto max-h-96">
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-gray-400">
            <Bell size={28} className="mb-2 opacity-30" />
            <p className="text-sm">알림이 없습니다</p>
          </div>
        ) : (
          notifications.map(n => (
            <NotificationItem key={n.id} item={n} onRead={id => readMutation.mutate(id)} />
          ))
        )}
      </div>
    </div>
  )
}
