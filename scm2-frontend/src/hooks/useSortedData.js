import { useState, useMemo } from 'react'

/**
 * 테이블 컬럼 정렬 훅
 *
 * @param {Array} data - 정렬할 데이터 배열
 * @returns {{ sorted, sortKey, sortDir, toggleSort }}
 *
 * Usage:
 *   const { sorted, sortKey, sortDir, toggleSort } = useSortedData(items)
 *   // 컬럼 헤더에: onClick={() => toggleSort('created_at')}
 *   // 정렬 표시:   sortKey === col.key ? (sortDir === 'asc' ? '▲' : '▼') : ''
 */
export function useSortedData(data) {
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    if (!sortKey || !data?.length) return data ?? []
    return [...data].sort((a, b) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv), 'ko')
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  return { sorted, sortKey, sortDir, toggleSort }
}
