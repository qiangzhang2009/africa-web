import { Link } from 'react-router-dom'
import { track } from '../utils/track'

const plans = [
  {
    id: 'free',
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
    id: 'pro',
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
    id: 'enterprise',
    name: '企业版',
    price: '¥298',
    period: '/年',
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
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16">
      <div className="text-center mb-14">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-3">
          简单透明的定价
        </h1>
        <p className="text-slate-600">
          按年订阅，随时取消。5月1日零关税生效前，Pro 版先到先得。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-14">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative bg-white rounded-2xl border-2 p-6 ${
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

            <ul className="space-y-3 mb-8">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                  <svg className="w-4 h-4 text-green-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>

            {plan.id === 'free' ? (
              <div className={plan.ctaStyle + ' w-full text-center py-2.5 rounded-xl text-sm font-medium'}>
                {plan.cta}
              </div>
            ) : (
              <Link
                to="/dashboard"
                onClick={() => track.pricingCtaClick(plan.id, plan.name)}
                className={`block w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors ${plan.ctaStyle}`}
              >
                {plan.cta}
              </Link>
            )}
          </div>
        ))}
      </div>

      <div className="text-center">
        <p className="text-sm text-slate-500 mb-3">
          支付方式：微信 / 支付宝收款码转账，请联系我们付款后开通
        </p>
        <p className="text-sm text-slate-400">
          企业对公转账、发票需求请联系：<a href="mailto:zxq@zxqconsulting.com" className="text-primary-600 hover:underline">zxq@zxqconsulting.com</a>
        </p>
      </div>

      <div className="mt-16">
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
              a: '联系客服微信（公众号底部），转账后1小时内开通。',
            },
            {
              q: '可以退款吗？',
              a: '开通后7天内如对产品不满意，可申请全额退款。',
            },
          ].map((faq) => (
            <div key={faq.q} className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="font-medium text-slate-900 mb-1">{faq.q}</h3>
              <p className="text-sm text-slate-600">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
