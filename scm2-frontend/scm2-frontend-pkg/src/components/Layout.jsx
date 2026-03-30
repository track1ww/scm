import { NavLink, Outlet } from 'react-router-dom'
import useAuthStore from '../stores/authStore'

const MENU = [
  { path: '/',        icon: '📊', label: '대시보드' },
  { path: '/mm',      icon: '🛒', label: 'MM 자재관리' },
  { path: '/sd',      icon: '🛍️', label: 'SD 판매출하' },
  { path: '/pp',      icon: '🏭', label: 'PP 생산계획' },
  { path: '/qm',      icon: '🔬', label: 'QM 품질관리' },
  { path: '/wm',      icon: '📦', label: 'WM 창고관리' },
  { path: '/tm',      icon: '🚢', label: 'TM 운송관리' },
  { path: '/fi',      icon: '💰', label: 'FI 재무회계' },
  { path: '/hr',      icon: '👥', label: 'HR 인사관리' },
  { path: '/chat',    icon: '💬', label: '메신저' },
  { path: '/wi',      icon: '📋', label: '작업지시서' },
]

export default function Layout() {
  const { user, logout } = useAuthStore()

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 사이드바 */}
      <div style={{
        width: 220, background: '#f7f7f5',
        borderRight: '1px solid #e9e9e7',
        display: 'flex', flexDirection: 'column',
        position: 'fixed', top: 0, left: 0, height: '100vh',
        overflowY: 'auto',
      }}>
        {/* 로고 */}
        <div style={{ padding: '20px 16px 12px', borderBottom: '1px solid #e9e9e7' }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>📦 SCM 통합관리</div>
        </div>

        {/* 메뉴 */}
        <nav style={{ padding: '8px 8px', flex: 1 }}>
          {MENU.map(({ path, icon, label }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '7px 10px', borderRadius: 6, marginBottom: 2,
                textDecoration: 'none', fontSize: 13, fontWeight: 500,
                color: isActive ? '#1a1a1a' : '#6b6b6b',
                background: isActive ? '#e9e9e7' : 'transparent',
                transition: 'all 0.12s',
              })}
            >
              <span style={{ fontSize: 14 }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* 사용자 정보 */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid #e9e9e7' }}>
          <div style={{ fontSize: 12, color: '#9b9b9b', marginBottom: 2 }}>로그인 중</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{user?.name}</div>
          <div style={{ fontSize: 11, color: '#6b6b6b', marginBottom: 10 }}>{user?.email}</div>
          <button
            onClick={logout}
            style={{
              width: '100%', padding: '6px', fontSize: 12,
              background: 'white', border: '1px solid #d3d3cf',
              borderRadius: 6, cursor: 'pointer', color: '#6b6b6b',
            }}
          >
            로그아웃
          </button>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div style={{ marginLeft: 220, flex: 1, padding: '32px 40px', background: 'white', minHeight: '100vh' }}>
        <Outlet />
      </div>
    </div>
  )
}
