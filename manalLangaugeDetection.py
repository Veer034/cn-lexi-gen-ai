import re
import unicodedata
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import logging
import os

logger = logging.getLogger(__name__)

class ManualLanguageDetector:
    def __init__(self):
        self.setup_language_support()
        self.setup_scripts()
        self.setup_common_patterns()
        self.setup_method_weights()
        
    def setup_language_support(self):
        """Setup supported languages with their code, English name, and native name"""
        self.supported_languages = {
            'en': {'name': 'English', 'native': 'English'},
            'en-ca': {'name': 'English (Canada)', 'native': 'English (Canada)'},
            'en-au': {'name': 'English (Australia)', 'native': 'English (Australia)'},
            'en-gb': {'name': 'English (UK)', 'native': 'English (UK)'},
            'fr': {'name': 'French', 'native': 'Français'},
            'es': {'name': 'Spanish', 'native': 'Español'},
            'de': {'name': 'German', 'native': 'Deutsch'},
            'it': {'name': 'Italian', 'native': 'Italiano'},
            'pt': {'name': 'Portuguese', 'native': 'Português'},
            'pt-br': {'name': 'Portuguese (Brazil)', 'native': 'Português (Brasil)'},
            'nl': {'name': 'Dutch', 'native': 'Nederlands'},
            'sv': {'name': 'Swedish', 'native': 'Svenska'},
            'no': {'name': 'Norwegian', 'native': 'Norsk'},
            'da': {'name': 'Danish', 'native': 'Dansk'},
            'fi': {'name': 'Finnish', 'native': 'Suomi'},
            'pl': {'name': 'Polish', 'native': 'Polski'},
            'ru': {'name': 'Russian', 'native': 'Русский'},
            'uk': {'name': 'Ukrainian', 'native': 'Українська'},
            'cs': {'name': 'Czech', 'native': 'Čeština'},
            'sk': {'name': 'Slovak', 'native': 'Slovenčina'},
            'sl': {'name': 'Slovenian', 'native': 'Slovenščina'},
            'hr': {'name': 'Croatian', 'native': 'Hrvatski'},
            'bs': {'name': 'Bosnian', 'native': 'Bosanski'},
            'sr': {'name': 'Serbian (Cyrillic)', 'native': 'Српски'},
            'sr-latn': {'name': 'Serbian (Latin)', 'native': 'Srpski'},
            'ro': {'name': 'Romanian', 'native': 'Română'},
            'bg': {'name': 'Bulgarian', 'native': 'Български'},
            'mk': {'name': 'Macedonian', 'native': 'Македонски'},
            'el': {'name': 'Greek', 'native': 'Ελληνικά'},
            'tr': {'name': 'Turkish', 'native': 'Türkçe'},
            'hu': {'name': 'Hungarian', 'native': 'Magyar'},
            'lt': {'name': 'Lithuanian', 'native': 'Lietuvių'},
            'ca': {'name': 'Catalan', 'native': 'Català'},
            'gl': {'name': 'Galician', 'native': 'Galego'},
            'af': {'name': 'Afrikaans', 'native': 'Afrikaans'},
            'sq': {'name': 'Albanian', 'native': 'Shqip'},
            'az': {'name': 'Azerbaijani', 'native': 'Azərbaycan'},
            'kk': {'name': 'Kazakh', 'native': 'Қазақша'},
            'he': {'name': 'Hebrew', 'native': 'עברית'},
            'ar': {'name': 'Arabic', 'native': 'العربية'},
            'fa': {'name': 'Persian', 'native': 'فارسی'},
            'ur': {'name': 'Urdu', 'native': 'اردو'},
            'hi': {'name': 'Hindi', 'native': 'हिन्दी'},
            'bn': {'name': 'Bengali', 'native': 'বাংলা'},
            'pa': {'name': 'Punjabi', 'native': 'ਪੰਜਾਬੀ'},
            'gu': {'name': 'Gujarati', 'native': 'ગુજરાતી'},
            'mr': {'name': 'Marathi', 'native': 'मराठी'},
            'ne': {'name': 'Nepali', 'native': 'नेपाली'},
            'si': {'name': 'Sinhala', 'native': 'සිංහල'},
            'ta': {'name': 'Tamil', 'native': 'தமிழ்'},
            'te': {'name': 'Telugu', 'native': 'తెలుగు'},
            'ml': {'name': 'Malayalam', 'native': 'മലയാളം'},
            'kn': {'name': 'Kannada', 'native': 'ಕನ್ನಡ'},
            'th': {'name': 'Thai', 'native': 'ไทย'},
            'zh': {'name': 'Chinese (Simplified)', 'native': '简体中文'},
            'zh-tw': {'name': 'Chinese (Traditional)', 'native': '繁體中文'},
            'ja': {'name': 'Japanese', 'native': '日本語'},
            'ko': {'name': 'Korean', 'native': '한국어'},
            'vi': {'name': 'Vietnamese', 'native': 'Tiếng Việt'},
            'id': {'name': 'Indonesian', 'native': 'Bahasa Indonesia'},
            'ms': {'name': 'Malay', 'native': 'Bahasa Melayu'},
            'sw': {'name': 'Swahili', 'native': 'Kiswahili'},
            'ha': {'name': 'Hausa', 'native': 'Hausa'},
            'ig': {'name': 'Igbo', 'native': 'Igbo'},
            'ak': {'name': 'Akan', 'native': 'Akan'},
            'tw': {'name': 'Twi', 'native': 'Twi'},
            'sd': {'name': 'Sindhi', 'native': 'سنڌي'},
            'ps': {'name': 'Pashto', 'native': 'پښتو'}
        }
        
        # Regional language distribution for fallback
        self.region_languages = {
            'north_america': ['en', 'es', 'fr'],
            'south_america': ['es', 'pt-br', 'pt'],
            'europe_west': ['en', 'fr', 'de', 'es', 'it', 'nl', 'pt'],
            'europe_north': ['en', 'sv', 'no', 'da', 'fi'],
            'europe_east': ['ru', 'pl', 'uk', 'cs', 'sk', 'hu', 'ro'],
            'europe_south': ['it', 'es', 'pt', 'el', 'tr'],
            'europe_balkans': ['hr', 'bs', 'sr', 'sr-latn', 'bg', 'mk', 'sq'],
            'middle_east': ['ar', 'he', 'fa', 'tr'],
            'south_asia': ['hi', 'ur', 'bn', 'pa', 'gu', 'mr', 'ne', 'si', 'ta', 'te', 'ml', 'kn'],
            'east_asia': ['zh', 'zh-tw', 'ja', 'ko'],
            'southeast_asia': ['th', 'vi', 'id', 'ms'],
            'africa': ['en', 'fr', 'ar', 'sw', 'ha', 'ig', 'ak', 'tw']
        }
        
        # IP range to region mapping (simplified)
        self.ip_region_map = {
            'north_america': ['US', 'CA', 'MX'],
            'south_america': ['BR', 'AR', 'CL', 'CO', 'PE', 'VE'],
            'europe_west': ['GB', 'FR', 'DE', 'ES', 'IT', 'NL', 'PT', 'BE', 'CH', 'AT', 'IE'],
            'europe_north': ['SE', 'NO', 'DK', 'FI', 'IS'],
            'europe_east': ['RU', 'PL', 'UA', 'CZ', 'SK', 'HU', 'RO', 'BY', 'MD'],
            'europe_south': ['IT', 'ES', 'PT', 'GR', 'TR', 'CY', 'MT'],
            'europe_balkans': ['HR', 'BA', 'RS', 'BG', 'MK', 'AL', 'XK', 'ME', 'SI'],
            'middle_east': ['SA', 'AE', 'IL', 'TR', 'IR', 'IQ', 'JO', 'LB', 'SY', 'YE', 'OM', 'QA', 'KW', 'BH'],
            'south_asia': ['IN', 'PK', 'BD', 'NP', 'LK', 'BT', 'MV', 'AF'],
            'east_asia': ['CN', 'JP', 'KR', 'TW', 'HK', 'MO', 'MN'],
            'southeast_asia': ['TH', 'VN', 'ID', 'MY', 'PH', 'SG', 'MM', 'KH', 'LA', 'BN', 'TL'],
            'africa': ['ZA', 'NG', 'EG', 'KE', 'GH', 'TZ', 'DZ', 'MA', 'TN', 'ET', 'CD', 'UG', 'SN']
        }
        
    def setup_scripts(self):
        """Setup script-to-language mappings for quick script detection"""
        self.script_language_map = {
            'latin': ['en', 'fr', 'es', 'de', 'it', 'pt', 'nl', 'sv', 'no', 'da', 'fi', 'pl', 'cs', 'sk', 
                     'sl', 'hr', 'bs', 'sr-latn', 'ro', 'hu', 'lt', 'ca', 'gl', 'af', 'sq', 'vi', 'id', 'ms', 'sw', 'ha', 'ig', 'ak', 'tw'],
            'cyrillic': ['ru', 'uk', 'sr', 'bg', 'mk', 'kk'],
            'arabic': ['ar', 'fa', 'ur', 'sd', 'ps'],
            'devanagari': ['hi', 'mr', 'ne'],
            'bengali': ['bn'],
            'gurmukhi': ['pa'],
            'gujarati': ['gu'],
            'tamil': ['ta'],
            'telugu': ['te'],
            'kannada': ['kn'],
            'malayalam': ['ml'],
            'sinhala': ['si'],
            'thai': ['th'],
            'han': ['zh', 'zh-tw', 'ja'],
            'hiragana': ['ja'],
            'katakana': ['ja'],
            'hangul': ['ko'],
            'hebrew': ['he'],
            'greek': ['el']
        }
        
        # Script detection ranges
        self.script_ranges = {
            'latin': [(0x0041, 0x007A)],  # Basic Latin
            'cyrillic': [(0x0400, 0x04FF)],
            'arabic': [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)],
            'devanagari': [(0x0900, 0x097F)],
            'bengali': [(0x0980, 0x09FF)],
            'gurmukhi': [(0x0A00, 0x0A7F)],
            'gujarati': [(0x0A80, 0x0AFF)],
            'tamil': [(0x0B80, 0x0BFF)],
            'telugu': [(0x0C00, 0x0C7F)],
            'kannada': [(0x0C80, 0x0CFF)],
            'malayalam': [(0x0D00, 0x0D7F)],
            'sinhala': [(0x0D80, 0x0DFF)],
            'thai': [(0x0E00, 0x0E7F)],
            'han': [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)],  # CJK Unified Ideographs
            'hiragana': [(0x3040, 0x309F)],
            'katakana': [(0x30A0, 0x30FF)],
            'hangul': [(0xAC00, 0xD7AF)],
            'hebrew': [(0x0590, 0x05FF)],
            'greek': [(0x0370, 0x03FF)]
        }
        
    def setup_common_patterns(self):
        """Setup common text patterns/words for each language"""
        self.common_words = {
            'en': [r'\b(the|and|is|in|to|it|you|that|he|was|for|on|are|with|as|his|they|at|be|this|have|from|or|had|by|but|what|not|all|were|we|when|your|can|said|there|use|an|each|which|she|do|how|their|if|will|up|other|about|out|many|then|them|these|so|some|would|make|like|into|time|has|look|more|go|see|number|no|way|could|people|my|first|water|been|call|who|oil|now|find|long|down|day|did|get|come|made|may|part)\b'],
            'fr': [r'\b(le|la|les|un|une|des|et|est|en|à|de|dans|du|pour|avec|ce|qui|que|il|elle|ils|elles|nous|vous|je|tu|mon|ton|son|ma|ta|sa|mes|tes|ses|notre|votre|leur|au|aux|sur|par|mais|où|ou|donc|car|ni)\b'],
            'es': [r'\b(el|la|los|las|un|una|unos|unas|y|es|en|a|de|para|con|por|que|yo|tú|él|ella|nosotros|vosotros|ellos|mi|tu|su|nuestro|vuestro|este|esta|estos|estas|ese|esa|esos|esas|aquel|aquella|aquellos|aquellas)\b'],
            'de': [r'\b(der|die|das|ein|eine|und|ist|in|zu|von|für|mit|dem|den|auf|dass|des|ich|du|er|sie|es|wir|ihr|Sie|mein|dein|sein|unser|euer|dieser|diese|dieses|jener|jene|jenes)\b'],
            'it': [r'\b(il|lo|la|i|gli|le|un|uno|una|dei|degli|delle|e|è|in|a|di|da|per|con|su|che|io|tu|lui|lei|noi|voi|loro|mio|tuo|suo|nostro|vostro|questo|questa|questi|queste|quello|quella|quelli|quelle)\b'],
            'pt': [r'\b(o|a|os|as|um|uma|uns|umas|e|é|em|de|para|com|por|que|eu|tu|ele|ela|nós|vós|eles|elas|meu|teu|seu|nosso|vosso|este|esta|estes|estas|esse|essa|esses|essas|aquele|aquela|aqueles|aquelas)\b'],
            'nl': [r'\b(de|het|een|is|en|van|in|voor|met|op|dat|die|deze|dit|te|zijn|hebben|ik|jij|hij|zij|wij|jullie|mijn|jouw|zijn|haar|ons|jullie|hun)\b'],
            'ru': [r'\b(и|в|на|с|по|для|не|я|ты|он|она|мы|вы|они|мой|твой|его|её|наш|ваш|их|этот|эта|это|эти|тот|та|то|те)\b'],
            'ar': [r'\b(ال|و|من|في|على|إلى|عن|مع|هذا|هذه|هؤلاء|ذلك|تلك|أولئك|أنا|أنت|هو|هي|نحن|أنتم|هم|لي|لك|له|لها|لنا|لكم|لهم)\b'],
            'hi': [r'\b(का|के|की|एक|में|है|और|को|से|पर|यह|वह|हैं|मैं|तुम|वे|हम|मेरा|तेरा|उसका|हमारा|यहाँ|वहाँ)\b'],
            'ja': [r'\b(の|に|は|を|た|が|で|て|と|も|な|か|ない|です|ます|こと|もの|よう|れる|られる|なる|ある|いる|する|できる|おる|くれる|やる|くださる|いく|くる|しまう|なさる|いい)\b'],
            'zh': [r'\b(的|一|是|在|不|了|有|和|人|这|中|大|为|上|个|国|我|以|要|他|时|来|用|们|生|到|作|地|于|出|就|分|对|成|会|可|主|发|年|动|同|工|也|能|下|过|子|说|产|种|面|而|方|后|多|定|行|学|法|所|民|得|经|十|三|之|进|着|等|部|度|家|电|力|里|如|水|化|高|自|二|理|起|小|物|现|实|加|量|都|两|体|制|机|当|使|点|从|业|本|去|把|性|好|应|开|它|合|还|因|由|其|些|然|前|外|天|政|四|日|那|社|义|事|平|形|相|全|表|间|样|与|关|各|重|新|线|内|数|正|心|反|你|明|看|原|又|么|利|比|或|但|质|气|第|向|道|命|此|变|条|只|没|结|解|问|意|建|月|公|无|系|军|很|情|者|最|立|代|想|已|通|并|提|直|题|党|程|展|五|果|料|象|员|革|位|入|常|文|总|次|品|式|活|设|及|管|特|件|长|求|老|头|基|资|边|流|路|级|少|图|山|统|接|知|较|将|组|见|计|别|她|手|角|期|根|论|运|农|指|几|九|区|强|放|决|西|被|干|做|必|战|先|回|则|任|取|据|处|队|南|给|色|光|门|即|保|治|北|造|百|规|热|领|七|海|口|东|导|器|压|志|世|金|增|争|济|阶|油|思|术|极|交|受|联|什|认|六|共|权|收|证|改|清|美|再|采|转|更|单|风|切|打|白|教|速|花|带|安|场|身|车|例|真|务|具|万|每|目|至|达|走|积|示|议|声|报|斗|完|类|八|离|华|名|确|才|科|张|信|马|节|话|米|整|空|元|况|今|集|温|传|土|许|步|群|广|石|记|需|段|研|界|拉|林|律|叫|且|究|观|越|织|装|影|算|低|持|音|众|书|布|复|容|儿|须|际|商|非|验|连|断|深|难|近|矿|千|周|委|素|技|备|半|办|青|省|列|习|响|约|支|般|史|感|劳|便|团|往|酸|历|市|克|何|除|消|构|府|称|太|准|精|值|号|率|族|维|划|选|标|写|存|候|毛|亲|快|效|斯|院|查|江|型|眼|王|按|格|养|易|置|派|层|片|始|却|专|状|育|厂|京|识|适|属|圆|包|火|住|调|满|县|局|照|参|红|细|引|听|该|铁|价|严|首|底|液|官|德|随|病|苏|失|尔|死|讲|配|女|黄|推|显|谈|罪|神|艺|呢|席|含|企|望|密|批|营|项|防|举|球|英|氧|势|告|李|台|落|木|帮|轮|破|亚|师|围|注|远|字|材|排|供|河|态|封|另|施|减|树|溶|怎|止|案|言|士|均|武|固|叶|鱼|波|视|仅|费|紧|爱|左|章|早|朝|害|续|轻|服|试|食|充|兵|源|判|护|司|足|某|练|差|致|板|田|降|黑|犯|负|击|范|继|兴|似|余|坚|曲|输|修|故|城|夫|够|送|笔|船|占|右|财|吃|富|春|职|觉|汉|画|功|巴|跟|虽|杂|飞|检|吸|助|升|阳|互|初|创|抗|考|投|坏|策|古|径|换|未|跑|留|钢|曾|端|责|站|简|述|钱|副|尽|帝|射|草|冲|承|独|令|限|阿|宣|环|双|请|超|微|让|控|州|良|轴|找|否|纪|益|依|优|顶|础|载|倒|房|突|坐|粉|敌|略|客|袁|冷|胜|绝|析|块|剂|测|丝|协|诉|念|陈|仍|罗|盐|友|洋|错|苦|夜|刑|移|频|逐|靠|混|母|短|皮|终|聚|汽|村|云|哪|既|距|卫|停|烈|央|察|烧|迅|境|若|印|洲|刻|括|激|孔|搞|甚|室|待|核|校|散|侵|吧|甲|游|久|菜|味|旧|模|湖|货|损|预|阻|毫|普|稳|乙|妈|植|息|扩|银|语|挥|酒|守|拿|序|纸|医|缺|雨|吗|针|刘|啊|急|唱|误|训|愿|审|附|获|茶|鲜|粮|斤|孩|脱|硫|肥|善|龙|演|父|渐|血|欢|械|掌|歌|沙|刚|攻|谓|盾|讨|晚|粒|乱|燃|矛|乎|杀|药|宁|鲁|贵|钟|煤|读|班|伯|香|介|迫|句|丰|培|握|兰|担|弦|蛋|沉|假|穿|执|答|乐|谁|顺|烟|缩|征|脸|喜|松|脚|困|异|免|背|星|福|买|染|井|概|慢|怕|磁|倍|祖|皇|促|静|补|评|翻|肉|践|尼|衣|宽|扬|棉|希|伤|操|垂|秋|宜|氢|套|督|振|架|亮|末|宪|庆|编|牛|触|映|雷|销|诗|座|居|抓|裂|胞|呼|娘|景|威|绿|晶|厚|盟|衡|鸡|孙|延|危|胶|屋|乡|临|陆|顾|掉|呀|灯|岁|措|束|耐|剧|玉|赵|跳|哥|季|课|凯|胡|额|款|绍|卷|齐|伟|蒸|殖|永|宗|苗|川|炉|岩|弱|零|杨|奏|沿|露|杆|探|滑|镇|饭|浓|航|怀|赶|库|夺|伊|灵|税|途|灭|赛|归|召|鼓|播|盘|裁|险|康|唯|录|菌|纯|借|糖|盖|横|符|私|努|堂|域|枪|润|幅|哈|竟|熟|虫|泽|脑|壤|碳|欧|遍|侧|寨|敢|彻|虑|斜|薄|庭|纳|弹|饲|伸|折|麦|湿|暗|荷|瓦|塞|床|筑|恶|户|访|塔|奇|透|梁|刀|旋|迹|卡|氯|遇|份|毒|泥|退|洗|摆|灰|彩|卖|耗|夏|择|忙|铜|献|硬|予|繁|圈|雪|函|亦|抽|篇|阵|阴|丁|尺|追|堆|雄|迎|泛|爸|楼|避|谋|吨|野|猪|旗|累|偏|典|馆|索|秦|脂|潮|爷|豆|忽|托|惊|塑|遗|固)\b'],
            'ko': [r'\b(이|그|저|것|수|더|나|우리|아니|어떤|때|년|한|말|일|이런|그런|무슨|어느|많은|안|좀|나는|우리는|당신|당신은|그들|그들은|우리의|나의|너의|그의|그녀의|이것|그것|저것|이것은|그것은|저것은)\b'],
            'tr': [r'\b(ve|bir|bu|için|o|ben|sen|biz|siz|onlar|de|da|mi|ki|değil|ama|ancak|fakat|çünkü|eğer|ya|ile|gibi|hem|hem de|kadar|daha|en|hiç|şey|tüm|sadece|yani|nasıl|ne|nerede|neden|ne zaman|kim|hangi|kendi|her)\b'],
            'sv': [r'\b(och|i|att|en|som|den|det|av|på|för|med|är|till|har|de|ett|om|jag|du|han|hon|vi|ni|dem|min|din|hans|hennes|vår|er|deras|denna|detta|dessa)\b'],
            'no': [r'\b(og|i|å|en|som|den|det|av|på|for|med|er|til|har|de|et|om|jeg|du|han|hun|vi|dere|dem|min|din|hans|hennes|vår|deres|denne|dette|disse)\b'],
            'da': [r'\b(og|i|at|en|som|den|det|af|på|for|med|er|til|har|de|et|om|jeg|du|han|hun|vi|I|dem|min|din|hans|hendes|vores|jeres|deres|denne|dette|disse)\b'],
            'fi': [r'\b(ja|on|se|että|ei|hän|me|te|he|tämä|tuo|nämä|nuo|minun|sinun|hänen|meidän|teidän|heidän|minä|sinä|me|te|he|kuka|mikä|missä|milloin|miksi)\b'],
            'pl': [r'\b(i|w|to|jest|nie|na|z|się|do|że|a|o|jak|ale|co|po|tak|za|od|go|już|jego|jej|ich|tylko|dla|tu|tego|przez|albo|więc|czy|nim|sam|pan|wszystko|nas)\b'],
            'cs': [r'\b(a|v|to|je|se|na|že|o|s|z|do|ale|jak|už|po|tak|za|od|mi|ho|jen|jeho|její|jejich|pouze|pro)\b'],
            'hu': [r'\b(a|az|és|van|nem|hogy|egy|ez|azt|is|én|te|ő|mi|ti|ők|de|ha|mint|mert|csak|még|már|így|vagy|valami|minden|aki|ami|mikor|hol|miért|ki|milyen|kell)\b'],
            'ro': [r'\b(și|în|a|o|la|de|pe|cu|pentru|este|că|nu|din|care|mai|se|sunt|ceea ce|cum|dar|sau|dacă|când|unde|cine|ce|acel|acest|acești|acele|unul|una|ei|ele|lui|ei|lor|meu|tău|său|nostru|vostru)\b'],
            'uk': [r'\b(і|в|на|що|з|до|це|не|я|ти|він|вона|ми|ви|вони|мій|твій|його|її|наш|ваш|їх|цей|ця|це|ці|той|та|те|ті)\b'],
            'bg': [r'\b(и|в|на|че|с|за|от|по|е|да|не|се|като|а|но|ако|или|което|който|това|този|тази|тези|онзи|онази|онова|онези|аз|ти|той|тя|то|ние|вие|те)\b'],
            'id': [r'\b(dan|di|ke|dari|dengan|untuk|adalah|bahwa|ini|itu|tidak|ya|saya|kamu|dia|kami|kalian|mereka|siapa|apa|di mana|kapan|mengapa|bagaimana)\b'],
            'th': [r'\b(และ|ใน|ที่|ว่า|จาก|กับ|สำหรับ|เป็น|นี้|ไม่|ฉัน|คุณ|เขา|เธอ|พวกเรา|พวกคุณ|พวกเขา|ของฉัน|ของคุณ|ของเขา|ของเธอ|ของเรา|ของพวกคุณ|ของพวกเขา)\b'],
            'sw': [r'\b(na|katika|kwa|kutoka|kwamba|hii|hiyo|hizo|si|mimi|wewe|yeye|sisi|ninyi|wao|wangu|wako|wake|wetu|wenu|wao)\b'],
            'ha': [r'\b(da|a|na|daga|ga|wannan|ba|ni|kai|shi|ita|mu|ku|su|nawa|naka|nasa|namu|naku|nasu)\b'],
            'ak': [r'\b(na|wɔ|a|firi|yɛ|wei|saa|ɛno|dɛn|me|wo|ɔno|yɛn|mo|wɔn|me|wo|ne|yɛn|mo|wɔn)\b'],
            'ur': [r'\b(اور|میں|کے|سے|کو|کہ|ہے|کی|نہیں|ہوں|تم|وہ|ہم|آپ|میرا|تمہارا|اس|یہ|وہ|کون|کیا|کہاں|کب|کیوں|کیسے)\b']
        }
        
        # Very common customer service phrases and questions in different languages (most useful for short text detection)
        self.service_phrases = {
            'en': [r'\b(hello|hi|hey|thanks|thank you|help|please|support|question|problem|issue|order|refund|return|cancel|delivery|shipping|payment|price|discount|where is|how to|can i|do you|when will)\b', 
                  r'\b(order status|track|shipping status|delivery time|contact us|forgot password|reset password|account|login|sign up|not working)\b'],
            'fr': [r'\b(bonjour|salut|merci|aide|s\'il vous plaît|service|question|problème|commande|remboursement|retour|annuler|livraison|paiement|prix|réduction|où est|comment|puis-je|pouvez-vous|quand)\b'],
            'es': [r'\b(hola|gracias|ayuda|por favor|servicio|pregunta|problema|pedido|reembolso|devolución|cancelar|entrega|envío|pago|precio|descuento|dónde está|cómo|puedo|puede|cuándo)\b'],
            'de': [r'\b(hallo|guten tag|danke|hilfe|bitte|dienst|frage|problem|bestellung|erstattung|rückgabe|stornieren|lieferung|versand|zahlung|preis|rabatt|wo ist|wie|kann ich|können sie|wann)\b'],
            'it': [r'\b(ciao|salve|grazie|aiuto|per favore|servizio|domanda|problema|ordine|rimborso|reso|annullare|consegna|spedizione|pagamento|prezzo|sconto|dov\'è|come|posso|potete|quando)\b'],
            'hi': [r'\b(नमस्ते|धन्यवाद|मदद|कृपया|सेवा|सवाल|समस्या|ऑर्डर|रिफंड|वापसी|रद्द|डिलीवरी|शिपिंग|भुगतान|कीमत|छूट|कहां है|कैसे|क्या मैं|क्या आप|कब)\b'],
            'zh': [r'\b(你好|谢谢|帮助|请|服务|问题|订单|退款|退货|取消|送货|运输|付款|价格|折扣|在哪里|怎么样|我能|你能|什么时候)\b'],
            'ja': [r'\b(こんにちは|ありがとう|助けて|お願いします|サービス|質問|問題|注文|返金|返品|キャンセル|配達|発送|支払い|価格|割引|どこ|どのように|できますか|いつ)\b'],
            'ru': [r'\b(здравствуйте|привет|спасибо|помощь|пожалуйста|служба|вопрос|проблема|заказ|возврат|отмена|доставка|отправка|оплата|цена|скидка|где|как|могу ли я|можете ли вы|когда)\b'],
            'ar': [r'\b(مرحبا|شكرا|مساعدة|من فضلك|خدمة|سؤال|مشكلة|طلب|استرداد|إرجاع|إلغاء|توصيل|شحن|دفع|سعر|خصم|أين|كيف|هل يمكنني|هل يمكنك|متى)\b'],
            'pt': [r'\b(olá|oi|obrigado|obrigada|ajuda|por favor|serviço|pergunta|problema|pedido|reembolso|devolução|cancelar|entrega|envio|pagamento|preço|desconto|onde está|como|posso|pode|quando)\b']
        }
        
    def setup_method_weights(self):
        """Setup weights for different detection methods"""
        self.method_weights = {
            'script': 0.9,         # Script detection: very reliable for non-Latin scripts
            'common_words': 0.7,   # Common word detection: reliable for enough text
            'service_phrases': 0.8, # Service phrases: very reliable for customer service context
            'spelling': 0.6,       # Spelling patterns: moderately reliable
            'region': 0.4,         # Region-based detection: provides a fallback
            'history': 0.5         # User history: provides context but can change
        }
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Main method to detect language using multiple signals
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with detected language, confidence, methods used
        """
        # Normalize text
        cleaned_text = self._normalize_text(text)
        
        # Track signals with confidence values
        signals = []
        
        # 1. Script detection (very reliable for non-Latin scripts)
        script_lang, script_conf = self._detect_by_script(cleaned_text)
        if script_conf > 0.6:
            signals.append(('script', script_lang, script_conf * self.method_weights['script']))
        
        # 2. Common words detection
        if len(cleaned_text.split()) >= 3:
            common_lang, common_conf = self._detect_by_common_words(cleaned_text)
            if common_conf > 0.2:
                signals.append(('common_words', common_lang, common_conf * self.method_weights['common_words']))
        
        # 3. Service phrase detection (especially useful for short texts)
        service_lang, service_conf = self._detect_by_service_phrases(cleaned_text)
        if service_conf > 0.3:
            signals.append(('service_phrases', service_lang, service_conf * self.method_weights['service_phrases']))
            
        # 4. Spelling patterns detection
        spelling_lang, spelling_conf = self._detect_by_spelling_patterns(cleaned_text)
        if spelling_conf > 0.3:
            signals.append(('spelling', spelling_lang, spelling_conf * self.method_weights['spelling']))
            


        # If no signals were found, default to English with low confidence
        if not signals:
            return {
                'language': 'en',
                'confidence': 0.2,
                'methods': ['default'],
                'reliable': False
            }
            
        # Combine signals with a weighted voting system
        final_lang, confidence, methods = self._combine_signals(signals)
        
        return {
            'language': final_lang, 
            'confidence': confidence,
            'methods': methods,
            'reliable': confidence > 0.7
        }
        
    def _normalize_text(self, text: str) -> str:
        """Normalize and clean text for analysis"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _detect_by_script(self, text: str) -> Tuple[str, float]:
        """Detect language based on character script"""
        if not text:
            return 'en', 0.0
            
        # Count characters by script
        script_counts = {}
        total_chars = 0
        
        for char in text:
            if char.isspace() or not char.isalnum():
                continue
                
            total_chars += 1
            char_script = None
            
            # Check which script range the character falls into
            for script, ranges in self.script_ranges.items():
                for start, end in ranges:
                    if start <= ord(char) <= end:
                        char_script = script
                        break
                if char_script:
                    break
            
            if char_script:
                script_counts[char_script] = script_counts.get(char_script, 0) + 1
        
        if not script_counts or total_chars == 0:
            return 'en', 0.0
            
        # Find dominant script
        dominant_script = max(script_counts.items(), key=lambda x: x[1])
        script_name, count = dominant_script
        
        # Calculate confidence
        confidence = count / total_chars
        
        # For Latin script, confidence is lower since many languages use it
        if script_name == 'latin':
            confidence *= 0.7  # Reduce confidence for Latin script
            
        # Map script to most likely language
        if script_name in self.script_language_map:
            # For scripts used by multiple languages, return the most common one
            language = self.script_language_map[script_name][0]
        else:
            language = 'en'  # Default fallback
            
        return language, confidence
    
    def _detect_by_common_words(self, text: str) -> Tuple[str, float]:
        """Detect language based on common words"""
        language_matches = {}
        
        for lang, patterns in self.common_words.items():
            matches = 0
            words = re.findall(r'\b\w+\b', text.lower())
            total_words = len(words)
            
            if total_words == 0:
                continue
                
            for pattern in patterns:
                try:
                    matches += len(re.findall(pattern, text.lower()))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}' for language '{lang}': {e}")
                    continue
            
            if matches > 0:
                # Score based on percentage of matched words
                language_matches[lang] = min(1.0, matches / (total_words * 0.5))
        
        if not language_matches:
            return 'en', 0.0
            
        # Get language with highest score
        best_lang = max(language_matches.items(), key=lambda x: x[1])
        language, confidence = best_lang
        
        return language, confidence
    
    def _detect_by_service_phrases(self, text: str) -> Tuple[str, float]:
        """Detect language based on customer service phrases - useful for short texts"""
        language_matches = {}
        
        for lang, patterns in self.service_phrases.items():
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text.lower()):
                    matches += 1
            
            if matches > 0:
                # Score based on matches
                language_matches[lang] = matches / len(patterns)
        
        if not language_matches:
            return 'en', 0.0
            
        # Get language with highest score
        best_lang = max(language_matches.items(), key=lambda x: x[1])
        language, confidence = best_lang
        
        return language, confidence
    
    def _detect_by_spelling_patterns(self, text: str) -> Tuple[str, float]:
        """Detect language based on spelling patterns and character combinations"""
        # Language-specific character combinations
        patterns = {
            'en': ['th', 'er', 'on', 'an', 'ch', 'ea', 'ing', 'the'],
            'fr': ['ou', 'ai', 'oi', 'eu', 'au', 'eux', 'ement', 'qu'],
            'es': ['ll', 'ñ', 'ió', 'ci', 'rr', 'ue', 'ón', 'iente'],
            'de': ['sch', 'ei', 'ch', 'ie', 'eu', 'äu', 'ung', 'lich'],
            'it': ['gli', 'zz', 'sci', 'gn', 'cch', 'tto', 'ett', 'cio'],
            'pt': ['ão', 'lh', 'nh', 'er', 'ç', 'ent', 'ado', 'ment'],
            'ru': ['ий', 'ый', 'ть', 'щ', 'ст', 'ни', 'но', 'ет'],
            'pl': ['cz', 'sz', 'rz', 'szcz', 'ść', 'ą', 'ę', 'ow'],
            # Add more languages as needed
        }
        
        scores = {}
        
        for lang, lang_patterns in patterns.items():
            matches = 0
            for p in lang_patterns:
                if p.lower() in text.lower():
                    matches += 1
            
            if matches > 0:
                scores[lang] = matches / len(lang_patterns)
        
        if not scores:
            return 'en', 0.0
            
        best_lang = max(scores.items(), key=lambda x: x[1])
        return best_lang
 

    def _combine_signals(self, signals: List[Tuple[str, str, float]]) -> Tuple[str, float, List[str]]:
        """Combine multiple signals to make final decision"""
        if not signals:
            return 'en', 0.2, ['default']
            
        # Initialize weighted votes
        lang_votes = Counter()
        methods_by_lang = {}
        
        # Calculate votes
        for method, lang, confidence in signals:
            lang_votes[lang] += confidence
            
            # Track which methods detected each language
            if lang not in methods_by_lang:
                methods_by_lang[lang] = []
            methods_by_lang[lang].append(method)
        
        # Find language with highest votes
        top_langs = lang_votes.most_common(2)
        winner = top_langs[0]
        winner_lang, winner_votes = winner
        
        # Calculate overall confidence
        total_votes = sum(lang_votes.values())
        confidence = winner_votes / total_votes
        
        # Consider margin if we have more than one language
        if len(top_langs) > 1:
            runner_up = top_langs[1]
            _, runner_up_votes = runner_up
            
            # Calculate margin to adjust confidence
            margin = (winner_votes - runner_up_votes) / winner_votes
            confidence = (confidence + margin) / 2
        
        # Get methods that contributed to winning language
        methods = methods_by_lang.get(winner_lang, [])
        
        return winner_lang, min(confidence, 0.99), methods
    
    def make_best_guess(self, text: str) -> str:
        """
        Make best guess at language even for very short texts
        Always returns a valid language code, never fails
        """
        if not text or len(text.strip()) == 0:
            return 'en'
            
        # For very short texts (1-3 words), rely heavily on patterns and region
        if len(text.split()) <= 3:
            # Try service phrases first (optimized for customer service context)
            service_lang, service_conf = self._detect_by_service_phrases(text)
            if service_conf > 0.4:
                return service_lang
                
            # Try script detection (works well for non-Latin scripts)
            script_lang, script_conf = self._detect_by_script(text)
            if script_conf > 0.7:
                return script_lang
                
            
            # Last resort: analyze first few characters and make an educated guess
            # This works surprisingly well for short greetings
            lower_text = text.lower()
            if re.match(r'^(hi|hey|hello|help|ok|yes|no|thanks|thank)', lower_text):
                return 'en'
            elif re.match(r'^(hola|gracias|ayuda|sí|no)', lower_text):
                return 'es'
            elif re.match(r'^(bonjour|salut|merci|oui|non|aide)', lower_text):
                return 'fr'
            elif re.match(r'^(hallo|danke|hilfe|ja|nein)', lower_text):
                return 'de'
            elif re.match(r'^(ciao|grazie|aiuto|sì|no)', lower_text):
                return 'it'
            # Add more language-specific patterns as needed
            
            # Default to English if no pattern matches
            return 'en'
        
        # For longer texts, use full detection
        result = self.detect_language(text)
        return result['language']