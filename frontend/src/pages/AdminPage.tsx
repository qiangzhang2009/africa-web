import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'
import {
  adminListUsers, adminGetStats, adminUpdateUser,
  adminChangeTier, adminGetUserDetail, adminGetRevenueStats,
  adminGetUsageStats, adminGetSubscriptionAnalytics,
} from '../utils/api'
import type {
  AdminUserSummary, AdminStats, AdminUserDetail,
  TierChangeRequest, RevenueStats, UsageStats, SubscriptionAnalytics,
  SubscriptionTier,
} from '../types'

type TabId = 'overview' | 'users' | 'revenue' | 'usage' | 'subscriptions'

// ─── Tier helpers ────────────────────────────────────────────────────────────────

const TIER_COLORS: Record<string, string> = {
  free: 'bg-slate-100 text-slate-600',
  pro: 'bg-amber-100 text-amber-700',
  enterprise: 'bg-purple-100 text-purple-700',
}
const TIER_LABELS: Record<string, string> = {
  free: '免费版', pro: 'Pro', enterprise: '企业版',
}
const ALL_TIERS: SubscriptionTier[] = ['free', 'pro', 'enterprise']

// ─── TierChangeModal ────────────────────────────────────────────────────────────

interface TierChangeModalProps {
  user: AdminUserSummary
  onClose: () => void
  onDone: (newTier: SubscriptionTier) => void
}

function TierChangeModal({ user, onClose, onDone }: TierChangeModalProps) {
  const [targetTier, setTargetTier] = useState<SubscriptionTier>(user.tier)
  const [durationDays, setDurationDays] = useState<number | ''>('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const tiers: { id: SubscriptionTier; label: string; desc: string }[] = [
    { id: 'free', label: '免费版', desc: '每日3次查询，无高级功能' },
    { id: 'pro', label: 'Pro', desc: '全年不限查询，¥99/年' },
    { id: 'enterprise', label: '企业版', desc: 'API Key + 子账号，¥298/年' },
  ]

  async function handleSubmit() {
    if (targetTier === user.tier && !durationDays && !reason) {
      onClose(); return
    }
    setSubmitting(true)
    setError('')
    try {
      const body: TierChangeRequest = {
        tier: targetTier,
        reason: reason || undefined,
        duration_days: durationDays !== '' ? Number(durationDays) : undefined,
      }
      await adminChangeTier(user.id, body)
      onDone(targetTier)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || '操作失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }


  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">变更订阅方案</h2>
            <p className="text-sm text-slate-500 mt-0.5">{user.email}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">&times;</button>
        </div>

        {/* Current state */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-slate-500">当前方案</p>
              <span className={`inline-block mt-1 px-2.5 py-1 rounded-full text-sm font-semibold ${TIER_COLORS[user.tier]}`}>
                {TIER_LABELS[user.tier]}
              </span>
            </div>
            {user.expires_at && (
              <div>
                <p className="text-xs text-slate-500">到期时间</p>
                <p className="text-sm font-medium text-slate-700 mt-1">{user.expires_at}</p>
              </div>
            )}
            {user.calculations_count > 0 && (
              <div>
                <p className="text-xs text-slate-500">累计计算</p>
                <p className="text-sm font-medium text-slate-700 mt-1">{user.calculations_count} 次</p>
              </div>
            )}
          </div>
        </div>

        {/* Tier options */}
        <div className="px-6 py-5 space-y-3">
          <p className="text-sm font-medium text-slate-700">选择新方案</p>
          {tiers.map(t => {
            const isSelected = t.id === targetTier
            const isCurrent = t.id === user.tier
            const tIdx = tiers.findIndex(x => x.id === t.id)
            const curIdx = tiers.findIndex(x => x.id === user.tier)
            const isDown = tIdx < curIdx
            return (
              <button
                key={t.id}
                onClick={() => setTargetTier(t.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all text-left ${
                  isSelected
                    ? 'border-orange-500 bg-orange-50'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                } ${isCurrent ? 'opacity-60 cursor-not-allowed' : ''}`}
                disabled={isCurrent}
              >
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                  isSelected ? 'border-orange-500' : 'border-slate-300'
                }`}>
                  {isSelected && <div className="w-2.5 h-2.5 rounded-full bg-orange-500" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${TIER_COLORS[t.id]}`}>
                      {t.label}
                    </span>
                    {isCurrent && <span className="text-xs text-slate-400">当前</span>}
                    {isDown && !isCurrent && <span className="text-xs text-red-500 font-medium">降级</span>}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{t.desc}</p>
                </div>
              </button>
            )
          })}
        </div>

        {/* Advanced options */}
        <div className="px-6 pb-4 space-y-3">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">自定义时长（天）</label>
              <input
                type="number"
                value={durationDays}
                onChange={e => setDurationDays(e.target.value ? Number(e.target.value) : '')}
                placeholder="默认365天"
                min={1}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-400 outline-none"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-600 mb-1">到期日期</label>
              <input
                type="date"
                onChange={() => {/* handled via duration_days */}}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-400 outline-none opacity-50"
                disabled
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">操作备注</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="如：客户申请退款、人工降级处理..."
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-400 outline-none"
            />
          </div>
        </div>

        {error && (
          <div className="mx-6 mb-3 px-4 py-2.5 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="px-6 pb-6 flex gap-3 justify-end">
          <button onClick={onClose} className="px-5 py-2.5 text-sm border border-slate-200 rounded-xl hover:bg-slate-50">
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-5 py-2.5 text-sm bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50"
          >
            {submitting ? '提交中...' : targetTier !== user.tier ? '确认变更' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── UserDetailDrawer ──────────────────────────────────────────────────────────

interface UserDetailDrawerProps {
  userId: number
  onClose: () => void
  onTierChange: (newTier: SubscriptionTier) => void
}

function UserDetailDrawer({ userId, onClose, onTierChange: _onTierChange }: UserDetailDrawerProps) {
  const [detail, setDetail] = useState<AdminUserDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'overview' | 'subscriptions' | 'apis' | 'subaccounts'>('overview')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await adminGetUserDetail(userId)
      setDetail(d)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => { load() }, [load])

  const user = detail?.user as Record<string, unknown> | undefined
  const usage = detail?.usage
  const subList = (detail?.subscriptions || []) as Array<Record<string, unknown>>
  const apiKeys = (detail?.api_keys || []) as Array<Record<string, unknown>>
  const subAccounts = (detail?.sub_accounts || []) as Array<Record<string, unknown>>

  // Build mini bar chart data (last 14 days)
  const last14 = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (13 - i))
    return d.toISOString().slice(0, 10)
  })
  const usageMap: Record<string, number> = {}
  ;(usage?.daily_usage_30d || []).forEach((r: { day: string; cnt: number }) => { usageMap[r.day] = r.cnt })
  const barData = last14.map(day => ({ day, cnt: usageMap[day] || 0 }))
  const maxCnt = Math.max(...barData.map(d => d.cnt), 1)

  const statusColor = (s: string) =>
    s === 'active' ? 'text-green-600 bg-green-50' :
    s === 'expired' ? 'text-red-600 bg-red-50' : 'text-slate-600 bg-slate-50'

  return (
    <div className="fixed inset-0 bg-black/30 flex justify-end z-40" onClick={onClose}>
      <div
        className="w-full max-w-xl bg-white shadow-2xl overflow-y-auto flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Drawer header */}
        <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-lg font-bold text-slate-900">{user?.email as string || '加载中...'}</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              ID: {userId} · 注册于 {String(user?.created_at || '').slice(0, 10)}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">&times;</button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-slate-400">加载中...</div>
          </div>
        ) : detail ? (
          <>
            {/* Tier + key metrics */}
            <div className="px-6 py-5 border-b border-slate-100">
              <div className="flex flex-wrap gap-6">
                {[
                  { label: '当前方案', value: TIER_LABELS[user?.tier as string] || '-', color: TIER_COLORS[user?.tier as string] || '' },
                  { label: '累计计算', value: String(usage?.total_calculations ?? 0), unit: '次' },
                  { label: '近30天', value: String(usage?.calculations_30d ?? 0), unit: '次' },
                  { label: '最后活跃', value: usage?.last_calculation ? String(usage.last_calculation).slice(0, 10) : '从未', unit: '' },
                ].map(m => (
                  <div key={m.label}>
                    <p className="text-xs text-slate-500">{m.label}</p>
                    {m.color ? (
                      <span className={`inline-block mt-1 px-2.5 py-1 rounded-full text-sm font-semibold ${m.color}`}>{m.value}</span>
                    ) : (
                      <p className="text-lg font-bold text-slate-900 mt-1">{m.value}<span className="text-xs text-slate-400 ml-0.5">{m.unit}</span></p>
                    )}
                  </div>
                ))}
              </div>

              {/* Mini bar chart */}
              {barData.some(d => d.cnt > 0) && (
                <div className="mt-4">
                  <p className="text-xs text-slate-500 mb-2">近14天使用趋势</p>
                  <div className="flex items-end gap-0.5 h-12">
                    {barData.map(d => (
                      <div key={d.day} className="flex-1 flex flex-col items-center gap-0.5 group relative">
                        <div
                          className="w-full bg-orange-200 rounded-sm hover:bg-orange-400 transition-colors min-h-[2px]"
                          style={{ height: `${Math.max(2, (d.cnt / maxCnt) * 44)}px` }}
                          title={`${d.day}: ${d.cnt}次`}
                        />
                        <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-10">
                          {d.day.slice(5)}: {d.cnt}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Tabs */}
            <div className="px-6 border-b border-slate-200 flex gap-1 flex-shrink-0">
              {(['overview', 'subscriptions', 'apis', 'subaccounts'] as const).map(t => (
                <button key={t} onClick={() => setTab(t)} className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  tab === t ? 'border-orange-500 text-orange-600' : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}>
                  {t === 'overview' ? '使用概览' : t === 'subscriptions' ? '订阅记录' : t === 'apis' ? 'API Key' : '子账号'}
                  {t === 'subscriptions' && <span className="ml-1.5 text-xs bg-slate-100 px-1.5 py-0.5 rounded-full">{subList.length}</span>}
                  {t === 'apis' && <span className="ml-1.5 text-xs bg-slate-100 px-1.5 py-0.5 rounded-full">{apiKeys.length}</span>}
                  {t === 'subaccounts' && <span className="ml-1.5 text-xs bg-slate-100 px-1.5 py-0.5 rounded-full">{subAccounts.length}</span>}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {tab === 'overview' && usage && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: '总计算次数', value: usage.total_calculations },
                      { label: '近30天计算', value: usage.calculations_30d },
                    ].map(m => (
                      <div key={m.label} className="bg-slate-50 rounded-xl p-4">
                        <p className="text-xs text-slate-500">{m.label}</p>
                        <p className="text-2xl font-bold text-slate-900 mt-1">{m.value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4">
                    <p className="text-xs text-slate-500">账户状态</p>
                    <div className="flex gap-3 mt-2">
                      <span className={`px-2.5 py-1 rounded-full text-sm font-medium ${TIER_COLORS[user?.tier as string]}`}>
                        {TIER_LABELS[user?.tier as string]}
                      </span>
                      <span className={`px-2.5 py-1 rounded-full text-sm font-medium ${Boolean(user?.is_active) ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                        {Boolean(user?.is_active) ? '正常' : '已禁用'}
                      </span>
                      {Boolean(user?.is_admin) && <span className="px-2.5 py-1 rounded-full text-sm font-medium bg-red-100 text-red-600">管理员</span>}
                    </div>
                  </div>
                </div>
              )}

              {tab === 'subscriptions' && (
                <div className="space-y-3">
                  {subList.length === 0 ? (
                    <p className="text-slate-400 text-sm text-center py-8">暂无订阅记录</p>
                  ) : subList.map((s: Record<string, unknown>, i: number) => (
                    <div key={i} className="border border-slate-200 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2.5 py-1 rounded-full text-sm font-semibold ${TIER_COLORS[s.tier as string]}`}>
                            {TIER_LABELS[s.tier as string]}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(s.status as string)}`}>
                            {s.status === 'active' ? '生效中' : s.status === 'expired' ? '已过期' : String(s.status)}
                          </span>
                        </div>
                        <span className="text-sm font-medium text-slate-700">
                          ¥{Number(s.amount).toFixed(0)}
                        </span>
                      </div>
                      <div className="flex gap-4 text-xs text-slate-500">
                        <span>开始：{String(s.started_at || '').slice(0, 10)}</span>
                        <span>到期：{String(s.expires_at || '永久').slice(0, 10)}</span>
                        <span>{s.payment_channel as string}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {tab === 'apis' && (
                <div className="space-y-3">
                  {apiKeys.length === 0 ? (
                    <p className="text-slate-400 text-sm text-center py-8">暂无 API Key</p>
                  ) : apiKeys.map((ak: Record<string, unknown>, i: number) => (
                    <div key={i} className="border border-slate-200 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <p className="font-medium text-slate-800">{ak.name as string || '未命名'}</p>
                          <p className="text-xs text-slate-400 font-mono mt-0.5">{ak.key_prefix as string}***</p>
                        </div>
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${ak.is_active ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                          {ak.is_active ? '有效' : '已撤销'}
                        </span>
                      </div>
                      <div className="flex gap-3 text-xs text-slate-500">
                        <span>限额：{Number(ak.rate_limit_day)}/天</span>
                        {Boolean(ak.last_used_at) && <span>最近使用：{String(ak.last_used_at).slice(0, 10)}</span>}
                        <span>创建：{String(ak.created_at || '').slice(0, 10)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {tab === 'subaccounts' && (
                <div className="space-y-3">
                  {subAccounts.length === 0 ? (
                    <p className="text-slate-400 text-sm text-center py-8">暂无子账号</p>
                  ) : subAccounts.map((sa: Record<string, unknown>, i: number) => (
                    <div key={i} className="border border-slate-200 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <p className="font-medium text-slate-800">{sa.email as string}</p>
                          <p className="text-xs text-slate-400 mt-0.5">{sa.name as string || '无名称'}</p>
                        </div>
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${sa.is_active ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                          {sa.is_active ? '活跃' : '已删除'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">创建于：{String(sa.created_at || '').slice(0, 10)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Tier change CTA */}
            <div className="px-6 py-4 border-t border-slate-200 flex-shrink-0">
              <button
                onClick={() => {
                  // Trigger parent to open modal
                  const summaryUser: AdminUserSummary = {
                    id: userId,
                    email: user?.email as string,
                    tier: user?.tier as SubscriptionTier,
                    is_admin: Boolean(user?.is_admin),
                    is_active: Boolean(user?.is_active),
                    subscribed_at: user?.subscribed_at as string | null,
                    expires_at: user?.expires_at as string | null,
                    created_at: user?.created_at as string | null,
                    latest_subscription: null,
                    calculations_count: usage?.total_calculations || 0,
                    last_active: usage?.last_calculation || null,
                    sub_accounts_count: subAccounts.length,
                    api_keys_count: apiKeys.length,
                    api_keys_used: (apiKeys as Array<Record<string, unknown>>).filter(ak => Boolean(ak.last_used_at)).length,
                  }
                  // Signal parent to open modal
                  {(() => {
                    const opener = (window as unknown as Record<string, (u: AdminUserSummary) => void>).__adminOpenTierModal
                    return opener ? opener(summaryUser) : null
                  })()}
                }}
                className="w-full py-2.5 bg-orange-500 text-white rounded-xl hover:bg-orange-600 text-sm font-medium"
              >
                变更订阅方案
              </button>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            加载失败
          </div>
        )}
      </div>
    </div>
  )
}

// ─── RevenueChart ───────────────────────────────────────────────────────────────

function RevenueChart({ data }: { data: RevenueStats }) {
  const last30 = (data.daily_series || []).slice(0, 30).reverse()
  if (last30.length === 0) return <p className="text-slate-400 text-sm text-center py-8">暂无收入数据</p>

  const maxVal = Math.max(...last30.map(d => d.total), 1)

  return (
    <div>
      <div className="flex items-center gap-4 text-xs text-slate-500 mb-3">
        <span>¥{data.total_revenue.toLocaleString()}</span>
        <span>Pro: ¥{data.tier_revenue.pro.toLocaleString()}</span>
        <span>企业: ¥{data.tier_revenue.enterprise.toLocaleString()}</span>
      </div>
      <div className="flex items-end gap-1 h-28">
        {last30.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group">
            <div className="w-full flex flex-col gap-0.5" style={{ height: '96px' }}>
              {d.pro > 0 && (
                <div
                  className="w-full bg-amber-400 rounded-t-sm min-h-[2px]"
                  style={{ height: `${Math.max(2, (d.pro / maxVal) * 60)}px` }}
                />
              )}
              {d.enterprise > 0 && (
                <div
                  className="w-full bg-purple-500 rounded-t-sm min-h-[2px]"
                  style={{ height: `${Math.max(2, (d.enterprise / maxVal) * 60)}px` }}
                />
              )}
            </div>
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 pointer-events-none z-10 whitespace-nowrap">
              {d.day.slice(5)}: ¥{d.total}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-slate-400 mt-1 px-0.5">
        <span>{last30[0]?.day?.slice(5)}</span>
        <span>{last30[last30.length - 1]?.day?.slice(5)}</span>
      </div>
    </div>
  )
}

// ─── UsageChart ────────────────────────────────────────────────────────────────

function UsageChart({ data }: { data: UsageStats }) {
  const last30 = [...(data.daily_calculations || [])].reverse().slice(-30)
  if (last30.length === 0) return <p className="text-slate-400 text-sm text-center py-8">暂无使用数据</p>

  const maxCalcs = Math.max(...last30.map(d => d.calc_count), 1)
  const maxUsers = Math.max(...last30.map(d => d.active_users), 1)

  return (
    <div className="space-y-4">
      {/* Calculation bars */}
      <div>
        <p className="text-xs text-slate-500 mb-1.5">每日计算次数</p>
        <div className="flex items-end gap-0.5 h-20">
          {last30.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group relative" style={{ height: '80px' }}>
              <div
                className="w-full bg-orange-200 rounded-t-sm hover:bg-orange-400 transition-colors min-h-[2px]"
                style={{ height: `${Math.max(2, (d.calc_count / maxCalcs) * 76)}px` }}
              />
            </div>
          ))}
        </div>
      </div>
      {/* Active users bars */}
      <div>
        <p className="text-xs text-slate-500 mb-1.5">活跃用户数</p>
        <div className="flex items-end gap-0.5 h-14">
          {last30.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group relative" style={{ height: '56px' }}>
              <div
                className="w-full bg-blue-200 rounded-t-sm hover:bg-blue-400 transition-colors min-h-[2px]"
                style={{ height: `${Math.max(2, (d.active_users / maxUsers) * 52)}px` }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Main AdminPage ────────────────────────────────────────────────────────────

export default function AdminPage() {
  const navigate = useNavigate()
  const { isLoggedIn, currentUser } = useAppStore()

  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUserSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [adminError, setAdminError] = useState<string | null>(null)

  // Drawer & modal
  const [drawerUserId, setDrawerUserId] = useState<number | null>(null)
  const [tierModalUser, setTierModalUser] = useState<AdminUserSummary | null>(null)

  // Analytics data
  const [revenueStats, setRevenueStats] = useState<RevenueStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [subAnalytics, setSubAnalytics] = useState<SubscriptionAnalytics | null>(null)

  const PAGE_SIZE = 20

  useEffect(() => {
    if (!isLoggedIn || !currentUser?.is_admin) {
      navigate('/'); return
    }
  }, [isLoggedIn, currentUser, navigate])

  const loadStats = useCallback(async () => {
    try {
      const s = await adminGetStats()
      setStats(s)
    } catch { /* ignore */ }
  }, [])

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setAdminError(null)
    try {
      const uData = await adminListUsers({
        page, page_size: PAGE_SIZE,
        tier: tierFilter || undefined,
        search: search || undefined,
        sort: sortBy,
      })
      setUsers(uData.users)
      setTotal(uData.total)
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 401 || status === 403) {
        setAdminError('无权限访问，请重新登录')
        setTimeout(() => navigate('/'), 1500); return
      }
      setAdminError('加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, tierFilter, search, sortBy, navigate])

  useEffect(() => {
    if (!isLoggedIn || !currentUser?.is_admin) return
    loadStats()
    loadUsers()
  }, [loadStats, loadUsers, isLoggedIn, currentUser])

  // Load analytics on tab change
  useEffect(() => {
    if (!isLoggedIn || !currentUser?.is_admin) return
    if (activeTab === 'revenue' && !revenueStats) {
      adminGetRevenueStats(90).then(setRevenueStats).catch(() => {})
    }
    if (activeTab === 'usage' && !usageStats) {
      adminGetUsageStats(30).then(setUsageStats).catch(() => {})
    }
    if (activeTab === 'subscriptions' && !subAnalytics) {
      adminGetSubscriptionAnalytics().then(setSubAnalytics).catch(() => {})
    }
  }, [activeTab, isLoggedIn, currentUser, revenueStats, usageStats, subAnalytics])

  // Register global tier modal opener from drawer
  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__adminOpenTierModal = (user: AdminUserSummary) => {
      setTierModalUser(user)
    }
    return () => {
      delete (window as unknown as Record<string, unknown>).__adminOpenTierModal
    }
  }, [])

  function showMsg(m: string) {
    setMsg(m); setTimeout(() => setMsg(''), 4000)
  }

  function handleTierModalDone(newTier: SubscriptionTier) {
    setTierModalUser(null)
    showMsg(`用户方案已变更为 ${TIER_LABELS[newTier]}`)
    loadStats()
    if (activeTab === 'users') loadUsers()
  }

  async function handleToggleActive(u: AdminUserSummary) {
    if (u.id === currentUser?.id) { showMsg('不能禁用自己的账号'); return }
    try {
      await adminUpdateUser(u.id, { is_active: !u.is_active })
      showMsg(`${u.is_active ? '禁用' : '启用'}成功`)
      loadUsers()
    } catch { showMsg('操作失败') }
  }

  async function handleToggleAdmin(u: AdminUserSummary) {
    if (u.id === currentUser?.id) { showMsg('不能修改自己的管理员权限'); return }
    try {
      await adminUpdateUser(u.id, { is_admin: !u.is_admin })
      showMsg(`${u.email} 管理员权限已${!u.is_admin ? '授予' : '撤销'}`)
      loadUsers()
    } catch { showMsg('操作失败') }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: '总览' },
    { id: 'users', label: '用户列表' },
    { id: 'revenue', label: '收入分析' },
    { id: 'usage', label: '使用分析' },
    { id: 'subscriptions', label: '订阅管理' },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">管理后台</h1>
          <p className="text-slate-500 text-sm mt-1">AfricaZero 数据运营中心</p>
        </div>
        <button onClick={() => navigate('/account')} className="text-sm text-slate-500 hover:text-slate-700">
          ← 返回账号中心
        </button>
      </div>

      {/* Msg banners */}
      {msg && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 text-green-700 rounded-xl text-sm font-medium">
          {msg}
        </div>
      )}
      {adminError && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
          {adminError}
        </div>
      )}

      {/* Tab nav */}
      <div className="flex gap-1 mb-6 border-b border-slate-200 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
              activeTab === tab.id ? 'border-orange-500 text-orange-600' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW TAB ─────────────────────────────────────────── */}
      {activeTab === 'overview' && stats && (
        <div className="space-y-6">
          {/* Primary metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: '总用户', value: stats.total_users.toLocaleString(), color: 'bg-blue-50 text-blue-700', sub: `+${stats.new_users_today} 今日` },
              { label: '付费用户', value: stats.paying_users.toLocaleString(), color: 'bg-green-50 text-green-700', sub: `${stats.enterprise_users} 企业 / ${stats.pro_users} Pro` },
              { label: '总收入', value: `¥${stats.total_revenue.toLocaleString()}`, color: 'bg-orange-50 text-orange-700', sub: `人均 ¥${stats.paying_users > 0 ? Math.round(stats.total_revenue / stats.paying_users) : 0}` },
              { label: '活跃用户(30d)', value: stats.active_users_30d.toLocaleString(), color: 'bg-purple-50 text-purple-700', sub: `占总用户 ${stats.total_users > 0 ? Math.round(stats.active_users_30d / stats.total_users * 100) : 0}%` },
            ].map(s => (
              <div key={s.label} className={`rounded-2xl p-5 ${s.color}`}>
                <p className="text-xs opacity-70">{s.label}</p>
                <p className="text-3xl font-black mt-1">{s.value}</p>
                <p className="text-xs opacity-60 mt-1">{s.sub}</p>
              </div>
            ))}
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: '本周新注册', value: stats.new_users_this_week },
              { label: '本月新注册', value: stats.new_users_this_month },
              { label: '总计算次数', value: stats.total_calculations.toLocaleString() },
              { label: '付费用户均计算', value: `${stats.avg_calcs_per_paying_user}次` },
              { label: '到期(7天内)', value: stats.expiring_soon_7d, warn: stats.expiring_soon_7d > 0 },
            ].map(s => (
              <div key={s.label} className={`rounded-xl p-4 border ${(s as { warn?: boolean }).warn ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'}`}>
                <p className="text-xs text-slate-500">{(s as { warn?: boolean }).warn ? '⚠️' : ''}{s.label}</p>
                <p className={`text-xl font-bold mt-1 ${(s as { warn?: boolean }).warn ? 'text-red-600' : 'text-slate-900'}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Quick user list preview */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">最新注册用户</h3>
              <button onClick={() => setActiveTab('users')} className="text-sm text-orange-500 hover:text-orange-600">
                查看全部 →
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {users.slice(0, 5).map(u => (
                <div key={u.id} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 truncate">{u.email}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      注册 {u.created_at?.slice(0, 10)} · 计算 {u.calculations_count}次
                      {u.last_active && ` · 活跃 ${u.last_active.slice(0, 10)}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TIER_COLORS[u.tier]}`}>
                      {TIER_LABELS[u.tier]}
                    </span>
                    {!u.is_active && <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-600">禁用</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── USERS TAB ─────────────────────────────────────────── */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col sm:flex-row gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text" value={search}
                onChange={e => { setSearch(e.target.value); setPage(1) }}
                placeholder="搜索邮箱、微信..."
                className="w-full px-4 py-2 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-400 outline-none"
              />
            </div>
            <select value={tierFilter} onChange={e => { setTierFilter(e.target.value); setPage(1) }}
              className="px-4 py-2 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-400 outline-none">
              <option value="">全部方案</option>
              <option value="free">免费版</option>
              <option value="pro">Pro</option>
              <option value="enterprise">企业版</option>
            </select>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)}
              className="px-4 py-2 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-400 outline-none">
              <option value="created_at">按注册时间</option>
              <option value="calculations_count">按计算次数</option>
              <option value="last_active">按最后活跃</option>
            </select>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">用户</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">方案</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">计算次数</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">最后活跃</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">到期</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">资源</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-400">加载中...</td></tr>
                  ) : users.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-400">暂无用户</td></tr>
                  ) : users.map(u => (
                    <tr key={u.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => setDrawerUserId(u.id)}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-800">{u.email}</div>
                        {u.wechat_id && <div className="text-xs text-slate-400">微信: {u.wechat_id}</div>}
                        <div className="text-xs text-slate-400">ID: {u.id}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${TIER_COLORS[u.tier]}`}>
                          {TIER_LABELS[u.tier]}
                        </span>
                        {u.is_admin && <span className="ml-1 px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-600">Admin</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-medium text-slate-700">{u.calculations_count.toLocaleString()}</span>
                        <span className="text-xs text-slate-400 ml-1">次</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {u.last_active ? u.last_active.slice(0, 10) : <span className="text-slate-300">从未</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {u.expires_at ? (
                          <span className={new Date(u.expires_at) < new Date() ? 'text-red-500' : 'text-slate-600'}>
                            {u.expires_at}
                          </span>
                        ) : <span className="text-slate-300">无</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        <div>子账号: {u.sub_accounts_count}</div>
                        <div>API Key: {u.api_keys_count}{u.api_keys_used > 0 ? ` (${u.api_keys_used}用过)` : ''}</div>
                      </td>
                      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                        <div className="flex gap-1 justify-end flex-wrap">
                          {ALL_TIERS.filter(t => t !== u.tier).map(t => (
                            <button
                              key={t} onClick={() => setTierModalUser(u)}
                              className={`px-2 py-1 text-xs rounded hover:opacity-80 ${TIER_COLORS[t]}`}
                            >
                              变{t}
                            </button>
                          ))}
                          <button onClick={() => handleToggleAdmin(u)}
                            className={`px-2 py-1 text-xs rounded ${u.is_admin ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}>
                            {u.is_admin ? '撤Admin' : '设Admin'}
                          </button>
                          <button onClick={() => handleToggleActive(u)}
                            className={`px-2 py-1 text-xs rounded ${u.is_active ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}>
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
                <span className="text-sm text-slate-500">第 {page} / {totalPages} 页，共 {total} 人</span>
                <div className="flex gap-2">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                    className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50">
                    上一页
                  </button>
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                    className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50">
                    下一页
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── REVENUE TAB ──────────────────────────────────────────── */}
      {activeTab === 'revenue' && (
        <div className="space-y-6">
          {/* Revenue summary */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: '总收入', value: `¥${(revenueStats?.total_revenue || 0).toLocaleString()}`, bg: 'bg-orange-50', text: 'text-orange-700' },
              { label: 'Pro 收入', value: `¥${(revenueStats?.tier_revenue?.pro || 0).toLocaleString()}`, bg: 'bg-amber-50', text: 'text-amber-700' },
              { label: '企业版收入', value: `¥${(revenueStats?.tier_revenue?.enterprise || 0).toLocaleString()}`, bg: 'bg-purple-50', text: 'text-purple-700' },
            ].map(s => (
              <div key={s.label} className={`rounded-2xl p-5 ${s.bg}`}>
                <p className="text-xs opacity-70">{s.label}</p>
                <p className={`text-2xl font-black mt-1 ${s.text}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-800 mb-4">每日收入趋势（近30天）</h3>
            {revenueStats ? <RevenueChart data={revenueStats} /> : <p className="text-slate-400 text-sm text-center py-8">加载中...</p>}
            <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
              <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-amber-400 rounded-sm inline-block" />Pro</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-purple-500 rounded-sm inline-block" />企业版</span>
            </div>
          </div>

          {/* Paying user counts */}
          <div className="grid grid-cols-2 gap-4">
            {revenueStats && (
              <>
                <div className="bg-white rounded-2xl border border-slate-200 p-5">
                  <p className="text-xs text-slate-500">当前付费用户</p>
                  <p className="text-3xl font-black text-slate-900 mt-1">
                    {(revenueStats.paying_counts.pro || 0) + (revenueStats.paying_counts.enterprise || 0)}
                  </p>
                  <div className="flex gap-4 mt-2 text-sm">
                    <span className="text-amber-600">Pro: {revenueStats.paying_counts.pro || 0}</span>
                    <span className="text-purple-600">企业: {revenueStats.paying_counts.enterprise || 0}</span>
                  </div>
                </div>
                <div className="bg-white rounded-2xl border border-slate-200 p-5">
                  <p className="text-xs text-slate-500">平均客单价</p>
                  <p className="text-3xl font-black text-slate-900 mt-1">
                    ¥{revenueStats.total_revenue > 0 && (revenueStats.paying_counts.pro + revenueStats.paying_counts.enterprise) > 0
                      ? Math.round(revenueStats.total_revenue / (revenueStats.paying_counts.pro + revenueStats.paying_counts.enterprise))
                      : 0}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── USAGE TAB ─────────────────────────────────────────────── */}
      {activeTab === 'usage' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            {usageStats && [
              { label: '总计算次数', value: (usageStats.daily_calculations || []).reduce((s: number, d: { calc_count: number }) => s + d.calc_count, 0).toLocaleString(), color: 'bg-orange-50 text-orange-700' },
              { label: '活跃用户数', value: new Set((usageStats.daily_calculations || []).map((d: { active_users: number }) => d.active_users)).size.toLocaleString(), color: 'bg-blue-50 text-blue-700' },
              { label: 'TOP 目的国', value: (usageStats.top_destinations || [])[0]?.destination || '-', color: 'bg-green-50 text-green-700' },
              { label: 'TOP HS编码', value: (usageStats.top_hs_codes || [])[0]?.hs_code || '-', color: 'bg-purple-50 text-purple-700' },
            ].map(s => (
              <div key={s.label} className={`rounded-2xl p-5 ${s.color}`}>
                <p className="text-xs opacity-70">{s.label}</p>
                <p className="text-2xl font-black mt-1">{s.value}</p>
              </div>
            ))}
          </div>

          {/* Usage chart */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-800 mb-4">每日使用趋势（近30天）</h3>
            {usageStats ? <UsageChart data={usageStats} /> : <p className="text-slate-400 text-sm text-center py-8">加载中...</p>}
          </div>

          {/* Top tables */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'TOP 目的市场', data: usageStats?.top_destinations || [], valueLabel: '次' },
              { title: 'TOP 原产国', data: usageStats?.top_origin_countries || [], valueLabel: '次' },
              { title: 'TOP HS 编码', data: usageStats?.top_hs_codes || [], valueLabel: '次' },
            ].map(box => (
              <div key={box.title} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-100">
                  <h3 className="font-semibold text-slate-700 text-sm">{box.title}</h3>
                </div>
                <div className="divide-y divide-slate-100">
                  {(box.data as Array<{ destination?: string; origin_country?: string; hs_code?: string; cnt: number }>).slice(0, 8).map((item, i) => (
                    <div key={i} className="px-4 py-2.5 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 w-5 text-right">{i + 1}</span>
                        <span className="font-mono text-sm text-slate-700">
                          {item.destination || item.origin_country || item.hs_code}
                        </span>
                      </div>
                      <span className="text-sm font-medium text-slate-500">{item.cnt}{box.valueLabel}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── SUBSCRIPTIONS TAB ─────────────────────────────────────── */}
      {activeTab === 'subscriptions' && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: '当前活跃订阅', value: stats?.active_subscriptions || 0, color: 'bg-green-50 text-green-700' },
              { label: '平均订阅时长', value: `${subAnalytics?.avg_subscription_days || 0}天`, color: 'bg-blue-50 text-blue-700' },
              { label: '近期流失用户', value: subAnalytics?.churned_users || 0, color: 'bg-red-50 text-red-700', warn: (subAnalytics?.churned_users || 0) > 0 },
            ].map(s => (
              <div key={s.label} className={`rounded-2xl p-5 ${s.color}`}>
                <p className="text-xs opacity-70">{s.label}</p>
                <p className="text-2xl font-black mt-1">{s.value}</p>
              </div>
            ))}
          </div>

          {/* Subscription breakdown */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h3 className="font-semibold text-slate-800">订阅方案分布</h3>
            </div>
            <div className="p-6">
              {subAnalytics?.subscription_breakdown ? (
                <div className="space-y-4">
                  {(['free', 'pro', 'enterprise'] as const).map(tier => {
                    const breakdown = subAnalytics.subscription_breakdown[tier] || {}
                    const total = Object.values(breakdown).reduce((s, v) => s + v, 0)
                    return (
                      <div key={tier}>
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span className={`px-2.5 py-1 rounded-full text-sm font-semibold ${TIER_COLORS[tier]}`}>
                              {TIER_LABELS[tier]}
                            </span>
                            <span className="text-sm text-slate-500">共 {total} 条记录</span>
                          </div>
                        </div>
                        <div className="space-y-1.5">
                          {Object.entries(breakdown).map(([status, cnt]) => (
                            <div key={status} className="flex items-center gap-3 text-sm">
                              <span className={`w-20 text-xs px-2 py-0.5 rounded ${
                                status === 'active' ? 'bg-green-50 text-green-700' :
                                status === 'expired' ? 'bg-red-50 text-red-700' :
                                'bg-slate-100 text-slate-600'
                              }`}>
                                {status === 'active' ? '生效中' : status === 'expired' ? '已过期' : status}
                              </span>
                              <div className="flex-1 bg-slate-100 rounded-full h-2">
                                <div className="bg-green-500 h-2 rounded-full" style={{ width: `${total > 0 ? (cnt as number) / total * 100 : 0}%` }} />
                              </div>
                              <span className="text-slate-600 text-xs w-16 text-right">{cnt} 条</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : <p className="text-slate-400 text-sm text-center py-8">加载中...</p>}
            </div>
          </div>

          {/* Renewal alert */}
          {stats && stats.expiring_soon_7d > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
              <div className="flex items-start gap-3">
                <span className="text-2xl">⚠️</span>
                <div>
                  <h4 className="font-semibold text-amber-800">续费预警</h4>
                  <p className="text-sm text-amber-700 mt-1">
                    未来 7 天内有 <strong>{stats.expiring_soon_7d} 位</strong>付费用户到期，建议主动联系挽留。
                  </p>
                  {stats.expired_recently_7d > 0 && (
                    <p className="text-sm text-amber-700 mt-1">
                      过去 7 天已有 <strong>{stats.expired_recently_7d} 位</strong>用户到期（已降级为免费版）。
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── USER DETAIL DRAWER ──────────────────────────────────── */}
      {drawerUserId && (
        <UserDetailDrawer
          userId={drawerUserId}
          onClose={() => setDrawerUserId(null)}
          onTierChange={handleTierModalDone}
        />
      )}

      {/* ── TIER CHANGE MODAL ────────────────────────────────────── */}
      {tierModalUser && (
        <TierChangeModal
          user={tierModalUser}
          onClose={() => setTierModalUser(null)}
          onDone={handleTierModalDone}
        />
      )}
    </div>
  )
}
