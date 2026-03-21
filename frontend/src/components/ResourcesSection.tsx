import { ExternalLink, Banknote, ScrollText, BarChart3, Ship, Building2 } from 'lucide-react'
import { track } from '../utils/track'

const resourceGroups = [
  {
    icon: <Banknote className="w-5 h-5" />,
    label: '汇率与货币',
    color: 'text-emerald-600 bg-emerald-50',
    links: [
      {
        name: 'XE 实时汇率',
        desc: 'CNY/USD 及主要非洲国家货币',
        url: 'https://www.xe.com/zh-cn/',
      },
      {
        name: 'Wise 汇率监控',
        desc: '国际汇款实际汇率对比',
        url: 'https://wise.com/cn/',
      },
    ],
  },
  {
    icon: <ScrollText className="w-5 h-5" />,
    label: '海关与关税',
    color: 'text-blue-600 bg-blue-50',
    links: [
      {
        name: '中国海关HS编码查询',
        desc: '中国进出口税则税率查询（国家统计局官方数据）',
        url: 'https://data.stats.gov.cn/easyquery.htm?cn=E0110',
      },
      {
        name: 'AfCFTA 原产地规则',
        desc: '非洲大陆自由贸易区规则原文',
        url: 'https://au-afcfta.org/',
      },
      {
        name: '贸促会原产地证书',
        desc: '中国国际贸易促进委员会办理指南',
        url: 'https://www.ccpit.org/',
      },
    ],
  },
  {
    icon: <BarChart3 className="w-5 h-5" />,
    label: '贸易数据',
    color: 'text-violet-600 bg-violet-50',
    links: [
      {
        name: 'UN Comtrade 数据库',
        desc: '全球双边贸易流量数据',
        url: 'https://comtradeplus.un.org/',
      },
      {
        name: 'ITC Trade Map',
        desc: '非洲各国进出口统计 & 商机发现',
        url: 'https://www.trademap.org/',
      },
    ],
  },
  {
    icon: <Ship className="w-5 h-5" />,
    label: '物流与运价',
    color: 'text-amber-600 bg-amber-50',
    links: [
      {
        name: 'Freightos 运价查询',
        desc: '中国→非洲主要港口海运费对比',
        url: 'https://www.freightos.com/freight-rate/',
      },
      {
        name: 'MSC 非洲航线',
        desc: '地中海航运非洲线运价与船期',
        url: 'https://www.msc.com/',
      },
    ],
  },
  {
    icon: <Building2 className="w-5 h-5" />,
    label: '联系我们',
    color: 'text-orange-600 bg-orange-50',
    links: [
      {
        name: '咨询合作',
        desc: '定制官网、AI工具、全球扩张战略方案',
        url: 'mailto:zxq@zxqconsulting.com',
      },
    ],
  },
]

export default function ResourcesSection() {
  return (
    <section className="py-20 bg-white border-t border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-heading font-bold text-slate-900 mb-4">
            配套实用工具 & 官网链接
          </h2>
          <p className="text-slate-600 max-w-xl mx-auto">
            算完关税，下一步做什么？这里汇总了非洲进出口从业者每天都在用的官方工具和数据源。
          </p>
        </div>

        {/* Groups */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {resourceGroups.map((group) => (
            <div key={group.label} className="space-y-4">
              {/* Group header */}
              <div className="flex items-center gap-2">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${group.color}`}>
                  {group.icon}
                </div>
                <span className="font-semibold text-slate-900 text-sm">{group.label}</span>
              </div>

              {/* Links */}
              <div className="space-y-2">
                {group.links.map((link) => (
                  <a
                    key={link.name}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => track.click(`resource_link_${link.name}`, 'external_resource', { url: link.url, group: group.label })}
                    className="group flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors"
                  >
                    <div className="shrink-0 mt-0.5 text-slate-400 group-hover:text-primary-500 transition-colors">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-800 group-hover:text-primary-600 transition-colors">
                        {link.name}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                        {link.desc}
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
