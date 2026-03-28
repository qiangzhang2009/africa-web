import { useState } from 'react'
import { Link } from 'react-router-dom'
import { searchHSCodes } from '../data/local'
import { track } from '../utils/track'
import type { HSSearchResult } from '../types'

// ─── African trade-friendly categories ──────────────────────────────────────
const CATEGORIES = [
  {
    label: '咖啡 & 可可',
    color: 'bg-amber-50 text-amber-700',
    keywords: ['咖啡', '可可', '咖啡豆', '可可豆', '生豆', '焙炒', '速溶'],
    hsExamples: ['0901', '1801', '1805', '1806'],
    hint: '埃塞俄比亚、肯尼亚、加纳、科特迪瓦是主力产区',
  },
  {
    label: '坚果 & 油籽',
    color: 'bg-emerald-50 text-emerald-700',
    keywords: ['腰果', '坚果', '芝麻', '花生', '蓖麻', '油籽', '去壳', '带壳'],
    hsExamples: ['0801', '1201', '1202', '1203', '1204', '1207'],
    hint: '坦桑尼亚、莫桑比克、尼日尔的腰果产量居非洲前列',
  },
  {
    label: '矿产品',
    color: 'bg-slate-100 text-slate-700',
    keywords: ['铜', '钴', '锰', '铬', '镍', '矿', '砂', '精矿', '锂'],
    hsExamples: ['2603', '2605', '2602', '2604', '2617'],
    hint: '刚果（金）、南非、赞比亚是中国重要矿产品进口来源',
  },
  {
    label: '皮革 & 皮毛',
    color: 'bg-orange-50 text-orange-700',
    keywords: ['皮革', '牛皮', '羊皮', '毛皮', '皮张', '皮革制品'],
    hsExamples: ['4101', '4104', '4105', '4107', '4301'],
    hint: '埃塞俄比亚皮革质量优良，畜牧业资源丰富',
  },
  {
    label: '木材 & 木制品',
    color: 'bg-lime-50 text-lime-700',
    keywords: ['木材', '原木', '锯材', '木浆', '木板', '红木'],
    hsExamples: ['4401', '4402', '4403', '4404', '4407'],
    hint: '加蓬、喀麦隆、莫桑比克的优质硬木资源丰富',
  },
  {
    label: '香料 & 草本',
    color: 'bg-rose-50 text-rose-700',
    keywords: ['胡椒', '丁香', '香草', '桂皮', '八角', '茶叶'],
    hsExamples: ['0904', '0905', '0906', '0907', '0908', '1211'],
    hint: '马达加斯加的香草、埃塞俄比亚的咖啡全球知名',
  },
  {
    label: '农产品 & 棉麻',
    color: 'bg-yellow-50 text-yellow-700',
    keywords: ['棉花', '棉纱', '棉纤维', '麻', '剑麻', '棉籽'],
    hsExamples: ['5201', '5203', '5205', '5301', '5302'],
    hint: '贝宁、马里、苏丹是非洲重要产棉国',
  },
  {
    label: '其他工业品',
    color: 'bg-blue-50 text-blue-700',
    keywords: ['钢材', '废钢', '铝', '铜材', '化工', '塑料'],
    hsExamples: ['7204', '7601', '7403', '3901'],
    hint: '钢材/废钢(72章)大多不在零关税范围，建议关注非洲优势矿产品',
  },
]

// ─── Fuzzy tip mappings ──────────────────────────────────────────────────────
const FUZZY_TIPS: Record<string, string> = {
  '钢材': '钢材类(72章)目前不在零关税政策范围内，进口需缴纳6-8%的MFN关税。建议关注铜矿(2603)、钴矿砂(2605)、锰矿(2602)等零关税矿产品。',
  '废钢': '废钢(7204)不在零关税范围内。可关注：铜矿、钴矿砂、锰矿等非洲优势矿产品。',
  '废旧钢材': '废钢(7204)不在零关税范围内。可关注：铜矿(2603)、钴矿砂(2605)、锰矿(2602)等非洲优势矿产品。',
  '汽车': '整车进口需3C认证，门槛极高。建议了解：矿产品、农产品等非洲特色货源。',
  '手机': '手机(8517)进口需3C认证，门槛较高，且大多数为一般贸易进口，非洲手机出口较少。建议关注：原材料、农矿产品方向。',
  '衣服': '服装(61-62章)大多不在零关税范围。可尝试：皮革制品、棉纤维原料。',
  '家具': '家具品类复杂，建议先确认HS编码，或浏览下方品类获取选品灵感。',
  '塑料': '初级形态的塑料(39章)有部分可享零关税。可浏览"坚果油籽"品类参考分析思路。',
  '可可': '可可豆(1801)是零关税入门品类，加纳和科特迪瓦是全球最大产区，非常适合新手！试试搜索「可可豆」或浏览"咖啡可可"分类。',
  '可可豆': '可可豆(1801)是零关税入门品类！加纳和科特迪瓦是全球可可产量最大的两个国家，非常适合新手启动中非贸易。',
  '腰果': '腰果(0801)是零关税入门品类！坦桑尼亚、莫桑比克、贝宁产量丰富，去壳腰果仁适合零食品牌或B2B分销。',
  '铜': '铜矿(2603)享受零关税！赞比亚和刚果(金)是中国铜矿进口主要来源，属于有资金门槛的大宗商品。',
  '钴': '钴矿砂(2605)零关税，刚果(金)和赞比亚是核心产区。新能源产业链热门品类，适合有下游渠道的企业。',
  '锰': '锰矿(2602)零关税，南非是主要来源。适合钢铁厂或锰合金厂，需规模化运作。',
  '铝': '铝材(76章)部分享受零关税。可浏览"矿产品"分类了解更多详情。',
  '木材': '热带硬木原木(44章)部分零关税！加蓬、喀麦隆有优质硬木资源。注意需要FSC认证。',
  '咖啡': '咖啡(0901)是零关税入门首选！埃塞俄比亚耶加雪菲、肯尼亚AA都是全球精品咖啡知名产区。',
  '钢铁': '钢铁(72章)目前不在非洲零关税政策范围内，进口需缴纳6-8%MFN关税。',
  '煤炭': '煤炭(27章)不在零关税范围内，进口关税约5-6%，不适合作为中非零关税贸易品类。',
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function HSLookupPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<HSSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [searchGuidance, setSearchGuidance] = useState<string | null>(null)

  async function handleSearch(searchQuery?: string) {
    const q = searchQuery ?? query
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    setSearched(true)
    setActiveCategory(null)
    setSearchGuidance(null)
    try {
      const data = await searchHSCodes(q.trim())
      setResults(data ?? [])
      // 检查是否有非零关税品类，给出通用引导
      const hasNonZero = data?.some(r => r.zero_tariff === false)
      const zeroCount = data?.filter(r => r.zero_tariff === true).length ?? 0
      track.hsSearch(q.trim(), data?.length ?? 0, zeroCount)
      if (hasNonZero) {
        setSearchGuidance('以上结果中，非零关税品类已用红色标注。零关税节省 = MFN税率（最惠国税率）。部分品类（汽车、电子)另有3C认证要求，请确认后再投入。')
      }
    } catch {
      setError('查询失败，请重试')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const fuzzyTip = query.trim() ? FUZZY_TIPS[query.trim()] : null
  const hasResults = searched && results.length > 0
  const noResults = searched && results.length === 0 && !loading && !error

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">HS编码查询</h1>
        <p className="text-slate-600">输入商品中文名称或关键词，智能匹配10位HS税号与零关税适用情况</p>
      </div>

      {/* Search bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-8">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="如：咖啡生豆，腰果、铜矿砂、钢材、汽车、手机"
            className="flex-1 px-4 py-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? '搜索中...' : '查询'}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {/* 搜索建议提示 */}
        {!searched && (
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="text-xs text-slate-400">试试：</span>
            {['咖啡', '可可', '腰果', '钢材', '汽车', '铜矿', '芝麻'].map((word) => (
              <button
                key={word}
                onClick={() => { setQuery(word); handleSearch(word) }}
                className="text-xs text-slate-500 hover:text-primary-600 hover:bg-primary-50 px-2 py-0.5 rounded transition-colors"
              >
                {word}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Fuzzy tip for known "hard" queries */}
      {fuzzyTip && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl">
          <div className="flex items-start gap-3">
            <span className="text-xl mt-0.5 shrink-0">💡</span>
            <div>
              <p className="text-sm font-medium text-amber-800 mb-1">关于「{query.trim()}」的提示</p>
              <p className="text-sm text-amber-700">{fuzzyTip}</p>
              <Link to="/products" className="inline-flex items-center gap-1 text-xs text-orange-600 font-medium mt-2 hover:text-orange-700">
                浏览全部可选品类 →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* 通用引导（当结果中有非零关税品类时显示） */}
      {hasResults && searchGuidance && (
        <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-xl">
          <p className="text-xs text-slate-600">{searchGuidance}</p>
        </div>
      )}

      {/* No results guidance */}
      {noResults && !fuzzyTip && (
        <div className="mb-6 p-5 bg-slate-50 border border-slate-200 rounded-xl">
          <p className="text-sm font-medium text-slate-800 mb-3">未找到相关HS编码，以下方向可能有帮助：</p>
          <div className="flex flex-wrap gap-2 mb-4">
            {['咖啡', '可可', '腰果', '芝麻', '铜矿', '钴矿', '锰矿', '生皮'].map((word) => (
              <button
                key={word}
                onClick={() => { setQuery(word); handleSearch(word); track.hsSearch(word, -1, 0) }}
                className="px-3 py-1.5 bg-white border border-slate-300 text-slate-600 text-sm rounded-lg hover:border-primary-400 hover:text-primary-600 transition-colors"
              >
                {word}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500 mb-4">
            或者 <Link to="/products" className="text-primary-600 hover:underline">浏览全部可选品类</Link> — 按行业分类展示非洲优势出口产品清单
          </p>
          {/* 选品方向引导 */}
          <div className="mt-4 pt-4 border-t border-slate-200">
            <p className="text-xs font-semibold text-slate-600 mb-2">不知道做什么方向？试试这些思路：</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { icon: '☕', title: '食品消费', desc: '咖啡、可可、腰果 — 品质标准清晰，适合电商或B2B', tags: ['🥉 入门', '零关税'] },
                { icon: '⛏️', title: '工业原料', desc: '铜矿、钴矿、锰矿 — 大宗商品，资金门槛高但利润稳定', tags: ['🥇 有门槛'] },
                { icon: '👜', title: '特色农产品', desc: '皮革、芝麻、香草 — 细分市场，适合有特定渠道的商家', tags: ['🥈 中等'] },
              ].map((dir) => (
                <Link
                  key={dir.title}
                  to="/products"
                  className="bg-white border border-slate-200 rounded-xl p-3 hover:border-primary-300 hover:shadow-sm transition-all group"
                >
                  <div className="text-xl mb-1">{dir.icon}</div>
                  <div className="text-sm font-semibold text-slate-800 group-hover:text-primary-600 transition-colors">{dir.title}</div>
                  <div className="text-xs text-slate-500 mt-1 leading-relaxed">{dir.desc}</div>
                  <div className="flex gap-1 mt-2">
                    {dir.tags.map((tag) => (
                      <span key={tag} className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{tag}</span>
                    ))}
                  </div>
                </Link>
              ))}
            </div>
            <div className="mt-4 text-center">
              <Link
                to="/getting-started"
                className="inline-flex items-center gap-1.5 text-sm text-orange-600 font-medium hover:text-orange-700"
              >
                新手入门完整指南：从选品到第一单 →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {hasResults && (
        <div className="space-y-3">
          <p className="text-sm text-slate-500">{results.length} 个结果</p>
          {results.map((item, i) => {
            const isZero = item.zero_tariff === true
            const isNonZero = item.zero_tariff === false
            return (
              <div key={i} className={`bg-white rounded-xl border p-4 flex items-start justify-between gap-4 ${
                isNonZero ? 'border-red-200 bg-red-50' : 'border-slate-200'
              }`}>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-mono text-sm bg-slate-100 text-slate-700 px-2 py-0.5 rounded">{item.hs_10 || '—'}
                    </span>
                    {item.category && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        isNonZero ? 'bg-red-100 text-red-700' : 'bg-primary-50 text-primary-700'
                      }`}>
                        {item.category}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-900">{item.name_zh}</p>
                  {/* 非零关税品类额外提示 */}
                  {isNonZero && item.category_guidance && (
                    <p className="text-xs text-red-600 mt-1 leading-relaxed">{item.category_guidance}</p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs text-slate-500 mb-1">MFN税率</div>
                  <div className={`text-sm font-semibold ${
                    isZero ? 'text-green-600' : isNonZero ? 'text-red-600' : 'text-slate-700'
                  }`}>
                    {(item.mfn_rate * 100).toFixed(1)}%
                  </div>
                  {isZero ? (
                    <div className="text-xs text-green-600 mt-0.5 font-medium">✅ 零关税</div>
                  ) : isNonZero ? (
                    <div className="text-xs text-red-600 mt-0.5 font-medium">❌ 不适用</div>
                  ) : (
                    <div className="text-xs text-slate-500 mt-0.5">—</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Category browser — visible when no search */}
      {!searched && (
        <div>
          <h3 className="font-semibold text-slate-900 mb-4">按品类浏览（非洲优势出口产品）</h3>
          <div className="flex flex-wrap gap-2 mb-6">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.label}
                onClick={() => { setActiveCategory(activeCategory === cat.label ? null : cat.label); track.hsBrowseCategory(cat.label) }}
                className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                  activeCategory === cat.label
                    ? 'bg-primary-500 text-white border-primary-500'
                    : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300 hover:text-primary-600'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Expanded category detail */}
          {activeCategory && (() => {
            const cat = CATEGORIES.find((c) => c.label === activeCategory)!
            return (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-8">
                <div className="flex items-start gap-4 mb-4">
                  <div className={`px-3 py-1 rounded-full text-sm font-medium shrink-0 ${cat.color}`}>
                    {cat.label}
                  </div>
                  <p className="text-sm text-slate-500 leading-relaxed">{cat.hint}</p>
                </div>
                <p className="text-xs text-slate-400 mb-4">
                  参考HS编码：{cat.hsExamples.join('、')}
                </p>
                <div className="flex flex-wrap gap-2 mb-4">
                  {cat.keywords.map((kw) => (
                    <button
                      key={kw}
                      onClick={() => { setQuery(kw); handleSearch(kw); track.hsSearch(kw, -1, 0) }}
                      className="px-3 py-1.5 bg-slate-50 border border-slate-200 text-slate-600 text-sm rounded-lg hover:border-primary-300 hover:text-primary-600 transition-colors"
                    >
                      搜索「{kw}」
                    </button>
                  ))}
                </div>
                <div className="text-xs text-slate-400 pt-3 border-t border-slate-100">
                  💡 {cat.hint}
                </div>
              </div>
            )
          })()}

          {/* Quick links */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
            {[
              { to: '/cost-calculator', icon: '💰', title: '成本精算器', desc: '选好心仪品类后，一键算出到岸总成本' },
              { to: '/origin-check', icon: '📋', title: '原产地自测', desc: 'AI判断你的货物是否符合零关税原产地规则' },
              { to: '/products', icon: '📦', title: '完整选品清单', desc: '按行业分类的非洲优势出口产品汇总' },
            ].map((card) => (
              <Link
                key={card.to}
                to={card.to}
                onClick={() => track.hsQuickLink(card.to)}
                className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow group"
              >
                <div className="text-2xl mb-2">{card.icon}</div>
                <div className="text-sm font-semibold text-slate-900 group-hover:text-primary-600 transition-colors">{card.title}</div>
                <div className="text-xs text-slate-500 mt-1">{card.desc}</div>
              </Link>
            ))}
          </div>

          {/* Common codes */}
          <h3 className="font-semibold text-slate-900 mb-4">常用品类速查</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { name: '咖啡生豆（未焙炒）', code: '0901.11.00' },
              { name: '可可豆（生或焙炒）', code: '1801.00.00' },
              { name: '腰果仁（去壳）', code: '0801.32.00' },
              { name: '铜矿砂及其精矿', code: '2603.00.00' },
              { name: '钴矿砂', code: '2605.00.00' },
              { name: '锰矿', code: '2602.00.00' },
              { name: '生皮（牛）', code: '4101.20.00' },
              { name: '芝麻', code: '1207.40.00' },
            ].map((c) => (
              <div key={c.code} className="bg-white rounded-xl border border-slate-200 p-3">
                <p className="text-sm text-slate-900 font-medium">{c.name}</p>
                <p className="text-xs text-slate-500 font-mono mt-1">{c.code}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
