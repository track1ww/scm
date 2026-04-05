import { useState, useEffect, useRef, useCallback } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import api from "../api/client"
import useAuthStore from "../stores/authStore"

export default function ChatPage() {
  const { user } = useAuthStore()
  const [activeRoom, setActiveRoom] = useState(null)
  const [activeName, setActiveName] = useState("")
  const [input, setInput] = useState("")
  const [showUsers, setShowUsers] = useState(false)
  const [wsMessages, setWsMessages] = useState([])
  const bottomRef = useRef(null)
  const wsRef = useRef(null)
  const qc = useQueryClient()

  const { data: rooms = [] } = useQuery({
    queryKey: ["chat-rooms"],
    queryFn: () => api.get("/chat/rooms/").then(r => r.data.results ?? r.data),
    refetchInterval: 5000,
  })

  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get("/accounts/users/").then(r => r.data.results ?? r.data),
  })

  const { data: initialMessages = [] } = useQuery({
    queryKey: ["chat-messages", activeRoom],
    queryFn: () => api.get("/chat/messages/", { params: { room_id: activeRoom } }).then(r => (r.data.results ?? r.data).reverse()),
    enabled: !!activeRoom,
  })

  // WebSocket 연결 관리
  const connectWebSocket = useCallback((roomId) => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (!roomId) return

    const token = localStorage.getItem("access_token")
    if (!token) return

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const wsHost = import.meta.env.VITE_WS_URL || "localhost:8000"
    const wsUrl = `${wsProtocol}//${wsHost}/ws/chat/${roomId}/?token=${token}`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log(`[WS] 채팅방 ${roomId} 연결됨`)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "message") {
        setWsMessages(prev => [...prev, {
          id: data.id,
          content: data.content,
          sender: data.sender_id,
          sender_name: data.sender_name,
          created_at: data.created_at,
          is_mine: String(data.sender_id) === String(user?.id),
        }])
      }
    }

    ws.onerror = (err) => {
      console.error("[WS] 오류:", err)
    }

    ws.onclose = (event) => {
      console.log(`[WS] 채팅방 ${roomId} 연결 종료 (code: ${event.code})`)
    }

    wsRef.current = ws
  }, [user?.id])

  // activeRoom 변경 시 WebSocket 재연결 & 메시지 초기화
  useEffect(() => {
    setWsMessages([])
    connectWebSocket(activeRoom)

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [activeRoom, connectWebSocket])

  // 합쳐진 메시지: 초기 HTTP 로드 + WebSocket 실시간 메시지
  const messages = [...initialMessages, ...wsMessages.filter(
    wsMsg => !initialMessages.some(m => m.id === wsMsg.id)
  )]

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const createDM = useMutation({
    mutationFn: (userId) => api.post("/chat/rooms/create_dm/", { target_user_id: userId }),
    onSuccess: (res) => {
      setActiveRoom(res.data.id)
      setActiveName(res.data.room_name)
      setShowUsers(false)
      qc.invalidateQueries(["chat-rooms"])
    },
  })

  const leaveRoom = useMutation({
    mutationFn: (roomId) => api.post(`/chat/rooms/${roomId}/leave/`),
    onSuccess: () => {
      setActiveRoom(null)
      setActiveName("")
      qc.invalidateQueries(["chat-rooms"])
    },
  })

  const deleteRoom = useMutation({
    mutationFn: (roomId) => api.delete(`/chat/rooms/${roomId}/`),
    onSuccess: () => {
      setActiveRoom(null)
      setActiveName("")
      qc.invalidateQueries(["chat-rooms"])
    },
  })

  // WebSocket으로 메시지 전송, fallback으로 HTTP 사용
  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim() || !activeRoom) return

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content: input }))
      setInput("")
    } else {
      // WebSocket 연결 실패 시 HTTP fallback
      api.post("/chat/messages/", { room: activeRoom, content: input }).then(() => {
        setInput("")
        qc.invalidateQueries(["chat-messages", activeRoom])
      })
    }
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>메신저</h1>
      <div style={{ display: "flex", gap: 16, height: 600 }}>
        <div style={{ width: 240, border: "1px solid #e9e9e7", borderRadius: 10, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid #e9e9e7", background: "#f7f7f5" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#6b6b6b" }}>채팅방</span>
              <button onClick={() => setShowUsers(!showUsers)} style={{ fontSize: 11, padding: "3px 8px", background: "#1a1a2e", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}>+ DM</button>
            </div>
            {showUsers && (
              <div style={{ background: "white", border: "1px solid #e9e9e7", borderRadius: 6, maxHeight: 150, overflowY: "auto" }}>
                {users.filter(u => u.id !== user?.id).map(u => (
                  <div key={u.id} onClick={() => createDM.mutate(u.id)} style={{ padding: "8px 12px", fontSize: 12, cursor: "pointer", borderBottom: "1px solid #f1f1ef" }}>
                    {u.name} <span style={{ color: "#9b9b9b" }}>{u.email}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            {rooms.map(room => (
              <div key={room.id}
                style={{ padding: "10px 12px", cursor: "pointer", background: activeRoom === room.id ? "#e9e9e7" : "white", borderBottom: "1px solid #f1f1ef", display: "flex", alignItems: "center", gap: 6 }}
                onClick={() => { setActiveRoom(room.id); setActiveName(room.room_name) }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#1a1a1a" }}>{room.room_name}</div>
                  {room.last_message && (
                    <div style={{ fontSize: 11, color: "#9b9b9b", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{room.last_message.content}</div>
                  )}
                </div>
                <button
                  title="나가기"
                  onClick={e => { e.stopPropagation(); if (window.confirm(`"${room.room_name}"에서 나가시겠습니까?`)) leaveRoom.mutate(room.id) }}
                  style={{ flexShrink: 0, background: "none", border: "none", cursor: "pointer", fontSize: 14, color: "#9b9b9b", lineHeight: 1, padding: "2px 4px" }}
                >×</button>
              </div>
            ))}
          </div>
        </div>
        <div style={{ flex: 1, border: "1px solid #e9e9e7", borderRadius: 10, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {!activeRoom ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#9b9b9b" }}>채팅방을 선택하세요</div>
          ) : (
            <>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid #e9e9e7", background: "#f7f7f5", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{activeName}</span>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    onClick={() => { if (window.confirm(`"${activeName}"에서 나가시겠습니까?`)) leaveRoom.mutate(activeRoom) }}
                    style={{ fontSize: 11, padding: "3px 10px", background: "#f5f5f3", color: "#6b6b6b", border: "1px solid #e9e9e7", borderRadius: 4, cursor: "pointer" }}
                  >나가기</button>
                  <button
                    onClick={() => { if (window.confirm(`"${activeName}" 채팅방을 삭제하시겠습니까? 모든 메시지가 삭제됩니다.`)) deleteRoom.mutate(activeRoom) }}
                    style={{ fontSize: 11, padding: "3px 10px", background: "#fff0f0", color: "#cc3333", border: "1px solid #f5c5c5", borderRadius: 4, cursor: "pointer" }}
                  >삭제</button>
                </div>
              </div>
              <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
                {messages.map((msg, i) => {
                  const isMe = msg.is_mine || String(msg.sender) === String(user?.id)
                  return (
                    <div key={msg.id || i} style={{ display: "flex", justifyContent: isMe ? "flex-end" : "flex-start", marginBottom: 10 }}>
                      <div style={{ maxWidth: "70%" }}>
                        {!isMe && <div style={{ fontSize: 11, color: "#9b9b9b", marginBottom: 3 }}>{msg.sender_name}</div>}
                        <div style={{ padding: "8px 12px", background: isMe ? "#1a1a2e" : "#f7f7f5", color: isMe ? "white" : "#1a1a1a", borderRadius: isMe ? "12px 12px 2px 12px" : "12px 12px 12px 2px", fontSize: 13 }}>
                          {msg.content}
                        </div>
                        <div style={{ fontSize: 10, color: "#9b9b9b", marginTop: 2, textAlign: isMe ? "right" : "left" }}>{msg.created_at}</div>
                      </div>
                    </div>
                  )
                })}
                <div ref={bottomRef} />
              </div>
              <form onSubmit={handleSend} style={{ display: "flex", gap: 8, padding: "12px 16px", borderTop: "1px solid #e9e9e7" }}>
                <input value={input} onChange={e => setInput(e.target.value)} placeholder="메시지 입력..."
                  style={{ flex: 1, padding: "9px 12px", border: "1px solid #d3d3cf", borderRadius: 6, fontSize: 13, outline: "none" }} />
                <button type="submit" style={{ padding: "9px 18px", background: "#1a1a2e", color: "white", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>전송</button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
