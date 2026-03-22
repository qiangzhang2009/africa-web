import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAppStore(s => s.setAuth)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login({ email, password })
      setAuth(res.access_token, res.user, res.remaining_today)
      navigate('/account')
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        setError(axiosErr.response?.data?.detail || '登录失败，请检查邮箱和密码')
      } else {
        setError('登录失败，请检查网络连接')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold">A0</span>
            </div>
            <span className="font-heading text-2xl font-bold text-white">AfricaZero</span>
          </Link>
          <h1 className="text-2xl font-bold text-white mb-2">登录账号</h1>
          <p className="text-slate-400 text-sm">欢迎回来，继续探索非洲零关税商机</p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">邮箱</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                placeholder="your@email.com"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">密码</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-500">
            还没有账号？{' '}
            <Link to="/register" className="text-orange-600 hover:text-orange-700 font-medium">
              立即注册
            </Link>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 text-center">
            <Link to="/pricing" className="text-sm text-slate-500 hover:text-slate-700">
              查看定价方案 →
            </Link>
          </div>
        </div>

        <p className="text-center mt-6 text-slate-500 text-xs">
          <Link to="/" className="hover:text-slate-300">← 返回首页</Link>
        </p>
      </div>
    </div>
  )
}
