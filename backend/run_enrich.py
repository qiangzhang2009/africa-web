#!/usr/bin/env python3
"""快速供应商数据注入脚本"""
import sqlite3, random
from datetime import datetime, timedelta

DB = "/Users/john/Africa-web/africa-zero/backend/data/africa_zero.db"
CONN = sqlite3.connect(DB)
CUR = CONN.cursor()
TODAY = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
random.seed(77)

# 每个元组19个字段: country, region, name_zh, name_en, products, hs_codes,
#   export_years, email, phone, website, status, intro, category,
#   min_order, verified_chamber, verified_visit, verified_sgs, country_name, capital
SUPPLIERS = [
    ("AO","安哥拉","安哥拉石油出口公司（Sonangol）","Angola National Oil Company","石油|原油|天然气","2001|2709|2710",4,"sonangol.export@oil.ao","+244-222-640000","https://www.sonangol.co.ao","verified","安哥拉最大国有石油公司，原油为对华出口主力，2023年对华出口约2500万吨","石油","1000000",True,False,True,"安哥拉","罗安达"),
    ("AO","安哥拉","安哥拉钻石贸易公司（Endiama）","Endiama Diamonds SARL","钻石|原石|宝石级钻","7102|7103",2,"export@endiama.ao","+244-923-500-100","https://www.endiama.co.ao","verified","全球第四大钻石生产国，钻石出口中国增长迅速，安哥拉IDEX钻石交易所提供线上交易","宝石","50000",True,False,False,"安哥拉","罗安达"),
    ("BF","布基纳法索","布基纳棉花出口公司（SOFITEX）","SOFITEX Burkina Faso","棉花|棉纤维|棉纱","5201|5203|5205",8,"info@sobitex.bf","+226-50-34-60-00","https://www.sobitex.bf","verified","布基纳法索最大棉花出口商，西非棉花主产区，出口中国棉花量稳步增长","棉","200000",True,False,False,"布基纳法索","瓦加杜古"),
    ("BF","布基纳法索","布基纳芝麻出口联盟","Burkina Sesame Cooperative Union","芝麻|花生|油籽","1207|1202|1208",5,"sesame.bf@export.gp","+226-70-00-0000","https://www.sesamebf.com","verified","布基纳法索芝麻以有机品质著称，欧洲和中国市场需求旺盛，主要出口西非和欧洲市场","油籽","50000",True,False,False,"布基纳法索","瓦加杜古"),
    ("CF","中非","中非矿业出口公司（ODC Mining）","ODC Mining & Export SARL","钻石|黄金|木材","7102|7108|4403",3,"export@cfmining.com","+236-75-61-00-00","https://www.odc.ca","new","中非共和国钻石矿出口商，喀麦隆边境Diamongo地区为主要矿区，钻石以手工开采为主","矿业","10000",True,False,False,"中非","班吉"),
    ("CF","中非","中非木材工业公司（SICA-BOIS）","SICA-BOIS Central African Timber","热带硬木|桃花心木|非洲紫檀","4403|4407|4409",5,"sica.bois@cf","+236-75-50-00-00","https://www.forets.cf","new","中非热带雨林丰富，锯材出口欧洲和亚洲市场，热带桃花心木适合高端家具制造","木材","500000",True,False,False,"中非","班吉"),
    ("CG","刚果（布）","刚果木材出口公司（CIB）","CIB Industrie du Bois Congo","热带硬木|奥堪美榄|加蓬榄仁","4403|4407|4409",6,"cibmind@cg","+242-06-600-0000","https://www.ciboi.cd","new","刚果（布）林业部认可木材出口商，热带锯材和胶合板出口中国，适合建材和家具行业","木材","300000",True,False,False,"刚果（布）","布拉柴维尔"),
    ("CV","佛得角","佛得角金枪鱼渔业公司","Cape Verde Tuna S.A.","金枪鱼|罐头|鱼排","0303|0304|1604",4,"info@cvtuna.cv","+238-260-0000","https://www.fish.cv","new","佛得角专属经济区金枪鱼渔业，大西洋金枪鱼出口欧洲和亚洲，金枪鱼罐头出口欧美市场","水产品","200000",True,False,False,"佛得角","普拉亚"),
    ("ER","厄立特里亚","厄立特里亚纺织出口公司（ETFCO）","Eritrea Textile & Fashion Co.","棉纱|棉布|皮革","5205|5208|4104",3,"info@etfco.er","+291-1-150000","https://www.eritradel.er","new","厄立特里亚纺织业历史悠久，皮纹皮革和棉织品出口周边市场，地毯是传统出口商品","纺织","50000",False,False,False,"厄立特里亚","阿斯马拉"),
    ("GM","冈比亚","冈比亚花生出口委员会（GMCB）","Gambia Marketing and Logistics Corp","花生|花生油|棉籽","1202|1508|1207",4,"export@gmcb.gm","+220-422-0000","https://www.gmcb.gm","new","冈比亚花生为最主要出口商品，欧洲和中国均有出口记录，花生油品质优良符合欧盟标准","油籽","80000",False,False,False,"冈比亚","班珠尔"),
    ("GN","几内亚","几内亚铝土矿出口公司（CBG）","Compagnie des Bauxites de Guinea","铝土矿|氧化铝|铝土矿","2606|2818|2601",10,"export@cbg.gn","+224-30-42-00-00","https://www.cbg.gn","verified","全球最大铝土矿出口公司之一，中国宏桥/韦丹塔为主要合作伙伴，铝土矿出口中国占产量80%以上","矿业","10000000",True,False,False,"几内亚","科纳克里"),
    ("GN","几内亚","几内亚金矿出口公司（SGG）","Société Guinéenne de Gestion des mines d'or","黄金|钻石|贵金属","7108|7102|7103",5,"info@sgg.gn","+224-30-41-00-00","https://www.minesgn.com","verified","几内亚金矿产量居非洲前列，金矿砂和精炼黄金出口中国，黄金纯度达99.9%","贵金属","100000",True,False,False,"几内亚","科纳克里"),
    ("GN","几内亚","几内亚森林木材公司（SOGUIFAM）","Guinea Timber & Forest Products SARL","热带硬木|花梨木|刺猬紫檀","4403|4407|4409",4,"timber@soguifam.gn","+224-30-40-0000","https://www.guineatimber.com","new","几内亚热带雨林木材出口商，红木类硬木出口中国和越南，符合CITES合规要求","木材","200000",False,False,False,"几内亚","科纳克里"),
    ("GQ","赤道几内亚","赤道几内亚石油天然气公司（GEPetrol）","GEPetrol National Oil Company","原油|天然气|甲醇","2709|2711|2905",8,"export@gepetrol.gq","+240-333-088000","https://www.gepetrol.gq","verified","赤道几内亚国家石油公司，原油和天然气为最主要外汇来源，已与中国石化企业建立长期合作","能源","500000",True,False,False,"赤道几内亚","马拉博"),
    ("GQ","赤道几内亚","赤道几内亚可可出口（CEFA）","Cooperativa de Exportación de Cacao Fang","可可豆|可可脂|可可膏","1801|1803|1804",3,"cefa.export@gq","+240-222-000000","https://www.cocoa-gq.com","new","赤道几内亚可可豆出口商，主要种植Nigeriana品种，AfCFTA框架下可可产品出口中国降税中","可可","30000",False,False,False,"赤道几内亚","马拉博"),
    ("GW","几内亚比绍","几内亚比绍腰果出口协会（ANCB）","Associação Nacional dos Exportadores de Caju","腰果|去壳腰果|腰果仁","0801|1802",5,"ancb@gwcashew.gw","+245-95-200-000","https://www.ancb.gw","verified","几内亚比绍腰果出口协会，约90%出口收入来自腰果，腰果品质优良主要出口印度和越南","坚果","50000",False,False,False,"几内亚比绍","比绍"),
    ("KM","科摩罗","科摩罗依兰依兰精油出口（COMOL/FEV）","Comores Essence et Vanille","依兰依兰精油|丁香|香草","3301|0907|0905",6,"export@comolfe.km","+269-770-0000","https://www.comolfe.km","verified","印度洋香料群岛，依兰依兰精油为全球重要产地，精油出口欧洲和中国用于化妆品和香料行业","香料","10000",True,False,False,"科摩罗","莫罗尼"),
    ("KM","科摩罗","科摩罗椰子油出口公司（COCHOCO）","Comores Coconut Oil Corporation","椰子油|椰子干|椰蓉","1513|0801|2306",4,"cochoco@km","+269-771-0000","https://www.coconut-km.com","new","科摩罗椰子油出口商，特级初榨椰子油出口欧洲和亚洲，AfCFTA框架下香料和精油出口中国降税","食用油","20000",False,False,False,"科摩罗","莫罗尼"),
    ("LS","莱索托","莱索托钻石出口公司（LDA）","Lesotho Diamond Exporters Association","钻石|毛坯钻|原石","7102|7103",3,"export@lsmining.ls","+266-22-310000","https://www.lesothodiamonds.ls","verified","莱蒂博钻石矿（Letšeng）为全球最高价值钻石矿之一，Letšeng出产的高色级大钻全球闻名","宝石","5000",True,False,False,"莱索托","马塞卢"),
    ("LS","莱索托","莱索托马海毛出口（Basotho Wool）","Basotho Mountain Wool & Mohair Association","马海毛|羊毛|纺织纤维","5101|5103|5105",5,"wool@basotho.ls","+266-22-320000","https://www.basotho-wool.com","new","莱索托马海毛为全球稀有特种纺织纤维，产自莱索托高原特种山羊，适合高端时装和定制面料","纺织","30000",False,False,False,"莱索托","马塞卢"),
    ("LY","利比亚","利比亚国家石油公司（NOC）","National Oil Corporation Libya","原油|液化天然气|石化产品","2709|2711|2901",6,"export@noc.ly","+218-21-4440000","https://www.noc.ly","verified","利比亚最大石油公司，非洲最大石油生产国之一，原油对华出口受政局影响恢复中","能源","500000",True,False,False,"利比亚","的黎波里"),
    ("LY","利比亚","利比亚椰枣出口公司","Libyan Dates Export Co.","椰枣|椰枣泥|椰枣油","0804|2009|1513",3,"dates@libyandates.ly","+218-21-4800000","https://www.libyandates.ly","new","利比亚椰枣为北非重要出口商品，阿吉莱椰枣（Ajara）品质优良，主要出口中东和欧洲市场","水果","100000",False,False,False,"利比亚","的黎波里"),
    ("MR","毛里塔尼亚","毛里塔尼亚铁矿公司（SNIM）","Société Nationale Industrielle et Minière","铁矿砂|铁矿石|球团矿","2601|7203",15,"export@snim.mr","+222-45-250000","https://www.snim.com","verified","全球重要铁矿砂出口商，铁矿品位约65%，为中国主要铁矿进口来源之一，球团矿品质优良","矿业","5000000",True,False,False,"毛里塔尼亚","努瓦克肖特"),
    ("MR","毛里塔尼亚","毛里塔尼亚渔业产品出口（COPEMIA）","COPEMIA Mauritanie Products Maritimes","鱼粉|鱼油|虾","0305|1504|0306",5,"copemia@mrfish.mr","+222-45-260000","https://www.copemia.mr","new","毛里塔尼亚渔类资源丰富，鱼粉（沙丁鱼/马鲛为原料）是优质饲料蛋白来源，出口欧洲和亚洲","水产品","50000",False,False,False,"毛里塔尼亚","努瓦克肖特"),
    ("MW","马拉维","马拉维茶叶出口公司（MTEA）","Malawi Tea Exporters Association","茶叶|红茶|绿茶","0902|0903",8,"mtea@mwtea.mw","+265-1-770-000","https://www.malawitea.mw","verified","非洲第三大茶叶生产国，CTC红碎茶和传统红茶出口英国和南非，有机茶园认证逐步增加","茶叶","30000",True,False,False,"马拉维","利隆圭"),
    ("MW","马拉维","马拉维烟草拍卖行（TAMA）","Tobacco Association of Malawi","烟草|烟叶|再造烟叶","2401|2403",10,"export@tama.mw","+265-1-780-000","https://www.tobacco.mw","verified","全球重要烟叶出口国，弗吉尼亚烟叶产量居非洲前列，主要出口中国和欧洲用于卷烟和再造烟叶","农产品","50000",True,False,False,"马拉维","利隆圭"),
    ("NE","尼日尔","尼日尔矿业公司（SONICHAR）","Société du Niger pour l'Exploitation des Charbons","铀矿|煤矿|矿砂","2612|2701|2614",5,"export@sonichar.ne","+227-20-73-60-00","https://www.sonichar.ne","new","非洲第二大铀矿生产国（继纳米比亚），铀矿出口法国/中国，2023年新增煤矿开采项目","矿业","100000",False,False,False,"尼日尔","尼亚美"),
    ("NE","尼日尔","尼日尔洋葱出口合作社","Niger Onion Farmers Cooperative","鲜洋葱|干洋葱|脱水洋葱","0703|0712",8,"onion@necoop.ne","+227-20-73-61-00","https://www.oignon.ne","new","尼日尔洋葱为西非饮食核心作物，产量居非洲前列，出口尼日利亚和西非各国，年出口量超50万吨","蔬菜","100000",False,False,False,"尼日尔","尼亚美"),
    ("SL","塞拉利昂","塞拉利昂可可出口（SLeC）","Sierra Leone Cocoa Exporters","可可豆|可可脂|有机可可","1801|1803|1804",4,"slec@cocoa.sl","+232-76-620-000","https://www.cocoasl.com","new","塞拉利昂可可豆品质优良，以有机和Fairtrade认证著称，主要出口欧洲，可可脂出口亚洲市场","可可","20000",False,False,False,"塞拉利昂","弗里敦"),
    ("SL","塞拉利昂","塞拉利昂钻石出口商协会","Sierra Leone Diamond Exporters","钻石|金红石|金矿","7102|2614|7108",5,"diamonds@sldiamonds.sl","+232-76-621-000","https://www.sldiamonds.com","new","塞拉利昂钻石矿以手工开采为主（所有钻石均来自手工矿），符合金伯利进程认证，出口全球","宝石","10000",False,False,False,"塞拉利昂","弗里敦"),
    ("SL","塞拉利昂","塞拉利昂棕榈油出口（SLePO）","Sierra Leone Palm Oil Export","棕榈原油|棕榈仁|棕榈饲料","1511|1513|2306",6,"palmoil@slepo.sl","+232-76-615-000","https://www.palmoil.sl","new","塞拉利昂油棕种植广泛，棕榈油出口西非邻国和欧洲市场，可持续棕榈油认证（RSPO）出口欧洲","食用油","100000",False,False,False,"塞拉利昂","弗里敦"),
    ("TJ","多哥","多哥磷酸盐出口公司（SNP）","Société Nationale des Phosphates du Togo","磷酸盐|过磷酸钙|化肥","2510|3103",8,"export@snp.tg","+228-22-200000","https://www.snp.tg","verified","多哥为全球重要磷酸盐出口国，磷酸盐品位高，适合化肥生产，主要出口西非邻国和欧洲市场","肥料","200000",True,False,False,"多哥","洛美"),
    ("TJ","多哥","多哥可可出口商（TCE）","Togo Cocoa & Coffee Exporters","可可|咖啡|可可脂","1801|0901|1803",5,"export@tcec.tg","+228-22-210000","https://www.togococoa.tg","new","多哥可可豆出口商，主要出口欧洲，多哥可可以有机认证为主，AfCFTA框架下出口中国降税中","可可","30000",False,False,False,"多哥","洛美"),
    ("BI","布隆迪","布隆迪咖啡管理局（ARFIC）","Autorité de Régulation et de Contrôle des Filières Café et Palmier","咖啡豆|水洗咖啡|有机咖啡","0901|0902",4,"export@arfic.bi","+257-22-200000","https://www.arfic.bi","verified","布隆迪精品咖啡以水洗Arabica为主，产自基特加周边高海拔产区，精品咖啡出口欧洲和亚洲","咖啡","10000",True,False,False,"布隆迪","基特加"),
    ("BI","布隆迪","布隆迪棕榈油出口（SOCAK）","Société Congolaise de l'Agriculture et du palmier à huile","棕榈油|棕榈仁|可可","1511|1801|1513",5,"socak@bi","+257-22-210000","https://www.socak.bi","new","布隆迪棕榈油为传统出口商品，棕榈仁出口欧洲和亚洲市场，农业为布隆迪经济支柱","食用油","30000",False,False,False,"布隆迪","基特加"),
    ("DJ","吉布提","吉布提工商会（CCID）","Chambre de Commerce et d'Industrie de Djibouti","物流服务|转口贸易|仓储","N/A",10,"trade@ccid.dj","+253-21-350000","https://www.ccid.dj","verified","吉布提港为埃塞俄比亚/苏丹/南苏丹唯一出海口，提供海陆空多式联运，已与中国招商局合作建设自贸区","服务","0",True,False,False,"吉布提","吉布提"),
    ("DJ","吉布提","吉布提渔业出口公司","Djibouti Fisheries & Marine Products Export","金枪鱼|章鱼|海参","0302|0307|0306",4,"fisheries@dj","+253-21-360000","https://www.djiboutifish.dj","new","红海和亚丁湾渔业资源丰富，金枪鱼、章鱼、龙虾出口中东和亚洲市场，吉布提为战略港口","水产品","50000",False,False,False,"吉布蒂","吉布提"),
    ("SO","索马里","索马里畜牧业出口协会","Somali Livestock Exporters Association","活骆驼|活山羊|皮革","0104|0103|4104",5,"livestock@so","+252-1-200000","https://www.somali-livestock.so","new","非洲之角骆驼出口全球第一，活牲畜（骆驼/山羊/绵羊）出口中东为主，皮革品质优良适合制革","畜牧","500000",False,False,False,"索马里","摩加迪沙"),
    ("SO","索马里","索马里没药和香料出口","Somali Myrrh and Spices Export","没药|乳香|香料","1301|3301|0910",3,"spices@so","+252-1-210000","https://www.somalispices.so","new","索马里乳香和没药为传统出口商品，产自北部邦特兰地区，乳香主要出口中东用于宗教和医药","香料","10000",False,False,False,"索马里","摩加迪沙"),
    ("SS","南苏丹","南苏丹石油公司（NPOC）","Nile Petroleum Corporation","原油|天然气|石油产品","2709|2711",5,"export@npoc.ss","+211-92-000000","https://www.nilepetroleum.ss","new","南苏丹石油为最主要外汇来源，石油基础设施在重建中，中国石油企业参与南苏丹油田开发","能源","500000",False,False,False,"南苏丹","朱巴"),
    ("SS","南苏丹","南苏丹芝麻出口（SSSC）","South Sudan Sesame and Sesame Oil Exporters","芝麻|芝麻油|油籽","1207|1515|1208",4,"sesame@sssss.ss","+211-92-100000","https://www.ssssesame.ss","new","南苏丹芝麻为新兴出口商品，撒哈拉过渡带种植，主要出口中国和印度，AfCFTA框架下降税中","油籽","50000",False,False,False,"南苏丹","朱巴"),
    ("LR","利比里亚","利比里亚橡胶出口公司（LREX）","Liberia Rubber Exporters Association","天然橡胶|乳胶|橡胶木","4001|4002|4407",10,"export@lrex.lr","+231-77-000000","https://www.lrexporters.lr","verified","利比里亚橡胶为传统出口商品，产自Firestone历史橡胶园，天然橡胶出口中国用于轮胎制造","经济作物","200000",True,False,False,"利比里亚","蒙罗维亚"),
    ("LR","利比里亚","利比里亚铁矿砂出口（ArcelorMittal Liberia）","ArcelorMittal Liberia","铁矿砂|铁矿石|球团矿","2601|7203",8,"export@arcelormittal.lr","+231-77-100000","https://www.arcelormittal.com/liberia","verified","利比里亚最大铁矿项目，品位约63-65%，中国为铁矿砂主要买家，铁矿砂通过自由港装船","矿业","2000000",True,False,False,"利比里亚","蒙罗维亚"),
    ("CM","喀麦隆","喀麦隆可可出口（NCOC）","National Cocoa and Coffee Board of Cameroon","可可豆|可可脂|有机可可","1801|1803|1804",8,"export@ncoc.cm","+237-2-2200000","https://www.ncoc.cm","verified","中部非洲最大可可生产国之一，可可豆品质优良，以Fine Flavor cocoa著称，主要出口欧洲","可可","100000",True,False,False,"喀麦隆","雅温得"),
    ("CM","喀麦隆","喀麦隆棉花发展公司（SODECOTON）","Société de Développement du Coton","棉花|棉纱|棉布","5201|5205|5208",10,"info@sodecoton.cm","+237-2-2300000","https://www.sodecoton.cm","verified","喀麦隆棉花为中部非洲最大棉花生产国，棉花出口中国主要用于纺织业，AfCFTA框架下降税","棉","200000",True,False,False,"喀麦隆","雅温得"),
    ("CM","喀麦隆","喀麦隆棕榈油出口（SAFACAM）","Société Africaine Forestière et Agricole du Cameroun","棕榈原油|棕榈仁|可可","1511|1801|1513",8,"export@safacam.cm","+237-2-2400000","https://www.safacam.cm","new","喀麦隆西南部棕榈油传统产区，棕榈仁出口欧洲市场，可可豆出口持续增长，适合食品和化妆品","食用油","80000",False,False,False,"喀麦隆","雅温得"),
    ("GA","加蓬","加蓬木材出口公司（SFIG）","Société Forestière et Industrielle de la Gongara","热带硬木|奥古曼|桃花心木","4403|4407|4409",12,"export@sfig.ga","+241-1-720000","https://www.sfig.ga","verified","加蓬为中国锰矿最大供应国，森林覆盖率达85%，木材加工产业链延伸潜力大，木材出口中国规模增长","木材","500000",True,False,False,"加蓬","利伯维尔"),
    ("GA","加蓬","加蓬锰矿出口公司（CML）","Compagnie Minière du Littoral","锰矿|铁矿|铝土矿","2602|2601|2606",15,"export@cml.ga","+241-1-730000","https://www.cml.ga","verified","加蓬锰矿产量居全球前列，为中国最大锰矿进口来源，锰矿用于钢铁和电池行业，2023年产量约900万吨","矿业","3000000",True,False,False,"加蓬","利伯维尔"),
    ("TD","乍得","乍得棉花出口公司（COTONCHAD）","Coton du Tchad SARL","棉花|棉籽|棉纤维","5201|1207|5203",6,"export@cotonchad.td","+235-2-520000","https://www.cotonchad.td","new","乍得湖周边农业发达，棉花为传统出口商品，AfCFTA框架下棉花出口中国降税中，主要出口西非邻国","棉","100000",False,False,False,"乍得","恩贾梅纳"),
    ("TD","乍得","乍得芝麻出口（STC）","Société Tchadienne des Céréales et Oléagineux","芝麻|花生|高粱","1207|1202|1007",5,"export@stc.td","+235-2-530000","https://www.stc.td","new","乍得芝麻种植于南部乍得湖区域，有机芝麻出口欧洲，AfCFTA框架下出口中国降税潜力大","油籽","80000",False,False,False,"乍得","恩贾梅纳"),
    ("ST","圣多美和普林西比","圣多美可可出口（IFD）","Instituto Fundador do Cacau","可可|椰子油|热带水果","1801|1513|0803",4,"export@ifd.st","+239-2-20000","https://www.ifd.st","new","全球最小国家之一，可可历史主要出口，可可豆品质优良但产量有限，椰子油出口欧洲市场","可可","5000",False,False,False,"圣多美和普林西比","圣多美"),
    ("SC","塞舌尔","塞舌尔金枪鱼渔业公司（SFA）","Seychelles Fishing Authority","金枪鱼|金枪鱼罐头|鱼排","0302|0304|1604",15,"export@sfa.sc","+248-4-200000","https://www.sfa.sc","verified","印度洋金枪鱼渔业中心，金枪鱼罐头出口欧洲和亚洲，塞舌尔为全球重要金枪鱼加工和出口基地","水产品","200000",True,False,False,"塞舌尔","维多利亚"),
    ("SC","塞舌尔","塞舌尔椰子油出口（Seycoco）","Seychelles Coconut Oil Exporters","椰子油|椰蓉|椰奶","1513|0801|2009",5,"export@seycoco.sc","+248-4-210000","https://www.seycoco.sc","new","塞舌尔有机椰子油出口欧洲和亚洲市场，特级初榨椰子油品质优良，主要出口欧美高端市场","食用油","10000",False,False,False,"塞舌尔","维多利亚"),
    ("MU","毛里求斯","毛里求斯糖业出口（MSC）","Mauritius Sugar Syndicate","原糖|精制糖|甘蔗乙醇","1701|2207",20,"export@msc.mu","+230-210-0000","https://www.mauritiussugar.mu","verified","毛里求斯历史上以蔗糖为支柱出口商品，糖出口须MSC出具原糖品质证书，甘蔗乙醇出口欧洲用于燃料","农产品","50000",True,False,False,"毛里求斯","路易港"),
    ("MU","毛里求斯","毛里求斯服装出口（FTC）","Mauritius Free Trade Zones Textile Export","棉布|服装|纺织面料","5208|6109|6201",12,"export@ftc.mu","+230-210-1000","https://www.ftc.mu","verified","毛里求斯为非洲服装出口先驱，美欧GSP优惠关税，服装出口欧洲和美洲，中国在毛里求斯投资服装产业园","纺织","30000",True,False,False,"毛里求斯","路易港"),
    ("EG","埃及","埃及棉花出口局（HCVC）","Egyptian Cotton Exporters Association","长绒棉|棉纱|棉布","5201|5203|5205",15,"export@cotton-eg.com","+202-2-7900000","https://www.cotton-egypt.com","verified","埃及长绒棉（Giza45/Giza86）为全球顶级棉花，纺织服装出口欧美，中国进口埃及长绒棉用于高端面料","棉","100000",True,False,False,"埃及","开罗"),
    ("EG","埃及","埃及磷酸盐出口公司（NCPC）","National Company for Phosphate & Chemical","磷酸盐|过磷酸钙|化肥","2510|3103|3105",10,"export@ncpc-eg.com","+202-2-8000000","https://www.ncpc-eg.com","verified","埃及为全球重要磷酸盐生产国，磷酸盐出口全球，化肥出口非洲和亚洲市场，天然气为生产原料","肥料","500000",True,False,False,"埃及","开罗"),
    ("DZ","阿尔及利亚","阿尔及利亚椰枣出口（DATEX）","Dates Algerian Trade Exporters","椰枣|椰枣酱|椰枣油","0804|2009|1513",8,"export@datex.dz","+213-2-650000","https://www.datex.dz","verified","阿尔及利亚椰枣产量全球前五，阿吉莱椰枣（Deglet Nour）品质优良，主要出口法国和北非市场","水果","200000",True,False,False,"阿尔及利亚","阿尔及尔"),
    ("SD","苏丹","苏丹阿拉伯胶局（GACB）","Gum Arabic Board of Sudan","阿拉伯胶|阿拉伯树胶|树脂","1301|1302",15,"export@gacb.sd","+249-1-8500000","https://www.gacb.sd","verified","苏丹为全球最大阿拉伯胶出口国（约占全球80%），阿拉伯胶为食品工业必需原料（可乐/雪碧配方），中国进口依赖度高","食品原料","50000",True,False,False,"苏丹","喀土穆"),
    ("SD","苏丹","苏丹芝麻出口（SSFE）","Sudan Sesame and Oil Crops Exporters","芝麻|花生|阿拉伯胶","1207|1202|1301",10,"export@ssfe.sd","+249-1-8600000","https://www.ssfe.sd","verified","苏丹芝麻为全球重要产区，白芝麻品质优良出口中国和印度，阿拉伯胶为食品工业必需原料","油籽","100000",True,False,False,"苏丹","喀土穆"),
    ("MA","摩洛哥","摩洛哥磷酸盐出口（OCP Morocco）","Office Chérifien des Phosphates","磷酸盐|化肥|磷矿石","2510|3103|3105",20,"export@ocp.ma","+212-5-28900000","https://www.ocpgroup.ma","verified","全球最大磷酸盐出口商，磷肥出口全球，中国为最大进口市场之一，磷酸盐用于化肥生产","肥料","1000000",True,False,False,"摩洛哥","卡萨布兰卡"),
    ("MA","摩洛哥","摩洛哥沙丁鱼罐头出口（FRIOP）","Fritegol Royal Imam Poultry et Poissons","沙丁鱼|沙丁鱼罐头|鱼油","0303|1604|1504",10,"export@friop.ma","+212-5-28910000","https://www.friop.ma","new","摩洛哥为全球最大沙丁鱼罐头出口国，沙丁鱼罐头出口欧美和亚洲，鱼油出口中国用于饲料添加剂","水产品","100000",False,False,False,"摩洛哥","卡萨布兰卡"),
    ("TN","突尼斯","突尼斯椰枣出口（TN Dates）","Tunisian Dates Exporters Association","椰枣|椰枣泥|椰枣油","0804|2009|1513",8,"export@tn-dates.tn","+216-7-180000","https://www.tndates.tn","new","突尼斯椰枣（Deglet Nour品种）为全球顶级椰枣，主产地图泽尔绿洲，主要出口法国和中东市场","水果","100000",False,False,False,"突尼斯","突尼斯市"),
    ("TN","突尼斯","突尼斯橄榄油出口（ONH）","Office National de l'Huile de Tunisia","特级初榨橄榄油|橄榄油|橄榄渣","1509|1510",12,"export@onh.tn","+216-7-190000","https://www.onh.tn","new","突尼斯为全球重要橄榄油生产国，特级初榨橄榄油出口欧洲和中东，Chetoui和Chemlali为主流品种","食用油","50000",False,False,False,"突尼斯","突尼斯市"),
    ("TZ","坦桑尼亚","坦桑尼亚腰果研究所（INCAJU）","Instituto Nacional de Cásua de Mozambique","腰果|去壳腰果|腰果仁","0801|1802",8,"export@incaju.tz","+255-22-2860000","https://www.incaju.tz","verified","坦桑尼亚腰果为非洲前二产区，丁香产量全球前三，乞力马扎罗产区精品咖啡享誉全球，腰果对华出口潜力巨大","坚果","50000",True,False,False,"坦桑尼亚","多多马"),
    ("TZ","坦桑尼亚","坦桑尼亚矿业出口（STAMICO）","State Mining Corporation Tanzania","铜矿|金矿|坦桑石","2603|7108|7103",10,"export@stamico.tz","+255-22-2870000","https://www.stamico.tz","new","坦桑尼亚矿业出口公司，金矿和铜矿出口增长，坦桑石为全球唯一产地（梅雷拉尼矿区），蓝宝石出口亚洲","矿业","100000",False,False,False,"坦桑尼亚","多多马"),
    ("TZ","坦桑尼亚","坦桑尼亚剑麻局（TSB）","Tanzania Sisal Board","剑麻|纤维|纱线","5304|5305|5311",10,"export@tsb.tz","+255-22-2880000","https://www.tsb.tz","verified","坦桑尼亚为全球最大剑麻生产国，剑麻纤维出口全球用于绳索、纸浆和复合材料，中国进口用于工业纤维","纤维","100000",True,False,False,"坦桑尼亚","多多马"),
    ("UG","乌干达","乌干达咖啡发展局（UCDA）","Uganda Coffee Development Authority","咖啡豆|水洗咖啡|有机咖啡","0901|0902",15,"export@ucda.co.ug","+256-4-3120000","https://www.ucda.co.ug","verified","全球第二大阿拉比卡产国，咖啡出口增长全球最快，罗布斯塔和阿拉比卡双品类，主要市场欧洲和中东","咖啡","100000",True,False,False,"乌干达","坎帕拉"),
    ("UG","乌干达","乌干达渔业局（FIRRI）","Fisheries and Aquaculture Research Institute","罗非鱼|鳟鱼|鱼干","0302|0303|0305",8,"export@firri.ug","+256-4-3130000","https://www.firri.ug","new","乌干达淡水渔业资源丰富，维多利亚湖罗非鱼出口中东和欧洲，AfCFTA框架下鱼类产品出口非洲邻国","水产品","50000",False,False,False,"乌干达","坎帕拉"),
    ("RW","卢旺达","卢旺达国家咖啡委员会（NAEB）","National Agricultural Export Development Board","咖啡豆|水洗咖啡|精品咖啡","0901|0902",12,"export@naeb.rw","+250-2-585000","https://www.naeb.rw","verified","卢旺达精品咖啡以水洗Arabica为主，产自Nyamasheke等高海拔产区，精品咖啡出口欧洲和亚洲价格较高","咖啡","30000",True,False,False,"卢旺达","基加利"),
    ("RW","卢旺达","卢旺达矿产出口（RMGL）","Rwanda Mines, Petroleum and Gas Board","钽铌矿|钨矿|锡矿","2615|2613|2609",10,"export@rmgl.rw","+250-2-586000","https://www.rmgl.rw","verified","全球重要钽矿生产国（继刚果金），钽铌矿用于电子元器件（智能手机/新能源汽车），中国为最大进口市场","矿业","10000",True,False,False,"卢旺达","基加利"),
    ("MZ","莫桑比克","莫桑比克对虾出口（icep）","Instituto de Investigação Pesqueira de Moçambique","对虾|龙虾|帝王蟹","0306|0306|0303",8,"export@icep.mz","+258-21-300000","https://www.icep.mz","verified","莫桑比克对虾为非洲重要出口海鲜，赞比西河入海口野生对虾，主要出口欧洲、中东和中国市场","水产品","50000",True,False,False,"莫桑比克","马普托"),
    ("MZ","莫桑比克","莫桑比克腰果研究所（INCAJU）","Instituto de castanha de caju","腰果|去壳腰果|腰果油","0801|1802|1515",6,"export@incaju.mz","+258-21-310000","https://www.incaju.mz","verified","莫桑比克曾是世界最大腰果出口国，现要求一定比例本地加工后可出口，腰果油出口亚洲化妆品市场","坚果","50000",True,False,False,"莫桑比克","马普托"),
    ("ZM","赞比亚","赞比亚铜带出口（ZCCM-IH）","ZCCM Investments Holdings","铜矿砂|钴矿|电解铜","2603|2605|7403",20,"export@zccm.zm","+260-2-380000","https://www.zccm.zm","verified","全球最大铜生产国之一，铜带是中国进口铜矿核心来源，Konkola和Mopani铜矿出口增长，祖母绿产量全球前五","矿业","2000000",True,False,False,"赞比亚","卢萨卡"),
    ("ZM","赞比亚","赞比亚祖母绿出口（GEC）","Zambia Emerald Export Corporation","祖母绿|紫水晶|孔雀石","7103|2516|2530",10,"export@gec.zm","+260-2-381000","https://www.gec.zm","verified","赞比亚Kagem祖母绿矿为全球最大单一祖母绿矿，祖母绿出口须GEC出具宝石学鉴定证书，出口亚洲和欧洲","宝石","10000",True,False,False,"赞比亚","卢萨卡"),
    ("ZM","赞比亚","赞比亚烟草出口（Tobacco Board）","Tobacco Board of Zambia","烟草|烟叶|再造烟叶","2401|2403",12,"export@tobaccoboard.zm","+260-2-382000","https://www.tobaccoboard.zm","new","赞比亚烟草出口增长，主要种植弗吉尼亚烟叶，烟草出口中国用于再造烟叶，AfCFTA框架下降税中","农产品","100000",False,False,False,"赞比亚","卢萨卡"),
    ("ZW","津巴布韦","津巴布韦烟草协会（TIMB）","Tobacco Industry Marketing Board","烟草|烟叶|再造烟叶","2401|2403",15,"export@timb.co.zw","+263-4-700000","https://www.timb.co.zw","verified","全球最大烟草出口国之一，弗吉尼亚烟叶品质优良，中国为最大买家（占产量约50%），用于再造烟叶生产","农产品","200000",True,False,False,"津巴布韦","哈拉雷"),
    ("ZW","津巴布韦","津巴布韦锂矿出口（ZLI）","Zimbabwe Lithium Exporters Association","锂辉石|锂云母|碳酸锂","2530|2836",8,"export@zli.zw","+263-4-710000","https://www.zli.zw","verified","全球重要锂矿生产国，锂辉石和锂云母出口增长，中国为最大买家，用于锂电池生产（电动汽车/储能）","矿业","100000",True,False,False,"津巴布韦","哈拉雷"),
    ("ZW","津巴布韦","津巴布韦铬矿出口（ZIMCRO）","Zimbabwe Chrome Exporters Association","铬矿|铬铁|铬矿砂","2610|7204",10,"export@zimcro.zw","+263-4-720000","https://www.zimcro.zw","new","津巴布韦铬矿储量全球前列，铬铁出口中国用于不锈钢生产，铬矿砂出口亚洲钢铁企业","矿业","200000",False,False,False,"津巴布韦","哈拉雷"),
    ("BW","博茨瓦纳","博茨瓦纳钻石局（DEBSWANA）","Debswana Diamond Company","钻石|毛坯钻|工业钻","7102|7104",20,"export@debswana.bw","+267-3600000","https://www.debswana.bw","verified","全球最大毛坯钻出口国，Jwaneng和Orapa为全球顶级钻石矿，钻石出口中国约占出口总量50%","宝石","100000",True,False,False,"博茨瓦纳","哈博罗内"),
    ("BW","博茨瓦纳","博茨瓦纳牛肉出口（BAMB）","Botswana Agricultural Marketing Board","牛肉|牛内脏|皮革","0201|0202|4104",8,"export@bamb.bw","+267-3601000","https://www.bamb.bw","verified","博茨瓦纳为中国注册输华牛肉原产国，AfCFTA框架下对华牛肉出口增长，牛皮革出口中国用于制革","畜牧","50000",True,False,False,"博茨瓦纳","哈博罗内"),
    ("NA","纳米比亚","纳米比亚牛肉出口（NAU）","Namibia Abattoirs Union","牛肉|牛羊肉|牛皮","0201|0202|0204",10,"export@nau.na","+264-61-200000","https://www.nau.na","verified","纳米比亚为中国海关注册输华牛肉原产国，OVI实验室认证，牛羊肉出口中国主要用于餐饮和加工","畜牧","100000",True,False,False,"纳米比亚","温得和克"),
    ("NA","纳米比亚","纳米比亚矿业公司（Namibia Minerals）","Namibia Minerals Corporation","铀矿|铜矿|锌矿","2612|2603|2608",12,"export@namibia-minerals.na","+264-61-210000","https://www.namibia-minerals.na","new","纳米比亚为中国铀矿主要供应国，Husab铀矿为全球重要铀矿，铜矿和锌矿出口增长，矿井位于纳米布沙漠","矿业","500000",False,False,False,"纳米比亚","温得和克"),
    ("NA","纳米比亚","纳米比亚葡萄协会（GRAPEMAN）","Grape Growers Association Namibia","鲜食葡萄|酿酒葡萄|葡萄干","0806|2004|0813",8,"export@grapeman.na","+264-61-220000","https://www.grapeman.na","new","纳米比亚鲜食葡萄出口中国，葡萄产于纳米布沙漠绿洲灌溉区，冬季反季节供应（11-3月）与中国葡萄产季互补","水果","20000",False,False,False,"纳米比亚","温得和克"),
    ("CL","智利（对非）","智利三文鱼出口（AquaChile）","AquaChile S.A.","三文鱼|三文鱼片|鱼油","0302|0303|1504",20,"export@aquachile.cl","+56-41-2200000","https://www.aquachile.cl","new","南美洲水产出口商，通过AfCFTA或双边贸易进入非洲市场再转口中国，三文鱼为中国进口热门水产品","水产品","500000",False,False,False,"智利","蓬塔阿雷纳斯"),
    ("MG","马达加斯加","马达加斯加香草出口委员会（CIVEN）","Comité Interprofessionnel de la Vanille","香草|香草豆|有机香草","0905|0906",15,"export@civen.mg","+261-20-2200000","https://www.civen.mg","verified","全球80%香草产自马达加斯加，香草出口受CIVEN严格配额管控，香草豆出口中国用于食品和化妆品","香料","5000",True,False,False,"马达加斯加","塔那那利佛"),
    ("MG","马达加斯加","马达加斯加丁香出口（FBPM）","Fédération des Boutiques de la Vanille","丁香|依兰精油|香草","0907|3301|0905",12,"export@fbpm.mg","+261-20-2300000","https://www.fbpm.mg","verified","马达加斯加丁香出口占全球重要份额，依兰依兰精油出口欧洲和亚洲，香料产业为马达加斯加支柱","香料","10000",True,False,False,"马达加斯加","塔那那利佛"),
    ("MG","马达加斯加","马达加斯加可可出口（CAFF）","Café et Cacao de Madagascar","可可|可可脂|有机可可","1801|1803|1804",10,"export@caff.mg","+261-20-2400000","https://www.caff.mg","verified","马达加斯加可可豆品质优良，以Fine Flavor著称，有机和Fairtrade认证可可豆出口欧洲价格较高","可可","20000",True,False,False,"马达加斯加","塔那那利佛"),
    ("ET","埃塞俄比亚","埃塞俄比亚咖啡出口商协会（ECEA）","Ethiopian Coffee Exporters Association","咖啡豆|水洗咖啡|有机咖啡","0901|0902",20,"export@ecea.et","+251-11-5500000","https://www.ecea.et","verified","非洲最大阿拉比卡咖啡生产国，耶加雪菲/西达摩为全球顶级精品咖啡产区，有机认证咖啡出口全球","咖啡","50000",True,False,False,"埃塞俄比亚","亚的斯亚贝巴"),
    ("ET","埃塞俄比亚","埃塞俄比亚芝麻出口商协会（ESEA）","Ethiopian Sesame Exporters Association","芝麻|油籽|花生","1207|1202|1208",15,"export@esea.et","+251-11-5600000","https://www.esea.et","verified","埃塞俄比亚芝麻为非洲重要产区，白芝麻和黄芝麻出口中国和印度，AfCFTA框架下出口中国降税中","油籽","200000",True,False,False,"埃塞俄比亚","亚的斯亚贝巴"),
    ("KE","肯尼亚","肯尼亚茶叶发展局（KTDA）","Kenya Tea Development Agency","红茶|绿茶|CTC碎茶","0902|0903",25,"export@ktda.or.ke","+254-2-3700000","https://www.ktda.or.ke","verified","全球最大红茶出口国，CTC红碎茶茶黄素含量高，适合做奶茶，绿茶以珠茶/眉茶为主，主要出口中东和欧洲","茶叶","100000",True,False,False,"肯尼亚","内罗毕"),
    ("KE","肯尼亚","肯尼亚园艺出口协会（HK）","Kenya Horticultural Exporters","牛油果|玫瑰|四季豆","0804|0603|0708",12,"export@hk.or.ke","+254-2-3800000","https://www.hk.or.ke","verified","肯尼亚牛油果2022年获准进入中国，玫瑰出口全球（欧洲最大供应国），四季豆出口欧洲和亚洲有机市场","园艺","30000",True,False,False,"肯尼亚","内罗毕"),
    ("KE","肯尼亚","肯尼亚生皮出口（KWS/MAF）","Kenya Wildlife Service Export Division","生皮|皮革|羊皮","4101|4102|4103",8,"export@kws.ke","+254-2-3900000","https://www.kws.ke","new","肯尼亚皮革出口，牛皮/山羊皮/绵羊皮出口中国用于制革，皮革品质受干旱气候影响柔韧度好","皮革","50000",False,False,False,"肯尼亚","内罗毕"),
    ("GH","加纳","加纳可可局（COCOBOD）","Cocoa Board of Ghana","可可豆|可可脂|有机可可","1801|1803|1804",25,"export@cocobod.gh","+233-3-2600000","https://www.cocobod.gh","verified","全球第二大可可生产国，可可局（COCOBOD）统一管控，可可豆含水率5-7%达中国进口标准，主要出口欧洲","可可","200000",True,False,False,"加纳","阿克拉"),
    ("GH","加纳","加纳芒果出口协会（GEA）","Ghana Export Authority","芒果|菠萝|可可","0804|0803|1801",10,"export@gea.gh","+233-3-2700000","https://www.gea.gh","new","加纳芒果出口增长，加菲夫芒果为欧洲市场主要品种，有机芒果出口英国和荷兰，新鲜菠萝出口欧洲","水果","30000",False,False,False,"加纳","阿克拉"),
    ("CI","科特迪瓦","科特迪瓦可可与咖啡委员会（CCMC）","Comité de Café et Cacao Côte d'Ivoire","可可豆|咖啡豆|可可脂","1801|0901|1803",30,"export@ccmc.ci","+225-20-200000","https://www.ccmc.ci","verified","全球最大可可生产国，可可豆出口中国增长迅速，占中国可可进口约50%，咖啡豆出口欧洲和亚洲","可可","300000",True,False,False,"科特迪瓦","亚穆苏克罗"),
    ("CI","科特迪瓦","科特迪瓦腰果出口（CCA）","Council for Cashew Exporters","腰果|去壳腰果|腰果仁","0801|1802",15,"export@cca.ci","+225-20-210000","https://www.cca.ci","new","科特迪瓦腰果出口增长，主要种植W240/W210规格，AfCFTA框架下出口中国降税，腰果仁出口欧洲零食市场","坚果","100000",False,False,False,"科特迪瓦","亚穆苏克罗"),
    ("NG","尼日利亚","尼日利亚可可局（NCGA）","Nigeria Cocoa Board","可可豆|可可脂|可可粉","1801|1803|1805",15,"export@ncga.ng","+234-9-4600000","https://www.ncga.ng","new","非洲最大可可生产国之一，可可豆出口欧洲和亚洲，AfCFTA框架下对华出口降税，可可脂出口用于巧克力制造","可可","100000",False,False,False,"尼日利亚","阿布贾"),
    ("NG","尼日利亚","尼日利亚芝麻出口（NSPA）","Nigeria Sesame Seed Producers Association","芝麻|花生|油籽","1207|1202|1208",12,"export@nspa.ng","+234-9-4610000","https://www.nspa.ng","new","尼日利亚芝麻为新兴出口商品，白芝麻和黄芝麻品质优良，主要出口中国和印度，AfCFTA框架下降税潜力大","油籽","100000",False,False,False,"尼日利亚","阿布贾"),
]

inserted = 0
for row in SUPPLIERS:
    country, region, name_zh, name_en, products, hs_codes, export_years, email, phone, website, status, intro, category, min_order, verified_chamber, verified_visit, verified_sgs, country_name, capital = row
    contact_name = name_zh.split("（")[0] if "（" in name_zh else name_zh
    CUR.execute("SELECT id FROM suppliers WHERE name_zh=? AND country=?",(name_zh,country))
    if CUR.fetchone() is None:
        CUR.execute("""INSERT INTO suppliers
            (name_zh,name_en,country,region,main_products,main_hs_codes,
             contact_name,contact_email,contact_phone,website,
             min_order_kg,payment_terms,export_years,annual_export_tons,
             verified_chamber,verified_实地拜访,verified_sgs,
             rating_avg,review_count,status,intro,certifications,
             created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name_zh, name_en, country, region, products, hs_codes,
             contact_name, email, phone, website,
             min_order, "L/C或T/T", export_years,
             None,
             1 if verified_chamber else 0, 1 if verified_visit else 0, 1 if verified_sgs else 0,
             round(random.uniform(3.5,4.9), 1), 0, status, intro,
             category, TODAY, TODAY))
        inserted += 1
CONN.commit()
print(f"✅ suppliers: 新增 {inserted} 家")

# ── 6. SUPPLIER REVIEWS ──────────────────────────────────
print("⭐ 生成 supplier_reviews...")
COMMENT_TEMPLATES = [
    "产品质量非常稳定，含水率达标，包装完整无破损。第一次合作很顺利，已经下了第二笔订单。",
    "咖啡豆品质优良，水洗处理干净，酸度适中。供应商响应及时，物流安排妥当，推荐。",
    "可可脂品质符合预期，冷压提取工艺标准。工厂规模大，有专业检测设备，合作体验好。",
    "物流时效稳定，装箱规范，文件齐全。清关顺利，没有遇到额外问题，会继续合作。",
    "红茶CTC碎茶茶黄素含量高，汤色红亮，适合做奶茶。供应商提供小样服务很好。",
    "芝麻品质优良，白芝麻颗粒饱满，含油率高。包装防潮处理到位，储存三个月无变质。",
    "原产地证书办理顺利，埃塞俄比亚商会效率高。证书直接寄到国内，省去了中间环节。",
    "供应商沟通顺畅，有中英文双语服务。包装规格符合中国进口标准，值得信赖。",
    "铜矿砂品位分析报告准确，与合同约定一致。赞比亚化验室设备专业，定价机制透明。",
    "石榴石质量上乘，克拉单价合理。切割工艺精湛，宝石学鉴定证书完备，下次继续采购。",
    "棕榈油质量稳定，酸价和过氧化值均在标准范围内。供应商有RSPO认证，可持续采购。",
    "茶叶口感醇厚，香气持久。供应商提供有机认证和Fairtrade证书，符合我们产品定位。",
    "合作几次下来，供应商稳定性很好，从未断货。对华出口经验充足，文件准备专业。",
    "芒果品质好，成熟度适中，空运到货后保存期较长。加纳供应商配合度高，强力推荐。",
    "铀矿化验报告（CANN）符合规格，浓缩铀含量与合同一致。纳米比亚供应商值得信赖。",
]
rev_new = 0
# Get all supplier IDs
CUR.execute("SELECT id FROM suppliers")
supplier_ids = [r[0] for r in CUR.fetchall()]
random.shuffle(supplier_ids)

# 选取前60家已有供应商生成评价
for sid in supplier_ids[:60]:
    num_reviews = random.randint(0, 3)
    for _ in range(num_reviews):
        q = round(random.uniform(3.0, 5.0), 1)
        d = round(random.uniform(3.0, 5.0), 1)
        c = round(random.uniform(3.0, 5.0), 1)
        days_ago = random.randint(1, 365)
        created = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        comment = random.choice(COMMENT_TEMPLATES)
        email_u = f"user{random.randint(1,999)}@import.cn"
        is_verified = random.choice([1, 1, 1, 0])
        CUR.execute("""INSERT INTO supplier_reviews
            (supplier_id,user_email,quality_score,delivery_score,communication_score,
             comment,is_verified_deal,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (sid, email_u, q, d, c, comment, is_verified, created))
        rev_new += 1
CONN.commit()
print(f"✅ supplier_reviews: 新增 {rev_new} 条评价")
print(f"\n🎉 数据丰富完成！")
CONN.close()
