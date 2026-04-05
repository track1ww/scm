import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import {
  DollarSign, Factory, Warehouse, Users,
  Package, ShoppingCart,
  TrendingUp, AlertTriangle, CheckCircle, Clock,
  Globe,
} from 'lucide-react'
import client from '../api/client'
import useAuthStore from '../stores/authStore'

const fetchSummary = () => client.get('/dashboard/summary/').then(r => r.data)

function formatKRW(amount) {
  if (!amount) return '0원'
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억원`
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}만원`
  return `${amount.toLocaleString()}원`
}

function KpiCard({ icon: Icon, label, value, sub, color = 'blue', alert = false }) {
  const colorMap = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-green-50 text-green-600',
    amber:  'bg-amber-50 text-amber-600',
    red:    'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    indigo: 'bg-indigo-50 text-indigo-600',
  }
  return (
    <div className={`bg-white rounded-lg border p-4 flex items-start gap-4 ${alert ? 'border-amber-300' : 'border-gray-200'}`}>
      <div className={`p-2 rounded-lg shrink-0 ${colorMap[color]}`}>
        <Icon size={20} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 mb-1">{label}</p>
        <p className="text-xl font-bold text-gray-900">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function SectionHeader({ icon: Icon, title, color }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={16} className={color} />
      <h3 className="font-semibold text-gray-700 text-sm">{title}</h3>
    </div>
  )
}

const CHART_COLORS = {
  primary: '#2563eb',
  success: '#16a34a',
  warning: '#d97706',
  danger:  '#dc2626',
  indigo:  '#4f46e5',
  gray:    '#6b7280',
}

export default function DashboardPage() {
  const user = useAuthStore(s => s.user)
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: fetchSummary,
    refetchInterval: 60000,
  })

  const { data: activeFeatures = [] } = useQuery({
    queryKey: ['external-active-features'],
    queryFn: () => client.get('/external/configs/active-features/').then(r => r.data?.active_features || []).catch(() => []),
    staleTime: 5 * 60 * 1000,
  })

  const hasExchangeRate = activeFeatures.includes('exchange_rate')

  const { data: rateData } = useQuery({
    queryKey: ['external-exchange-rates'],
    queryFn: () => client.get('/external/proxy/exchange-rates/').then(r => r.data),
    enabled: hasExchangeRate,
    refetchInterval: 300000,
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
      대시보드 로딩 중...
    </div>
  )
  if (error) return (
    <div className="flex items-center justify-center h-64 text-red-500 text-sm">
      데이터를 불러올 수 없습니다.
    </div>
  )

  const d = data || {}
  const fi = d.fi || {}
  const pp = d.pp || {}
  const wm = d.wm || {}
  const hr = d.hr || {}
  const mm = d.mm || {}
  const sd = d.sd || {}
  const wf = d.workflow || {}

  const today = new Date().toLocaleDateString('ko-KR', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  })

  // Chart data
  const ppChartData = [
    { name: '계획', value: pp.planned || 0, fill: CHART_COLORS.primary },
    { name: '생산중', value: pp.in_progress || 0, fill: CHART_COLORS.warning },
    { name: '완료', value: pp.completed || 0, fill: CHART_COLORS.success },
  ]

  const wmPieData = [
    { name: '정상재고', value: Math.max(0, (wm.total_items || 0) - (wm.low_stock || 0)) },
    { name: '부족재고', value: wm.low_stock || 0 },
  ]
  const wmPieColors = [CHART_COLORS.success, CHART_COLORS.danger]

  const hrChartData = [
    { name: '재직', value: hr.employee_count || 0, fill: CHART_COLORS.indigo },
    { name: '오늘출근', value: hr.attendance_today || 0, fill: CHART_COLORS.primary },
    { name: '휴가대기', value: hr.pending_leaves || 0, fill: CHART_COLORS.warning },
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">경영 대시보드</h1>
        <p className="text-sm text-gray-500 mt-1">{today} · {user?.name || user?.email || '사용자'}</p>
      </div>

      {/* Alerts */}
      {(wm.low_stock > 0 || wf.pending_approvals > 0 || hr.pending_leaves > 0) && (
        <div className="mb-6 flex flex-wrap gap-3">
          {wm.low_stock > 0 && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-sm text-amber-700">
              <AlertTriangle size={14} /> 재고 부족 <strong>{wm.low_stock}건</strong>
            </div>
          )}
          {wf.pending_approvals > 0 && (
            <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-sm text-blue-700">
              <Clock size={14} /> 결재 대기 <strong>{wf.pending_approvals}건</strong>
            </div>
          )}
          {hr.pending_leaves > 0 && (
            <div className="flex items-center gap-2 bg-purple-50 border border-purple-200 rounded-lg px-4 py-2 text-sm text-purple-700">
              <Users size={14} /> 휴가 승인 대기 <strong>{hr.pending_leaves}건</strong>
            </div>
          )}
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
        <div className="bg-gray-50 rounded-xl p-4">
          <SectionHeader icon={DollarSign} title="재무회계 (FI)" color="text-blue-600" />
          <div className="space-y-3">
            <KpiCard icon={TrendingUp} label="당월 매출" value={formatKRW(fi.monthly_revenue || 0)} color="blue" />
            <KpiCard icon={CheckCircle} label="전기 완료" value={`${fi.posted_count || 0}건`} sub={`임시 ${fi.draft_count || 0}건`} color="green" />
            <KpiCard
              icon={TrendingUp}
              label="예산 집행률"
              value={`${fi.budget_execution_rate ?? 0}%`}
              sub={`예산 ${formatKRW(fi.budget_total || 0)}`}
              color={fi.budget_execution_rate > 90 ? 'red' : fi.budget_execution_rate > 70 ? 'amber' : 'green'}
            />
          </div>
          {fi.budget_execution_rate !== undefined && (
            <div className="mt-3 px-1">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>예산 집행</span>
                <span>{fi.budget_execution_rate}%</span>
              </div>
              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    fi.budget_execution_rate > 90 ? 'bg-red-500' :
                    fi.budget_execution_rate > 70 ? 'bg-amber-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(fi.budget_execution_rate, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <SectionHeader icon={Factory} title="생산계획 (PP)" color="text-indigo-600" />
          <div className="space-y-3">
            <KpiCard icon={Factory} label="생산 중" value={`${pp.in_progress || 0}건`} sub={`전체 ${pp.total || 0}건`} color="indigo" />
            <KpiCard icon={CheckCircle} label="완료" value={`${pp.completed || 0}건`} sub={`계획 ${pp.planned || 0}건`} color="green" />
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <SectionHeader icon={Warehouse} title="창고관리 (WM)" color="text-amber-600" />
          <div className="space-y-3">
            <KpiCard icon={Warehouse} label="관리 품목" value={`${wm.total_items || 0}개`} sub={`오늘 입출고 ${wm.movements_today || 0}건`} color="amber" />
            <KpiCard icon={AlertTriangle} label="재고 부족" value={`${wm.low_stock || 0}개`} color={wm.low_stock > 0 ? 'red' : 'green'} alert={wm.low_stock > 0} />
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <SectionHeader icon={Users} title="인사관리 (HR)" color="text-purple-600" />
          <div className="space-y-3">
            <KpiCard icon={Users} label="재직 인원" value={`${hr.employee_count || 0}명`} sub={`오늘 출근 ${hr.attendance_today || 0}명`} color="purple" />
            <KpiCard icon={Clock} label="휴가 승인 대기" value={`${hr.pending_leaves || 0}건`} color={hr.pending_leaves > 0 ? 'amber' : 'green'} />
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <SectionHeader icon={Package} title="자재관리 (MM)" color="text-green-600" />
          <div className="space-y-3">
            <KpiCard icon={Package} label="등록 자재" value={`${mm.material_count || 0}개`} color="green" />
            <KpiCard icon={Clock} label="발주 진행 중" value={`${mm.pending_orders || 0}건`} color="amber" />
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <SectionHeader icon={ShoppingCart} title="판매출하 (SD)" color="text-red-600" />
          <div className="space-y-3">
            <KpiCard icon={ShoppingCart} label="당월 수주" value={`${sd.monthly_orders || 0}건`} color="blue" />
            <KpiCard icon={Clock} label="출하 대기" value={`${sd.pending_delivery || 0}건`} color={sd.pending_delivery > 5 ? 'red' : 'amber'} />
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">

        {/* PP Bar Chart */}
        <div className="xl:col-span-1 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-700 text-sm mb-4">생산 현황</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={ppChartData} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="건수" radius={[4, 4, 0, 0]}>
                {ppChartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* WM Pie Chart */}
        <div className="xl:col-span-1 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-700 text-sm mb-4">재고 상태</h3>
          {wm.total_items > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={wmPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {wmPieData.map((_, i) => (
                    <Cell key={i} fill={wmPieColors[i]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v}개`, n]} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-44 text-gray-400 text-sm">
              등록된 재고 없음
            </div>
          )}
        </div>

        {/* HR Bar Chart */}
        <div className="xl:col-span-1 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-700 text-sm mb-4">인사 현황</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={hrChartData} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="인원" radius={[4, 4, 0, 0]}>
                {hrChartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>

      {/* 실시간 환율 위젯 */}
      <div className="mt-6">
        <div className="flex items-center gap-2 mb-3">
          <Globe size={16} className="text-blue-500" />
          <h3 className="font-semibold text-gray-700 text-sm">실시간 환율</h3>
          {hasExchangeRate && <span className="text-xs text-gray-400 ml-1">5분마다 갱신</span>}
        </div>
        {!hasExchangeRate ? (
          <div className="border border-dashed border-gray-300 rounded-lg p-5 text-center text-sm text-gray-400 bg-gray-50">
            관리자 페이지 &gt; 외부 API 관리에서 환율 API를 등록하시면 나타납니다.
          </div>
        ) : rateData ? (() => {
          const kr = rateData.krw_rates || {}
          const usdKrw = rateData.rates?.KRW
          const currencies = [
            { code: 'USD', flag: '🇺🇸', rate: usdKrw,   label: 'USD',     jpyMode: false },
            { code: 'EUR', flag: '🇪🇺', rate: kr.EUR,    label: 'EUR',     jpyMode: false },
            { code: 'JPY', flag: '🇯🇵', rate: kr.JPY,    label: 'JPY 100', jpyMode: true  },
            { code: 'CNY', flag: '🇨🇳', rate: kr.CNY,    label: 'CNY',     jpyMode: false },
            { code: 'GBP', flag: '🇬🇧', rate: kr.GBP,    label: 'GBP',     jpyMode: false },
          ].filter(c => c.rate != null)
          return (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {currencies.map(c => {
                const displayRate = c.jpyMode
                  ? (c.rate * 100).toLocaleString('ko-KR', { maximumFractionDigits: 2 })
                  : Math.round(c.rate).toLocaleString('ko-KR')
                return (
                  <div key={c.code} className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col gap-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-lg leading-none">{c.flag}</span>
                      <span className="text-xs font-semibold text-gray-500">{c.label}</span>
                    </div>
                    <div className="text-lg font-bold text-gray-900">
                      {displayRate}<span className="text-xs font-normal text-gray-400 ml-0.5">원</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        })() : (
          <div className="text-sm text-gray-400">환율 정보를 불러오는 중...</div>
        )}
      </div>

      <p className="text-xs text-gray-400 text-right mt-4">60초마다 자동 갱신</p>
    </div>
  )
}
