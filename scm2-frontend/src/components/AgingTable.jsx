// AR/AP Aging 공통 테이블 컴포넌트
// props: data (aging API 응답), title

const fmt = v => (v != null ? Number(v).toLocaleString() + '원' : '-')

// 컬럼별 컬러 코딩 정의
const AGING_COLORS = {
  not_yet_due:  { bg: '#f5f5f3', color: '#6b6b6b' },  // 미도래 - 중립
  days_0_30:    { bg: '#f0f4ff', color: '#3366cc' },   // 0-30일 - 파랑
  days_31_60:   { bg: '#fff8e1', color: '#e65100' },   // 31-60일 - 주황
  days_61_90:   { bg: '#fdecea', color: '#c62828' },   // 61-90일 - 빨강 연
  over_90:      { bg: '#ffcdd2', color: '#b71c1c' },   // 90일 초과 - 빨강 진
  total:        { bg: '#f5f5f3', color: '#1a1a1a' },   // 합계 - 기본
}

function AgingCell({ value, colorKey }) {
  const { bg, color } = AGING_COLORS[colorKey] ?? AGING_COLORS.not_yet_due
  return (
    <td style={{
      padding: '10px 16px',
      fontWeight: colorKey === 'total' ? 700 : 400,
      background: bg,
      color,
      whiteSpace: 'nowrap',
    }}>
      {fmt(value)}
    </td>
  )
}

export default function AgingTable({ data, title }) {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div style={{ padding: '48px 0', textAlign: 'center', color: '#9b9b9b', fontSize: 13 }}>
        {title ? `[${title}] ` : ''}데이터가 없습니다
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      {title && (
        <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', padding: '16px 16px 8px' }}>
          {title}
        </div>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={{ background: '#f5f5f3', padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#6b6b6b', borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              거래처
            </th>
            <th style={{ background: AGING_COLORS.not_yet_due.bg, padding: '10px 16px', textAlign: 'right', fontWeight: 600, color: AGING_COLORS.not_yet_due.color, borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              미도래
            </th>
            <th style={{ background: AGING_COLORS.days_0_30.bg, padding: '10px 16px', textAlign: 'right', fontWeight: 600, color: AGING_COLORS.days_0_30.color, borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              0–30일
            </th>
            <th style={{ background: AGING_COLORS.days_31_60.bg, padding: '10px 16px', textAlign: 'right', fontWeight: 600, color: AGING_COLORS.days_31_60.color, borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              31–60일
            </th>
            <th style={{ background: AGING_COLORS.days_61_90.bg, padding: '10px 16px', textAlign: 'right', fontWeight: 600, color: AGING_COLORS.days_61_90.color, borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              61–90일
            </th>
            <th style={{ background: AGING_COLORS.over_90.bg, padding: '10px 16px', textAlign: 'right', fontWeight: 600, color: AGING_COLORS.over_90.color, borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              90일 초과
            </th>
            <th style={{ background: AGING_COLORS.total.bg, padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: AGING_COLORS.total.color, borderBottom: '1px solid #e9e9e7', whiteSpace: 'nowrap' }}>
              합계
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={row.partner_id ?? row.partner ?? i}
              style={{ borderBottom: '1px solid #e9e9e7' }}
              onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(0.97)' }}
              onMouseLeave={e => { e.currentTarget.style.filter = 'none' }}
            >
              <td style={{ padding: '10px 16px', color: '#1a1a1a', fontWeight: 500 }}>
                {row.partner_name ?? row.partner ?? '-'}
              </td>
              <AgingCell value={row.not_yet_due} colorKey="not_yet_due" />
              <AgingCell value={row.days_0_30}   colorKey="days_0_30" />
              <AgingCell value={row.days_31_60}  colorKey="days_31_60" />
              <AgingCell value={row.days_61_90}  colorKey="days_61_90" />
              <AgingCell value={row.over_90}     colorKey="over_90" />
              <AgingCell value={row.total}       colorKey="total" />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
