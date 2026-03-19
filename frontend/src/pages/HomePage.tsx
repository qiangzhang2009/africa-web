import { Link } from 'react-router-dom'
import { ArrowRight, Calculator, TrendingUp, Globe, Shield } from 'lucide-react'

const features = [
  {
    icon: <Calculator className="w-6 h-6" />,
    title: '关税精准计算',
    desc: '输入商品和原产地，秒知中国零关税节省金额。支持53个非洲建交国全覆盖。',
  },
  {
    icon: <TrendingUp className="w-6 h-6" />,
    title: '成本精算',
    desc: 'FOB到岸成本、回本测算、建议零售价，一站式决策工具。咖啡/可可/坚果全覆盖。',
  },
  {
    icon: <Globe className="w-6 h-6" />,
    title: '多市场套利',
    desc: '中国零关税 + 欧盟EPA估算 + AfCFTA规则，智能比较哪个市场最划算。',
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: '原产地合规',
    desc: '税号改变规则 + 40%增值规则自动判定，AI辅助原产地证书合规自测。',
  },
]

const useCases = [
  { tag: '咖啡电商', example: '埃塞俄比亚耶加雪菲生豆，20kg，FOB $6/kg → 到岸成本？回本几包？' },
  { tag: '可可贸易商', example: '加纳可可豆进口中国，增值加工后返销欧洲 → 关税套利空间？' },
  { tag: '坚果出口商', example: '坦桑尼亚腰果，目的地中国 vs 欧盟 → 哪个市场净利润更高？' },
  { tag: '光伏组装厂', example: '中国组件→南非组装→返销中国 → 能否认定非洲原产、零关税？' },
]

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative bg-gradient-to-br from-slate-900 via-slate-800 to-primary-900 overflow-hidden">
        {/* Decorative */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-10 w-64 h-64 bg-primary-500 rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-20 w-48 h-48 bg-sky-400 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-20 md:py-28 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-primary-500/20 border border-primary-400/30 text-primary-300 text-sm font-medium px-4 py-1.5 rounded-full mb-8">
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-pulse" />
            2026年5月1日起，中国对53个非洲国家100%税目零关税
          </div>

          <h1 className="text-4xl md:text-6xl font-heading font-extrabold text-white leading-tight mb-6">
            非洲零关税<br />
            <span className="text-primary-400">进口决策，一键完成</span>
          </h1>

          <p className="text-lg md:text-xl text-slate-300 max-w-2xl mx-auto mb-10 leading-relaxed">
            输入商品和原产地，秒知关税节省金额与到岸总成本。<br />
            关税计算 + 成本精算 + 原产地合规，一站式决策工具。
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/calculator"
              className="inline-flex items-center gap-2 px-8 py-4 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-all shadow-lg shadow-primary-500/30"
            >
              开始计算关税
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/cost-calculator"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white/10 hover:bg-white/20 text-white font-medium rounded-xl border border-white/20 transition-all"
            >
              成本精算器
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mt-16 max-w-xl mx-auto">
            {[
              { value: '53', label: '非洲建交国' },
              { value: '100%', label: '税目覆盖' },
              { value: '<1s', label: '计算响应' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl md:text-3xl font-heading font-bold text-white">{stat.value}</div>
                <div className="text-sm text-slate-400 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-heading font-bold text-slate-900 mb-4">
              为什么选择 AfricaZero
            </h2>
            <p className="text-slate-600 max-w-xl mx-auto">
              不是"查税率的网站"，而是"告诉我这单能不能做、怎么做的决策工具"。
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f) => (
              <div key={f.title} className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-lg transition-shadow">
                <div className="w-12 h-12 bg-primary-50 text-primary-600 rounded-xl flex items-center justify-center mb-4">
                  {f.icon}
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">{f.title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="py-20 bg-slate-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-heading font-bold text-slate-900 mb-4">
              典型使用场景
            </h2>
            <p className="text-slate-600">
              无论你是咖啡电商、可可贸易商还是光伏组装厂，都能找到答案。
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {useCases.map((uc) => (
              <div key={uc.tag} className="bg-white rounded-xl border border-slate-200 p-6 flex gap-4">
                <div className="shrink-0">
                  <span className="inline-block px-3 py-1 bg-primary-50 text-primary-700 text-sm font-medium rounded-full">
                    {uc.tag}
                  </span>
                </div>
                <p className="text-slate-600 text-sm leading-relaxed">{uc.example}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-3xl font-heading font-bold text-slate-900 mb-4">
            5月1日前，抢占先机
          </h2>
          <p className="text-slate-600 mb-8 leading-relaxed">
            零关税政策5月1日正式生效。提前算清楚成本，锁定最优货源，才能在窗口期内快速卡位。
          </p>
          <Link
            to="/calculator"
            className="inline-flex items-center gap-2 px-8 py-4 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-all"
          >
            立即开始计算
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  )
}
