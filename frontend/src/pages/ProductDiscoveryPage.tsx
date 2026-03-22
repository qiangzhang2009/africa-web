import { useState, useMemo, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, CheckCircle, AlertCircle, TrendingUp, Calculator,
  Zap, Bookmark, BookmarkCheck, SlidersHorizontal, Search,
  ChevronDown, ChevronRight, X, Filter, Globe, MapPin, Package,
  Coffee, Gem, Trees, Shirt, Factory, Sparkles,
  Palette, Wheat, Fish, BookOpen
} from 'lucide-react'
import {
  PRODUCTS, DIFFICULTY_GROUPS, REGION_GROUPS, LEVEL_GROUPS,
  CATEGORY_TREE,
  filterProducts, findCategoryL1ByValue, findCategoryL2ByValue, findRegionByValue,
  type Product
} from '../data/products'
import { calculateImportCost } from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'
import { track } from '../utils/track'
import type { ImportCostResult } from '../types'

function fmt(n: number) {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(n)
}

function diffColor(d: string) {
  if (d.includes('入门')) return 'text-green-600'
  if (d.includes('中等')) return 'text-yellow-600'
  return 'text-red-600'
}

// ── 图标映射 ──────────────────────────────────────────────────────────────────
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  'agri-food':     <Coffee className="w-3.5 h-3.5" />,
  'spices-bev':    <Sparkles className="w-3.5 h-3.5" />,
  'minerals':      <Gem className="w-3.5 h-3.5" />,
  'leather-fur':   <Shirt className="w-3.5 h-3.5" />,
  'wood-forest':   <Trees className="w-3.5 h-3.5" />,
  'textiles':      <Shirt className="w-3.5 h-3.5" />,
  'industrial':    <Factory className="w-3.5 h-3.5" />,
  'cosmetics-beauty': <Sparkles className="w-3.5 h-3.5" />,
  'arts-crafts':   <Palette className="w-3.5 h-3.5" />,
  'livestock':     <Wheat className="w-3.5 h-3.5" />,
  'aquatic':       <Fish className="w-3.5 h-3.5" />,
  'not-zero-ref':  <BookOpen className="w-3.5 h-3.5" />,
}

const REGION_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  emerald:  { bg: 'bg-emerald-50',  border: 'border-emerald-200', text: 'text-emerald-700' },
  amber:    { bg: 'bg-amber-50',   border: 'border-amber-200',   text: 'text-amber-700' },
  blue:     { bg: 'bg-blue-50',    border: 'border-blue-200',    text: 'text-blue-700' },
  slate:    { bg: 'bg-slate-100',  border: 'border-slate-200',   text: 'text-slate-700' },
  violet:   { bg: 'bg-violet-50',  border: 'border-violet-200',  text: 'text-violet-700' },
  cyan:     { bg: 'bg-cyan-50',    border: 'border-cyan-200',    text: 'text-cyan-700' },
}

// ── 面包屑组件 ────────────────────────────────────────────────────────────────
function Breadcrumbs({
  difficulty, categoryL1, categoryL2, region, onReset
}: {
  difficulty: string
  categoryL1: string
  categoryL2: string
  region: string
  onReset: () => void
}) {
  const parts: { label: string; active?: boolean }[] = []
  if (difficulty !== 'all') {
    const dg = DIFFICULTY_GROUPS.find(d => d.value === difficulty)
    if (dg) parts.push({ label: dg.label, active: true })
  }
  if (categoryL1 !== 'all') {
    const cat = findCategoryL1ByValue(categoryL1)
    if (cat) parts.push({ label: cat.label, active: categoryL2 === 'all' })
  }
  if (categoryL2 !== 'all') {
    const cat = findCategoryL2ByValue(categoryL2)
    if (cat) parts.push({ label: cat.label, active: true })
  }
  if (region !== 'all') {
    const rg = findRegionByValue(region)
    if (rg) parts.push({ label: rg.label, active: true })
  }

  if (parts.length === 0) return null

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {parts.map((p, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <ChevronRight className="w-3 h-3 text-slate-400" />}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            p.active
              ? 'bg-primary-100 text-primary-700 border border-primary-200'
              : 'bg-slate-100 text-slate-600'
          }`}>
            {p.label}
          </span>
        </span>
      ))}
      <button onClick={onReset} className="text-xs text-slate-400 hover:text-primary-600 ml-1">
        <X className="w-3 h-3" />
      </button>
    </div>
  )
}

// ── 左侧分类树组件 ────────────────────────────────────────────────────────────
function CategoryTree({
  selectedL1, selectedL2, onSelectL1, onSelectL2,
  l1Counts, mobile = false
}: {
  selectedL1: string
  selectedL2: string
  onSelectL1: (v: string) => void
  onSelectL2: (v: string) => void
  l1Counts: Record<string, number>
  mobile?: boolean
}) {
  const [expandedL1, setExpandedL1] = useState<Set<string>>(
    selectedL1 !== 'all' ? new Set([selectedL1]) : new Set()
  )

  useEffect(() => {
    if (selectedL1 !== 'all') {
      setExpandedL1(prev => { const n = new Set(prev); n.add(selectedL1); return n })
    }
  }, [selectedL1])

  function toggleL1(v: string) {
    const next = new Set(expandedL1)
    if (next.has(v)) next.delete(v)
    else next.add(v)
    setExpandedL1(next)
  }

  const containerClass = mobile
    ? 'grid grid-cols-2 gap-1.5'
    : 'space-y-0.5'

  return (
    <div className={containerClass}>
      {CATEGORY_TREE.map(l1 => {
        const count = l1Counts[l1.value] || 0
        const isActive = selectedL1 === l1.value
        const isExpanded = expandedL1.has(l1.value)
        const hasChildren = !!l1.children?.length

        if (!mobile) {
          return (
            <div key={l1.value}>
              {/* 一级分类 */}
              <button
                onClick={() => { onSelectL1(l1.value); toggleL1(l1.value) }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-all ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 font-semibold border border-primary-200'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <span className={isActive ? 'text-primary-500' : 'text-slate-400'}>{l1.icon}</span>
                <span className="flex-1 text-left">{l1.label}</span>
                {hasChildren && (
                  <span
                    onClick={(e) => { e.stopPropagation(); toggleL1(l1.value) }}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  </span>
                )}
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  isActive ? 'bg-primary-100 text-primary-600' : 'bg-slate-100 text-slate-500'
                }`}>
                  {count}
                </span>
              </button>

              {/* 二级分类 */}
              {hasChildren && isExpanded && (
                <div className="ml-6 mt-0.5 space-y-0.5 border-l-2 border-slate-100 pl-3 py-0.5">
                  {l1.children!.map(l2 => {
                    const l2Active = selectedL2 === l2.value
                    return (
                      <button
                        key={l2.value}
                        onClick={() => onSelectL2(l2.value)}
                        className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-md transition-all ${
                          l2Active
                            ? 'bg-primary-100 text-primary-700 font-semibold'
                            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                        }`}
                      >
                        <span>{l2.icon}</span>
                        <span className="flex-1 text-left">{l2.label}</span>
                        {l2Active && <CheckCircle className="w-3 h-3 text-primary-500" />}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        }

        // 移动端：网格布局，不展开子级
        return (
          <button
            key={l1.value}
            onClick={() => onSelectL1(isActive ? 'all' : l1.value)}
            className={`flex items-center gap-2 px-3 py-2 text-sm rounded-xl border transition-all ${
              isActive
                ? 'bg-primary-50 text-primary-700 font-semibold border-primary-200'
                : 'bg-white text-slate-600 border-slate-200 hover:border-primary-300'
            }`}
          >
            <span className={isActive ? 'text-primary-500' : 'text-slate-400'}>{l1.icon}</span>
            <span className="flex-1 text-left text-xs">{l1.label}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${
              isActive ? 'bg-primary-100 text-primary-600' : 'bg-slate-100 text-slate-500'
            }`}>
              {count}
            </span>
          </button>
        )
      })}
    </div>
  )
}

// ── 地区选择面板 ─────────────────────────────────────────────────────────────
function RegionPanel({
  selectedRegion, onSelectRegion, onSelectLevel
}: {
  selectedRegion: string
  onSelectRegion: (v: string) => void
  onSelectLevel: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [level, setLevel] = useState('all')
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const selectedReg = findRegionByValue(selectedRegion)

  function handleLevel(v: string) {
    setLevel(v)
    onSelectLevel(v)
  }

  const filteredRegions = level === 'all'
    ? REGION_GROUPS
    : REGION_GROUPS.filter(r => r.level === level)

  return (
    <div ref={panelRef} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-all ${
          selectedRegion !== 'all'
            ? 'bg-blue-50 border-blue-200 text-blue-700 font-medium'
            : 'bg-white border-slate-200 text-slate-600 hover:border-blue-300'
        }`}
      >
        <MapPin className="w-3.5 h-3.5" />
        {selectedReg ? selectedReg.label : '全部地区'}
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-80 bg-white rounded-2xl border border-slate-200 shadow-xl z-50 overflow-hidden">
          {/* 发展水平快速切换 */}
          <div className="flex border-b border-slate-100 bg-slate-50">
            {LEVEL_GROUPS.map(l => (
              <button
                key={l.value}
                onClick={() => handleLevel(l.value)}
                className={`flex-1 px-2 py-2 text-xs font-medium transition-colors ${
                  level === l.value
                    ? 'bg-white text-primary-700 border-b-2 border-primary-500'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {l.icon} {l.label}
              </button>
            ))}
          </div>

          {/* 地区列表 */}
          <div className="p-2 max-h-72 overflow-y-auto space-y-0.5">
            <button
              onClick={() => { onSelectRegion('all'); setOpen(false) }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-all ${
                selectedRegion === 'all'
                  ? 'bg-primary-50 text-primary-700 font-semibold border border-primary-200'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Globe className="w-3.5 h-3.5 text-slate-400" />
              <span>全部地区</span>
              {selectedRegion === 'all' && <CheckCircle className="w-3.5 h-3.5 text-primary-500 ml-auto" />}
            </button>

            {filteredRegions.map(r => {
              const colors = REGION_COLORS[r.color] || REGION_COLORS.slate
              return (
                <button
                  key={r.value}
                  onClick={() => { onSelectRegion(r.value); setOpen(false) }}
                  className={`w-full flex items-start gap-2 px-3 py-2 text-sm rounded-lg transition-all ${
                    selectedRegion === r.value
                      ? 'bg-primary-50 text-primary-700 font-semibold border border-primary-200'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full ${colors.bg} border ${colors.border} flex items-center justify-center mt-0.5 shrink-0`}>
                    <span className={`text-xs ${colors.text}`}>{r.label[0]}</span>
                  </div>
                  <div className="flex-1 text-left">
                    <div className="font-medium text-xs">{r.label}</div>
                    <div className="text-xs text-slate-400 mt-0.5">{r.description}</div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.countries.slice(0, 4).map(c => (
                        <span key={c} className="text-xs bg-slate-100 text-slate-500 px-1 rounded">{c}</span>
                      ))}
                      {r.countries.length > 4 && (
                        <span className="text-xs text-slate-400">+{r.countries.length - 4}</span>
                      )}
                    </div>
                  </div>
                  {selectedRegion === r.value && <CheckCircle className="w-3.5 h-3.5 text-primary-500 mt-1" />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── 难度标签组 ────────────────────────────────────────────────────────────────
function DifficultyBar({
  selected, onChange
}: {
  selected: string
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {DIFFICULTY_GROUPS.map(g => (
        <button
          key={g.value}
          onClick={() => onChange(g.value)}
          className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full border transition-all ${
            selected === g.value
              ? g.value === 'easy'      ? 'bg-green-100 border-green-300 text-green-800 font-semibold' :
                g.value === 'medium'    ? 'bg-yellow-100 border-yellow-300 text-yellow-800 font-semibold' :
                g.value === 'pro'        ? 'bg-red-100 border-red-300 text-red-800 font-semibold' :
                g.value === 'not-zero'   ? 'bg-gray-100 border-gray-300 text-gray-800 font-semibold' :
                'bg-primary-100 border-primary-300 text-primary-800 font-semibold'
              : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
          }`}
        >
          <span>{g.emoji}</span>
          <span>{g.label}</span>
        </button>
      ))}
    </div>
  )
}

// ── 主页面 ────────────────────────────────────────────────────────────────────
export default function ProductDiscoveryPage() {
  const [difficulty, setDifficulty] = useState('all')
  const [categoryL1, setCategoryL1] = useState('all')
  const [categoryL2, setCategoryL2] = useState('all')
  const [region, setRegion] = useState('all')
  const [searchText, setSearchText] = useState('')
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null)
  const [previewResult, setPreviewResult] = useState<{ product: Product; data: ImportCostResult } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)

  const { addToInterestList, removeFromInterestList, isInInterestList } = useAppStore()

  // 计算各一级分类的产品数量
  const l1Counts = useMemo(() => {
    const counts: Record<string, number> = {}
    const filtered = filterProducts(PRODUCTS, difficulty, 'all', 'all', region, '')
    for (const p of filtered) {
      counts[p.hsChapter] = (counts[p.hsChapter] || 0) + 1
    }
    return counts
  }, [difficulty, region])

  const filtered = useMemo(() =>
    filterProducts(PRODUCTS, difficulty, categoryL1, categoryL2, region, searchText),
    [difficulty, categoryL1, categoryL2, region, searchText]
  )

  const zeroCount = useMemo(() => PRODUCTS.filter(p => p.zeroTariff).length, [])

  const hasActiveFilter = difficulty !== 'all' || categoryL1 !== 'all' || categoryL2 !== 'all' || region !== 'all' || searchText.trim().length > 0

  function handleSelectCategoryL1(v: string) {
    setCategoryL1(v)
    setCategoryL2('all')
  }

  function handleSelectCategoryL2(v: string) {
    if (categoryL2 === v) {
      setCategoryL2('all')
    } else {
      setCategoryL2(v)
    }
  }

  function handleSelectRegion(v: string) {
    setRegion(v)
  }

  function handleResetAll() {
    setDifficulty('all')
    setCategoryL1('all')
    setCategoryL2('all')
    setRegion('all')
    setSearchText('')
  }

  async function handleQuickPreview(product: Product) {
    const originCode = product.originCountryCodes[0]
    if (!product.defaultQty || !product.defaultPrice || !originCode) {
      setPreviewError('该品类暂无默认参数，请手动调整')
      track.productQuickPreview(product.name, false)
      return
    }
    setPreviewLoading(true)
    setPreviewError(null)
    setPreviewResult(null)
    try {
      const data = await calculateImportCost({
        product_name: product.name,
        quantity_kg: product.defaultQty,
        fob_per_kg: product.defaultPrice,
        origin: originCode,
      })
      setPreviewResult({ product, data })
      track.productQuickPreview(product.name, true)
    } catch {
      setPreviewError('计算失败，请稍后重试')
      track.productQuickPreview(product.name, false)
    } finally {
      setPreviewLoading(false)
    }
  }

  const selectedReg = findRegionByValue(region)
  const selectedCat = findCategoryL1ByValue(categoryL1)
  const selectedCatL2 = categoryL2 !== 'all' ? findCategoryL2ByValue(categoryL2) : null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="mb-5">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">
          非洲选品清单
        </h1>
        <p className="text-slate-600">
          基于零关税政策 × 非洲优势货源 × 入门门槛，筛选出的可行品类。已收录{' '}
          <strong className="text-primary-600">{zeroCount} 个零关税品类</strong>，覆盖农产品/香料/矿产/皮革/木材等
          <strong>全品类</strong>，支持按品类分类和地区筛选。
        </p>
      </div>

      {/* ── 新手引导卡片 ──────────────────────────────────────── */}
      <div className="bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50 border border-orange-200 rounded-2xl p-5 mb-6">
        <div className="flex items-start gap-3">
          <span className="text-xl mt-0.5">🤔</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-slate-800 mb-2">不知道选什么品类？先回答三个问题</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { q: '💰 启动资金多少？', a: '<¥5万: 咖啡·可可·腰果·芝麻 | ¥5-50万: 皮革·香料·棉花 | >¥50万: 矿产·木材' },
                { q: '🏭 有没有下游渠道？', a: '有食品/工厂 → 原材料B2B | 有零售/私域 → 咖啡·可可走品牌 | 无渠道 → 先调研小批量' },
                { q: '📦 做零售还是批发？', a: '零售/私域 → 咖啡·可可·乳木果油 | B2B供货 → 芝麻·腰果走量 | 供应链服务 → 先找买家再进货' },
              ].map((item, i) => (
                <div key={i} className="text-xs text-slate-600 leading-relaxed bg-white/60 rounded-lg p-2.5">
                  <strong className="text-slate-700">{item.q}</strong>
                  <div className="mt-1">{item.a}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── 顶部筛选栏（桌面端）───────────────────────────────── */}
      <div className="hidden lg:flex items-center gap-3 mb-4 flex-wrap">
        {/* 搜索框 */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="搜索品类、HS编码或国家..."
            className="w-full pl-9 pr-8 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          {searchText && (
            <button
              onClick={() => setSearchText('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* 难度筛选 */}
        <DifficultyBar selected={difficulty} onChange={setDifficulty} />

        {/* 地区选择 */}
        <RegionPanel
          selectedRegion={region}
          onSelectRegion={handleSelectRegion}
          onSelectLevel={() => {}}
        />

        {/* 重置 */}
        {hasActiveFilter && (
          <button
            onClick={handleResetAll}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-slate-500 hover:text-primary-600 border border-slate-200 rounded-lg hover:border-primary-300 transition-colors"
          >
            <X className="w-3 h-3" />
            重置
          </button>
        )}
      </div>

      {/* ── 面包屑（桌面端）───────────────────────────────────── */}
      <div className="hidden lg:flex items-center gap-2 mb-4 min-h-[24px]">
        <Breadcrumbs
          difficulty={difficulty}
          categoryL1={categoryL1}
          categoryL2={categoryL2}
          region={region}
          onReset={handleResetAll}
        />
      </div>

      {/* ── 主内容区：左侧树 + 右侧列表 ────────────────────────── */}
      <div className="flex gap-6 items-start">

        {/* ── 左侧分类树（桌面端）─────────────────────────────── */}
        <div className="hidden lg:block w-60 shrink-0 sticky top-6 max-h-[calc(100vh-12rem)] overflow-y-auto pr-1 scrollbar-thin">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">商品分类</span>
            {categoryL1 !== 'all' && (
              <button
                onClick={() => { setCategoryL1('all'); setCategoryL2('all') }}
                className="ml-auto text-xs text-primary-600 hover:text-primary-700"
              >
                重置
              </button>
            )}
          </div>
          <CategoryTree
            selectedL1={categoryL1}
            selectedL2={categoryL2}
            onSelectL1={handleSelectCategoryL1}
            onSelectL2={handleSelectCategoryL2}
            l1Counts={l1Counts}
          />
        </div>

        {/* ── 右侧产品列表 ──────────────────────────────────────── */}
        <div className="flex-1 min-w-0">

          {/* 移动端筛选按钮 */}
          <div className="lg:hidden flex items-center gap-2 mb-4">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="搜索品类、HS编码或国家..."
                className="w-full pl-9 pr-8 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              {searchText && (
                <button onClick={() => setSearchText('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <button
              onClick={() => setShowMobileFilters(o => !o)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl border transition-all ${
                showMobileFilters
                  ? 'bg-primary-50 border-primary-200 text-primary-700'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              筛选
            </button>
          </div>

          {/* 移动端筛选面板 */}
          {showMobileFilters && (
            <div className="lg:hidden mb-4 bg-white rounded-2xl border border-slate-200 p-4 space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-semibold text-slate-500">难度</span>
                </div>
                <DifficultyBar selected={difficulty} onChange={setDifficulty} />
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-semibold text-slate-500">地区</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    onClick={() => setRegion('all')}
                    className={`inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-full border transition-all ${
                      region === 'all' ? 'bg-blue-50 border-blue-200 text-blue-700 font-medium' : 'bg-white border-slate-200 text-slate-600'
                    }`}
                  >
                    🌍 全部地区
                  </button>
                  {REGION_GROUPS.slice(0, 5).map(r => {
                    const colors = REGION_COLORS[r.color] || REGION_COLORS.slate
                    return (
                      <button
                        key={r.value}
                        onClick={() => setRegion(region === r.value ? 'all' : r.value)}
                        className={`inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-full border transition-all ${
                          region === r.value ? `${colors.bg} ${colors.border} ${colors.text} font-medium` : 'bg-white border-slate-200 text-slate-600'
                        }`}
                      >
                        {r.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Package className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-semibold text-slate-500">商品分类</span>
                </div>
                <CategoryTree
                  selectedL1={categoryL1}
                  selectedL2={categoryL2}
                  onSelectL1={handleSelectCategoryL1}
                  onSelectL2={handleSelectCategoryL2}
                  l1Counts={l1Counts}
                  mobile
                />
              </div>

              {hasActiveFilter && (
                <button
                  onClick={handleResetAll}
                  className="w-full py-2 text-sm text-primary-600 hover:text-primary-700 border border-primary-200 rounded-xl hover:bg-primary-50 transition-colors"
                >
                  重置全部筛选
                </button>
              )}
            </div>
          )}

          {/* 结果统计 + 面包屑（移动端） */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-slate-500">
              <strong className="text-slate-700">{filtered.length}</strong> 个品类
              {selectedCat && (
                <span className="ml-1 text-primary-600">
                  {selectedCat.icon} {selectedCat.label}
                </span>
              )}
              {selectedCatL2 && (
                <span className="ml-1 text-primary-500">
                   → {selectedCatL2.icon} {selectedCatL2.label}
                </span>
              )}
              {selectedReg && (
                <span className="ml-1 text-blue-600">
                   → {selectedReg.label}
                </span>
              )}
            </p>
          </div>

          {/* ── 产品卡片列表 ──────────────────────────────────── */}
          <div className="space-y-3">
            {filtered.length === 0 ? (
              <div className="text-center py-16 text-slate-500">
                <div className="text-4xl mb-3">🔍</div>
                <p className="text-lg font-medium mb-1">未找到匹配的品类</p>
                <p className="text-sm">试试调整筛选条件，或搜索其他关键词</p>
                <button
                  onClick={handleResetAll}
                  className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg text-sm hover:bg-primary-600 transition-colors"
                >
                  清空筛选
                </button>
              </div>
            ) : (
              filtered.map(product => {
                const isExpanded = expandedProduct === product.hsCode
                const isPreviewing = previewResult?.product.hsCode === product.hsCode
                const inList = isInInterestList(product.hsCode)

                return (
                  <div
                    key={product.hsCode + product.name}
                    className={`bg-white rounded-2xl border transition-all ${
                      isExpanded || isPreviewing ? 'border-primary-300 shadow-md' : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {/* Card header */}
                    <button
                      className="w-full text-left p-4"
                      onClick={() => {
                        setExpandedProduct(isExpanded ? null : product.hsCode)
                        setPreviewResult(null)
                        if (!isExpanded) track.productExpand(product.name, product.hsCode)
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            {/* 分类标签 */}
                            <span className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded border border-slate-200 flex items-center gap-0.5">
                              {CATEGORY_ICONS[product.hsChapter] || <Package className="w-3 h-3" />}
                              {product.hsChapterLabel}
                              {product.hsChapterSubLabel && (
                                <span className="text-slate-400">›{product.hsChapterSubLabel}</span>
                              )}
                            </span>
                            <span className="font-semibold text-slate-900">{product.name}</span>
                            <span className="text-xs text-slate-400">{product.nameEn}</span>
                            <span className="font-mono text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                              {product.hsCode}
                            </span>
                            {product.zeroTariff ? (
                              <span className="inline-flex items-center gap-0.5 text-xs text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded-full">
                                <CheckCircle className="w-3 h-3" />零关税
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-0.5 text-xs text-orange-600 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded-full">
                                <AlertCircle className="w-3 h-3" />MFN {product.mfnRate}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-x-4 gap-y-1 text-xs text-slate-500 flex-wrap">
                            <span className={diffColor(product.difficulty)}>{product.difficulty}</span>
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3 text-slate-400" />
                              {product.originCountries.slice(0, 3).join('、')}{product.originCountries.length > 3 ? `...` : ''}
                            </span>
                            {product.regions.map(r => {
                              const rg = findRegionByValue(r)
                              if (!rg) return null
                              const colors = REGION_COLORS[rg.color] || REGION_COLORS.slate
                              return (
                                <span key={r} className={`text-xs px-1.5 py-0.5 rounded-full border ${colors.bg} ${colors.border} ${colors.text}`}>
                                  {rg.label}
                                </span>
                              )
                            })}
                            {product.tier === 'pro' && (
                              <span className="text-orange-500 font-medium">🥇 Pro专享</span>
                            )}
                          </div>
                        </div>
                        <ArrowRight className={`w-4 h-4 text-slate-400 mt-0.5 shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </div>
                    </button>

                    {/* Expanded content */}
                    {(isExpanded || isPreviewing) && (
                      <div className="px-4 pb-4 border-t border-slate-100 pt-3">
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                          <div className="bg-slate-50 rounded-lg p-2.5 text-xs">
                            <div className="text-slate-500 mb-0.5">适合人群</div>
                            <div className="text-slate-800 leading-snug">{product.suitable}</div>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-2.5 text-xs">
                            <div className="text-slate-500 mb-0.5">入门难度</div>
                            <div className={`leading-snug font-medium ${diffColor(product.difficulty)}`}>{product.difficulty}</div>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-2.5 text-xs">
                            <div className="text-slate-500 mb-0.5">零关税节省</div>
                            <div className="text-slate-800 leading-snug">vs MFN省{product.mfnRate}</div>
                          </div>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-2 mb-3">
                          <div className="flex-1 bg-amber-50 border border-amber-100 rounded-lg p-2.5">
                            <div className="flex items-center gap-1.5 mb-1">
                              <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                              <span className="text-xs font-semibold text-amber-800">风险提示</span>
                            </div>
                            <p className="text-xs text-amber-700 leading-relaxed">{product.riskNote}</p>
                          </div>
                          <div className="flex-1 bg-green-50 border border-green-100 rounded-lg p-2.5">
                            <div className="flex items-center gap-1.5 mb-1">
                              <TrendingUp className="w-3.5 h-3.5 text-green-600 shrink-0" />
                              <span className="text-xs font-semibold text-green-800">商业模式</span>
                            </div>
                            <p className="text-xs text-green-700 leading-relaxed">{product.modelTip}</p>
                          </div>
                        </div>

                        {/* Quick preview */}
                        {isPreviewing && previewResult?.data && previewResult.data.breakdown && (
                          <div className="bg-gradient-to-br from-primary-50 to-sky-50 border border-primary-200 rounded-xl p-4 mb-3">
                            <div className="flex items-center gap-2 mb-3">
                              <Calculator className="w-4 h-4 text-primary-600" />
                              <span className="text-sm font-semibold text-primary-800">
                                快速估算（{product.defaultQty}kg / ${product.defaultPrice}/kg）
                              </span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                              {[
                                { label: 'FOB货值', val: fmt(previewResult.data.breakdown.fob_value) },
                                { label: '国际运费', val: fmt(previewResult.data.breakdown.international_freight) },
                                { label: '关税', val: product.zeroTariff ? '¥0（零关税）' : fmt(previewResult.data.breakdown.tariff), green: product.zeroTariff },
                                { label: '到岸总成本', val: fmt(previewResult.data.breakdown.total_cost), bold: true },
                              ].map(item => (
                                <div key={item.label} className={`bg-white/80 rounded-lg p-2.5 text-center ${item.bold ? 'border-2 border-primary-200' : ''}`}>
                                  <div className="text-xs text-slate-500 mb-0.5">{item.label}</div>
                                  <div className={`text-sm font-bold ${item.green ? 'text-green-600' : item.bold ? 'text-primary-700' : 'text-slate-900'}`}>
                                    {item.val}
                                  </div>
                                </div>
                              ))}
                            </div>
                            <div className="mt-1.5 text-xs text-primary-700 text-center">
                              回本需卖 {previewResult.data.breakdown.payback_packages} 包 · 建议零售价 {fmt(previewResult.data.breakdown.suggested_retail_price)}/包
                            </div>
                          </div>
                        )}

                        {previewError && isPreviewing && (
                          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3 text-sm text-red-700">
                            {previewError}
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex flex-wrap gap-1.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              if (inList) {
                                removeFromInterestList(product.hsCode)
                                track.productRemoveInterest(product.name, product.hsCode)
                              } else {
                                addToInterestList({
                                  hsCode: product.hsCode,
                                  name: product.name,
                                  originCountries: product.originCountries,
                                  originCountryCodes: product.originCountryCodes,
                                  mfnRate: product.mfnRate,
                                  zeroTariff: product.zeroTariff,
                                  difficulty: product.difficulty,
                                  addedAt: Date.now(),
                                  defaultQty: product.defaultQty,
                                  defaultPrice: product.defaultPrice,
                                })
                                track.productAddInterest(product.name, product.hsCode)
                              }
                            }}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                              inList
                                ? 'bg-orange-100 border border-orange-300 text-orange-700'
                                : 'bg-white border border-slate-300 text-slate-700 hover:border-primary-400'
                            }`}
                          >
                            {inList ? <><BookmarkCheck className="w-3.5 h-3.5" />已加入</> : <><Bookmark className="w-3.5 h-3.5" />加入清单</>}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleQuickPreview(product)
                              if (!isExpanded) setExpandedProduct(product.hsCode)
                            }}
                            disabled={previewLoading && previewResult?.product.hsCode === product.hsCode}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white text-sm font-medium rounded-lg transition-colors"
                          >
                            {previewLoading && previewResult?.product.hsCode === product.hsCode ? (
                              <><div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />计算中...</>
                            ) : (
                              <><Zap className="w-3.5 h-3.5" />快速估算</>
                            )}
                          </button>
                          <Link
                            to={`/cost-calculator?product=${encodeURIComponent(product.name)}&qty=${product.defaultQty || ''}&price=${product.defaultPrice || ''}&origin=${product.originCountryCodes[0] || ''}`}
                            onClick={() => track.productNav('/cost-calculator', { product: product.name, origin: product.originCountryCodes[0] || '' })}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition-colors"
                          >
                            <Calculator className="w-3.5 h-3.5" />
                            完整成本精算 →
                          </Link>
                          <Link
                            to={`/calculator?hs=${product.hsCode}&origin=${product.originCountryCodes[0] || ''}`}
                            onClick={() => track.productNav('/calculator', { hs: product.hsCode, origin: product.originCountryCodes[0] || '' })}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white text-sm font-medium rounded-lg transition-colors"
                          >
                            关税计算 →
                          </Link>
                          <Link
                            to={`/origin-check?hs=${product.hsCode}&origin=${product.originCountryCodes[0] || ''}`}
                            onClick={() => track.productNav('/origin-check', { hs: product.hsCode, origin: product.originCountryCodes[0] || '' })}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 text-sm font-medium rounded-lg transition-colors"
                          >
                            原产地自测 →
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>

          {/* Bottom CTA */}
          <div className="mt-12 text-center">
            <p className="text-sm text-slate-500 mb-4">选好品类后，用工具验证成本和原产地资格</p>
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
      </div>
    </div>
  )
}
