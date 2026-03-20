import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle, AlertCircle, TrendingUp, Package } from 'lucide-react'

// ─── Product data ─────────────────────────────────────────────────────────────
type Difficulty = '🥉 入门' | '🥈 中等' | '🥇 有门槛'
type Tier = 'free' | 'pro'

interface ProductEntry {
  name: string
  nameEn: string
  hsCode: string
  hsChapter: string
  originCountries: string[]
  zeroTariff: boolean
  mfnRate: string
  difficulty: Difficulty
  tier: Tier
  suitable: string          // 适合什么人
  riskNote: string          // 风险/注意事项
  modelTip: string          // 商业模式建议
}

const PRODUCTS: ProductEntry[] = [
  // ── 咖啡 & 可可 ──────────────────────────────────────────────────────────
  {
    name: '生咖啡豆（未焙炒）',
    nameEn: 'Coffee, not roasted',
    hsCode: '0901.11.00',
    hsChapter: '09',
    originCountries: ['埃塞俄比亚', '肯尼亚', '卢旺达', '坦桑尼亚', '科特迪瓦'],
    zeroTariff: true,
    mfnRate: '8%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: 'SOHO / 初次试水者',
    riskNote: '咖啡品质鉴定有门槛，建议先拿样。国内精品咖啡赛道竞争激烈，需找准分销渠道。',
    modelTip: 'FOB进口 → 找烘焙厂代工 → 精品电商/私域/线下精品咖啡馆分销',
  },
  {
    name: '可可豆（生或焙炒）',
    nameEn: 'Cocoa beans',
    hsCode: '1801.00.00',
    hsChapter: '18',
    originCountries: ['加纳', '科特迪瓦', '尼日利亚', '喀麦隆'],
    zeroTariff: true,
    mfnRate: '8%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: '食品进口商 / 巧克力品牌',
    riskNote: '可可期货价格波动大，建议锁定长期供应商合同。品质分级（ICCO标准）需学习。',
    modelTip: 'FOB进口 → 食品工厂代加工 → 巧克力/可可原料B2B销售，或自有品牌零售',
  },
  {
    name: '可可脂 / 可可液块',
    nameEn: 'Cocoa butter / paste',
    hsCode: '1804.00.00 / 1805.00.00',
    hsChapter: '18',
    originCountries: ['加纳', '科特迪瓦'],
    zeroTariff: true,
    mfnRate: '8%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '食品工厂 / 护肤品原料商',
    riskNote: '需食品进口资质和QS认证。护肤品原料市场利润较高但账期长。',
    modelTip: 'B2B原料供应给食品/化妆品工厂，账期谈判是关键能力',
  },
  {
    name: '速溶咖啡',
    nameEn: 'Instant coffee',
    hsCode: '2101.11.00',
    hsChapter: '21',
    originCountries: ['埃塞俄比亚', '科特迪瓦'],
    zeroTariff: true,
    mfnRate: '10%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '有食品资质的企业进口商',
    riskNote: '速溶咖啡国内竞争激烈（雀巢、麦斯威尔占据主流），差异化定位至关重要。',
    modelTip: '精品速溶定位（如冷萃冻干）切入细分市场，走电商或私域',
  },
  // ── 坚果 & 油籽 ──────────────────────────────────────────────────────────
  {
    name: '腰果仁（去壳）',
    nameEn: 'Cashew kernels',
    hsCode: '0801.32.00',
    hsChapter: '08',
    originCountries: ['坦桑尼亚', '莫桑比克', '贝宁', '科特迪瓦'],
    zeroTariff: true,
    mfnRate: '10%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: '零食品牌 / 食品贸易商',
    riskNote: '腰果仁水分控制要求高，到港后需冷库存放。品质参差不齐，建议亲自验货。',
    modelTip: 'FOB进口 → 分销给零食品牌/烘焙连锁/超市，或自有品牌包装零售',
  },
  {
    name: '带壳腰果（Raw Cashew）',
    nameEn: 'Cashew nuts in shell',
    hsCode: '0801.31.00',
    hsChapter: '08',
    originCountries: ['坦桑尼亚', '莫桑比克'],
    zeroTariff: true,
    mfnRate: '10%',
    difficulty: '🥈 中等',
    tier: 'pro',
    suitable: '有工厂资源的进口商',
    riskNote: '带壳腰果需要加工厂去壳处理，门槛高但利润空间更大。',
    modelTip: '带壳进口 → 国内工厂加工 → 分级腰果仁销售全产业链',
  },
  {
    name: '芝麻',
    nameEn: 'Sesame seeds',
    hsCode: '1207.40.00',
    hsChapter: '12',
    originCountries: ['埃塞俄比亚', '尼日尔', '苏丹', '乍得'],
    zeroTariff: true,
    mfnRate: '9%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: '油脂厂 / 食品厂 / 贸易商',
    riskNote: '芝麻含油量高，存储不当易酸败。品质按含油量、杂质、水分分级。',
    modelTip: '大贸FOB → 供货给油厂/芝麻食品工厂，走量为主，利润薄但稳定',
  },
  {
    name: '花生仁',
    nameEn: 'Groundnut kernels',
    hsCode: '1202.30.00',
    hsChapter: '12',
    originCountries: ['苏丹', '尼日利亚', '塞内加尔'],
    zeroTariff: true,
    mfnRate: '15%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: '食品加工商 / 贸易商',
    riskNote: '花生黄曲霉素检测是过关关键，需要求供应商提供检测报告。',
    modelTip: 'FOB进口 → 食品工厂或零食品牌，走B2B渠道',
  },
  {
    name: '蓖麻籽',
    nameEn: 'Castor beans',
    hsCode: '1207.30.00',
    hsChapter: '12',
    originCountries: ['印度（对比）', '莫桑比克', '坦桑尼亚'],
    zeroTariff: true,
    mfnRate: '15%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '化工原料贸易商',
    riskNote: '蓖麻油用于化工/医药/航空领域，零关税后有成本优势。',
    modelTip: 'B2B供货给化工厂或贸易商，账期谈判很重要',
  },
  // ── 矿产品 ──────────────────────────────────────────────────────────────
  {
    name: '铜矿砂及其精矿',
    nameEn: 'Copper ores & concentrates',
    hsCode: '2603.00.00',
    hsChapter: '26',
    originCountries: ['赞比亚', '刚果（金）', '南非'],
    zeroTariff: true,
    mfnRate: '0%',
    difficulty: '🥇 有门槛',
    tier: 'pro',
    suitable: '大宗贸易商 / 有资金实力的企业',
    riskNote: '大宗商品，汇率风险高，资金占用大。需要稳定的物流和质检合作方。',
    modelTip: 'LCL或整柜进口，供货给铜冶炼厂；或与冶炼厂签订长期供货协议',
  },
  {
    name: '钴矿砂',
    nameEn: 'Cobalt ores & concentrates',
    hsCode: '2605.00.00',
    hsChapter: '26',
    originCountries: ['刚果（金）', '赞比亚'],
    zeroTariff: true,
    mfnRate: '0%',
    difficulty: '🥇 有门槛',
    tier: 'pro',
    suitable: '新能源产业链企业',
    riskNote: '钴价随新能源市场波动极大。需要钴盐/正极材料工厂作为下游。',
    modelTip: '供货给新能源材料工厂，或通过期货对冲价格风险后操作现货',
  },
  {
    name: '锰矿',
    nameEn: 'Manganese ores',
    hsCode: '2602.00.00',
    hsChapter: '26',
    originCountries: ['南非', '加蓬', '澳大利亚（对比）'],
    zeroTariff: true,
    mfnRate: '0%',
    difficulty: '🥇 有门槛',
    tier: 'pro',
    suitable: '钢铁厂 / 锰合金厂',
    riskNote: '南非政治稳定，运输周期约30-40天。锰矿品位差异影响定价。',
    modelTip: '与国内锰合金厂签订FOB或CIF合同，规模化运作',
  },
  {
    name: '铬矿',
    nameEn: 'Chromium ores',
    hsCode: '2610.00.00',
    hsChapter: '26',
    originCountries: ['南非', '津巴布韦'],
    zeroTariff: true,
    mfnRate: '0%',
    difficulty: '🥇 有门槛',
    tier: 'pro',
    suitable: '不锈钢厂 / 铬铁合金厂',
    riskNote: '铬铁是不锈钢的关键原料，国内需求稳定。',
    modelTip: 'CIF进口直供工厂，建立长期供应关系',
  },
  // ── 皮革 & 毛皮 ──────────────────────────────────────────────────────────
  {
    name: '生牛皮（整张）',
    nameEn: 'Raw hides & skins of bovine',
    hsCode: '4101.20.00',
    hsChapter: '41',
    originCountries: ['埃塞俄比亚', '肯尼亚', '苏丹'],
    zeroTariff: true,
    mfnRate: '5%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '皮革制品厂 / 鞋材供应商',
    riskNote: '皮张需要盐腌保存，处理不当到货质量差。需有冷库或合作仓储。',
    modelTip: 'FOB进口 → 供货给皮革厂/鞋材商，质量稳定后建立长期合同',
  },
  {
    name: '已剖开生牛皮',
    nameEn: 'Whole hides, split',
    hsCode: '4101.50.00',
    hsChapter: '41',
    originCountries: ['埃塞俄比亚', '尼日利亚'],
    zeroTariff: true,
    mfnRate: '5%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '皮革化工厂 / 皮件制造商',
    riskNote: '关注含盐量、斑点等质量指标。',
    modelTip: '与国内皮革化工厂建立供应关系',
  },
  // ── 木材 ──────────────────────────────────────────────────────────────
  {
    name: '原木（热带硬木）',
    nameEn: 'Wood in the rough, tropical',
    hsCode: '4403.11.00',
    hsChapter: '44',
    originCountries: ['加蓬', '喀麦隆', '莫桑比克', '刚果（布）'],
    zeroTariff: true,
    mfnRate: '0%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '家具厂 / 建材贸易商',
    riskNote: '木材进口涉及FSC认证（合法性证明），无认证可能遭海关退运。',
    modelTip: '确认供应商能提供FSC证书和出口许可 → 进口 → 家具厂或建材分销',
  },
  {
    name: '锯材（已加工木材）',
    nameEn: 'Wood sawn / chipped',
    hsCode: '4407.00.00',
    hsChapter: '44',
    originCountries: ['加蓬', '喀麦隆'],
    zeroTariff: true,
    mfnRate: '0%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '家具厂 / 地板厂',
    riskNote: '板材含水率控制是关键，过高导致开裂。FSC认证同样重要。',
    modelTip: '进口板材直供家具厂或地板品牌，建立稳定供货关系',
  },
  // ── 香料 & 草本 ──────────────────────────────────────────────────────────
  {
    name: '未磨胡椒',
    nameEn: 'Pepper, neither crushed nor ground',
    hsCode: '0904.11.00',
    hsChapter: '09',
    originCountries: ['马达加斯加', '埃塞俄比亚'],
    zeroTariff: true,
    mfnRate: '15%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: '调料品牌 / 食品贸易商',
    riskNote: '马达加斯加胡椒在全球有品牌溢价（如萨哈拉马达加斯加胡椒）。',
    modelTip: '定位精品调料品牌，进入高端超市或餐饮B2B渠道',
  },
  {
    name: '香草（未加工）',
    nameEn: 'Vanilla, not processed',
    hsCode: '0905.00.00',
    hsChapter: '09',
    originCountries: ['马达加斯加', '科摩罗', '乌干达'],
    zeroTariff: true,
    mfnRate: '15%',
    difficulty: '🥇 有门槛',
    tier: 'pro',
    suitable: '香料贸易商 / 食品厂',
    riskNote: '香草是全球第二贵香料，天然香草产量不稳定，价格波动剧烈。',
    modelTip: '低价时囤货，做香料B2B分销；或与食品厂签订长期供货合同',
  },
  {
    name: '茴香籽 / 葛缕子籽',
    nameEn: 'Seeds: fennel, caraway',
    hsCode: '0909.30.00',
    hsChapter: '09',
    originCountries: ['摩洛哥', '埃及', '苏丹'],
    zeroTariff: true,
    mfnRate: '15%',
    difficulty: '🥉 入门',
    tier: 'free',
    suitable: '调料品牌 / 食品加工',
    riskNote: '香辛料市场需求稳定，适合初学者起步。',
    modelTip: 'FOB进口 → 食品调料品牌分销或B2B供货',
  },
  // ── 农产品 & 棉麻 ──────────────────────────────────────────────────────────
  {
    name: '生棉纤维',
    nameEn: 'Raw cotton, not carded/combed',
    hsCode: '5201.00.00',
    hsChapter: '52',
    originCountries: ['贝宁', '马里', '布基纳法索', '苏丹', '坦桑尼亚'],
    zeroTariff: true,
    mfnRate: '10%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '纺织厂 / 棉纱贸易商',
    riskNote: '棉花进口需配额，但非洲部分国家有单独配额优惠。长度、强力是核心指标。',
    modelTip: '供货给纺织厂，棉花价格与国际期货挂钩，定价能力有限，走量为主',
  },
  {
    name: '剑麻 / 龙舌兰纤维',
    nameEn: 'Sisal, raw',
    hsCode: '5304.00.00',
    hsChapter: '53',
    originCountries: ['坦桑尼亚', '肯尼亚', '莫桑比克'],
    zeroTariff: true,
    mfnRate: '5%',
    difficulty: '🥈 中等',
    tier: 'free',
    suitable: '纤维制品厂 / 复合材料工厂',
    riskNote: '剑麻用于复合材料、绳索、特种纸。国内市场需求较为细分。',
    modelTip: '工业B2B供货，与纤维制品工厂建立长期合作',
  },
]

const CATEGORY_GROUPS = [
  { label: '全部', value: 'all' },
  { label: '🥉 入门级', value: 'easy' },
  { label: '🥈 中等级', value: 'medium' },
  { label: '🥇 有门槛', value: 'hard' },
  { label: '🥤 咖啡 & 可可', value: '09,18' },
  { label: '🥜 坚果 & 油籽', value: '08,12' },
  { label: '⛏️ 矿产品', value: '26' },
  { label: '👜 皮革 & 木才', value: '41,44' },
  { label: '🌿 香料 & 农产品', value: '09,52,53' },
]

function filterProducts(products: ProductEntry[], filter: string): ProductEntry[] {
  if (filter === 'all') return products
  if (filter === 'easy') return products.filter((p) => p.difficulty === '🥉 入门')
  if (filter === 'medium') return products.filter((p) => p.difficulty === '🥈 中等')
  if (filter === 'hard') return products.filter((p) => p.difficulty === '🥇 有门槛')
  return products.filter((p) => filter.split(',').includes(p.hsChapter))
}

export default function ProductDiscoveryPage() {
  const [activeFilter, setActiveFilter] = useState('all')
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null)

  const filtered = filterProducts(PRODUCTS, activeFilter)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">非洲选品清单</h1>
        <p className="text-slate-600">
          基于零关税政策 × 非洲优势货源 × 入门门槛，筛选出的可行品类。标注难度和适合人群，小白也能看懂。
        </p>
      </div>

      {/* Beginner guidance - "I don't know where to start" entry */}
      <div className="bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50 border border-orange-200 rounded-2xl p-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center shrink-0">
            <span className="text-xl">🤔</span>
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-slate-900 mb-1">不知道做什么方向？先回答三个问题</h2>
            <p className="text-sm text-slate-600 mb-4 leading-relaxed">
              选品是新人最难的部分。我们把问题拆成三步，帮助你快速找到适合的方向——不需要经验，只需要知道自己属于哪类。
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              {[
                {
                  icon: '💼',
                  q: '你有多少启动资金？',
                  a: '小额试水 (<¥5万)：咖啡、可可、腰果、芝麻',
                  b: '中等规模 (¥5-50万)：皮革、香料、棉纤维',
                  c: '大宗贸易 (>¥50万)：矿产品（铜、钴、锰）',
                },
                {
                  icon: '🏭',
                  q: '你有没有下游渠道？',
                  a: '有食品/工厂渠道 → 选原材料 B2B',
                  b: '有零售/私域资源 → 选咖啡/可可走品牌路线',
                  c: '没有渠道 → 先做选品调研+小批量找感觉',
                },
                {
                  icon: '📦',
                  q: '你想做零售还是批发？',
                  a: '零售/私域 → 咖啡、可可（品牌溢价高）',
                  b: 'B2B供货 → 芝麻、腰果仁（走量稳定）',
                  c: '供应链服务 → 找下游买家再进货',
                },
              ].map((card, i) => (
                <div key={i} className="bg-white/80 rounded-xl p-4 border border-orange-100">
                  <div className="text-xl mb-2">{card.icon}</div>
                  <div className="text-sm font-semibold text-slate-700 mb-2">{card.q}</div>
                  <div className="space-y-1">
                    {[card.a, card.b, card.c].map((t, j) => (
                      <div key={j} className="text-xs text-slate-500 leading-relaxed">• {t}</div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/getting-started"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                新手入门完整路线图
              </Link>
              <button
                onClick={() => setActiveFilter('easy')}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-orange-50 text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:border-orange-300 transition-colors"
              >
                查看「入门级」品类
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pro callout */}
      <div className="bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 rounded-xl p-4 mb-8 flex items-start gap-3">
        <Package className="w-5 h-5 text-orange-500 mt-0.5 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-orange-800 mb-1">标注「有门槛 / Pro」品类的完整信息</p>
          <p className="text-xs text-orange-700 leading-relaxed">
            矿产品（铜、钴、锰、铬）和部分加工品需要更大的资金规模、物流安排和资质要求。开通 Pro 后解锁详细供应链分析。
          </p>
        </div>
        <Link
          to="/pricing"
          className="shrink-0 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold rounded-lg transition-colors"
        >
          开通 Pro
        </Link>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORY_GROUPS.map((f) => (
          <button
            key={f.value}
            onClick={() => setActiveFilter(f.value)}
            className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
              activeFilter === f.value
                ? 'bg-primary-500 text-white border-primary-500'
                : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300 hover:text-primary-600'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Results count */}
      <p className="text-sm text-slate-500 mb-4">{filtered.length} 个品类</p>

      {/* Product list */}
      <div className="space-y-4">
        {filtered.map((product) => {
          const isExpanded = expandedProduct === product.hsCode
          return (
            <div
              key={product.hsCode + product.name}
              className={`bg-white rounded-2xl border transition-colors ${
                isExpanded ? 'border-primary-300 shadow-md' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {/* Card header */}
              <button
                className="w-full text-left p-5"
                onClick={() => setExpandedProduct(isExpanded ? null : product.hsCode)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-semibold text-slate-900">{product.name}</span>
                      <span className="text-xs text-slate-400">{product.nameEn}</span>
                      <span className="font-mono text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {product.hsCode}
                      </span>
                      {product.zeroTariff ? (
                        <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded-full">
                          <CheckCircle className="w-3 h-3" />
                          零关税
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded-full">
                          <AlertCircle className="w-3 h-3" />
                          不适用
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                      <span>MFN基准税率：{product.mfnRate}</span>
                      <span>主要产区：{product.originCountries.join('、')}</span>
                      <span className={
                        product.difficulty === '🥉 入门' ? 'text-green-600' :
                        product.difficulty === '🥈 中等' ? 'text-yellow-600' : 'text-red-600'
                      }>
                        {product.difficulty}
                      </span>
                      {product.tier === 'pro' && (
                        <span className="text-orange-500 font-medium">Pro</span>
                      )}
                    </div>
                  </div>
                  <ArrowRight className={`w-4 h-4 text-slate-400 mt-1 shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </div>
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-5 pb-5 border-t border-slate-100 pt-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="bg-slate-50 rounded-xl p-4">
                      <div className="text-xs font-medium text-slate-500 mb-1">适合人群</div>
                      <div className="text-sm text-slate-800">{product.suitable}</div>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-4">
                      <div className="text-xs font-medium text-slate-500 mb-1">难度</div>
                      <div className="text-sm text-slate-800">{product.difficulty}</div>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-4">
                      <div className="text-xs font-medium text-slate-500 mb-1">零关税节省</div>
                      <div className="text-sm text-slate-800">vs MFN省{product.mfnRate}</div>
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 mb-4">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-semibold text-amber-800 mb-1">风险提示</p>
                        <p className="text-xs text-amber-700 leading-relaxed">{product.riskNote}</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-green-50 border border-green-100 rounded-xl p-4 mb-5">
                    <div className="flex items-start gap-2">
                      <TrendingUp className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-semibold text-green-800 mb-1">商业模式建议</p>
                        <p className="text-xs text-green-700 leading-relaxed">{product.modelTip}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Link
                      to={`/hs-lookup?q=${encodeURIComponent(product.name)}`}
                      className="flex items-center gap-1.5 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      查询HS详情 →
                    </Link>
                    <Link
                      to="/cost-calculator"
                      className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 text-sm font-medium rounded-lg transition-colors"
                    >
                      成本精算 →
                    </Link>
                    <Link
                      to="/origin-check"
                      className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 text-sm font-medium rounded-lg transition-colors"
                    >
                      原产地自测 →
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom CTA */}
      <div className="mt-12 text-center">
        <p className="text-sm text-slate-500 mb-4">
          选好品类后，用工具验证成本和原产地资格
        </p>
        <div className="flex justify-center gap-3">
          <Link
            to="/cost-calculator"
            className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-medium rounded-xl transition-colors"
          >
            成本精算器
          </Link>
          <Link
            to="/origin-check"
            className="px-6 py-3 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 font-medium rounded-xl transition-colors"
          >
            原产地自测
          </Link>
        </div>
      </div>
    </div>
  )
}
