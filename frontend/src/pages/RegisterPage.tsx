import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'

export default function RegisterPage() {
  const navigate = useNavigate()
  const setAuth = useAppStore(s => s.setAuth)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('两次输入的密码不一致')
      return
    }

    if (password.length < 6) {
      setError('密码至少需要6位')
      return
    }

    setLoading(true)
    try {
      const res = await register({ email, password })
      setAuth(res.access_token, res.user, res.remaining_today)
      navigate('/account')
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        setError(axiosErr.response?.data?.detail || '注册失败，请稍后重试')
      } else {
        setError('注册失败，请检查网络连接')
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
          <h1 className="text-2xl font-bold text-white mb-2">创建账号</h1>
          <p className="text-slate-400 text-sm">免费注册，每天3次关税计算机会</p>
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
                placeholder="至少6位"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">确认密码</label>
              <input
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                required
                placeholder="再次输入密码"
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
              {loading ? '注册中...' : '免费注册'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-500">
            已有账号？{' '}
            <Link to="/login" className="text-orange-600 hover:text-orange-700 font-medium">
              立即登录
            </Link>
          </div>

          <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-100">
            <p className="text-xs text-amber-700">
              <strong>注册即代表：</strong>免费账号每天可使用3次关税计算。升级
              <Link to="/pricing" className="text-orange-600 hover:underline"> Pro/企业版</Link>
              解锁无限次使用、API调用和子账号管理。
            </p>
          </div>
        </div>

        <p className="text-center mt-6 text-slate-500 text-xs">
          <Link to="/" className="hover:text-slate-300">← 返回首页</Link>
        </p>
      </div>
    </div>
  )
}
