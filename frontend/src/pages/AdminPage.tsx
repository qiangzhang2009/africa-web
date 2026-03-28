import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'
import { adminListUsers, adminGetStats, adminUpdateUser, adminCreateSubscription } from '../utils/api'
import type { AdminUserSummary, AdminStats } from '../types'

const TIER_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-600',
  pro: 'bg-amber-100 text-amber-700',
  enterprise: 'bg-purple-100 text-purple-700',
}

const TIER_LABELS: Record<string, string> = {
  free: '免费版',
  pro: 'Pro',
  enterprise: '企业版',
}

export default function AdminPage() {
  const navigate = useNavigate()
  const { isLoggedIn, currentUser } = useAppStore()

  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUserSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [adminError, setAdminError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoggedIn || !currentUser?.is_admin) {
      navigate('/')
      return
    }
    loadData()
  }, [isLoggedIn, currentUser])

  async function loadData() {
    setLoading(true)
    setAdminError(null)
    try {
      const [s, uData] = await Promise.all([
        adminGetStats().catch(() => null),
        adminListUsers({ page, page_size: 20, tier: tierFilter || undefined, search: search || undefined }).catch(() => ({ total: 0, page: 1, page_size: 20, users: [] })),
      ])
      setStats(s)
      setUsers(uData.users)
      setTotal(uData.total)
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        setAdminError('无权限访问，请重新登录')
        setTimeout(() => navigate('/'), 1500)
        return
      }
      setAdminError('加载失败，请刷新页面')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [page, tierFilter, search])

  function showMsg(m: string) {
    setMsg(m)
    setTimeout(() => setMsg(''), 3000)
  }

  async function handleActivate(userId: number, tier: string) {
    try {
      await adminCreateSubscription(userId, tier)
      showMsg(`${TIER_LABELS[tier] || tier} 开通成功`)
      loadData()
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        setAdminError('无权限，请重新登录')
        setTimeout(() => navigate('/'), 1500)
        return
      }
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      showMsg(detail || '操作失败')
    }
  }

  async function handleToggleAdmin(user: AdminUserSummary) {
    if (user.id === currentUser?.id) {
      showMsg('不能修改自己的管理员权限')
      return
    }
    try {
      await adminUpdateUser(user.id, { is_admin: !user.is_admin })
      showMsg(`${user.email} 管理员权限已${!user.is_admin ? '授予' : '撤销'}`)
      loadData()
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        setAdminError('无权限，请重新登录')
        setTimeout(() => navigate('/'), 1500)
        return
      }
      showMsg('操作失败')
    }
  }

  async function handleToggleActive(user: AdminUserSummary) {
    if (user.id === currentUser?.id) {
      showMsg('不能禁用自己的账号')
      return
    }
    try {
      await adminUpdateUser(user.id, { is_active: !user.is_active })
      showMsg(`${user.email} 已${!user.is_active ? '启用' : '禁用'}`)
      loadData()
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        setAdminError('无权限，请重新登录')
        setTimeout(() => navigate('/'), 1500)
        return
      }
      showMsg('操作失败')
    }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">管理后台</h1>
          <p className="text-slate-500 text-sm mt-1">AfricaZero 用户与订阅管理</p>
        </div>
        <button onClick={() => navigate('/account')} className="text-sm text-slate-500 hover:text-slate-700">
          ← 返回账号中心
        </button>
      </div>

      {msg && (
        <div className="mb-6 px-4 py-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
          {msg}
        </div>
      )}

      {adminError && (
        <div className="mb-6 px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {adminError}
        </div>
      )}

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          {[
            { label: '总用户', value: stats.total_users, color: 'bg-blue-50 text-blue-700' },
            { label: '付费用户', value: stats.paying_users, color: 'bg-green-50 text-green-700' },
            { label: 'Pro 用户', value: stats.pro_users, color: 'bg-amber-50 text-amber-700' },
            { label: '企业用户', value: stats.enterprise_users, color: 'bg-purple-50 text-purple-700' },
            { label: '总收入', value: `¥${stats.total_revenue.toLocaleString()}`, color: 'bg-orange-50 text-orange-700' },
          ].map(s => (
            <div key={s.label} className={`rounded-xl p-4 ${s.color}`}>
              <p className="text-xs opacity-70">{s.label}</p>
              <p className="text-2xl font-bold mt-1">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Secondary stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: '活跃 API Key', value: stats.api_keys_active },
            { label: '活跃子账号', value: stats.sub_accounts_active },
            { label: '本周新用户', value: stats.new_users_this_week },
            { label: '即将到期(7天)', value: stats.expiring_soon_7d },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">{s.label}</p>
              <p className="text-xl font-bold text-slate-900 mt-1">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* User table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <h2 className="text-sm font-semibold text-slate-700 flex-1">
            用户列表 {total > 0 && <span className="text-slate-400 font-normal">（{total} 人）</span>}
          </h2>
          <div className="flex gap-2 flex-wrap">
            <input
              type="text"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              placeholder="搜索邮箱..."
              className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-400 outline-none"
            />
            <select
              value={tierFilter}
              onChange={e => { setTierFilter(e.target.value); setPage(1) }}
              className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-400 outline-none"
            >
              <option value="">全部方案</option>
              <option value="free">免费版</option>
              <option value="pro">Pro</option>
              <option value="enterprise">企业版</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">用户</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">方案</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">状态</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">订阅</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">资源</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">注册时间</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-400">加载中...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-400">暂无用户</td></tr>
              ) : users.map(u => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-slate-800">{u.email}</p>
                      <p className="text-xs text-slate-400">ID: {u.id}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TIER_COLORS[u.tier]}`}>
                      {TIER_LABELS[u.tier]}
                    </span>
                    {u.is_admin && (
                      <span className="ml-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-600">管理员</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                      {u.is_active ? '正常' : '已禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">
                    {u.expires_at ? (
                      <span>{u.expires_at.slice(0, 10)}</span>
                    ) : (
                      <span className="text-slate-400">无</span>
                    )}
                    {u.latest_subscription && (
                      <div className="text-xs text-slate-400">
                        ¥{u.latest_subscription.amount} · {TIER_LABELS[u.latest_subscription.tier as keyof typeof TIER_LABELS]}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">
                    <div>子账号: {u.sub_accounts_count}</div>
                    <div>API Key: {u.api_keys_count}</div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {u.created_at?.slice(0, 10)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-end flex-wrap">
                      {u.tier === 'free' && (
                        <>
                          <button
                            onClick={() => handleActivate(u.id, 'pro')}
                            className="px-2 py-1 text-xs bg-amber-100 text-amber-700 rounded hover:bg-amber-200"
                          >
                            开通Pro
                          </button>
                          <button
                            onClick={() => handleActivate(u.id, 'enterprise')}
                            className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                          >
                            开通企业
                          </button>
                        </>
                      )}
                      {u.tier === 'pro' && (
                        <button
                          onClick={() => handleActivate(u.id, 'enterprise')}
                          className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                        >
                          升级企业
                        </button>
                      )}
                      <button
                        onClick={() => handleToggleAdmin(u)}
                        className={`px-2 py-1 text-xs rounded ${u.is_admin ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}
                      >
                        {u.is_admin ? '撤销Admin' : '设Admin'}
                      </button>
                      <button
                        onClick={() => handleToggleActive(u)}
                        className={`px-2 py-1 text-xs rounded ${u.is_active ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}
                      >
                        {u.is_active ? '禁用' : '启用'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-slate-200 flex items-center justify-between">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50"
            >
              上一页
            </button>
            <span className="text-sm text-slate-500">
              第 {page} / {totalPages} 页，共 {total} 人
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50"
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
