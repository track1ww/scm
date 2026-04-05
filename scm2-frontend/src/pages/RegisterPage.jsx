import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

export default function RegisterPage() {
  const [form, setForm] = useState({
    name: '', email: '', password: '', passwordConfirm: '',
    department: '', company_code: '',
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }
    setLoading(true)
    try {
      await api.post('/accounts/register/', {
        name: form.name,
        email: form.email,
        password: form.password,
        department: form.department,
        company_code: form.company_code,
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      const data = err.response?.data
      if (data) {
        const msgs = Object.values(data).flat().join(' ')
        setError(msgs || '가입에 실패했습니다.')
      } else {
        setError('가입에 실패했습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '10px 12px',
    border: '1px solid #d3d3cf', borderRadius: 6,
    fontSize: 14, outline: 'none', boxSizing: 'border-box',
  }
  const labelStyle = { display: 'block', fontSize: 12, fontWeight: 500, color: '#6b6b6b', marginBottom: 6 }

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
        width: 400, boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', letterSpacing: '-0.02em' }}>
            회원 가입
          </div>
          <div style={{ fontSize: 13, color: '#9b9b9b', marginTop: 4 }}>
            ERP 통합관리 시스템
          </div>
        </div>

        {success ? (
          <div style={{ background: '#e8f5e9', border: '1px solid #b2dfdb', borderRadius: 6, padding: '16px', textAlign: 'center', color: '#2e7d32', fontSize: 14 }}>
            가입이 완료되었습니다. 로그인 페이지로 이동합니다...
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {[
              { id: 'reg-name', name: 'name', label: '이름 *', type: 'text', key: 'name', placeholder: '홍길동' },
              { id: 'reg-email', name: 'email', label: '이메일 *', type: 'email', key: 'email', placeholder: 'your@company.com' },
              { id: 'reg-password', name: 'password', label: '비밀번호 * (8자 이상)', type: 'password', key: 'password', placeholder: '••••••••' },
              { id: 'reg-password-confirm', name: 'passwordConfirm', label: '비밀번호 확인 *', type: 'password', key: 'passwordConfirm', placeholder: '••••••••' },
              { id: 'reg-department', name: 'department', label: '부서', type: 'text', key: 'department', placeholder: '예: 구매팀' },
              { id: 'reg-company-code', name: 'company_code', label: '회사코드', type: 'text', key: 'company_code', placeholder: '회사코드 입력 (선택사항)' },
            ].map(f => (
              <div key={f.id} style={{ marginBottom: 16 }}>
                <label htmlFor={f.id} style={labelStyle}>{f.label}</label>
                <input
                  id={f.id} name={f.name} type={f.type}
                  value={form[f.key]} onChange={set(f.key)}
                  placeholder={f.placeholder}
                  required={f.label.includes('*')}
                  style={inputStyle}
                />
              </div>
            ))}

            {error && (
              <div style={{ background: '#fdecea', border: '1px solid #f5c2c7', borderRadius: 6, padding: '10px 12px', fontSize: 13, color: '#d44c47', marginBottom: 16 }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '11px',
              background: loading ? '#d3d3cf' : '#1a1a2e',
              color: 'white', border: 'none', borderRadius: 6,
              fontSize: 14, fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}>
              {loading ? '가입 중...' : '가입하기'}
            </button>

            <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#6b6b6b' }}>
              이미 계정이 있으신가요?{' '}
              <Link to="/login" style={{ color: '#1a1a2e', fontWeight: 600, textDecoration: 'none' }}>로그인</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
