import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout      from './components/Layout'
import LoginPage   from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ChatPage    from './pages/ChatPage'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30000 } },
})

function PrivateRoute({ children }) {
  const token = localStorage.getItem('access_token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index        element={<DashboardPage />} />
            <Route path="chat"  element={<ChatPage />} />
            <Route path="mm"    element={<div><h2>MM 자재관리</h2><p>개발 중...</p></div>} />
            <Route path="sd"    element={<div><h2>SD 판매출하</h2><p>개발 중...</p></div>} />
            <Route path="pp"    element={<div><h2>PP 생산계획</h2><p>개발 중...</p></div>} />
            <Route path="qm"    element={<div><h2>QM 품질관리</h2><p>개발 중...</p></div>} />
            <Route path="wm"    element={<div><h2>WM 창고관리</h2><p>개발 중...</p></div>} />
            <Route path="tm"    element={<div><h2>TM 운송관리</h2><p>개발 중...</p></div>} />
            <Route path="fi"    element={<div><h2>FI 재무회계</h2><p>개발 중...</p></div>} />
            <Route path="hr"    element={<div><h2>HR 인사관리</h2><p>개발 중...</p></div>} />
            <Route path="wi"    element={<div><h2>작업지시서</h2><p>개발 중...</p></div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
