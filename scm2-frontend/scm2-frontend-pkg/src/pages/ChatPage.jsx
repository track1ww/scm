import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import useAuthStore from '../stores/authStore'

function useWebSocket(roomId) {
  const wsRef  = useRef(null)
  const [msgs, setMsgs] = useState([])

  useEffect(() => {
    if (!roomId) return
    const token = localStorage.getItem('access_token')
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}/?token=${token}`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'message') {
        setMsgs(prev => [...prev, data])
      }
    }
    return () => ws.close()
  }, [roomId])

  const send = (content) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content }))
    }
  }

  return { msgs, send }
}

export default function ChatPage() {
  const { user } = useAuthStore()
  const [activeRoom, setActiveRoom] = useState(null)
  const [input, setInput]           = useState('')
  const [dmEmail, setDmEmail]       = useState('')
  const bottomRef = useRef(null)
  const qc = useQueryClient()

  const { data: rooms = [] } = useQuery({
    queryKey: ['chat-rooms'],
    queryFn:  () => api.get('/chat/rooms/').then(r => r.data.results ?? r.data),
    refetchInterval: 10000,
  })

  const { data: history = [] } = useQuery({
    queryKey: ['chat-messages', activeRoom],
    queryFn:  () => api.get('/chat/messages/', { params: { room_id: activeRoom } })
                       .then(r => (r.data.results ?? r.data).reverse()),
    enabled: !!activeRoom,
  })

  const { msgs: wsMsgs, send } = useWebSocket(activeRoom)
  const allMsgs = [...history, ...wsMsgs]

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [allMsgs])

  const createDM = useMutation({
    mutationFn: () => api.post('/chat/rooms/create_dm/', { target_user_email: dmEmail }),
    onSuccess: (res) => {
      setActiveRoom(res.data.id)
      setDmEmail('')
      qc.invalidateQueries(['chat-rooms'])
    },
  })

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim() || !activeRoom) return
    send(input)
    setInput('')
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24, letterSpacing: '-0.02em' }}>💬 메신저</h1>

      <div style={{ display: 'flex', gap: 16, height: 600 }}>
        {/* 채팅방 목록 */}
        <div style={{
          width: 240, border: '1px solid #e9e9e7', borderRadius: 10,
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #e9e9e7', background: '#f7f7f5' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#6b6b6b', marginBottom: 8 }}>채팅방</div>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                value={dmEmail}
                onChange={e => setDmEmail(e.target.value)}
                placeholder="이메일로 DM"
                style={{
                  flex: 1, padding: '5px 8px', fontSize: 11,
                  border: '1px solid #d3d3cf', borderRadius: 4, outline: 'none',
                }}
              />
              <button
                onClick={() => dmEmail && createDM.mutate()}
                style={{
                  padding: '5px 8px', fontSize: 11, background: '#1a1a2e',
                  color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer',
                }}
              >
                DM
              </button>
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {rooms.map(room => (
              <div
                key={room.id}
                onClick={() => setActiveRoom(room.id)}
                style={{
                  padding: '12px 16px', cursor: 'pointer',
                  background: activeRoom === room.id ? '#e9e9e7' : 'white',
                  borderBottom: '1px solid #f1f1ef',
                  transition: 'background 0.1s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#1a1a1a' }}>
                    {room.room_type === 'dm' ? '💬' : '👥'} {room.room_name}
                  </div>
                  {room.unread_count > 0 && (
                    <span style={{
                      background: '#d44c47', color: 'white',
                      fontSize: 10, fontWeight: 700,
                      padding: '1px 6px', borderRadius: 10,
                    }}>
                      {room.unread_count}
                    </span>
                  )}
                </div>
                {room.last_message && (
                  <div style={{ fontSize: 11, color: '#9b9b9b', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {room.last_message.content}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 메시지 영역 */}
        <div style={{
          flex: 1, border: '1px solid #e9e9e7', borderRadius: 10,
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          {!activeRoom ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9b9b9b' }}>
              채팅방을 선택하세요
            </div>
          ) : (
            <>
              {/* 메시지 목록 */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
                {allMsgs.map((msg, i) => {
                  const isMe = msg.sender_id === user?.id || msg.is_mine
                  return (
                    <div key={i} style={{
                      display: 'flex', justifyContent: isMe ? 'flex-end' : 'flex-start',
                      marginBottom: 10,
                    }}>
                      <div style={{ maxWidth: '70%' }}>
                        {!isMe && (
                          <div style={{ fontSize: 11, color: '#9b9b9b', marginBottom: 3 }}>
                            {msg.sender_name}
                          </div>
                        )}
                        <div style={{
                          padding: '8px 12px',
                          background: isMe ? '#1a1a2e' : '#f7f7f5',
                          color: isMe ? 'white' : '#1a1a1a',
                          borderRadius: isMe ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                          fontSize: 13, lineHeight: 1.5,
                        }}>
                          {msg.content}
                        </div>
                        <div style={{ fontSize: 10, color: '#9b9b9b', marginTop: 2, textAlign: isMe ? 'right' : 'left' }}>
                          {msg.created_at}
                        </div>
                      </div>
                    </div>
                  )
                })}
                <div ref={bottomRef} />
              </div>

              {/* 입력창 */}
              <form onSubmit={handleSend} style={{
                display: 'flex', gap: 8, padding: '12px 16px',
                borderTop: '1px solid #e9e9e7',
              }}>
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="메시지 입력..."
                  style={{
                    flex: 1, padding: '9px 12px',
                    border: '1px solid #d3d3cf', borderRadius: 6,
                    fontSize: 13, outline: 'none',
                  }}
                />
                <button
                  type="submit"
                  style={{
                    padding: '9px 18px', background: '#1a1a2e',
                    color: 'white', border: 'none', borderRadius: 6,
                    fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  전송
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
