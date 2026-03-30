import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

function KpiCard({ icon, label, value, sub, color = '#2383e2' }) {
  return (
    <div style={{
      background: 'white', border: '1px solid #e9e9e7',
      borderRadius: 10, padding: '18px 20px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div style={{ fontSize: 11, fontWeight: 500, color: '#9b9b9b', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span>{icon}</span> {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a1a', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#9b9b9b', marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

export default function DashboardPage() {
  const { data: poData } = useQuery({
    queryKey: ['po-dashboard'],
    queryFn:  () => api.get('/mm/orders/dashboard/').then(r => r.data),
  })

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a1a', marginBottom: 4, letterSpacing: '-0.02em' }}>
        대시보드
      </h1>
      <p style={{ fontSize: 13, color: '#9b9b9b', marginBottom: 32 }}>
        SCM 통합관리 시스템 현황
      </p>

      {/* KPI */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        <KpiCard icon="📋" label="진행 중 발주"   value={poData?.pending  ?? '-'} sub="미입고 발주건수" />
        <KpiCard icon="✅" label="입고 완료"      value={poData?.complete ?? '-'} sub="이번 달 기준" />
        <KpiCard icon="📦" label="전체 발주"      value={poData?.total    ?? '-'} sub="누적" />
        <KpiCard icon="💬" label="메신저"         value="실시간" sub="WebSocket 연결" color="#0f9960" />
      </div>

      {/* 빠른 이동 */}
      <div style={{ fontSize: 11, fontWeight: 600, color: '#9b9b9b', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 12 }}>
        빠른 이동
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { icon: '🛒', label: 'MM 자재관리', path: '/mm' },
          { icon: '🛍️', label: 'SD 판매출하', path: '/sd' },
          { icon: '📦', label: 'WM 창고관리', path: '/wm' },
          { icon: '💰', label: 'FI 재무회계', path: '/fi' },
          { icon: '👥', label: 'HR 인사관리', path: '/hr' },
          { icon: '💬', label: '메신저',       path: '/chat' },
          { icon: '📋', label: '작업지시서',   path: '/wi' },
          { icon: '🔬', label: 'QM 품질관리', path: '/qm' },
        ].map(({ icon, label, path }) => (
          <a
            key={path}
            href={path}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '14px 16px', background: '#f7f7f5',
              border: '1px solid #e9e9e7', borderRadius: 8,
              textDecoration: 'none', color: '#1a1a1a',
              fontSize: 13, fontWeight: 500,
              transition: 'all 0.12s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#f1f1ef'}
            onMouseLeave={e => e.currentTarget.style.background = '#f7f7f5'}
          >
            <span style={{ fontSize: 18 }}>{icon}</span>
            {label}
          </a>
        ))}
      </div>
    </div>
  )
}
