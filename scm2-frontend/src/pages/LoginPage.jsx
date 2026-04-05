import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import useAuthStore from '../stores/authStore'

export default function LoginPage() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    const ok = await login(email, password)
    if (ok) navigate('/')
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: '#f7f7f5',
      fontFamily: "'Inter', 'Noto Sans KR', sans-serif",
    }}>
      <div style={{
        background: 'white', borderRadius: 12,
        border: '1px solid #e9e9e7', padding: '48px 40px',
        width: 380, boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', letterSpacing: '-0.02em' }}>
            ERP 통합관리
          </div>
          <div style={{ fontSize: 13, color: '#9b9b9b', marginTop: 4 }}>
            Supply Chain Management System
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="login-email" style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#6b6b6b', marginBottom: 6 }}>
              이메일
            </label>
            <input
              id="login-email"
              name="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="your@company.com"
              required
              style={{
                width: '100%', padding: '10px 12px',
                border: '1px solid #d3d3cf', borderRadius: 6,
                fontSize: 14, outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label htmlFor="login-password" style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#6b6b6b', marginBottom: 6 }}>
              비밀번호
            </label>
            <input
              id="login-password"
              name="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={{
                width: '100%', padding: '10px 12px',
                border: '1px solid #d3d3cf', borderRadius: 6,
                fontSize: 14, outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          {error && (
            <div style={{
              background: '#fdecea', border: '1px solid #f5c2c7',
              borderRadius: 6, padding: '10px 12px',
              fontSize: 13, color: '#d44c47', marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '11px',
              background: loading ? '#d3d3cf' : '#1a1a2e',
              color: 'white', border: 'none', borderRadius: 6,
              fontSize: 14, fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
          <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#6b6b6b' }}>
            계정이 없으신가요?{' '}
            <Link to="/register" style={{ color: '#1a1a2e', fontWeight: 600, textDecoration: 'none' }}>회원가입</Link>
          </div>
        </form>
      </div>
    </div>
  )
}