import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getSubscriptionStatus, getSubscriptionHistory,
  listApiKeys, createApiKey, revokeApiKey,
  listSubAccounts, createSubAccount, deleteSubAccount,
  createSubscription,
} from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'
import type {
  SubscriptionStatus,
  SubscriptionHistoryItem,
  ApiKeyResponse,
  ApiKeyWithPlain,
  SubAccountResponse,
} from '../types'

const TIER_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-600 border-slate-200',
  pro: 'bg-amber-50 text-amber-700 border-amber-200',
  enterprise: 'bg-purple-50 text-purple-700 border-purple-200',
}

const TIER_LABELS: Record<string, string> = {
  free: '免费版',
  pro: 'Pro 版',
  enterprise: '企业版',
}

const PLAN_PRICES: Record<string, { price: string; period: string }> = {
  free: { price: '免费', period: '永久' },
  pro: { price: '¥99', period: '/年' },
  enterprise: { price: '¥298', period: '/年' },
}

export default function AccountPage() {
  const navigate = useNavigate()
  const { currentUser, isLoggedIn, logout: storeLogout, updateUser } = useAppStore()

  const [subStatus, setSubStatus] = useState<SubscriptionStatus | null>(null)
  const [history, setHistory] = useState<SubscriptionHistoryItem[]>([])
  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])
  const [subAccounts, setSubAccounts] = useState<SubAccountResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'apikeys' | 'subaccounts' | 'subscription'>('overview')
  const [showNewKey, setShowNewKey] = useState<ApiKeyWithPlain | null>(null)
  const [showSubForm, setShowSubForm] = useState(false)
  const [newSubEmail, setNewSubEmail] = useState('')
  const [newSubPass, setNewSubPass] = useState('')
  const [newSubName, setNewSubName] = useState('')
  const [actionMsg, setActionMsg] = useState('')
  const [accountDisabled, setAccountDisabled] = useState(false)

  useEffect(() => {
    if (!isLoggedIn) {
      navigate('/login')
      return
    }
    loadData()
  }, [isLoggedIn])

  async function loadData() {
    setLoading(true)
    setAccountDisabled(false)
    try {
      const [st, hist, keys, subs] = await Promise.all([
        getSubscriptionStatus().catch((e: unknown) => {
          const status = (e as { response?: { status?: number } })?.response?.status
          if (status === 401 || status === 403) {
            setAccountDisabled(true)
          }
          return null
        }),
        getSubscriptionHistory().catch(() => []),
        listApiKeys().catch(() => []),
        listSubAccounts().catch(() => []),
      ])
      setSubStatus(st)
      setHistory(hist)
      setApiKeys(keys)
      setSubAccounts(subs)
      if (st && st.user) updateUser(st.user)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  function handleLogout() {
    storeLogout()
    navigate('/')
  }

  async function handleCreateKey() {
    try {
      const name = prompt('给这个 API Key 起个名字（可选，直接确定跳过）：') || undefined
      const key = await createApiKey({ name })
      setShowNewKey(key)
      setApiKeys(prev => [key, ...prev])
      showMsg('API Key 创建成功，请妥善保存！关闭后将无法再查看完整密钥。')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建失败'
      showMsg(msg)
    }
  }

  async function handleRevokeKey(id: number) {
    if (!confirm('确认吊销此 API Key？吊销后不可恢复。')) return
    try {
      await revokeApiKey(id)
      setApiKeys(prev => prev.filter(k => k.id !== id))
      showMsg('API Key 已吊销')
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        showMsg('无权限，请重新登录')
        return
      }
      showMsg('吊销失败')
    }
  }

  async function handleCreateSub() {
    if (!newSubEmail || !newSubPass) {
      showMsg('请填写邮箱和密码')
      return
    }
    try {
      const sub = await createSubAccount(newSubEmail, newSubPass, newSubName || undefined)
      setSubAccounts(prev => [...prev, sub])
      setShowSubForm(false)
      setNewSubEmail('')
      setNewSubPass('')
      setNewSubName('')
      showMsg('子账号创建成功')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建失败'
      showMsg(msg)
    }
  }

  async function handleDeleteSub(id: number) {
    if (!confirm('确认删除此子账号？')) return
    try {
      await deleteSubAccount(id)
      setSubAccounts(prev => prev.filter(s => s.id !== id))
      showMsg('子账号已删除')
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        showMsg('无权限，请重新登录')
        return
      }
      showMsg('删除失败')
    }
  }

  async function handleUpgrade(tier: string) {
    if (tier === 'free') return
    try {
      const result = await createSubscription({ tier: tier as 'pro' | 'enterprise', payment_method: 'wechat', payment_channel: 'mock' })
      setSubStatus(result)
      if (result.user) updateUser(result.user)
      showMsg(`${TIER_LABELS[tier]}开通成功！`)
      loadData()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                  '请联系 zxq@zxqconsulting.com 人工开通'
      showMsg(msg)
    }
  }

  function showMsg(msg: string) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(''), 4000)
  }

  const tier = subStatus?.tier || currentUser?.tier || 'free'
  const canApi = tier === 'enterprise'
  const canSub = tier === 'enterprise'

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">账号中心</h1>
          <p className="text-slate-500 text-sm mt-1">{currentUser?.email}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${TIER_COLORS[tier]}`}>
            {TIER_LABELS[tier]}
          </span>
          <button onClick={handleLogout} className="text-sm text-slate-500 hover:text-red-600">
            退出登录
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="mb-6 px-4 py-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-sm">
          {actionMsg}
        </div>
      )}

      {accountDisabled && (
        <div className="mb-6 px-4 py-4 bg-red-50 border border-red-200 rounded-xl text-center">
          <p className="text-red-700 font-medium">⚠️ 您的账号已被管理员禁用</p>
          <p className="text-red-500 text-sm mt-1">如需恢复账号，请联系管理员：<a href="mailto:zxq@zxqconsulting.com" className="underline">zxq@zxqconsulting.com</a></p>
          <button
            onClick={() => { storeLogout(); navigate('/') }}
            className="mt-3 px-4 py-2 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
          >
            退出登录
          </button>
        </div>
      )}

      {/* Tier upgrade banner for free/pro users */}
      {tier !== 'enterprise' && (
        <div className="mb-8 bg-gradient-to-r from-purple-600 to-indigo-700 rounded-2xl p-6 text-white">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold mb-1">
                {tier === 'free' ? '升级 Pro，解锁无限次关税计算' : '升级企业版，解锁 API + 子账号'}
              </h3>
              <p className="text-purple-100 text-sm">
                {tier === 'free'
                  ? '每天3次已用完？Pro版一年仅¥99，无限次计算 + 全品类覆盖 + PDF报告'
                  : '企业版一年¥298，含5个子账号 + API调用权限 + 批量计算 + 优先支持'}
              </p>
            </div>
            <div className="flex gap-3">
              {tier === 'free' && (
                <button
                  onClick={() => handleUpgrade('pro')}
                  className="px-5 py-2.5 bg-white text-purple-700 font-semibold rounded-lg hover:bg-purple-50 transition-colors text-sm"
                >
                  升级 Pro ¥99/年
                </button>
              )}
              <button
                onClick={() => handleUpgrade('enterprise')}
                className="px-5 py-2.5 bg-white/20 border border-white/30 text-white font-semibold rounded-lg hover:bg-white/30 transition-colors text-sm"
              >
                企业版 ¥298/年
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-slate-200 mb-6">
        {[
          { id: 'overview', label: '账号概览' },
          { id: 'apikeys', label: 'API 密钥', badge: canApi ? null : '企业' },
          { id: 'subaccounts', label: '子账号', badge: canSub ? null : '企业' },
          { id: 'subscription', label: '订阅历史' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-orange-500 text-orange-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
            {tab.badge && <span className="ml-1.5 text-xs text-slate-400">({tab.badge})</span>}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-400">加载中...</div>
      ) : (
        <>
          {/* ── Overview ── */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6m6 0V9a2 2 0 012-2h2a2 2 0 012 2v10m6 0v-4a2 2 0 00-2-2h-2a2 2 0 00-2 2v4"/></svg>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">当前方案</p>
                    <p className="text-lg font-bold text-slate-900">{TIER_LABELS[tier]}</p>
                  </div>
                </div>
                <p className="text-sm text-slate-500">
                  {subStatus?.expires_at ? `有效期至 ${subStatus.expires_at}` : '永久有效'}
                </p>
                {subStatus?.days_remaining !== null && subStatus?.days_remaining !== undefined && (
                  <p className="text-xs text-amber-600 mt-1">剩余 {subStatus.days_remaining} 天</p>
                )}
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">API 密钥</p>
                    <p className="text-lg font-bold text-slate-900">{apiKeys.filter(k => k.is_active).length} 个</p>
                  </div>
                </div>
                <p className="text-sm text-slate-500">
                  {canApi ? '企业版专属，可调用关税计算API' : '升级企业版解锁'}
                </p>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">子账号</p>
                    <p className="text-lg font-bold text-slate-900">{subAccounts.length} / 5</p>
                  </div>
                </div>
                <p className="text-sm text-slate-500">
                  {canSub ? '企业版专属，团队协作使用' : '升级企业版解锁'}
                </p>
              </div>

              {/* Subscription plans quick ref */}
              <div className="md:col-span-3 bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="text-sm font-semibold text-slate-700 mb-4">订阅方案对比</h3>
                <div className="grid grid-cols-3 gap-4 text-center">
                  {(['free', 'pro', 'enterprise'] as const).map(t => (
                    <div key={t} className={`rounded-xl p-4 ${tier === t ? 'ring-2 ring-orange-400 bg-orange-50' : 'bg-slate-50'}`}>
                      <p className="text-sm font-bold text-slate-900">{TIER_LABELS[t]}</p>
                      <p className="text-lg font-bold text-slate-900 mt-1">{PLAN_PRICES[t].price}</p>
                      <p className="text-xs text-slate-500">{PLAN_PRICES[t].period}</p>
                      <ul className="mt-3 space-y-1 text-xs text-slate-600 text-left">
                        <li>{t === 'free' ? '✓' : '✓'} 每天3次计算</li>
                        <li>{t !== 'free' ? '✓' : '✗'} 无限次计算</li>
                        <li>{t !== 'free' ? '✓' : '✗'} 全品类覆盖</li>
                        <li>{t === 'enterprise' ? '✓' : '✗'} 5个子账号</li>
                        <li>{t === 'enterprise' ? '✓' : '✗'} API调用权限</li>
                        <li>{t === 'enterprise' ? '✓' : '✗'} 专属客服</li>
                      </ul>
                      {tier !== t && (
                        <button
                          onClick={() => handleUpgrade(t)}
                          className="mt-3 w-full py-1.5 text-xs font-medium rounded-lg bg-orange-500 text-white hover:bg-orange-600 transition-colors"
                        >
                          {t === 'free' ? '免费' : t === 'pro' ? '¥99/年' : '¥298/年'}
                        </button>
                      )}
                      {tier === t && (
                        <p className="mt-3 text-xs text-orange-600 font-medium">当前方案</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── API Keys ── */}
          {activeTab === 'apikeys' && (
            <div>
              {!canApi ? (
                <div className="text-center py-16">
                  <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">API 密钥（企业版专属）</h3>
                  <p className="text-slate-500 mb-6 text-sm">企业版用户可生成 API Key，通过程序调用关税计算接口，实现自动化批量计算。</p>
                  <button
                    onClick={() => handleUpgrade('enterprise')}
                    className="px-6 py-2.5 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    升级企业版 ¥298/年
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-700">API 密钥列表</h3>
                      <p className="text-xs text-slate-500 mt-0.5">使用 X-API-Key 请求头调用 API，有效期与账号一致</p>
                    </div>
                    <button
                      onClick={handleCreateKey}
                      className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
                    >
                      + 生成新密钥
                    </button>
                  </div>

                  {showNewKey && (
                    <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                      <p className="text-xs text-amber-700 font-medium mb-2">⚠️ 新密钥（仅显示一次，请妥善保存）</p>
                      <div className="flex gap-2 items-center">
                        <code className="flex-1 bg-white px-3 py-2 rounded border border-amber-200 text-sm font-mono break-all">
                          {showNewKey.plain_key}
                        </code>
                        <button
                          onClick={() => navigator.clipboard.writeText(showNewKey.plain_key)}
                          className="px-3 py-2 text-xs bg-amber-200 text-amber-800 rounded hover:bg-amber-300"
                        >
                          复制
                        </button>
                        <button
                          onClick={() => setShowNewKey(null)}
                          className="px-3 py-2 text-xs text-slate-500 hover:text-slate-700"
                        >
                          关闭
                        </button>
                      </div>
                    </div>
                  )}

                  {apiKeys.length === 0 ? (
                    <div className="text-center py-12 text-slate-400">暂无 API 密钥，点击上方按钮生成</div>
                  ) : (
                    <div className="space-y-3">
                      {apiKeys.map(key => (
                        <div key={key.id} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-slate-800">{key.name || '未命名密钥'}</p>
                              <span className={`text-xs px-2 py-0.5 rounded-full ${key.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                                {key.is_active ? '活跃' : '已吊销'}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 font-mono mt-1">
                              {key.key_prefix}...（完整密钥仅显示一次）
                            </p>
                            <p className="text-xs text-slate-400 mt-1">
                              每日限额 {key.rate_limit_day} 次 · 创建于 {key.created_at?.slice(0, 10)} ·{' '}
                              {key.last_used_at ? `最后使用 ${key.last_used_at?.slice(0, 10)}` : '从未使用'}
                            </p>
                          </div>
                          <button
                            onClick={() => handleRevokeKey(key.id)}
                            className="text-sm text-red-500 hover:text-red-700"
                          >
                            吊销
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* API usage example */}
                  <div className="mt-6 bg-slate-900 rounded-xl p-5">
                    <p className="text-xs text-slate-400 mb-2 font-medium">API 调用示例</p>
                    <pre className="text-xs text-green-400 overflow-x-auto">{`curl -X POST https://your-backend.com/api/v1/calculate/tariff \\
  -H "X-API-Key: az_xxxxxxxxxxxxxxxxxxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"hs_code":"0901.11","origin_country":"ET","destination":"CN","fob_value":5000}'`}</pre>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Sub-accounts ── */}
          {activeTab === 'subaccounts' && (
            <div>
              {!canSub ? (
                <div className="text-center py-16">
                  <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">子账号管理（企业版专属）</h3>
                  <p className="text-slate-500 mb-6 text-sm">企业版可创建最多5个子账号，适合团队多人使用，各子账号共享企业版权限。</p>
                  <button
                    onClick={() => handleUpgrade('enterprise')}
                    className="px-6 py-2.5 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    升级企业版 ¥298/年
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-700">子账号列表</h3>
                      <p className="text-xs text-slate-500 mt-0.5">已创建 {subAccounts.length} / 5 个子账号</p>
                    </div>
                    <button
                      onClick={() => setShowSubForm(!showSubForm)}
                      disabled={subAccounts.length >= 5}
                      className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-40 transition-colors"
                    >
                      + 创建子账号
                    </button>
                  </div>

                  {showSubForm && (
                    <div className="mb-4 p-5 bg-purple-50 border border-purple-200 rounded-xl space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <input
                          type="email"
                          value={newSubEmail}
                          onChange={e => setNewSubEmail(e.target.value)}
                          placeholder="子账号邮箱"
                          className="px-3 py-2 border border-purple-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-400 outline-none"
                        />
                        <input
                          type="password"
                          value={newSubPass}
                          onChange={e => setNewSubPass(e.target.value)}
                          placeholder="密码（至少6位）"
                          className="px-3 py-2 border border-purple-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-400 outline-none"
                        />
                        <input
                          type="text"
                          value={newSubName}
                          onChange={e => setNewSubName(e.target.value)}
                          placeholder="姓名（可选）"
                          className="px-3 py-2 border border-purple-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-400 outline-none"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={handleCreateSub}
                          className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700"
                        >
                          确认创建
                        </button>
                        <button
                          onClick={() => setShowSubForm(false)}
                          className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  )}

                  {subAccounts.length === 0 ? (
                    <div className="text-center py-12 text-slate-400">暂无子账号，点击上方按钮创建</div>
                  ) : (
                    <div className="space-y-3">
                      {subAccounts.map(sub => (
                        <div key={sub.id} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-slate-800">{sub.name || sub.email}</p>
                              <span className="text-xs text-slate-400">{sub.email}</span>
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">创建于 {sub.created_at?.slice(0, 10)}</p>
                          </div>
                          <button
                            onClick={() => handleDeleteSub(sub.id)}
                            className="text-sm text-red-500 hover:text-red-700"
                          >
                            删除
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── Subscription History ── */}
          {activeTab === 'subscription' && (
            <div>
              {history.length === 0 ? (
                <div className="text-center py-16 text-slate-400">暂无订阅记录</div>
              ) : (
                <div className="space-y-3">
                  {history.map(sub => (
                    <div key={sub.id} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TIER_COLORS[sub.tier]}`}>
                            {TIER_LABELS[sub.tier]}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${sub.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                            {sub.status === 'active' ? '生效中' : sub.status}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600 mt-1">
                          {sub.payment_method || '人工开通'} · ¥{sub.amount} · {sub.currency}
                        </p>
                        <p className="text-xs text-slate-400">
                          {sub.started_at?.slice(0, 10)} 至 {sub.expires_at?.slice(0, 10) || '永久'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-6 p-5 bg-slate-50 rounded-xl border border-slate-200">
                <h4 className="text-sm font-semibold text-slate-700 mb-2">如何升级？</h4>
                <ol className="text-sm text-slate-600 space-y-1">
                  <li>1. 微信/支付宝转账至客服账户</li>
                  <li>2. 联系 <a href="mailto:zxq@zxqconsulting.com" className="text-orange-600 hover:underline">zxq@zxqconsulting.com</a> 告知您的账号邮箱</li>
                  <li>3. 客服人工开通后刷新页面即可使用</li>
                </ol>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
