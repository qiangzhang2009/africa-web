import { Link } from 'react-router-dom'
import { ArrowRight, Users } from 'lucide-react'

const STEPS = [
  {
    step: 1,
    icon: '🔍',
    title: '了解政策：零关税到底是什么',
    time: '10 分钟',
    content: `2026年5月1日起，中国对全部53个非洲建交国给予100%税目零关税待遇。这意味着什么？

• 以前：非洲咖啡豆进口到中国要交8%关税 + 13%增值税
• 以后：关税为0，只需交13%增值税（相比MFN省8%）
• 覆盖范围：100% HS税目，覆盖面极广

但注意：零关税 ≠ 免所有税。增值税、消费税等仍需缴纳。

更重要的是：享受零关税的前提是你的货物"真正来自非洲"——这叫原产地规则。`,
    action: { label: '了解详细政策规则', to: '/policy' },
    tips: ['不要误以为"从非洲过境就算原产地"', '非洲53个建交国 ≠ 非洲全部国家，注意产地核查'],
  },
  {
    step: 2,
    icon: '🛍️',
    title: '选品：非洲什么货值得做',
    time: '20 分钟',
    content: `不是所有非洲货都值得做。选品要同时考虑三个维度：

① 零关税适用性 — 必须在零关税税目范围内
② 利润空间 — 关税节省能否覆盖其他成本
③ 启动门槛 — 小白能否快速起步

我们按难度筛选了三类：
• 🥉 入门级：咖啡生豆、腰果、可可豆、芝麻 — 品质标准清晰，供应商多
• 🥈 中等级：皮革、原木、香料 — 需要品质鉴别知识
• 🥇 有门槛：矿产品（铜、钴、锰）— 资金门槛高，适合企业操作`,
    action: { label: '浏览完整选品清单', to: '/products' },
    tips: ['小白建议从单一品类切入，不要一开始就做多品类', '咖啡、可可、腰果是公认最适合新手的三大品类'],
  },
  {
    step: 3,
    icon: '💰',
    title: '算账：真的省钱吗？到底能省多少',
    time: '15 分钟',
    content: `零关税听起来很美，但实际落地要算清楚。

成本精算需要包括：
• FOB货值（离岸价）
• 国际运费（海运/空运）
• 保险（约货值0.5%）
• 关税（零关税后为0）
• 增值税（13%，到岸价计征）
• 清关杂费（报关、检验等）
• 仓储物流

示例：一柜60kg埃塞俄比亚耶加雪菲咖啡生豆
• FOB货值：$6/kg × 60kg = $360
• 海运费：$4/kg = $240
• 零关税节省：$360 × 8% = $28.8/柜（对比MFN）
• 实际到岸增值税：($360+$240) × 13% = $78

工具帮您一键算出所有成本，不用手动套公式。`,
    action: { label: '用成本精算器试算', to: '/cost-calculator' },
    tips: ['零关税节省的金额相对于运费和汇率波动是次要的，关键是找到稳定的货源和分销渠道', '第一次建议小批量试货（60kg起步）'],
  },
  {
    step: 4,
    icon: '📋',
    title: '验证：你的货真的"够非洲"吗',
    time: '10 分钟',
    content: `这是最容易踩坑的环节。

原产地证书（CO, Certificate of Origin）是享受零关税的核心文件。海关凭此证书认定货物原产地。

非洲零关税的原产地认定有两种规则：
① 税则改变规则（CTH）：原材料在非洲经过了实质性加工，导致HS编码发生变化
② 增值比例规则：非洲区域内增值达到40%以上

举例：
• 埃塞俄比亚生咖啡豆 → 零关税 ✓（原产地就是埃塞俄比亚）
• 中国商人在非洲采购原料，回国简单包装 → 可能不满足原产地规则 ✗

建议在采购前先做原产地自测，确认货物能享受零关税再付款。`,
    action: { label: 'AI 原产地自测', to: '/origin-check' },
    tips: ['不要等货物到了海关再查原产地，那时候已经晚了', '找有经验的报关行或贸促会提前确认'],
  },
  {
    step: 5,
    icon: '🛻',
    title: '物流：怎么运回来',
    time: '15 分钟',
    content: `非洲到中国的主要物流方式：

• 海运（LCL/拼箱）：适合60kg-1吨，$3.5-5.5/kg，约30-40天到港
• 海运（FCL/整柜）：适合20英尺柜约17-20吨，$2-3/kg，适合大货
• 空运：适合高价值、时效要求高的货物，$6-8/kg，7-12天

小批量建议从LCL起步，减少资金压力。

关键节点：
① 国内卸港清关（找有非洲货物清关经验的报关行）
② 如涉及食品，需提前办理食品进口备案和检疫审批
③ 拿到原产地证书后，报关时享受零关税申报`,
    action: { label: '了解贸促会原产地证书办理', to: 'https://www.ccpit.org/', external: true },
    tips: ['选择有"门到门"服务能力的货代，减少中间环节', '提前确认货物是否需要进口许可或检疫证明'],
  },
  {
    step: 6,
    icon: '🤝',
    title: '分销：货进来了怎么卖',
    time: '15 分钟',
    content: `拿到货只是开始，分销才是真正的战场。

适合小白的几种分销路径：

• 精品电商（B2C）：淘宝、京东、抖音电商 — 需要品牌化运营，适合咖啡、可可等消费品
• B2B供货：供货给食品工厂、烘焙店、餐饮连锁 — 起量快，但账期长
• 私域分销：通过微信、小红书、社群卖货 — 适合精品定位，客单价高
• 供应链切入：不做零售，只做"非洲货源对接"服务，赚信息差和服务费

小白建议：先找一家下游B2B买家，谈好需求再进货，不要先进货再找买家。

AfricaZero帮您做前端选品和成本计算，分销策略需要结合您的资源来定。`,
    action: { label: '联系我们定制方案', to: 'mailto:zxq@zxqconsulting.com', external: true },
    tips: ['从小批量、多批次开始，不要一开始就压重仓', '选品比努力更重要——选对赛道事半功倍'],
  },
]

export default function GettingStartedPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 bg-orange-50 text-orange-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-4">
          <Users className="w-3.5 h-3.5" />
          新手入门
        </div>
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-3">
          零关税非洲贸易：从零到第一单的完整路径
        </h1>
        <p className="text-slate-600 max-w-2xl mx-auto leading-relaxed">
          如果你听说了"非洲零关税"新闻，想做点中非生意但不知道从哪里开始，这篇指南为你而写。
          零关税只是入场券，真正落地还有5个步骤。我们把每一步都拆开了讲。读完你就知道该不该做，以及从哪里切入。
        </p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-4 mb-12">
        {[
          { icon: '🌍', value: '53国', label: '零关税覆盖建交国' },
          { icon: '💯%', value: '100%', label: 'HS税目全覆盖' },
          { icon: '📅', value: '5月1日', label: '政策生效日期' },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl border border-slate-200 p-4 text-center">
            <div className="text-2xl mb-1">{stat.icon}</div>
            <div className="text-xl font-heading font-bold text-slate-900">{stat.value}</div>
            <div className="text-xs text-slate-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Steps */}
      <div className="space-y-6">
        {STEPS.map((step) => (
          <div key={step.step} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            {/* Step header */}
            <div className="flex items-center gap-4 px-6 py-5 border-b border-slate-100">
              <div className="w-12 h-12 bg-primary-50 text-primary-600 rounded-xl flex items-center justify-center text-2xl shrink-0">
                {step.icon}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-primary-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    {step.step}
                  </div>
                  <h3 className="font-semibold text-slate-900">{step.title}</h3>
                </div>
                <div className="flex items-center gap-4 mt-1">
                  <span className="text-xs text-slate-400">⏱ {step.time}</span>
                </div>
              </div>
            </div>

            {/* Step content */}
            <div className="px-6 py-5">
              <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-line mb-5 leading-relaxed">
                {step.content}
              </div>

              {/* Tips */}
              {step.tips && (
                <div className="bg-slate-50 rounded-xl p-4 mb-5">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">💡 过来人经验</p>
                  <ul className="space-y-1">
                    {step.tips.map((tip, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2">
                        <span className="text-primary-500 mt-0.5">•</span>
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action */}
              {step.action && (
                step.action.external ? (
                  <a
                    href={step.action.to}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-primary-500 hover:bg-primary-600 text-white text-sm font-semibold rounded-xl transition-colors"
                  >
                    {step.action.label}
                    <ArrowRight className="w-4 h-4" />
                  </a>
                ) : (
                  <Link
                    to={step.action.to}
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-primary-500 hover:bg-primary-600 text-white text-sm font-semibold rounded-xl transition-colors"
                  >
                    {step.action.label}
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                )
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom CTA */}
      <div className="mt-12 bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-8 text-center">
        <h3 className="text-xl font-heading font-bold text-white mb-2">
          准备好开始了？
        </h3>
        <p className="text-slate-300 text-sm mb-6 max-w-sm mx-auto">
          从选品开始，先确定哪个品类适合你，再算清成本，验证原产地。
        </p>
        <div className="flex justify-center gap-3 flex-wrap">
          <Link
            to="/products"
            className="inline-flex items-center gap-1.5 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-xl transition-colors"
          >
            浏览选品清单
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/calculator"
            className="inline-flex items-center gap-1.5 px-6 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-xl transition-colors border border-white/20"
          >
            关税计算器
          </Link>
        </div>
        <p className="text-slate-500 text-xs mt-6">
          如需一对一咨询，联系：<a href="mailto:zxq@zxqconsulting.com" className="text-primary-400 hover:underline">zxq@zxqconsulting.com</a>
        </p>
      </div>
    </div>
  )
}
