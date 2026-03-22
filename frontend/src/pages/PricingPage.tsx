import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'
import { createSubscription } from '../utils/api'
import type { SubscriptionTier } from '../types'

// ─── Payment Modal ─────────────────────────────────────────────────────────────
function PaymentModal({
  tier,
  onClose,
  onSuccess,
}: {
  tier: SubscriptionTier
  onClose: () => void
  onSuccess: () => void
}) {
  const [step, setStep] = useState<'method' | 'confirm' | 'done'>('method')
  const [selectedMethod, setSelectedMethod] = useState<'wechat' | 'alipay' | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const planInfo: Record<SubscriptionTier, { name: string; price: number; features: string }> = {
    free: { name: '免费版', price: 0, features: '每天3次关税计算' },
    pro: { name: 'Pro 版', price: 99, features: '全年无限次关税计算 + 全品类覆盖 + 原产地AI + PDF报告' },
    enterprise: { name: '企业版', price: 298, features: 'Pro全部 + 5子账号 + API权限 + 批量计算 + 专属客服' },
  }

  async function handleMockPay() {
    setLoading(true)
    setError('')
    try {
      await createSubscription({
        tier,
        payment_method: selectedMethod === 'wechat' ? 'wechat' : 'alipay',
        payment_channel: 'mock',
      })
      setStep('done')
      onSuccess()
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        '支付失败，请联系 zxq@zxqconsulting.com'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-white font-bold text-lg">{planInfo[tier].name}</h3>
              <p className="text-orange-100 text-sm mt-0.5">AfricaZero 订阅服务</p>
            </div>
            <button onClick={onClose} className="text-white/80 hover:text-white text-2xl leading-none">&times;</button>
          </div>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-heading font-bold text-white">¥{planInfo[tier].price}</span>
            <span className="text-orange-100 text-sm">/年</span>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {step === 'method' && (
            <>
              <p className="text-sm text-slate-600 mb-4">{planInfo[tier].features}</p>
              <p className="text-sm font-medium text-slate-700 mb-3">选择支付方式</p>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <button
                  onClick={() => setSelectedMethod('wechat')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    selectedMethod === 'wechat'
                      ? 'border-green-500 bg-green-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.108.24-.242 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.87c-.135-.003-.27-.012-.406-.012zm-2.53 3.274c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.969-.982z"/>
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-slate-700">微信支付</span>
                </button>
                <button
                  onClick={() => setSelectedMethod('alipay')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    selectedMethod === 'alipay'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-sm">支</span>
                  </div>
                  <span className="text-sm font-medium text-slate-700">支付宝</span>
                </button>
              </div>

              {selectedMethod && (
                <div className="mb-4 p-4 bg-slate-50 rounded-xl text-center">
                  <p className="text-xs text-slate-500 mb-2">扫码支付 ¥{planInfo[tier].price}</p>
                  <div className="w-32 h-32 bg-slate-200 rounded-lg mx-auto flex items-center justify-center text-slate-400 text-xs">
                    {/* Mock QR code placeholder */}
                    <div className="w-24 h-24 bg-slate-100 rounded border-2 border-dashed border-slate-300 flex items-center justify-center">
                      <span className="text-xs text-slate-400">模拟二维码</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">（演示环境：点击"确认支付"直接开通）</p>
                </div>
              )}

              <button
                onClick={() => selectedMethod && setStep('confirm')}
                disabled={!selectedMethod}
                className="w-full py-3 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors"
              >
                继续
              </button>
            </>
          )}

          {step === 'confirm' && (
            <>
              <div className="text-center mb-5">
                <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-8 h-8 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>
                  </svg>
                </div>
                <h4 className="font-bold text-slate-900">确认支付</h4>
                <p className="text-sm text-slate-500 mt-1">
                  支付 <span className="font-bold text-orange-600">¥{planInfo[tier].price}</span> 开通 {planInfo[tier].name}
                </p>
              </div>
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => setStep('method')}
                  className="flex-1 py-3 border border-slate-300 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors"
                >
                  返回
                </button>
                <button
                  onClick={handleMockPay}
                  disabled={loading}
                  className="flex-1 py-3 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                      开通中...
                    </>
                  ) : (
                    <>确认支付 ¥{planInfo[tier].price}</>
                  )}
                </button>
              </div>
              <p className="text-center text-xs text-slate-400 mt-3">
                支付遇到问题？联系 <a href="mailto:zxq@zxqconsulting.com" className="text-orange-500 hover:underline">zxq@zxqconsulting.com</a>
              </p>
            </>
          )}

          {step === 'done' && (
            <div className="text-center py-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7"/>
                </svg>
              </div>
              <h4 className="font-bold text-slate-900 text-lg">{planInfo[tier].name} 开通成功！</h4>
              <p className="text-sm text-slate-500 mt-2 mb-6">您已获得全年无限次关税计算权限</p>
              <button
                onClick={onClose}
                className="w-full py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-xl transition-colors"
              >
                前往账号中心 →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Pricing Page ──────────────────────────────────────────────────────────────
const PLANS = [
  {
    id: 'free' as SubscriptionTier,
    name: '免费版',
    price: '¥0',
    period: '永久',
    description: '适合初步了解关税计算',
    features: [
      '每天 3 次关税计算',
      '埃塞俄比亚咖啡品类',
      '中国零关税计算',
      '基础成本估算',
    ],
    cta: '当前方案',
    ctaStyle: 'bg-slate-100 text-slate-600 cursor-default',
    popular: false,
  },
  {
    id: 'pro' as SubscriptionTier,
    name: 'Pro 版',
    price: '¥99',
    period: '/年',
    badge: '最受欢迎',
    description: '适合咖啡电商、精品烘焙店主',
    features: [
      '无限次关税计算',
      '全品类覆盖（咖啡/可可/坚果）',
      '多市场计算（中国/欧盟/非洲）',
      '完整成本精算器',
      '原产地AI合规自测',
      'PDF报告导出',
      'HS编码无限查询',
      '邮件支持',
    ],
    cta: '开通 Pro',
    ctaStyle: 'bg-primary-500 hover:bg-primary-600 text-white',
    popular: true,
  },
  {
    id: 'enterprise' as SubscriptionTier,
    name: '企业版',
    price: '¥298',
    period: '/年',
    badge: '团队必备',
    description: '适合贸易公司、报关行',
    features: [
      'Pro 版全部功能',
      '5 个子账号',
      'API 调用权限',
      '批量计算',
      '专属客服',
      '优先数据更新',
    ],
    cta: '开通企业版',
    ctaStyle: 'bg-slate-700 hover:bg-slate-800 text-white',
    popular: false,
  },
]

export default function PricingPage() {
  const { tier: currentTier, isLoggedIn } = useAppStore()
  const navigate = useNavigate()
  const [showPayModal, setShowPayModal] = useState<SubscriptionTier | null>(null)

  function handleUpgrade(planId: SubscriptionTier) {
    if (!isLoggedIn) {
      navigate(`/login?redirect=/pricing&plan=${planId}`)
      return
    }
    setShowPayModal(planId)
  }

  function handlePaySuccess() {
    setShowPayModal(null)
    navigate('/account')
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16">
      {/* Hero */}
      <div className="text-center mb-14">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-3">
          简单透明的定价
        </h1>
        <p className="text-slate-600">
          按年订阅，随时取消。开通即享全年无限次关税计算。
        </p>
      </div>

      {/* Plans grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-14">
        {PLANS.map((plan) => {
          const isCurrent = currentTier === plan.id

          return (
            <div
              key={plan.id}
              className={`relative bg-white rounded-2xl border-2 p-6 flex flex-col ${
                plan.popular
                  ? 'border-primary-500 shadow-xl shadow-primary-100'
                  : 'border-slate-200'
              }`}
            >
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-primary-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    {plan.badge}
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-1">{plan.name}</h2>
                <p className="text-sm text-slate-500">{plan.description}</p>
              </div>

              <div className="mb-6">
                <span className="text-3xl font-heading font-bold text-slate-900">{plan.price}</span>
                <span className="text-slate-500 text-sm">{plan.period}</span>
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                    <svg className="w-4 h-4 text-green-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <div className={`w-full text-center py-2.5 rounded-xl text-sm font-medium ${plan.ctaStyle}`}>
                  {plan.cta}
                </div>
              ) : (
                <button
                  onClick={() => handleUpgrade(plan.id)}
                  className={`w-full py-2.5 rounded-xl text-sm font-medium transition-colors ${plan.ctaStyle}`}
                >
                  {plan.id === 'free' ? '免费使用' : `¥${plan.id === 'pro' ? 99 : 298}/年，立即开通`}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Comparison table */}
      <div className="mb-14 overflow-hidden rounded-2xl border border-slate-200">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">功能对比</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-slate-600 font-medium">功能</th>
                <th className="px-4 py-3 text-center text-slate-600 font-medium">免费版</th>
                <th className="px-4 py-3 text-center bg-orange-50 text-orange-700 font-medium">Pro 版</th>
                <th className="px-4 py-3 text-center text-slate-600 font-medium">企业版</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {[
                ['每天计算次数', '3次', '无限次', '无限次'],
                ['品类覆盖', '咖啡（埃塞）', '全品类', '全品类'],
                ['目的市场', '中国', '中国/欧盟/非洲', '中国/欧盟/非洲'],
                ['成本精算器', '—', '✓ 完整版', '✓ 完整版'],
                ['原产地AI', '—', '✓ DeepSeek', '✓ DeepSeek'],
                ['PDF报告', '—', '✓', '✓'],
                ['HS编码查询', '有限', '无限', '无限'],
                ['子账号', '—', '—', '5个'],
                ['API调用', '—', '—', '✓'],
                ['批量计算', '—', '—', '✓'],
                ['专属客服', '—', '邮件', '优先'],
              ].map(([feature, free, pro, enterprise]) => (
                <tr key={feature} className="hover:bg-slate-50/50">
                  <td className="px-6 py-3 text-slate-700">{feature}</td>
                  <td className="px-4 py-3 text-center text-slate-600">{free}</td>
                  <td className="px-4 py-3 text-center bg-orange-50/50 text-slate-800">{pro}</td>
                  <td className="px-4 py-3 text-center text-slate-600">{enterprise}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FAQ */}
      <div className="mb-10">
        <h2 className="text-xl font-heading font-bold text-slate-900 mb-6 text-center">常见问题</h2>
        <div className="space-y-4 max-w-2xl mx-auto">
          {[
            {
              q: '免费版用完了怎么办？',
              a: '每天有3次免费计算机会，用完后可开通 Pro 版（99元/年）无限制使用。',
            },
            {
              q: '关税计算结果准确吗？',
              a: '中国零关税政策基于国务院公告，税率数据来自海关总署。欧盟和非洲部分为规则估算，如有疑问请以海关确认为准。',
            },
            {
              q: '如何开通 Pro 版？',
              a: '直接在页面选择方案并完成支付（微信/支付宝），支付成功后1小时内开通。如遇问题联系 zxq@zxqconsulting.com。',
            },
            {
              q: '可以退款吗？',
              a: '开通后7天内如对产品不满意，可申请全额退款。',
            },
            {
              q: '企业版包含 API 怎么用？',
              a: '企业版用户可在账号中心生成 API Key，使用 X-API-Key 请求头调用接口，适合ERP、报关系统等自动化集成。',
            },
          ].map((faq) => (
            <div key={faq.q} className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="font-medium text-slate-900 mb-1">{faq.q}</h3>
              <p className="text-sm text-slate-600">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Payment note */}
      <div className="text-center bg-slate-50 rounded-2xl p-6">
        <p className="text-sm text-slate-500 mb-2">
          企业对公转账、发票需求请联系：
          <a href="mailto:zxq@zxqconsulting.com" className="text-orange-600 hover:underline ml-1">
            zxq@zxqconsulting.com
          </a>
        </p>
        <p className="text-xs text-slate-400">微信/支付宝扫码支付实时开通 · 7天无理由退款</p>
      </div>

      {/* Payment Modal */}
      {showPayModal && (
        <PaymentModal
          tier={showPayModal}
          onClose={() => setShowPayModal(null)}
          onSuccess={handlePaySuccess}
        />
      )}
    </div>
  )
}
