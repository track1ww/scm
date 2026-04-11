import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../api/client'

const TABS = ['재고 계산기', '발주 수요예측', '재고이관 목록']

const INV_TYPES = [
  { value: 'raw_material',  label: '원자재' },
  { value: 'finished_good', label: '완제품' },
  { value: 'semi_finished', label: '반제품' },
  { value: 'mro',           label: '소모품/MRO' },
  { value: 'perishable',    label: '신선/냉장' },
]

const FORECAST_METHODS = [
  { value: 'sma', label: '단순 이동평균 (SMA)' },
  { value: 'wma', label: '가중 이동평균 (WMA)' },
  { value: 'exp', label: '지수 평활 (Exponential)' },
]

// ─── 공통 스타일 ──────────────────────────────────────────────
const S = {
  card: {
    background: 'white', border: '1px solid #e9e9e7',
    borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
  },
  label: { fontSize: 12, color: '#6b6b6b', marginBottom: 4, display: 'block' },
  input: {
    width: '100%', padding: '8px 10px',
    border: '1px solid #e9e9e7', borderRadius: 6,
    fontSize: 13, boxSizing: 'border-box', outline: 'none',
  },
  select: {
    width: '100%', padding: '8px 10px',
    border: '1px solid #e9e9e7', borderRadius: 6,
    fontSize: 13, boxSizing: 'border-box',
    background: 'white', cursor: 'pointer',
  },
  field: { marginBottom: 12 },
  btn: {
    background: '#1a1a2e', color: 'white',
    padding: '10px 20px', borderRadius: 6, border: 'none',
    cursor: 'pointer', fontSize: 13, fontWeight: 500,
  },
  resultBox: {
    background: '#f5f7ff', border: '1px solid #d0daff',
    borderRadius: 8, padding: 16, marginTop: 16,
  },
  resultRow: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', padding: '6px 0',
    borderBottom: '1px solid #e8ecf8',
  },
  resultLabel: { fontSize: 12, color: '#6b6b6b' },
  resultValue: { fontSize: 15, fontWeight: 700, color: '#1a1a2e' },
  badge: (color) => ({
    display: 'inline-block', padding: '2px 8px',
    borderRadius: 99, fontSize: 11, fontWeight: 600,
    background: color === 'red'    ? '#fdecea' :
                color === 'orange' ? '#fff8e1' :
                color === 'green'  ? '#e8f5e9' : '#f0f0f0',
    color:      color === 'red'    ? '#d44c47' :
                color === 'orange' ? '#b45309' :
                color === 'green'  ? '#2e7d32' : '#6b6b6b',
  }),
}

// 리드타임 출처 배지 색상
const ltSourceColor = { material_supplier: 'green', material: 'blue', supplier: 'orange', default: 'gray' }
const ltSourceBg    = { green: '#e8f5e9', blue: '#e3f2fd', orange: '#fff8e1', gray: '#f5f5f3' }
const ltSourceFg    = { green: '#2e7d32', blue: '#1565c0', orange: '#b45309', gray: '#6b6b6b' }

function LeadTimeBadge({ source, label }) {
  const c = ltSourceColor[source] || 'gray'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 99,
      fontSize: 10, fontWeight: 600,
      background: ltSourceBg[c], color: ltSourceFg[c],
      marginLeft: 6, verticalAlign: 'middle',
    }}>
      {label}
    </span>
  )
}

// ─── 날씨/경제지표 유틸 ──────────────────────────────────────
function isBadWeather(weather) {
  if (!weather?.current) return false
  const id   = weather.current.weather_id ?? 0
  const wind = weather.current.wind_speed  ?? 0
  // 뇌우(200-299) / 이슬비·비(300-599) / 눈(600-699) / 강풍(10 m/s 이상)
  return (id >= 200 && id < 700) || wind >= 10
}

function WeatherSummaryBar({ weather }) {
  if (!weather?.current) return null
  const c = weather.current
  const bad = isBadWeather(weather)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      padding: '8px 14px', borderRadius: 8, marginBottom: 12,
      background: bad ? '#fff8e1' : '#f0fdf4',
      border: `1px solid ${bad ? '#fbbf24' : '#86efac'}`,
      fontSize: 12,
    }}>
      <span style={{ fontSize: 20 }}>{c.icon}</span>
      <span style={{ fontWeight: 600, color: bad ? '#b45309' : '#166534' }}>{c.description}</span>
      <span style={{ color: '#6b6b6b' }}>🌡 {c.temp}°C (체감 {c.feels_like}°C)</span>
      <span style={{ color: '#6b6b6b' }}>💨 {c.wind_speed} m/s</span>
      <span style={{ color: '#6b6b6b' }}>💧 {c.humidity}%</span>
      {bad && (
        <span style={{
          marginLeft: 'auto', fontWeight: 700,
          color: '#b45309', background: '#fef3c7',
          padding: '2px 8px', borderRadius: 99,
        }}>
          ⚠️ 악천후
        </span>
      )}
    </div>
  )
}

function WeatherForecastStrip({ weather }) {
  if (!weather?.forecast?.length) return null
  return (
    <div style={{ display: 'flex', gap: 6, overflowX: 'auto', padding: '2px 0 8px', marginBottom: 12 }}>
      {weather.forecast.map((f, i) => (
        <div key={i} style={{
          background: 'white', border: '1px solid #e9e9e7',
          borderRadius: 8, padding: '8px 12px', textAlign: 'center',
          minWidth: 70, flexShrink: 0,
        }}>
          <div style={{ fontSize: 10, color: '#9b9b9b', marginBottom: 2 }}>{f.date}</div>
          <div style={{ fontSize: 18 }}>{f.icon}</div>
          <div style={{ fontSize: 11, color: '#3b3b3b', fontWeight: 600 }}>{f.max_temp}°</div>
          <div style={{ fontSize: 10, color: '#9b9b9b' }}>{f.min_temp}°</div>
          {f.rain_prob > 0 && (
            <div style={{ fontSize: 10, color: '#3b82f6' }}>💧{f.rain_prob}%</div>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── 탭1: 재고 계산기 ────────────────────────────────────────
function InventoryCalcTab({ weather, econ }) {
  const [materialId, setMaterialId] = useState('')
  const [supplierId, setSupplierId] = useState('')
  const [ltInfo, setLtInfo]         = useState(null)
  const [form, setForm] = useState({
    inventory_type: 'raw_material',
    avg_demand: '',
    demand_std: '',
    lead_time: '',
    service_level: '',
  })
  const [result, setResult]   = useState(null)
  const [eoqForm, setEoqForm] = useState({ annual_demand: '', order_cost: '', holding_cost: '' })
  const [eoqResult, setEoqResult] = useState(null)

  // 날씨·경제지표 파생 값
  const badWeather  = isBadWeather(weather)
  const baseRate    = econ?.base_rate?.latest ?? null   // 기준금리 (%)

  // 품목·매입처 목록
  const { data: materialsData } = useQuery({
    queryKey: ['calc-materials'],
    queryFn: () => api.get('/mm/materials/').then(r => r.data),
  })
  const { data: suppliersData } = useQuery({
    queryKey: ['calc-suppliers'],
    queryFn: () => api.get('/mm/suppliers/').then(r => r.data),
  })
  const materials = Array.isArray(materialsData) ? materialsData : (materialsData?.results ?? [])
  const suppliers = Array.isArray(suppliersData) ? suppliersData : (suppliersData?.results ?? [])

  // 품목 또는 매입처가 바뀌면 리드타임 자동 조회
  useEffect(() => {
    if (!materialId && !supplierId) { setLtInfo(null); return }
    const params = new URLSearchParams()
    if (materialId) params.append('material_id', materialId)
    if (supplierId) params.append('supplier_id', supplierId)
    api.get(`/mm/calculator/lead-time/?${params}`)
      .then(r => {
        setLtInfo(r.data)
        setForm(p => ({ ...p, lead_time: String(r.data.lead_time_days) }))
      })
      .catch(() => setLtInfo(null))
  }, [materialId, supplierId])

  const ssMutation = useMutation({
    mutationFn: () => api.post('/mm/calculator/safety-stock/', form).then(r => r.data),
    onSuccess: setResult,
  })
  const eoqMutation = useMutation({
    mutationFn: () => api.post('/mm/calculator/eoq/', eoqForm).then(r => r.data),
    onSuccess: setEoqResult,
  })

  const f  = (key) => ({ value: form[key],    onChange: e => setForm(p => ({ ...p, [key]: e.target.value })) })
  const ef = (key) => ({ value: eoqForm[key], onChange: e => setEoqForm(p => ({ ...p, [key]: e.target.value })) })

  // 기준금리 기반 보관비용 힌트 (기준금리 + 창고관리비 2% 추정)
  const holdingRateHint = baseRate != null ? (parseFloat(baseRate) + 2).toFixed(1) : null

  return (
    <div style={{ padding: 20 }}>
      {/* 날씨·경제지표 컨텍스트 바 */}
      {(weather || econ) && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: '#9b9b9b', marginBottom: 6, fontWeight: 600 }}>
            📡 실시간 참고 정보
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {/* 날씨 요약 */}
            {weather?.current && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 14px', borderRadius: 8, flex: '1 1 200px',
                background: badWeather ? '#fff8e1' : '#f0fdf4',
                border: `1px solid ${badWeather ? '#fbbf24' : '#86efac'}`,
              }}>
                <span style={{ fontSize: 22 }}>{weather.current.icon}</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: badWeather ? '#b45309' : '#166534' }}>
                    {weather.current.description} {weather.current.temp}°C
                  </div>
                  <div style={{ fontSize: 11, color: '#6b6b6b' }}>
                    💨 {weather.current.wind_speed}m/s · 💧{weather.current.humidity}%
                    {badWeather && <span style={{ marginLeft: 6, color: '#b45309', fontWeight: 700 }}>⚠️ 악천후</span>}
                  </div>
                </div>
              </div>
            )}
            {/* 기준금리 */}
            {baseRate != null && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 14px', borderRadius: 8, flex: '1 1 180px',
                background: '#f0f9ff', border: '1px solid #7dd3fc',
              }}>
                <span style={{ fontSize: 20 }}>🏦</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#0369a1' }}>
                    기준금리 {baseRate}%
                  </div>
                  <div style={{ fontSize: 11, color: '#6b6b6b' }}>한국은행 ECOS</div>
                </div>
              </div>
            )}
            {/* CPI */}
            {econ?.cpi?.latest != null && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 14px', borderRadius: 8, flex: '1 1 160px',
                background: '#fefce8', border: '1px solid #fde047',
              }}>
                <span style={{ fontSize: 20 }}>📈</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#854d0e' }}>
                    CPI {econ.cpi.latest}{econ.cpi.unit || ''}
                  </div>
                  <div style={{ fontSize: 11, color: '#6b6b6b' }}>소비자물가지수</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {/* 안전재고 / 위험재고 계산기 */}
        <div style={{ ...S.card, flex: '1 1 320px', minWidth: 300 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: '#1a1a2e' }}>
            🛡️ 안전재고 · 위험재고 · 재주문점
          </div>

          {/* 품목 선택 */}
          <div style={S.field}>
            <label style={S.label}>품목 선택 (선택 시 리드타임 자동 반영)</label>
            <select style={S.select} value={materialId}
              onChange={e => setMaterialId(e.target.value)}>
              <option value="">-- 품목 선택 (선택사항) --</option>
              {materials.map(m => (
                <option key={m.id} value={m.id}>
                  {m.material_code} {m.material_name} (기본 {m.lead_time_days}일)
                </option>
              ))}
            </select>
          </div>

          {/* 매입처 선택 */}
          <div style={S.field}>
            <label style={S.label}>매입처 선택 (선택 시 리드타임 조정)</label>
            <select style={S.select} value={supplierId}
              onChange={e => setSupplierId(e.target.value)}>
              <option value="">-- 매입처 선택 (선택사항) --</option>
              {suppliers.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} (기본 {s.lead_time_days ?? 7}일)
                </option>
              ))}
            </select>
          </div>

          <div style={S.field}>
            <label style={S.label}>재고 유형</label>
            <select style={S.select} {...f('inventory_type')}>
              {INV_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div style={S.field}>
            <label style={S.label}>평균 일수요 (단위/일)</label>
            <input style={S.input} type="number" placeholder="예: 50" {...f('avg_demand')} />
          </div>
          <div style={S.field}>
            <label style={S.label}>수요 표준편차 (σ)</label>
            <input style={S.input} type="number" placeholder="예: 10" {...f('demand_std')} />
          </div>
          <div style={S.field}>
            <label style={S.label}>
              리드타임 (일)
              {ltInfo && (
                <LeadTimeBadge source={ltInfo.source} label={ltInfo.source_label} />
              )}
            </label>
            <input
              style={{
                ...S.input,
                borderColor: ltInfo ? '#a5c8f0' : '#e9e9e7',
                background:  ltInfo ? '#f0f7ff' : 'white',
              }}
              type="number"
              placeholder="예: 7"
              {...f('lead_time')}
              onChange={e => {
                setLtInfo(null)
                setForm(p => ({ ...p, lead_time: e.target.value }))
              }}
            />
            {/* 악천후 리드타임 연장 경고 */}
            {badWeather && form.lead_time && (
              <div style={{
                marginTop: 6, padding: '6px 10px', borderRadius: 6,
                background: '#fff8e1', border: '1px solid #fbbf24',
                fontSize: 11, color: '#b45309',
              }}>
                ⚠️ 현재 악천후({weather.current.description})가 감지되었습니다.
                리드타임을 <strong>{Math.ceil(Number(form.lead_time) * 1.2)}일</strong> (현재 +20%) 이상으로 연장하는 것을 고려하세요.
              </div>
            )}
          </div>
          <div style={S.field}>
            <label style={S.label}>목표 서비스 수준 (비워두면 유형 기본값 적용)</label>
            <select style={S.select} {...f('service_level')}>
              <option value="">유형 기본값 사용</option>
              <option value="0.90">90%</option>
              <option value="0.95">95%</option>
              <option value="0.97">97%</option>
              <option value="0.98">98%</option>
              <option value="0.99">99%</option>
            </select>
          </div>
          <button style={S.btn} onClick={() => ssMutation.mutate()} disabled={ssMutation.isPending}>
            {ssMutation.isPending ? '계산 중...' : '계산'}
          </button>
          {ssMutation.isError && (
            <div style={{ marginTop: 10, color: '#d44c47', fontSize: 12 }}>
              {ssMutation.error?.response?.data?.error || '오류가 발생했습니다.'}
            </div>
          )}

          {result && (
            <div style={S.resultBox}>
              <div style={{ fontSize: 12, color: '#6b6b6b', marginBottom: 10 }}>
                [{result.inventory_type_label}] 서비스 수준 {(result.service_level * 100).toFixed(0)}% · Z={result.z_score}
              </div>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>🟢 안전재고 (Safety Stock)</span>
                <span style={S.resultValue}>{result.safety_stock} 단위</span>
              </div>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>🔴 위험재고 (Danger Stock)</span>
                <span style={S.resultValue}>{result.danger_stock} 단위</span>
              </div>
              <div style={{ ...S.resultRow, borderBottom: 'none' }}>
                <span style={S.resultLabel}>🔵 재주문점 (ROP)</span>
                <span style={S.resultValue}>{result.reorder_point} 단위</span>
              </div>
              <div style={{
                marginTop: 12, padding: 10, background: 'white',
                borderRadius: 6, fontSize: 11, color: '#6b6b6b', lineHeight: 1.8,
              }}>
                <div>• {result.interpretation.safety_stock}</div>
                <div>• {result.interpretation.danger_stock}</div>
                <div>• {result.interpretation.reorder_point}</div>
              </div>
            </div>
          )}
        </div>

        {/* EOQ 계산기 */}
        <div style={{ ...S.card, flex: '1 1 320px', minWidth: 300 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: '#1a1a2e' }}>
            📦 경제적 주문량 (EOQ)
          </div>

          {/* 기준금리 기반 보관비용 힌트 */}
          {holdingRateHint && (
            <div style={{
              padding: '8px 12px', borderRadius: 8, marginBottom: 12,
              background: '#f0f9ff', border: '1px solid #7dd3fc',
              fontSize: 11, color: '#0369a1',
            }}>
              💡 기준금리 {baseRate}% 기준, 보관비용 = 취득원가 × <strong>{holdingRateHint}%</strong> (금리 + 창고비 2% 추정)
            </div>
          )}

          <div style={S.field}>
            <label style={S.label}>연간 수요량</label>
            <input style={S.input} type="number" placeholder="예: 12000" {...ef('annual_demand')} />
          </div>
          <div style={S.field}>
            <label style={S.label}>1회 발주비용 (원)</label>
            <input style={S.input} type="number" placeholder="예: 50000" {...ef('order_cost')} />
          </div>
          <div style={S.field}>
            <label style={S.label}>단위당 연간 보관비용 (원)</label>
            <input style={S.input} type="number" placeholder="예: 500" {...ef('holding_cost')} />
          </div>
          <button style={S.btn} onClick={() => eoqMutation.mutate()} disabled={eoqMutation.isPending}>
            {eoqMutation.isPending ? '계산 중...' : '계산'}
          </button>
          {eoqMutation.isError && (
            <div style={{ marginTop: 10, color: '#d44c47', fontSize: 12 }}>
              {eoqMutation.error?.response?.data?.error || '오류가 발생했습니다.'}
            </div>
          )}

          {eoqResult && (
            <div style={S.resultBox}>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>최적 주문량 (EOQ)</span>
                <span style={S.resultValue}>{eoqResult.eoq.toLocaleString()} 단위</span>
              </div>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>연간 발주 횟수</span>
                <span style={S.resultValue}>{eoqResult.annual_orders}회</span>
              </div>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>발주 주기</span>
                <span style={S.resultValue}>{eoqResult.cycle_days}일마다</span>
              </div>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>연간 발주비용</span>
                <span style={S.resultValue}>{eoqResult.annual_order_cost?.toLocaleString()}원</span>
              </div>
              <div style={S.resultRow}>
                <span style={S.resultLabel}>연간 보관비용</span>
                <span style={S.resultValue}>{eoqResult.annual_holding_cost?.toLocaleString()}원</span>
              </div>
              <div style={{ ...S.resultRow, borderBottom: 'none' }}>
                <span style={S.resultLabel}>✅ 연간 총 물류비용</span>
                <span style={{ ...S.resultValue, color: '#2e7d32' }}>{eoqResult.total_annual_cost?.toLocaleString()}원</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── 탭2: 발주 수요예측 ──────────────────────────────────────
function DemandForecastTab({ weather }) {
  const [itemCode, setItemCode] = useState('')
  const [method, setMethod]     = useState('wma')
  const [histMonths, setHistMonths] = useState('6')
  const [forecastPeriods, setForecastPeriods] = useState('3')
  const [enabled, setEnabled]   = useState(false)

  const { data, isFetching, isError } = useQuery({
    queryKey: ['scm-demand-forecast', itemCode, method, histMonths, forecastPeriods],
    queryFn: () => api.get('/mm/calculator/demand-forecast/', {
      params: {
        item_code: itemCode,
        method,
        history_months: histMonths,
        forecast_periods: forecastPeriods,
      }
    }).then(r => r.data),
    enabled,
    staleTime: 60000,
  })

  const handleSearch = () => setEnabled(true)
  const methodLabel = FORECAST_METHODS.find(m => m.value === method)?.label || method

  return (
    <div style={{ padding: 20 }}>
      {/* 검색 조건 */}
      <div style={{ ...S.card, marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 180px' }}>
            <label style={S.label}>품목 코드 (비워두면 전체)</label>
            <input style={S.input} placeholder="품목 코드 입력 또는 전체" value={itemCode}
              onChange={e => { setItemCode(e.target.value); setEnabled(false) }} />
          </div>
          <div style={{ flex: '1 1 180px' }}>
            <label style={S.label}>예측 방법</label>
            <select style={S.select} value={method} onChange={e => { setMethod(e.target.value); setEnabled(false) }}>
              {FORECAST_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
          <div style={{ flex: '0 1 120px' }}>
            <label style={S.label}>과거 기준 (개월)</label>
            <select style={S.select} value={histMonths} onChange={e => { setHistMonths(e.target.value); setEnabled(false) }}>
              {[3,6,9,12].map(n => <option key={n} value={n}>{n}개월</option>)}
            </select>
          </div>
          <div style={{ flex: '0 1 120px' }}>
            <label style={S.label}>예측 기간 (개월)</label>
            <select style={S.select} value={forecastPeriods} onChange={e => { setForecastPeriods(e.target.value); setEnabled(false) }}>
              {[1,2,3,6].map(n => <option key={n} value={n}>{n}개월</option>)}
            </select>
          </div>
          <button style={{ ...S.btn, height: 36, marginBottom: 0 }} onClick={handleSearch}>
            조회
          </button>
        </div>
      </div>

      {/* 날씨 5일 예보 스트립 */}
      {weather?.forecast?.length > 0 && (
        <div style={{ ...S.card, marginBottom: 16, padding: '12px 16px' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#9b9b9b', marginBottom: 8 }}>
            🌤️ 향후 5일 날씨 예보 (배송·수요 계획 참고)
          </div>
          <WeatherForecastStrip weather={weather} />
          {isBadWeather(weather) && (
            <div style={{
              fontSize: 11, color: '#b45309', background: '#fff8e1',
              padding: '6px 10px', borderRadius: 6, marginTop: 4,
            }}>
              ⚠️ 악천후 예보가 있습니다. 기상 영향을 고려하여 예측 수요에 완충을 두는 것을 권장합니다.
            </div>
          )}
        </div>
      )}

      {isFetching && (
        <div style={{ textAlign: 'center', padding: 40, color: '#9b9b9b', fontSize: 13 }}>
          수요 데이터를 분석 중...
        </div>
      )}
      {isError && (
        <div style={{ textAlign: 'center', padding: 40, color: '#d44c47', fontSize: 13 }}>
          데이터 조회 중 오류가 발생했습니다.
        </div>
      )}

      {data && !isFetching && (
        <>
          <div style={{ fontSize: 12, color: '#9b9b9b', marginBottom: 12 }}>
            예측 방법: {methodLabel} · {data.results?.length ?? 0}개 품목
          </div>
          {data.results?.length === 0 ? (
            <div style={{ ...S.card, textAlign: 'center', padding: 40, color: '#9b9b9b', fontSize: 13 }}>
              재고 출고 이력이 없습니다. 창고관리(WM)에서 출고 기록을 먼저 등록하세요.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {data.results.map((item, i) => (
                <div key={i} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <div>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{item.item_name}</span>
                      <span style={{ fontSize: 11, color: '#9b9b9b', marginLeft: 8 }}>{item.item_code}</span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 11, color: '#6b6b6b' }}>권고 발주량</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a2e' }}>
                        {item.recommended_order.toLocaleString()}
                        <span style={{ fontSize: 11, fontWeight: 400, color: '#9b9b9b', marginLeft: 4 }}>단위</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                    {/* 과거 이력 */}
                    <div style={{ flex: '1 1 200px' }}>
                      <div style={{ fontSize: 11, color: '#9b9b9b', marginBottom: 6 }}>
                        출고 이력 (월별) · 평균 {item.avg_monthly} · σ {item.std_monthly}
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {item.history.map((h, j) => (
                          <div key={j} style={{
                            background: '#f5f5f3', borderRadius: 4,
                            padding: '3px 8px', fontSize: 11, color: '#3b3b3b',
                          }}>
                            <span style={{ color: '#9b9b9b' }}>{h.month}</span>
                            <span style={{ marginLeft: 4, fontWeight: 600 }}>{h.qty}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 예측 */}
                    <div style={{ flex: '0 1 240px' }}>
                      <div style={{ fontSize: 11, color: '#9b9b9b', marginBottom: 6 }}>예측 ({methodLabel})</div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {item.forecast.map((f, j) => (
                          <div key={j} style={{
                            background: '#e8f5e9', border: '1px solid #b5ddb5',
                            borderRadius: 6, padding: '6px 10px', textAlign: 'center',
                          }}>
                            <div style={{ fontSize: 10, color: '#6b9b6b' }}>{j + 1}개월 후</div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: '#2e7d32' }}>{f.forecast}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ─── 탭3: 재고이관 목록 ──────────────────────────────────────
function TransferListTab({ weather }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['scm-transfer-list'],
    queryFn: () => api.get('/mm/calculator/transfer-list/').then(r => r.data),
    staleTime: 60000,
  })

  const urgent  = data?.results?.filter(r => r.urgency === '긴급') ?? []
  const advised = data?.results?.filter(r => r.urgency === '권고') ?? []
  const bad = isBadWeather(weather)

  const Row = ({ item }) => (
    <tr style={{ borderBottom: '1px solid #f0f0ee' }}
      onMouseEnter={e => { e.currentTarget.style.background = '#f9f9f7' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}>
      <td style={{ padding: '10px 14px' }}>
        <span style={S.badge(item.urgency === '긴급' ? 'red' : 'orange')}>{item.urgency}</span>
      </td>
      <td style={{ padding: '10px 14px', fontWeight: 500 }}>{item.item_name}</td>
      <td style={{ padding: '10px 14px', color: '#6b6b6b', fontSize: 12 }}>{item.item_code}</td>
      <td style={{ padding: '10px 14px', fontSize: 12, color: '#6b6b6b' }}>{item.category || '-'}</td>
      <td style={{ padding: '10px 14px', color: '#d44c47' }}>{item.from_warehouse}</td>
      <td style={{ padding: '10px 14px' }}>→</td>
      <td style={{ padding: '10px 14px', color: '#2e7d32' }}>{item.to_warehouse}</td>
      <td style={{ padding: '10px 14px', fontWeight: 700, textAlign: 'right' }}>
        {item.transfer_qty.toLocaleString()}
      </td>
      <td style={{ padding: '10px 14px', fontSize: 11, color: '#9b9b9b', textAlign: 'right' }}>
        현재고 {item.deficit_stock} / 최소 {item.deficit_min}
      </td>
    </tr>
  )

  if (isLoading) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
      재고 불균형 분석 중...
    </div>
  )
  if (isError) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#d44c47', fontSize: 13 }}>
      데이터 조회 중 오류가 발생했습니다.
    </div>
  )

  return (
    <div style={{ padding: 20 }}>
      {/* 악천후 이관 경고 배너 */}
      {bad && (
        <div style={{
          padding: '10px 16px', borderRadius: 8, marginBottom: 14,
          background: '#fff8e1', border: '1px solid #fbbf24',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 20 }}>{weather.current.icon}</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#b45309' }}>
              ⚠️ 악천후 감지 – 이관 일정 주의
            </div>
            <div style={{ fontSize: 11, color: '#6b6b6b', marginTop: 2 }}>
              현재 {weather.current.description}({weather.current.temp}°C, 풍속 {weather.current.wind_speed}m/s) 상태입니다.
              긴급 이관 건의 경우 기상 조건을 고려하여 일정을 조정하거나 대안 경로를 검토하세요.
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <span style={S.badge('red')}>{urgent.length}건 긴급</span>
          <span style={{ ...S.badge('orange'), marginLeft: 6 }}>{advised.length}건 권고</span>
          <span style={{ fontSize: 11, color: '#9b9b9b', marginLeft: 10 }}>
            창고 간 재고 불균형 자동 탐지 결과
          </span>
        </div>
        <button style={{ ...S.btn, padding: '6px 14px', fontSize: 12 }} onClick={() => refetch()}>
          새로고침
        </button>
      </div>

      {data?.results?.length === 0 ? (
        <div style={{ ...S.card, textAlign: 'center', padding: 40, color: '#9b9b9b', fontSize: 13 }}>
          이관이 필요한 재고가 없습니다. 모든 창고의 재고가 균형 상태입니다.
        </div>
      ) : (
        <div style={S.card}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  {['긴급도','품목명','품목코드','카테고리','출발 창고','','도착 창고','이관 권고량','현재고/최소재고'].map(h => (
                    <th key={h} style={{
                      background: '#f5f5f3', padding: '10px 14px', textAlign: 'left',
                      fontWeight: 600, color: '#6b6b6b', borderBottom: '1px solid #e9e9e7',
                      whiteSpace: 'nowrap', fontSize: 12,
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {urgent.map((item, i) => <Row key={`u${i}`} item={item} />)}
                {advised.map((item, i) => <Row key={`a${i}`} item={item} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── 메인 ─────────────────────────────────────────────────────
export default function ScmCalcPage() {
  const [activeTab, setActiveTab] = useState(0)

  // 활성화된 외부 API 기능 목록
  const { data: featuresData } = useQuery({
    queryKey: ['active-features'],
    queryFn: () => api.get('/external/configs/active-features/').then(r => r.data),
    staleTime: 300000,
  })
  const activeFeatures = featuresData?.active_features ?? []
  const hasWeather  = activeFeatures.includes('weather')
  const hasEcon     = activeFeatures.includes('economic_indicators')

  // 날씨 데이터
  const { data: weatherData } = useQuery({
    queryKey: ['weather'],
    queryFn: () => api.get('/external/weather/').then(r => r.data),
    enabled: hasWeather,
    staleTime: 600000,
    refetchInterval: 600000,
  })

  // 경제지표 데이터
  const { data: econData } = useQuery({
    queryKey: ['economic-indicators'],
    queryFn: () => api.get('/external/economic-indicators/').then(r => r.data),
    enabled: hasEcon,
    staleTime: 3600000,
    refetchInterval: 3600000,
  })

  return (
    <div style={{ fontFamily: "'Inter', 'Noto Sans KR', sans-serif" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 24 }}>🧮</span>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>SCM 계산기</h1>
        </div>
        <div style={{ fontSize: 13, color: '#9b9b9b' }}>
          안전재고·위험재고·EOQ 계산, 발주 수요예측, 재고이관 권고 목록
        </div>
      </div>

      {/* 탭 패널 */}
      <div style={{
        background: 'white', border: '1px solid #e9e9e7',
        borderRadius: 10, overflow: 'hidden',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      }}>
        <div style={{ borderBottom: '1px solid #e9e9e7', display: 'flex' }}>
          {TABS.map((tab, i) => (
            <button key={tab} onClick={() => setActiveTab(i)} style={{
              padding: '12px 22px', fontSize: 13, fontWeight: 500,
              border: 'none', cursor: 'pointer',
              background: activeTab === i ? '#1a1a2e' : 'transparent',
              color: activeTab === i ? 'white' : '#6b6b6b',
              borderBottom: activeTab === i ? '2px solid #1a1a2e' : '2px solid transparent',
              transition: 'all 0.12s',
            }}>
              {tab}
            </button>
          ))}
        </div>
        {activeTab === 0 && <InventoryCalcTab weather={weatherData} econ={econData} />}
        {activeTab === 1 && <DemandForecastTab weather={weatherData} />}
        {activeTab === 2 && <TransferListTab weather={weatherData} />}
      </div>
    </div>
  )
}
