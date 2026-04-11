import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout        from './components/Layout'
import LoginPage     from './pages/LoginPage'
import RegisterPage  from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ChatPage      from './pages/ChatPage'
import MmPage        from './pages/MmPage'
import SdPage        from './pages/SdPage'
import FiPage        from './pages/FiPage'
import WmPage        from './pages/WmPage'
import HrPage        from './pages/HrPage'
import PpPage        from './pages/PpPage'
import QmPage        from './pages/QmPage'
import TmPage        from './pages/TmPage'
import WiPage        from './pages/WiPage'
import WorkflowPage  from './pages/WorkflowPage'
import AdminPage     from './pages/AdminPage'
import ScmCalcPage   from './pages/ScmCalcPage'

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
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index       element={<DashboardPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="mm"   element={<MmPage />} />
            <Route path="sd"   element={<SdPage />} />
            <Route path="fi"   element={<FiPage />} />
            <Route path="wm"   element={<WmPage />} />
            <Route path="hr"   element={<HrPage />} />
            <Route path="pp"   element={<PpPage />} />
            <Route path="qm"   element={<QmPage />} />
            <Route path="tm"   element={<TmPage />} />
            <Route path="wi"       element={<WiPage />} />
            <Route path="workflow" element={<WorkflowPage />} />
            <Route path="admin"   element={<AdminPage />} />
            <Route path="calc"    element={<ScmCalcPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
