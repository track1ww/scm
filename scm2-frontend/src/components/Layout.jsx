import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Package, ShoppingCart, Warehouse, Factory,
  Users, DollarSign, CheckSquare, Truck,
  ClipboardList, LayoutDashboard, MessageSquare,
  LogOut, Microscope, GitMerge, Bell, Menu, X,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import useAuthStore from '../stores/authStore'
import client from '../api/client'
import NotificationPanel from './NotificationPanel'
import { useNotificationSocket } from '../hooks/useNotificationSocket'

const MENU = [
  { path: '/',     icon: <LayoutDashboard size={16} />, label: '대시보드' },
  { path: '/mm',   icon: <ShoppingCart size={16} />,   label: 'MM 자재관리' },
  { path: '/sd',   icon: <ShoppingCart size={16} />,   label: 'SD 판매출하' },
  { path: '/pp',   icon: <Factory size={16} />,        label: 'PP 생산계획' },
  { path: '/qm',   icon: <Microscope size={16} />,     label: 'QM 품질관리' },
  { path: '/wm',   icon: <Warehouse size={16} />,      label: 'WM 창고관리' },
  { path: '/tm',   icon: <Truck size={16} />,          label: 'TM 운송관리' },
  { path: '/fi',   icon: <DollarSign size={16} />,     label: 'FI 재무회계' },
  { path: '/hr',   icon: <Users size={16} />,          label: 'HR 인사관리' },
  { path: '/chat', icon: <MessageSquare size={16} />,  label: '메신저' },
  { path: '/wi',       icon: <ClipboardList size={16} />, label: '작업지시서' },
  { path: '/workflow', icon: <GitMerge size={16} />,     label: '결재 워크플로우' },
]

function UnreadBadge() {
  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => client.get('/notifications/?page=1&page_size=1').then(r => r.data),
    refetchInterval: 30000,
  })
  const count = data?.unread_count ?? 0
  if (!count) return null
  return (
    <span style={{
      position: 'absolute', top: -2, right: -2,
      width: 16, height: 16, background: '#ef4444', color: 'white',
      fontSize: 10, borderRadius: '50%', display: 'flex',
      alignItems: 'center', justifyContent: 'center', lineHeight: 1,
    }}>
      {count > 9 ? '9+' : count}
    </span>
  )
}

function Sidebar({ onClose }) {
  const { user, logout } = useAuthStore()
  const [notifOpen, setNotifOpen] = useState(false)

  return (
    <div style={{
      width: 224, flexShrink: 0, background: '#f7f7f5',
      borderRight: '1px solid #e9e9e7', display: 'flex',
      flexDirection: 'column', height: '100vh',
      position: 'sticky', top: 0, overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{ padding: '20px 16px 12px', borderBottom: '1px solid #e9e9e7', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Package size={16} /> SCM 통합관리
        </div>
        {onClose && (
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
            <X size={18} color="#6b6b6b" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav style={{ padding: 8, flex: 1 }}>
        {MENU.map(({ path, icon, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            onClick={onClose}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 10px', borderRadius: 6, marginBottom: 2,
              textDecoration: 'none', fontSize: 13, fontWeight: 500,
              color: isActive ? '#1a1a1a' : '#6b6b6b',
              background: isActive ? '#e9e9e7' : 'transparent',
              transition: 'all 0.12s',
            })}
          >
            <span style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #e9e9e7' }}>
        <div style={{ fontSize: 12, color: '#9b9b9b', marginBottom: 2 }}>로그인 중</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>
            {user?.name || '사용자'}님
          </div>
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setNotifOpen(o => !o)}
              aria-label="알림 열기"
              style={{ position: 'relative', padding: 6, background: 'none', border: 'none', cursor: 'pointer', borderRadius: 6 }}
            >
              <Bell size={18} color="#6b6b6b" aria-hidden="true" />
              <UnreadBadge />
            </button>
            <NotificationPanel isOpen={notifOpen} onClose={() => setNotifOpen(false)} />
          </div>
        </div>
        <button
          onClick={logout}
          style={{
            width: '100%', padding: '6px', fontSize: 12,
            cursor: 'pointer', background: '#fff', border: '1px solid #ddd',
            borderRadius: 4,
          }}
        >
          로그아웃
        </button>
      </div>
    </div>
  )
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  useNotificationSocket()

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>

      {/* ── 데스크탑 사이드바 (768px 이상) ── */}
      <div style={{ display: 'none' }} className="sidebar-desktop">
        <Sidebar />
      </div>

      {/* ── 모바일 오버레이 사이드바 ── */}
      {mobileOpen && (
        <>
          <div
            onClick={() => setMobileOpen(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 40,
              background: 'rgba(0,0,0,0.4)',
            }}
          />
          <div style={{ position: 'fixed', inset: '0 auto 0 0', zIndex: 50, display: 'flex' }}>
            <Sidebar onClose={() => setMobileOpen(false)} />
          </div>
        </>
      )}

      {/* ── 메인 콘텐츠 ── */}
      <main style={{ flex: 1, minWidth: 0, background: '#ffffff', display: 'flex', flexDirection: 'column' }}>
        {/* 모바일 햄버거 헤더 */}
        <div className="mobile-header" style={{ display: 'none', alignItems: 'center', padding: '8px 16px', borderBottom: '1px solid #e9e9e7', background: '#f7f7f5' }}>
          <button
            onClick={() => setMobileOpen(true)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, borderRadius: 6 }}
          >
            <Menu size={20} color="#1a1a1a" />
          </button>
          <span style={{ marginLeft: 8, fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>SCM 통합관리</span>
        </div>

        <div style={{ padding: '12px 24px', flex: 1 }}>
          <Outlet />
        </div>
      </main>
    </div>
  )
}
