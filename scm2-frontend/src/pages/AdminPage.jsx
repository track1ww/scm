import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import useAuthStore from '../stores/authStore'

const MODULES = [
  { key: 'mm',       label: '자재관리(MM)' },
  { key: 'sd',       label: '판매출하(SD)' },
  { key: 'pp',       label: '생산계획(PP)' },
  { key: 'qm',       label: '품질관리(QM)' },
  { key: 'wm',       label: '창고관리(WM)' },
  { key: 'tm',       label: '운송관리(TM)' },
  { key: 'fi',       label: '재무회계(FI)' },
  { key: 'hr',       label: '인사관리(HR)' },
  { key: 'wi',       label: '작업지시(WI)' },
  { key: 'workflow', label: '결재(WF)' },
  { key: 'chat',     label: '메신저' },
]

const PERM_COLS = [
  { key: 'can_read',   label: '조회' },
  { key: 'can_write',  label: '수정' },
  { key: 'can_delete', label: '삭제' },
]

const FEATURES = [
  {
    key: 'exchange_rate',
    label: '환율 조회',
    icon: '💱',
    desc: '실시간 환율 데이터 (USD/EUR/JPY/CNY 등)',
    providers: [
      { value: 'open_er',  label: 'Open Exchange Rates (무료·키 불필요)' },
      { value: 'ecos',     label: '한국은행 ECOS OpenAPI' },
    ],
  },
  {
    key: 'delivery_tracking',
    label: '배송 추적',
    icon: '📦',
    desc: '국내 택배 운송장 실시간 추적',
    providers: [
      { value: 'sweettracker',  label: '스윗트래커' },
      { value: 'smartdelivery', label: '스마트택배 API' },
    ],
  },
  {
    key: 'customs_tracking',
    label: '통관 조회',
    icon: '🛃',
    desc: '관세청 UNI-PASS 수입화물 통관 진행현황',
    providers: [
      { value: 'unipass', label: '관세청 UNI-PASS' },
    ],
  },
  {
    key: 'vessel_tracking',
    label: '선박 추적',
    icon: '🚢',
    desc: '국제 선박 위치 및 입출항 정보',
    providers: [
      { value: 'marinetraffic', label: 'Marine Traffic' },
    ],
  },
]

function buildDefaultPerms() {
  return Object.fromEntries(
    MODULES.map(m => [
      m.key,
      { can_read: false, can_write: false, can_delete: false },
    ])
  )
}

function permsArrayToState(arr) {
  const state = buildDefaultPerms()
  arr.forEach(p => {
    if (state[p.module] !== undefined) {
      state[p.module] = {
        can_read:   !!p.can_read,
        can_write:  !!p.can_write,
        can_delete: !!p.can_delete,
      }
    }
  })
  return state
}

function formatTestTime(isoString) {
  if (!isoString) return null
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60)  return `${diff}초 전`
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export default function AdminPage() {
  const user = useAuthStore(s => s.user)
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab]       = useState('users')
  const [selectedUser, setSelectedUser] = useState(null)
  const [permState, setPermState]       = useState(buildDefaultPerms())
  const [saveMsg, setSaveMsg]           = useState({ type: '', text: '' })

  // --- API settings state ---
  const [openFormFor, setOpenFormFor] = useState(null)
  const [formData, setFormData]       = useState({ provider: '', api_key: '' })
  const [testResults, setTestResults] = useState({})

  // --- Users list ---
  const {
    data: users = [],
    isLoading: usersLoading,
    error: usersError,
  } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get('/accounts/users/').then(r => {
      const d = r.data
      return Array.isArray(d) ? d : (d.results ?? [])
    }),
    enabled: !!user?.is_admin,
  })

  // --- Permissions for selected user ---
  const {
    data: permsData,
    isLoading: permsLoading,
  } = useQuery({
    queryKey: ['user-perms', selectedUser?.id],
    queryFn: () =>
      api.get(`/accounts/users/${selectedUser.id}/permissions/`).then(r => r.data),
    enabled: !!selectedUser,
  })

  useEffect(() => {
    if (permsData) {
      setPermState(permsArrayToState(permsData))
      setSaveMsg({ type: '', text: '' })
    }
  }, [permsData])

  useEffect(() => {
    if (selectedUser) {
      setSaveMsg({ type: '', text: '' })
    }
  }, [selectedUser])

  // --- Toggle admin mutation ---
  const toggleAdminMutation = useMutation({
    mutationFn: ({ userId, isAdmin }) =>
      api.patch(`/accounts/users/${userId}/set-admin/`, { is_admin: isAdmin }).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  // --- Save mutation ---
  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = Object.entries(permState).map(([module, perms]) => ({
        module,
        can_read:   perms.can_read,
        can_write:  perms.can_write,
        can_delete: perms.can_delete,
      }))
      return api.put(`/accounts/users/${selectedUser.id}/permissions/`, payload)
    },
    onSuccess: () => {
      setSaveMsg({ type: 'success', text: '권한이 저장되었습니다.' })
      queryClient.invalidateQueries({ queryKey: ['user-perms', selectedUser?.id] })
    },
    onError: (err) => {
      const detail = err.response?.data?.detail || '저장에 실패했습니다.'
      setSaveMsg({ type: 'error', text: detail })
    },
  })

  const togglePerm = (moduleKey, permKey) => {
    setPermState(prev => ({
      ...prev,
      [moduleKey]: {
        ...prev[moduleKey],
        [permKey]: !prev[moduleKey][permKey],
      },
    }))
    setSaveMsg({ type: '', text: '' })
  }

  // --- External configs query ---
  const {
    data: configs = [],
    isLoading: configsLoading,
  } = useQuery({
    queryKey: ['external-configs'],
    queryFn: () => api.get('/external/configs/').then(r => {
      const d = r.data
      return Array.isArray(d) ? d : (d.results ?? [])
    }),
    enabled: !!user?.is_admin && activeTab === 'api_settings',
  })

  // --- Create config mutation ---
  const createConfigMutation = useMutation({
    mutationFn: (payload) => api.post('/external/configs/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['external-configs'] })
      setOpenFormFor(null)
      setFormData({ provider: '', api_key: '' })
    },
  })

  // --- Toggle active mutation ---
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }) =>
      api.patch(`/external/configs/${id}/`, { is_active }).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['external-configs'] })
    },
  })

  // --- Delete config mutation ---
  const deleteConfigMutation = useMutation({
    mutationFn: (id) => api.delete(`/external/configs/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['external-configs'] })
    },
  })

  // --- Test config ---
  const handleTest = async (id) => {
    setTestResults(prev => ({ ...prev, [id]: { loading: true } }))
    try {
      const res = await api.post(`/external/configs/${id}/test/`).then(r => r.data)
      setTestResults(prev => ({
        ...prev,
        [id]: { loading: false, ok: res.ok ?? true, message: res.message || '성공' },
      }))
    } catch (err) {
      const message = err.response?.data?.message || err.response?.data?.detail || '연결 실패'
      setTestResults(prev => ({
        ...prev,
        [id]: { loading: false, ok: false, message },
      }))
    }
  }

  const handleOpenForm = (featureKey) => {
    const feature = FEATURES.find(f => f.key === featureKey)
    setOpenFormFor(featureKey)
    setFormData({ provider: feature?.providers[0]?.value ?? '', api_key: '' })
  }

  const handleCreateSubmit = (featureKey) => {
    if (!formData.provider) return
    createConfigMutation.mutate({
      feature_type: featureKey,
      provider: formData.provider,
      api_key: formData.api_key,
    })
  }

  // --- Access guard ---
  if (!user?.is_admin) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: '#f7f7f5',
        fontFamily: "'Inter', 'Noto Sans KR', sans-serif",
        fontSize: 15, color: '#6b6b6b',
      }}>
        접근 권한이 없습니다.
      </div>
    )
  }

  // --- Shared style tokens ---
  const card = {
    background: 'white',
    border: '1px solid #e9e9e7',
    borderRadius: 10,
  }

  const tabBase = {
    padding: '8px 20px',
    fontSize: 13,
    fontWeight: 500,
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'background 0.15s',
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f7f7f5',
      fontFamily: "'Inter', 'Noto Sans KR', sans-serif",
      padding: '32px 40px',
    }}>
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', letterSpacing: '-0.02em' }}>
          관리자 페이지
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b', marginTop: 4 }}>
          사용자 계정 및 모듈별 접근 권한을 관리합니다.
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { key: 'users',        label: '사용자 목록' },
          { key: 'perms',        label: '권한 관리' },
          { key: 'api_settings', label: '외부 API 관리' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              ...tabBase,
              background: activeTab === tab.key ? '#1a1a2e' : 'white',
              color:      activeTab === tab.key ? 'white'    : '#6b6b6b',
              border:     activeTab === tab.key ? 'none'     : '1px solid #e9e9e7',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: 사용자 목록 */}
      {activeTab === 'users' && (
        <div style={{ ...card, padding: 0, overflow: 'hidden', maxWidth: 720 }}>
          {usersLoading && (
            <div style={{ padding: 24, fontSize: 13, color: '#9b9b9b' }}>불러오는 중...</div>
          )}
          {usersError && (
            <div style={{ padding: 24, fontSize: 13, color: '#d44c47' }}>
              사용자 목록을 불러오지 못했습니다.
            </div>
          )}
          {!usersLoading && !usersError && users.length === 0 && (
            <div style={{ padding: 24, fontSize: 13, color: '#9b9b9b' }}>등록된 사용자가 없습니다.</div>
          )}
          {!usersLoading && users.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e9e9e7', background: '#fafafa' }}>
                  {['이름', '이메일', '부서', '관리자 여부'].map(h => (
                    <th key={h} style={{
                      textAlign: 'left', padding: '10px 16px',
                      fontWeight: 600, color: '#6b6b6b', fontSize: 12,
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => {
                  const isSelf = u.id === user?.id
                  const isPending = toggleAdminMutation.isPending && toggleAdminMutation.variables?.userId === u.id
                  return (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: i < users.length - 1 ? '1px solid #f0f0ee' : 'none',
                        background: isPending ? '#fafafa' : 'white',
                      }}
                    >
                      <td style={{ padding: '10px 16px', color: '#1a1a1a', fontWeight: 500 }}>
                        {u.name}
                        {isSelf && (
                          <span style={{ fontSize: 10, color: '#9b9b9b', marginLeft: 6 }}>(나)</span>
                        )}
                      </td>
                      <td style={{ padding: '10px 16px', color: '#6b6b6b' }}>{u.email}</td>
                      <td style={{ padding: '10px 16px', color: '#6b6b6b' }}>{u.department || '—'}</td>
                      <td style={{ padding: '10px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          {/* Toggle switch */}
                          <button
                            disabled={isSelf || isPending}
                            onClick={() => toggleAdminMutation.mutate({ userId: u.id, isAdmin: !u.is_admin })}
                            title={isSelf ? '자신의 권한은 변경할 수 없습니다' : (u.is_admin ? '관리자 해제' : '관리자 지정')}
                            style={{
                              width: 40, height: 22, borderRadius: 11,
                              border: 'none', cursor: isSelf ? 'not-allowed' : 'pointer',
                              background: u.is_admin ? '#1a1a2e' : '#d9d9d6',
                              position: 'relative',
                              transition: 'background 0.2s',
                              opacity: isSelf ? 0.4 : 1,
                              flexShrink: 0,
                            }}
                          >
                            <span style={{
                              position: 'absolute',
                              top: 3, left: u.is_admin ? 21 : 3,
                              width: 16, height: 16, borderRadius: '50%',
                              background: 'white',
                              transition: 'left 0.2s',
                              boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                            }} />
                          </button>
                          {/* Label */}
                          <span style={{
                            fontSize: 12, fontWeight: 600,
                            color: u.is_admin ? '#1a73e8' : '#9b9b9b',
                          }}>
                            {isPending ? '변경 중...' : (u.is_admin ? '관리자' : '일반')}
                          </span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Tab: 권한 관리 */}
      {activeTab === 'perms' && (
        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

          {/* Left: user list panel */}
          <div style={{ ...card, width: 240, flexShrink: 0, overflow: 'hidden' }}>
            <div style={{
              padding: '12px 16px',
              fontSize: 12, fontWeight: 600, color: '#6b6b6b',
              borderBottom: '1px solid #e9e9e7',
              background: '#fafafa',
            }}>
              사용자
            </div>
            {usersLoading && (
              <div style={{ padding: 16, fontSize: 13, color: '#9b9b9b' }}>불러오는 중...</div>
            )}
            {!usersLoading && users.length === 0 && (
              <div style={{ padding: 16, fontSize: 13, color: '#9b9b9b' }}>사용자 없음</div>
            )}
            {!usersLoading && users.map(u => {
              const isSelected = selectedUser?.id === u.id
              return (
                <div
                  key={u.id}
                  onClick={() => setSelectedUser(u)}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    background: isSelected ? '#f0f0ff' : 'transparent',
                    borderLeft: isSelected ? '3px solid #1a1a2e' : '3px solid transparent',
                    borderBottom: '1px solid #f0f0ee',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: isSelected ? 600 : 400, color: '#1a1a1a' }}>
                    {u.name}
                  </div>
                  <div style={{ fontSize: 11, color: '#9b9b9b', marginTop: 2 }}>{u.email}</div>
                </div>
              )
            })}
          </div>

          {/* Right: permissions editor */}
          <div style={{ flex: 1, ...card, overflow: 'hidden' }}>
            {!selectedUser ? (
              <div style={{
                padding: 40, textAlign: 'center',
                fontSize: 13, color: '#9b9b9b',
              }}>
                왼쪽에서 사용자를 선택하면 권한을 설정할 수 있습니다.
              </div>
            ) : (
              <>
                <div style={{
                  padding: '14px 20px',
                  borderBottom: '1px solid #e9e9e7',
                  background: '#fafafa',
                  display: 'flex', alignItems: 'center', gap: 12,
                }}>
                  <div>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>
                      {selectedUser.name}
                    </span>
                    <span style={{ fontSize: 12, color: '#9b9b9b', marginLeft: 8 }}>
                      {selectedUser.email}
                    </span>
                  </div>
                  <span style={{ fontSize: 13, color: '#6b6b6b', marginLeft: 'auto' }}>
                    권한 설정
                  </span>
                </div>

                {permsLoading ? (
                  <div style={{ padding: 24, fontSize: 13, color: '#9b9b9b' }}>불러오는 중...</div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #e9e9e7', background: '#fafafa' }}>
                          <th style={{
                            textAlign: 'left', padding: '10px 20px',
                            fontWeight: 600, color: '#6b6b6b', fontSize: 12, width: '40%',
                          }}>
                            모듈
                          </th>
                          {PERM_COLS.map(col => (
                            <th key={col.key} style={{
                              textAlign: 'center', padding: '10px 16px',
                              fontWeight: 600, color: '#6b6b6b', fontSize: 12,
                            }}>
                              {col.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {MODULES.map((mod, i) => (
                          <tr
                            key={mod.key}
                            style={{
                              borderBottom: i < MODULES.length - 1 ? '1px solid #f0f0ee' : 'none',
                            }}
                          >
                            <td style={{ padding: '10px 20px', color: '#1a1a1a', fontWeight: 500 }}>
                              {mod.label}
                            </td>
                            {PERM_COLS.map(col => (
                              <td key={col.key} style={{ textAlign: 'center', padding: '10px 16px' }}>
                                <input
                                  type="checkbox"
                                  id={`perm-${mod.key}-${col.key}`}
                                  checked={permState[mod.key]?.[col.key] ?? false}
                                  onChange={() => togglePerm(mod.key, col.key)}
                                  style={{ width: 15, height: 15, cursor: 'pointer', accentColor: '#1a1a2e' }}
                                />
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div style={{
                  padding: '14px 20px',
                  borderTop: '1px solid #e9e9e7',
                  display: 'flex', alignItems: 'center', gap: 16,
                }}>
                  <button
                    onClick={() => saveMutation.mutate()}
                    disabled={saveMutation.isPending || permsLoading}
                    style={{
                      padding: '9px 24px',
                      background: (saveMutation.isPending || permsLoading) ? '#d3d3cf' : '#1a1a2e',
                      color: 'white', border: 'none', borderRadius: 6,
                      fontSize: 13, fontWeight: 600,
                      cursor: (saveMutation.isPending || permsLoading) ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {saveMutation.isPending ? '저장 중...' : '저장'}
                  </button>

                  {saveMsg.text && (
                    <span style={{
                      fontSize: 13,
                      color: saveMsg.type === 'success' ? '#2e7d32' : '#d44c47',
                    }}>
                      {saveMsg.text}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Tab: 외부 API 관리 */}
      {activeTab === 'api_settings' && (
        <div>
          {configsLoading && (
            <div style={{ fontSize: 13, color: '#9b9b9b', padding: '8px 0' }}>불러오는 중...</div>
          )}

          {/* 2-column feature card grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(480px, 1fr))',
            gap: 20,
          }}>
            {FEATURES.map(feature => {
              const featureConfigs = configs.filter(c => c.feature_type === feature.key)
              const isFormOpen = openFormFor === feature.key

              return (
                <div
                  key={feature.key}
                  style={{
                    ...card,
                    padding: 20,
                  }}
                >
                  {/* Card header */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 6,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 20, lineHeight: 1 }}>{feature.icon}</span>
                      <span style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>
                        {feature.label}
                      </span>
                    </div>
                    <button
                      onClick={() => isFormOpen ? setOpenFormFor(null) : handleOpenForm(feature.key)}
                      style={{
                        padding: '5px 14px',
                        fontSize: 12,
                        fontWeight: 600,
                        background: isFormOpen ? '#f0f0ee' : '#1a1a2e',
                        color: isFormOpen ? '#6b6b6b' : 'white',
                        border: 'none',
                        borderRadius: 6,
                        cursor: 'pointer',
                        flexShrink: 0,
                      }}
                    >
                      {isFormOpen ? '취소' : '+ 등록'}
                    </button>
                  </div>

                  {/* Feature description */}
                  <div style={{ fontSize: 12, color: '#9b9b9b', marginBottom: 14 }}>
                    {feature.desc}
                  </div>

                  {/* Inline registration form */}
                  {isFormOpen && (
                    <div style={{
                      background: '#f7f7f5',
                      border: '1px solid #e9e9e7',
                      borderRadius: 8,
                      padding: '14px 16px',
                      marginBottom: 14,
                    }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {/* Provider select */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <label style={{
                            fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                            width: 56, flexShrink: 0,
                          }}>
                            Provider
                          </label>
                          <select
                            value={formData.provider}
                            onChange={e => setFormData(prev => ({ ...prev, provider: e.target.value }))}
                            style={{
                              flex: 1,
                              padding: '6px 10px',
                              fontSize: 13,
                              border: '1px solid #e9e9e7',
                              borderRadius: 6,
                              background: 'white',
                              color: '#1a1a1a',
                              outline: 'none',
                            }}
                          >
                            {feature.providers.map(p => (
                              <option key={p.value} value={p.value}>{p.label}</option>
                            ))}
                          </select>
                        </div>

                        {/* API key input */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <label style={{
                            fontSize: 12, fontWeight: 600, color: '#6b6b6b',
                            width: 56, flexShrink: 0,
                          }}>
                            API 키
                          </label>
                          <input
                            type="text"
                            value={formData.api_key}
                            onChange={e => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                            placeholder="키 불필요인 경우 비워두세요"
                            style={{
                              flex: 1,
                              padding: '6px 10px',
                              fontSize: 13,
                              border: '1px solid #e9e9e7',
                              borderRadius: 6,
                              background: 'white',
                              color: '#1a1a1a',
                              outline: 'none',
                            }}
                          />
                        </div>

                        {/* Form actions */}
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 2 }}>
                          <button
                            onClick={() => handleCreateSubmit(feature.key)}
                            disabled={createConfigMutation.isPending}
                            style={{
                              padding: '6px 18px',
                              fontSize: 12,
                              fontWeight: 600,
                              background: createConfigMutation.isPending ? '#d3d3cf' : '#1a1a2e',
                              color: 'white',
                              border: 'none',
                              borderRadius: 6,
                              cursor: createConfigMutation.isPending ? 'not-allowed' : 'pointer',
                            }}
                          >
                            {createConfigMutation.isPending ? '등록 중...' : '등록'}
                          </button>
                          <button
                            onClick={() => {
                              setOpenFormFor(null)
                              setFormData({ provider: '', api_key: '' })
                            }}
                            style={{
                              padding: '6px 14px',
                              fontSize: 12,
                              fontWeight: 500,
                              background: 'white',
                              color: '#6b6b6b',
                              border: '1px solid #e9e9e7',
                              borderRadius: 6,
                              cursor: 'pointer',
                            }}
                          >
                            취소
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Divider */}
                  <div style={{ borderTop: '1px solid #f0f0ee', marginBottom: 10 }} />

                  {/* Config rows */}
                  {featureConfigs.length === 0 ? (
                    <div style={{ fontSize: 12, color: '#9b9b9b', padding: '6px 0' }}>
                      등록된 API 없음
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {featureConfigs.map(cfg => {
                        const providerLabel =
                          feature.providers.find(p => p.value === cfg.provider)?.label ?? cfg.provider
                        const tr = testResults[cfg.id]
                        const timeAgo = formatTestTime(cfg.last_tested_at)

                        return (
                          <div
                            key={cfg.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 10,
                              padding: '8px 10px',
                              background: '#fafafa',
                              borderRadius: 7,
                              border: '1px solid #f0f0ee',
                              flexWrap: 'wrap',
                            }}
                          >
                            {/* Provider name */}
                            <span style={{
                              fontSize: 13,
                              fontWeight: 500,
                              color: '#1a1a1a',
                              flex: '1 1 120px',
                              minWidth: 0,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}>
                              {providerLabel}
                            </span>

                            {/* Active status badge */}
                            <span style={{
                              fontSize: 11,
                              fontWeight: 600,
                              padding: '2px 8px',
                              borderRadius: 4,
                              background: cfg.is_active ? '#e8f8e8' : '#f0f0ee',
                              color:      cfg.is_active ? '#2e7d32' : '#6b6b6b',
                              flexShrink: 0,
                            }}>
                              {cfg.is_active ? '활성' : '비활성'}
                            </span>

                            {/* Last test result */}
                            <span style={{
                              fontSize: 11,
                              color: tr
                                ? (tr.loading
                                    ? '#9b9b9b'
                                    : tr.ok ? '#2e7d32' : '#d44c47')
                                : (cfg.last_test_ok === true
                                    ? '#2e7d32'
                                    : cfg.last_test_ok === false
                                      ? '#d44c47'
                                      : '#9b9b9b'),
                              flexShrink: 0,
                              minWidth: 90,
                            }}>
                              {tr
                                ? (tr.loading
                                    ? '테스트 중...'
                                    : `${tr.ok ? '성공' : '실패'}: ${tr.message}`)
                                : timeAgo
                                  ? `마지막 테스트: ${timeAgo} · ${cfg.last_test_ok ? '성공' : '실패'}`
                                  : '미테스트'}
                            </span>

                            {/* Action buttons */}
                            <div style={{ display: 'flex', gap: 6, flexShrink: 0, marginLeft: 'auto' }}>
                              {/* Test */}
                              <button
                                onClick={() => handleTest(cfg.id)}
                                disabled={tr?.loading}
                                style={{
                                  padding: '4px 10px',
                                  fontSize: 11,
                                  fontWeight: 500,
                                  background: '#f0f4ff',
                                  color: '#3366cc',
                                  border: '1px solid #c5d5f5',
                                  borderRadius: 5,
                                  cursor: tr?.loading ? 'not-allowed' : 'pointer',
                                }}
                              >
                                테스트
                              </button>

                              {/* Toggle active/inactive */}
                              <button
                                onClick={() =>
                                  toggleActiveMutation.mutate({ id: cfg.id, is_active: !cfg.is_active })
                                }
                                disabled={toggleActiveMutation.isPending}
                                style={{
                                  padding: '4px 10px',
                                  fontSize: 11,
                                  fontWeight: 500,
                                  background: cfg.is_active ? '#fff8e1' : '#f0fff4',
                                  color:      cfg.is_active ? '#b45309' : '#2d7a2d',
                                  border: `1px solid ${cfg.is_active ? '#f5e0a0' : '#b8e8c0'}`,
                                  borderRadius: 5,
                                  cursor: toggleActiveMutation.isPending ? 'not-allowed' : 'pointer',
                                }}
                              >
                                {cfg.is_active ? '비활성화' : '활성화'}
                              </button>

                              {/* Delete */}
                              <button
                                onClick={() => {
                                  if (window.confirm(`'${providerLabel}' 설정을 삭제하시겠습니까?`)) {
                                    deleteConfigMutation.mutate(cfg.id)
                                  }
                                }}
                                disabled={deleteConfigMutation.isPending}
                                style={{
                                  padding: '4px 10px',
                                  fontSize: 11,
                                  fontWeight: 500,
                                  background: '#fff0f0',
                                  color: '#cc3333',
                                  border: '1px solid #f5c5c5',
                                  borderRadius: 5,
                                  cursor: deleteConfigMutation.isPending ? 'not-allowed' : 'pointer',
                                }}
                              >
                                삭제
                              </button>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
