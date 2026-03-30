import { create } from 'zustand'
import api from '../api/client'

const useAuthStore = create((set) => ({
  user:    JSON.parse(localStorage.getItem('user') || 'null'),
  loading: false,
  error:   null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.post('/auth/login/', { email, password })
      localStorage.setItem('access_token',  data.access)
      localStorage.setItem('refresh_token', data.refresh)

      // 프로필 조회
      const { data: profile } = await api.get('/accounts/profile/')
      localStorage.setItem('user', JSON.stringify(profile))
      set({ user: profile, loading: false })
      return true
    } catch (err) {
      set({ error: err.response?.data?.detail || '로그인 실패', loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.clear()
    set({ user: null })
    window.location.href = '/login'
  },

  isAdmin: () => {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    return user?.is_admin || false
  },
}))

export default useAuthStore
