// 非洲零关税选品数据
// 包含：零关税品类 + 常见非零关税品类说明

export interface Product {
  hsCode: string
  name: string
  nameEn: string
  mfnRate: string
  zeroTariff: boolean
  originCountries: string[]
  difficulty: string   // 🥉 入门 | 🥈 中等 | 🥇 有门槛
  suitable: string
  tier: 'free' | 'pro'
  riskNote: string
  modelTip: string
  category: string
}

export interface CategoryGroup {
  value: string
  label: string
  color: string
}

export const CATEGORY_GROUPS: CategoryGroup[] = [
  { value: 'all', label: '全部', color: 'bg-slate-100 text-slate-700' },
  { value: 'easy', label: '🥉 入门级', color: 'bg-green-100 text-green-700' },
  { value: 'medium', label: '🥈 中等级', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'pro', label: '🥇 有门槛', color: 'bg-red-100 text-red-700' },
  { value: 'not-zero', label: '⚠️ 非零关税', color: 'bg-gray-100 text-gray-700' },
]

export const PRODUCTS: Product[] = [
  // ─── 咖啡 & 可可 ───────────────────────────────────────────────────────────────
  {
    hsCode: '0901.11.00',
    name: '咖啡生豆（未焙炒）',
    nameEn: 'Coffee, not roasted',
    mfnRate: '8%',
    zeroTariff: true,
    originCountries: ['埃塞俄比亚', '肯尼亚', '卢旺达', '坦桑尼亚', '科特迪瓦'],
    difficulty: '🥉 入门',
    suitable: '无渠道经验的新人、B2B供货商、精品咖啡爱好者',
    tier: 'free',
    riskNote: '埃塞俄比亚咖啡多为部落合作社模式，品控需要经验。建议从单一产地批发出发，找有SCA杯测证书的供应商。',
    modelTip: 'B2B供货给烘焙厂/咖啡店：每柜20吨FOB约$3000-4000/吨，利润10-15%；C端电商：精品豆250g/罐售价¥60-120，回购率高。',
    category: 'easy',
  },
  {
    hsCode: '1801.00.00',
    name: '可可豆（生或焙炒）',
    nameEn: 'Cocoa beans',
    mfnRate: '8%',
    zeroTariff: true,
    originCountries: ['加纳', '科特迪瓦', '尼日利亚', '喀麦隆'],
    difficulty: '🥉 入门',
    suitable: '食品加工厂、巧克力品牌、烘焙店主、进口批发商',
    tier: 'free',
    riskNote: '加纳可可豆品质稳定，但价格受纽约ICE期货影响波动大，建议锁价采购。科特迪瓦可可豆性价比高，适合做大批量B2B。',
    modelTip: 'B2B供货给巧克力厂/食品厂：每柜25吨FOB约$2500-3500/吨；C端精品生巧/巧克力：毛利50-70%。',
    category: 'easy',
  },
  {
    hsCode: '0801.32.00',
    name: '腰果仁（去壳）',
    nameEn: 'Cashew nuts, shelled',
    mfnRate: '10%',
    zeroTariff: true,
    originCountries: ['坦桑尼亚', '莫桑比克', '贝宁', '科特迪瓦', '几内亚比绍'],
    difficulty: '🥉 入门',
    suitable: '零食品牌、进口零食批发商、食品电商、烘焙原料商',
    tier: 'free',
    riskNote: '非洲腰果加工能力有限，部分为越南/印度加工后转口，需确认原产地证书。坦桑尼亚腰果品质最优。',
    modelTip: '批发给食品厂/零食品牌：每柜10吨FOB约$4000-5500/吨，利润8-12%；C端零售：500g袋装售价¥50-80。',
    category: 'easy',
  },
  {
    hsCode: '1207.40.00',
    name: '芝麻种子',
    nameEn: 'Sesame seeds',
    mfnRate: '10%',
    zeroTariff: true,
    originCountries: ['苏丹', '埃塞俄比亚', '坦桑尼亚', '尼日利亚', '莫桑比克'],
    difficulty: '🥉 入门',
    suitable: '油厂、调味品厂、芝麻食品加工商、进口批发商',
    tier: 'free',
    riskNote: '非洲芝麻含油量高(50%以上)，品质优于国产。建议采购前要求SGS质检报告，含油量≥50%、水分≤6%。',
    modelTip: '大批量供货给油厂/调味品厂：每柜20吨FOB约$1200-1800/吨，利润5-8%；精品熟芝麻零售：毛利20-30%。',
    category: 'easy',
  },
  {
    hsCode: '2603.00.00',
    name: '铜矿砂及其精矿',
    nameEn: 'Copper ores and concentrates',
    mfnRate: '2%',
    zeroTariff: true,
    originCountries: ['赞比亚', '刚果（金）', '坦桑尼亚'],
    difficulty: '🥇 有门槛',
    suitable: '有色金属冶炼厂、铜材加工厂、大宗商品进口商',
    tier: 'pro',
    riskNote: '资金门槛极高（每柜货值$15-30万），需稳定的下游买家、专业的物流安排（散货船+港口清关）。赞比亚铜矿含铜量20-30%。',
    modelTip: '长协供货给冶炼厂：每批次500-1000吨，毛利2-5%；做期现结合对冲价格风险是必备能力。',
    category: 'pro',
  },
  {
    hsCode: '2605.00.00',
    name: '钴矿砂及其精矿',
    nameEn: 'Cobalt ores and concentrates',
    mfnRate: '2%',
    zeroTariff: true,
    originCountries: ['刚果（金）', '赞比亚'],
    difficulty: '🥇 有门槛',
    suitable: '新能源电池材料厂、钴盐加工厂、有色金属进口商',
    tier: 'pro',
    riskNote: '资金门槛极高，受新能源市场影响价格波动剧烈。刚果（金）政治风险需评估，建议通过有资质的国际贸易商操作。',
    modelTip: '供货给电池材料厂：每批次100-500吨，毛利3-8%；需绑定长期供货协议才能稳定运作。',
    category: 'pro',
  },
  {
    hsCode: '2602.00.00',
    name: '锰矿砂及其精矿',
    nameEn: 'Manganese ores and concentrates',
    mfnRate: '2%',
    zeroTariff: true,
    originCountries: ['南非', '加蓬', '澳大利亚'],
    difficulty: '🥇 有门槛',
    suitable: '钢铁厂、锰合金厂、冶金进口商',
    tier: 'pro',
    riskNote: '南非锰矿品位较高(Mn 37-48%)，但运输周期长(45-60天)。需要与下游钢铁厂有稳定合作。',
    modelTip: '长协供货给钢铁厂：每批次1000-5000吨FOB约$4-6/吨度，利润微薄但量大稳定。',
    category: 'pro',
  },
  {
    hsCode: '4101.20.00',
    name: '生牛皮（整张）',
    nameEn: 'Raw hides, bovine, whole',
    mfnRate: '5%',
    zeroTariff: true,
    originCountries: ['埃塞俄比亚', '肯尼亚', '坦桑尼亚', '苏丹'],
    difficulty: '🥈 中等',
    suitable: '皮革制品厂、皮具品牌、皮革进口商',
    tier: 'free',
    riskNote: '皮革需要盐腌保鲜处理，仓储和物流要求高。埃塞俄比亚皮革品质优良但供应不稳定，建议从小批量开始。',
    modelTip: '供货给皮革厂：每柜10-20吨FOB约$0.8-1.5/平方英尺；自营皮具品牌：毛利40-60%。',
    category: 'medium',
  },
  {
    hsCode: '0905.00.00',
    name: '香草（Vanilla）',
    nameEn: 'Vanilla',
    mfnRate: '15%',
    zeroTariff: true,
    originCountries: ['马达加斯加', '科摩罗', '印度尼西亚'],
    difficulty: '🥈 中等',
    suitable: '食品香料商、化妆品原料商、精品食品品牌',
    tier: 'free',
    riskNote: '马达加斯加香草全球占比80%，价格波动极大(2015年¥600/公厅→2018年¥1200/公厅)。需有冷库存储条件，保质期2年。',
    modelTip: '供货给食品香料厂/化妆品厂：每批500-2000公斤，毛利20-40%；精品香草荚零售：每克¥2-5。',
    category: 'medium',
  },
  {
    hsCode: '5201.00.00',
    name: '棉花（未梳化）',
    nameEn: 'Cotton, not carded',
    mfnRate: '1%',
    zeroTariff: true,
    originCountries: ['贝宁', '马里', '布基纳法索', '苏丹', '埃及'],
    difficulty: '🥈 中等',
    suitable: '纺织厂、棉纱贸易商、棉籽油加工厂',
    tier: 'free',
    riskNote: '棉花品质受品种和加工水平影响大，贝宁/马里棉花纤维长度好，适合中高端纺织。埃及长绒棉享誉全球但产量有限。',
    modelTip: '大批量供货给纺织厂：每批500-2000吨，毛利3-6%；棉花贸易商可做期现结合。',
    category: 'medium',
  },
  // ─── 橡木桶/特色 ──────────────────────────────────────────────────────────────
  {
    hsCode: '4403.41.00',
    name: '热带红木原木',
    nameEn: 'Tropical hardwood logs',
    mfnRate: '1%',
    zeroTariff: true,
    originCountries: ['加蓬', '喀麦隆', '莫桑比克', '刚果（布）'],
    difficulty: '🥇 有门槛',
    suitable: '家具厂、木材加工厂、建筑装饰商',
    tier: 'pro',
    riskNote: '热带硬木原木进口需FSC认证（森林可持续经营认证），且涉及CITES濒危物种附录。必须确认木材在非濒危名单内。',
    modelTip: '供货给家具厂/地板厂：每柜50-100立方米FOB约$300-600/立方米，利润8-15%。需有稳定的客户关系。',
    category: 'pro',
  },
  // ─── 以下为非零关税品类 ─────────────────────────────────────────────────────
  {
    hsCode: '7204.10.00',
    name: '钢铁废碎料',
    nameEn: 'Ferrous waste and scrap',
    mfnRate: '8%',
    zeroTariff: false,
    originCountries: ['全球供应，中国为主要进口国'],
    difficulty: '🥈 中等',
    suitable: '钢厂、废钢回收贸易商',
    tier: 'free',
    riskNote: '⚠️ 废钢不在零关税政策范围内！进口需缴纳8%MFN关税。中国钢厂需求量大但价格竞争激烈。',
    modelTip: '废钢进口每吨FOB约$350-450，8%关税后到岸成本约$380-490/吨。利润极薄(¥50-100/吨)，靠走量取胜。',
    category: 'not-zero',
  },
  {
    hsCode: '8703.23.41',
    name: '汽油型小客车（1500-3000cc）',
    nameEn: 'Gasoline car 1500-3000cc',
    mfnRate: '25%',
    zeroTariff: false,
    originCountries: ['全球主要汽车生产国'],
    difficulty: '🥇 有门槛',
    suitable: '汽车进口商、4S店集团',
    tier: 'pro',
    riskNote: '⚠️ 汽车不在零关税政策范围内！整车进口需3C认证，门槛极高（认证费用¥50-100万/车型，周期12-18个月）。不建议新人介入。',
    modelTip: '平行进口汽车：综合税率(含关税+消费税+增值税)约120-150%，终端价格高。除非有特定渠道，否则不建议。',
    category: 'not-zero',
  },
  {
    hsCode: '8517.12.10',
    name: '手机（GSM或CDMA制式）',
    nameEn: 'Mobile phones',
    mfnRate: '0%',
    zeroTariff: false,
    originCountries: ['中国、美国、韩国、日本'],
    difficulty: '🥇 有门槛',
    suitable: '手机进口商、通讯设备商',
    tier: 'pro',
    riskNote: '⚠️ 手机进口需3C认证，门槛较高。虽然MFN税率为0，但非洲手机制造能力弱，非洲进口手机到中国的业务量极小。',
    modelTip: '手机进口主要是从亚洲到非洲的贸易方向（与中国出口相反）。不建议做非洲→中国的手机进口。',
    category: 'not-zero',
  },
  {
    hsCode: '6109.10.00',
    name: '棉制针织T恤',
    nameEn: "Knitted T-shirt, cotton",
    mfnRate: '12%',
    zeroTariff: false,
    originCountries: ['越南', '孟加拉', '印度', '土耳其'],
    difficulty: '🥈 中等',
    suitable: '服装贸易商、跨境电商',
    tier: 'free',
    riskNote: '⚠️ 服装纺织品(61-62章)不在零关税政策范围内！进口需缴纳12-17%MFN关税。非洲服装制造业不发达，不是主要服装出口国。',
    modelTip: '服装进口多从东南亚（越南、孟加拉）进面料/成衣，毛利15-25%。非洲手工面料（如马里蜡染布）可走文创/奢侈品路线。',
    category: 'not-zero',
  },
  {
    hsCode: '3901.10.00',
    name: '聚乙烯（比重<0.94）',
    nameEn: 'Polyethylene, primary',
    mfnRate: '6.5%',
    zeroTariff: false,
    originCountries: ['中东（沙特、伊朗）、美国、新加坡'],
    difficulty: '🥈 中等',
    suitable: '塑料制品厂、化工厂、大宗贸易商',
    tier: 'free',
    riskNote: '⚠️ 初级塑料(39章)MFN税率6.5%，不在零关税政策非洲→中国范围内。虽然中东是主要来源，但非洲塑料产能有限。',
    modelTip: 'PE塑料粒子每吨FOB约$1000-1300，6.5%关税后到岸。利润薄（¥100-200/吨），靠走量，适合有稳定下游客户的贸易商。',
    category: 'not-zero',
  },
]

export function filterProducts(products: Product[], filter: string): Product[] {
  if (filter === 'all') return products
  if (filter === 'not-zero') return products.filter(p => !p.zeroTariff)
  return products.filter(p => p.category === filter)
}
