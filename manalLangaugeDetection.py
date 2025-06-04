import re
import random
import unicodedata
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import logging
import os

from logger_config import get_logger
logger = get_logger(__name__)

class ManualLanguageDetector:
    def __init__(self):
        logger.info("🔤 Initializing ManualLanguageDetector...")
        
        try:
            self.setup_language_support()
            logger.info("✅ Language support patterns loaded")
            
            self.setup_scripts()
            logger.info("✅ Script detection patterns loaded")
            
            self.setup_common_patterns()
            logger.info("✅ Common word patterns loaded")
            
            self.setup_method_weights()
            logger.info("✅ Detection method weights configured")
            
            self.setup_noanswer_message()
            logger.info("✅ No-answer messages loaded")
            
            self.setup_greeting_message()
            logger.info("✅ Greeting patterns loaded")
            
            # Log configuration summary
            logger.info(f"📊 Language detector configured for {len(getattr(self, 'supported_languages', {}))} languages")
            logger.info("🎯 ManualLanguageDetector initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ManualLanguageDetector: {str(e)}", exc_info=True)
            raise
        
    def setup_language_support(self):
        """Setup supported languages with their code, English name, and native name"""
        self.supported_languages = {
            'en': {'name': 'English', 'native': 'English'},
            'fr': {'name': 'French', 'native': 'Français'},
            'es': {'name': 'Spanish', 'native': 'Español'},
            'de': {'name': 'German', 'native': 'Deutsch'},
            'it': {'name': 'Italian', 'native': 'Italiano'},
            'pt': {'name': 'Portuguese', 'native': 'Português'},
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
            'south_america': ['es', 'pt'],
            'europe_west': ['en', 'fr', 'de', 'es', 'it', 'nl', 'pt'],
            'europe_north': ['en', 'sv', 'no', 'da', 'fi'],
            'europe_east': ['ru', 'pl', 'uk', 'cs', 'sk', 'hu', 'ro'],
            'europe_south': ['it', 'es', 'pt', 'el', 'tr'],
            'europe_balkans': ['hr', 'bs', 'sr',  'bg', 'mk', 'sq'],
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
                     'sl', 'hr', 'bs', 'ro', 'hu', 'lt', 'ca', 'gl', 'af', 'sq', 'vi', 'id', 'ms', 'sw', 'ha', 'ig', 'ak', 'tw'],
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

    def setup_noanswer_message(self):
        """Setup for default anser in multiple langauges"""
        self.no_results_responses = {
            'en': [
                "I wish I had the answer! Can you ask differently?",
                "I'm sorry, but I couldn't find an answer. Could you rephrase?",
                "I'm learning every day! Maybe try asking in another way?",
                "Sorry, I don't have an answer for that. Need help with something else?",
                "Hmm, I don't have that information right now. Could you try asking in a different way?"
            ],
            'en-ca': [
                "I wish I had the answer! Can you ask differently?",
                "I'm sorry, but I couldn't find an answer. Could you rephrase?",
                "I'm learning every day! Maybe try asking in another way?",
                "Sorry, I don't have an answer for that. Need help with something else?",
                "Hmm, I don't have that information right now. Could you try asking in a different way?"
            ],
            'en-au': [
                "I wish I had the answer! Can you ask differently?",
                "I'm sorry, but I couldn't find an answer. Could you rephrase?",
                "I'm learning every day! Maybe try asking in another way?",
                "Sorry, I don't have an answer for that. Need help with something else?",
                "Hmm, I don't have that information right now. Could you try asking in a different way?"
            ],
            'en-gb': [
                "I wish I had the answer! Can you ask differently?",
                "I'm sorry, but I couldn't find an answer. Could you rephrase?",
                "I'm learning every day! Maybe try asking in another way?",
                "Sorry, I don't have an answer for that. Need help with something else?",
                "Hmm, I don't have that information right now. Could you try asking in a different way?"
            ],
            'fr': [
                "J'aimerais avoir la réponse ! Pouvez-vous demander autrement ?",
                "Je suis désolé, mais je n'ai pas trouvé de réponse. Pourriez-vous reformuler ?",
                "J'apprends tous les jours ! Essayez peut-être de demander d'une autre façon ?",
                "Désolé, je n'ai pas de réponse à cela. Besoin d'aide pour autre chose ?",
                "Hmm, je n'ai pas cette information pour le moment. Pourriez-vous essayer de demander différemment ?"
            ],
            'es': [
                "¡Ojalá tuviera la respuesta! ¿Puedes preguntar de otra manera?",
                "Lo siento, pero no pude encontrar una respuesta. ¿Podrías reformular?",
                "¡Aprendo cada día! ¿Tal vez intenta preguntar de otra forma?",
                "Lo siento, no tengo respuesta para eso. ¿Necesitas ayuda con otra cosa?",
                "Hmm, no tengo esa información ahora mismo. ¿Podrías intentar preguntar de otra manera?"
            ],
            'de': [
                "Ich wünschte, ich hätte die Antwort! Kannst du anders fragen?",
                "Es tut mir leid, aber ich konnte keine Antwort finden. Könntest du umformulieren?",
                "Ich lerne jeden Tag! Vielleicht versuchst du, anders zu fragen?",
                "Tut mir leid, ich habe keine Antwort darauf. Brauchst du Hilfe bei etwas anderem?",
                "Hmm, ich habe diese Information gerade nicht. Könntest du versuchen, anders zu fragen?"
            ],
            'it': [
                "Vorrei avere la risposta! Puoi chiedere diversamente?",
                "Mi dispiace, ma non ho trovato una risposta. Potresti riformulare?",
                "Imparo ogni giorno! Magari prova a chiedere in un altro modo?",
                "Scusa, non ho una risposta per questo. Hai bisogno di aiuto con altro?",
                "Hmm, non ho questa informazione al momento. Potresti provare a chiedere in modo diverso?"
            ],
            'pt': [
                "Quem me dera ter a resposta! Pode perguntar de outra forma?",
                "Desculpe, mas não consegui encontrar uma resposta. Poderia reformular?",
                "Estou a aprender todos os dias! Talvez tente perguntar de outra maneira?",
                "Desculpe, não tenho resposta para isso. Precisa de ajuda com outra coisa?",
                "Hmm, não tenho essa informação agora. Poderia tentar perguntar de forma diferente?"
            ],
            'pt-br': [
                "Quem me dera ter a resposta! Pode perguntar de forma diferente?",
                "Desculpe, mas não consegui encontrar uma resposta. Poderia reformular?",
                "Estou aprendendo todos os dias! Talvez tente perguntar de outra maneira?",
                "Desculpe, não tenho resposta para isso. Precisa de ajuda com outra coisa?",
                "Hmm, não tenho essa informação agora. Poderia tentar perguntar de forma diferente?"
            ],
            'nl': [
                "Ik wou dat ik het antwoord had! Kun je het anders vragen?",
                "Het spijt me, maar ik kon geen antwoord vinden. Zou je het kunnen herformuleren?",
                "Ik leer elke dag! Misschien probeer je het op een andere manier te vragen?",
                "Sorry, ik heb daar geen antwoord op. Hulp nodig bij iets anders?",
                "Hmm, ik heb die informatie nu niet. Zou je het anders kunnen vragen?"
            ],
            'sv': [
                "Jag önskar att jag hade svaret! Kan du fråga annorlunda?",
                "Jag är ledsen, men jag kunde inte hitta ett svar. Kan du omformulera?",
                "Jag lär mig varje dag! Kanske försök fråga på ett annat sätt?",
                "Ledsen, jag har inget svar på det. Behöver du hjälp med något annat?",
                "Hmm, jag har inte den informationen just nu. Kan du försöka fråga på ett annat sätt?"
            ],
            'no': [
                "Skulle ønske jeg hadde svaret! Kan du spørre annerledes?",
                "Beklager, men jeg fant ikke et svar. Kan du omformulere?",
                "Jeg lærer hver dag! Kanskje prøv å spørre på en annen måte?",
                "Beklager, jeg har ikke noe svar på det. Trenger du hjelp med noe annet?",
                "Hmm, jeg har ikke den informasjonen nå. Kan du prøve å spørre på en annen måte?"
            ],
            'da': [
                "Jeg ville ønske, jeg havde svaret! Kan du spørge anderledes?",
                "Jeg beklager, men jeg kunne ikke finde et svar. Kunne du omformulere?",
                "Jeg lærer hver dag! Måske prøv at spørge på en anden måde?",
                "Beklager, jeg har ikke et svar på det. Har du brug for hjælp med noget andet?",
                "Hmm, jeg har ikke den information lige nu. Kunne du prøve at spørge på en anden måde?"
            ],
            'fi': [
                "Kunpa minulla olisi vastaus! Voitko kysyä toisin?",
                "Olen pahoillani, mutta en löytänyt vastausta. Voisitko muotoilla uudelleen?",
                "Opin joka päivä! Ehkä kokeile kysyä toisella tavalla?",
                "Anteeksi, minulla ei ole vastausta siihen. Tarvitsetko apua jossain muussa?",
                "Hmm, minulla ei ole tätä tietoa juuri nyt. Voisitko yrittää kysyä eri tavalla?"
            ],
            'pl': [
                "Chciałbym znać odpowiedź! Czy możesz zapytać inaczej?",
                "Przepraszam, ale nie znalazłem odpowiedzi. Czy mógłbyś przeformułować?",
                "Uczę się każdego dnia! Może spróbuj zapytać w inny sposób?",
                "Przepraszam, nie mam na to odpowiedzi. Potrzebujesz pomocy z czymś innym?",
                "Hmm, nie mam teraz tej informacji. Czy mógłbyś spróbować zapytać inaczej?"
            ],
            'ru': [
                "Жаль, что у меня нет ответа! Можете спросить иначе?",
                "Извините, но я не смог найти ответ. Не могли бы вы перефразировать?",
                "Я учусь каждый день! Может, попробуйте спросить по-другому?",
                "Извините, у меня нет ответа на это. Нужна помощь с чем-то другим?",
                "Хмм, у меня сейчас нет этой информации. Не могли бы вы попробовать спросить иначе?"
            ],
            'uk': [
                "Шкода, що я не маю відповіді! Можете запитати інакше?",
                "Вибачте, але я не зміг знайти відповідь. Чи не могли б ви перефразувати?",
                "Я навчаюся щодня! Можливо, спробуйте запитати по-іншому?",
                "Вибачте, у мене немає відповіді на це. Потрібна допомога з чимось іншим?",
                "Гмм, у мене зараз немає цієї інформації. Чи не могли б ви спробувати запитати інакше?"
            ],
            'cs': [
                "Přál bych si mít odpověď! Můžete se zeptat jinak?",
                "Je mi líto, ale nenašel jsem odpověď. Mohl byste to přeformulovat?",
                "Učím se každý den! Možná zkuste zeptat se jiným způsobem?",
                "Omlouvám se, na to nemám odpověď. Potřebujete pomoct s něčím jiným?",
                "Hmm, nemám teď tyto informace. Mohl byste se zkusit zeptat jinak?"
            ],
            'sk': [
                "Želal by som si mať odpoveď! Môžete sa spýtať inak?",
                "Je mi ľúto, ale nenašiel som odpoveď. Mohli by ste to preformulovať?",
                "Učím sa každý deň! Možno skúste opýtať sa iným spôsobom?",
                "Prepáčte, na to nemám odpoveď. Potrebujete pomôcť s niečím iným?",
                "Hmm, nemám teraz tieto informácie. Mohli by ste sa skúsiť spýtať inak?"
            ],
            'sl': [
                "Želim si, da bi imel odgovor! Lahko vprašate drugače?",
                "Oprostite, vendar nisem našel odgovora. Bi lahko preoblikovali vprašanje?",
                "Vsak dan se učim! Morda poskusite vprašati na drugačen način?",
                "Oprostite, na to nimam odgovora. Potrebujete pomoč pri čem drugem?",
                "Hmm, trenutno nimam teh informacij. Bi lahko poskusili vprašati drugače?"
            ],
            'hr': [
                "Volio bih da imam odgovor! Možete li pitati drugačije?",
                "Žao mi je, ali nisam mogao pronaći odgovor. Možete li preformulirati?",
                "Učim svaki dan! Možda pokušajte pitati na drugi način?",
                "Oprostite, nemam odgovor na to. Trebate li pomoć s nečim drugim?",
                "Hmm, nemam te informacije trenutno. Možete li pokušati pitati drugačije?"
            ],
            'bs': [
                "Volio bih da imam odgovor! Možete li pitati drugačije?",
                "Žao mi je, ali nisam mogao pronaći odgovor. Možete li preformulirati?",
                "Učim svaki dan! Možda pokušajte pitati na drugi način?",
                "Oprostite, nemam odgovor na to. Trebate li pomoć s nečim drugim?",
                "Hmm, nemam te informacije trenutno. Možete li pokušati pitati drugačije?"
            ],
            'sr': [
                "Волео бих да имам одговор! Можете ли питати другачије?",
                "Жао ми је, али нисам могао пронаћи одговор. Можете ли да преформулишете?",
                "Учим сваки дан! Можда покушајте да питате на други начин?",
                "Извините, немам одговор на то. Треба ли вам помоћ са нечим другим?",
                "Хмм, немам те информације тренутно. Можете ли покушати да питате другачије?"
            ],
            'sr-latn': [
                "Voleo bih da imam odgovor! Možete li pitati drugačije?",
                "Žao mi je, ali nisam mogao pronaći odgovor. Možete li da preformulišete?",
                "Učim svaki dan! Možda pokušajte da pitate na drugi način?",
                "Izvinite, nemam odgovor na to. Treba li vam pomoć sa nečim drugim?",
                "Hmm, nemam te informacije trenutno. Možete li pokušati da pitate drugačije?"
            ],
            'ro': [
                "Aș fi vrut să am răspunsul! Puteți întreba diferit?",
                "Îmi pare rău, dar nu am putut găsi un răspuns. Ați putea reformula?",
                "Învăț în fiecare zi! Poate încercați să întrebați în alt mod?",
                "Îmi pare rău, nu am un răspuns pentru asta. Aveți nevoie de ajutor cu altceva?",
                "Hmm, nu am aceste informații acum. Ați putea încerca să întrebați diferit?"
            ],
            'bg': [
                "Бих искал да имам отговора! Можете ли да попитате различно?",
                "Съжалявам, но не можах да намеря отговор. Бихте ли преформулирали?",
                "Уча всеки ден! Може би опитайте да попитате по друг начин?",
                "Съжалявам, нямам отговор за това. Имате ли нужда от помощ с нещо друго?",
                "Хмм, нямам тази информация в момента. Бихте ли опитали да попитате по различен начин?"
            ],
            'mk': [
                "Би сакал да го имам одговорот! Можете ли да прашате поинаку?",
                "Жалам, но не можев да најдам одговор. Дали можете да преформулирате?",
                "Учам секој ден! Можеби обидете се да прашате на друг начин?",
                "Жалам, немам одговор на тоа. Ви треба помош со нешто друго?",
                "Хмм, немам такви информации во моментот. Дали можете да се обидете да прашате поинаку?"
            ],
            'el': [
                "Μακάρι να είχα την απάντηση! Μπορείτε να ρωτήσετε διαφορετικά;",
                "Λυπάμαι, αλλά δεν μπόρεσα να βρω απάντηση. Μπορείτε να το επαναδιατυπώσετε;",
                "Μαθαίνω κάθε μέρα! Ίσως δοκιμάστε να ρωτήσετε με άλλο τρόπο;",
                "Συγγνώμη, δεν έχω απάντηση γι' αυτό. Χρειάζεστε βοήθεια με κάτι άλλο;",
                "Χμμ, δεν έχω αυτή την πληροφορία αυτή τη στιγμή. Μπορείτε να προσπαθήσετε να ρωτήσετε διαφορετικά;"
            ],
            'tr': [
                "Keşke cevabım olsaydı! Farklı şekilde sorabilir misiniz?",
                "Üzgünüm, ancak bir cevap bulamadım. Yeniden ifade edebilir misiniz?",
                "Her gün öğreniyorum! Belki başka bir şekilde sormayı deneyin?",
                "Üzgünüm, bunun için bir cevabım yok. Başka bir konuda yardıma ihtiyacınız var mı?",
                "Hmm, şu anda bu bilgiye sahip değilim. Farklı bir şekilde sormayı deneyebilir misiniz?"
            ],
            'hu': [
                "Bárcsak tudnám a választ! Tudnád másképp kérdezni?",
                "Sajnálom, de nem találtam választ. Át tudnád fogalmazni?",
                "Minden nap tanulok! Talán próbáld másképp kérdezni?",
                "Sajnálom, erre nincs válaszom. Segíthetek valami mással?",
                "Hmm, most nincs meg ez az információ. Megpróbálnád másképp kérdezni?"
            ],
            'lt': [
                "Norėčiau turėti atsakymą! Ar galite klausti kitaip?",
                "Atsiprašau, bet neradau atsakymo. Ar galėtumėte perfrazuoti?",
                "Mokausi kiekvieną dieną! Galbūt pabandykite klausti kitaip?",
                "Atsiprašau, neturiu atsakymo į tai. Reikia pagalbos dėl ko nors kito?",
                "Hmm, šiuo metu neturiu šios informacijos. Ar galėtumėte pabandyti klausti kitaip?"
            ],
            'ca': [
                "Tant de bo tingués la resposta! Pots preguntar d'una altra manera?",
                "Ho sento, però no he pogut trobar una resposta. Podries reformular-ho?",
                "Aprenc cada dia! Potser prova de preguntar d'una altra manera?",
                "Ho sento, no tinc resposta per això. Necessites ajuda amb alguna altra cosa?",
                "Mmm, no tinc aquesta informació ara mateix. Podries intentar preguntar d'una manera diferent?"
            ],
            'gl': [
                "Oxalá tivese a resposta! Podes preguntar doutro xeito?",
                "Síntoo, pero non puiden atopar unha resposta. Poderías reformular?",
                "Aprendo cada día! Talvez proba a preguntar doutro xeito?",
                "Síntoo, non teño resposta para iso. Precisas axuda con outra cousa?",
                "Hmm, non teño esa información agora mesmo. Poderías tentar preguntar dun xeito diferente?"
            ],
            'af': [
                "Ek wens ek het die antwoord! Kan jy anders vra?",
                "Jammer, maar ek kon nie 'n antwoord vind nie. Kan jy herformuleer?",
                "Ek leer elke dag! Dalk probeer om op 'n ander manier te vra?",
                "Jammer, ek het nie 'n antwoord daarvoor nie. Het jy hulp nodig met iets anders?",
                "Hmm, ek het nie daardie inligting op die oomblik nie. Kan jy probeer om anders te vra?"
            ],
            'sq': [
                "Do të doja të kisha përgjigjen! A mund ta pyesni ndryshe?",
                "Më vjen keq, por nuk gjeta dot përgjigje. A mund ta riformuloni?",
                "Unë mësoj çdo ditë! Ndoshta provoni të pyesni në një mënyrë tjetër?",
                "Më vjen keq, nuk kam përgjigje për këtë. Keni nevojë për ndihmë me diçka tjetër?",
                "Hmm, nuk e kam këtë informacion tani. A mund të provoni ta pyesni ndryshe?"
            ],
            'az': [
                "Kaş ki, cavabı bilərdim! Fərqli soruşa bilərsiniz?",
                "Üzr istəyirəm, amma cavab tapa bilmədim. Yenidən ifadə edə bilərsinizmi?",
                "Hər gün öyrənirəm! Bəlkə başqa cür soruşmağa çalışın?",
                "Üzr istəyirəm, buna cavabım yoxdur. Başqa bir şeylə kömək lazımdır?",
                "Hmm, hazırda bu məlumatım yoxdur. Fərqli şəkildə soruşmağa çalışa bilərsinizmi?"
            ],
            'kk': [
                "Әттең, жауабым болса ғой! Басқаша сұрай аласыз ба?",
                "Кешіріңіз, бірақ жауап таба алмадым. Қайта тұжырымдай аласыз ба?",
                "Мен күн сайын үйренемін! Мүмкін басқа жолмен сұрап көріңіз?",
                "Кешіріңіз, бұған жауабым жоқ. Басқа нәрсемен көмек керек пе?",
                "Хмм, қазір бұл ақпарат жоқ. Басқаша сұрап көре аласыз ба?"
            ],
            'he': [
                "הלוואי שהייתה לי תשובה! אפשר לשאול אחרת?",
                "אני מצטער, אבל לא הצלחתי למצוא תשובה. אפשר לנסח מחדש?",
                "אני לומד כל יום! אולי תנסה לשאול בצורה אחרת?",
                "מצטער, אין לי תשובה לזה. צריך עזרה במשהו אחר?",
                "אממ, אין לי את המידע הזה כרגע. אפשר לנסות לשאול בצורה אחרת?"
            ],
            'ar': [
                "أتمنى لو كان لدي الإجابة! هل يمكنك السؤال بطريقة مختلفة؟",
                "آسف، لكنني لم أتمكن من العثور على إجابة. هل يمكنك إعادة صياغة السؤال؟",
                "أنا أتعلم كل يوم! ربما حاول أن تسأل بطريقة أخرى؟",
                "آسف، ليس لدي إجابة على ذلك. هل تحتاج مساعدة في شيء آخر؟",
                "هممم، ليس لدي هذه المعلومات الآن. هل يمكنك محاولة السؤال بطريقة مختلفة؟"
            ],
            'fa': [
                "ای کاش پاسخ را داشتم! می‌توانید به شکل دیگری بپرسید؟",
                "متأسفم، اما نتوانستم پاسخی پیدا کنم. می‌توانید دوباره بیان کنید؟",
                "من هر روز یاد می‌گیرم! شاید به روش دیگری بپرسید؟",
                "متأسفم، پاسخی برای این ندارم. آیا در مورد چیز دیگری به کمک نیاز دارید؟",
                "هوم، در حال حاضر این اطلاعات را ندارم. می‌توانید به شکل دیگری بپرسید؟"
            ],
            'ur': [
                "کاش میرے پاس جواب ہوتا! کیا آپ مختلف انداز میں پوچھ سکتے ہیں؟",
                "معذرت، لیکن مجھے کوئی جواب نہیں ملا۔ کیا آپ دوبارہ بیان کر سکتے ہیں؟",
                "میں ہر روز سیکھتا ہوں! شاید کسی اور طریقے سے پوچھنے کی کوشش کریں؟",
                "معذرت، میرے پاس اس کا جواب نہیں ہے۔ کیا آپ کو کسی اور چیز میں مدد چاہیے؟",
                "ہمم، میرے پاس ابھی یہ معلومات نہیں ہیں۔ کیا آپ مختلف انداز میں پوچھنے کی کوشش کر سکتے ہیں؟"
            ],
            'hi': [
                "काश मेरे पास जवाब होता! क्या आप अलग तरह से पूछ सकते हैं?",
                "मुझे खेद है, लेकिन मुझे कोई जवाब नहीं मिला। क्या आप फिर से पूछ सकते हैं?",
                "मैं हर दिन सीखता हूं! शायद किसी अन्य तरीके से पूछने का प्रयास करें?",
                "क्षमा करें, मेरे पास इसका जवाब नहीं है। क्या आपको किसी अन्य चीज़ में मदद चाहिए?",
                "हम्म, मेरे पास अभी यह जानकारी नहीं है। क्या आप अलग तरीके से पूछने की कोशिश कर सकते हैं?"
            ],
            'bn': [
                "আমি যদি উত্তর জানতাম! আপনি কি অন্যভাবে জিজ্ঞাসা করতে পারেন?",
                "দুঃখিত, কিন্তু আমি কোনো উত্তর খুঁজে পাইনি। আপনি কি পুনরায় বলতে পারেন?",
                "আমি প্রতিদিন শিখছি! হয়তো অন্য উপায়ে জিজ্ঞাসা করার চেষ্টা করুন?",
                "দুঃখিত, আমার কাছে এর উত্তর নেই। অন্য কিছুতে সাহায্য দরকার?",
                "হুম, আমার এখন এই তথ্য নেই। আপনি কি অন্যভাবে জিজ্ঞাসা করার চেষ্টা করতে পারেন?"
            ],
            'pa': [
                "काश मेरे कोल जवाब हुंदा! की तुसी वखरे ढंग नाल पुछ सकदे हो?",
                "माफ करना, पर मैनूं कोई जवाब नहीं मिलिया। की तुसी फेर तों पुछ सकदे हो?",
                "मैं हर रोज सिखदा हां! शायद किसे होर तरीके नाल पुछण दी कोशिश करो?",
                "माफ करना, मेरे कोल इसदा जवाब नहीं है। की तुहानूं किसे होर चीज़ च मदद चाहीदी है?",
                "हम्म, मेरे कोल हुण इह जानकारी नहीं है। की तुसी वखरे तरीके नाल पुछण दी कोशिश कर सकदे हो?"
            ],
            'gu': [
                "કાશ મારી પાસે જવાબ હોત! શું તમે અલગ રીતે પૂછી શકો છો?",
                "માફ કરશો, પણ મને કોઈ જવાબ મળ્યો નથી. શું તમે ફરીથી કહી શકો છો?",
                "હું દરરોજ શીખું છું! કદાચ બીજી રીતે પૂછવાનો પ્રયાસ કરો?",
                "માફ કરશો, મારી પાસે આનો જવાબ નથી. શું તમને બીજી કોઈ બાબતમાં મદદ જોઈએ છે?",
                "હમ્મ, મારી પાસે હાલમાં આ માહિતી નથી. શું તમે અલગ રીતે પૂછવાનો પ્રયાસ કરી શકો છો?"
            ],
            'mr': [
                "अरे, मला उत्तर माहित असते तर किती बरं झालं असतं! तुम्ही वेगळ्या प्रकारे विचारू शकता का?",
                "क्षमस्व, पण मला उत्तर सापडले नाही. तुम्ही पुन्हा सांगू शकाल का?",
                "मी दररोज शिकतो! कदाचित वेगळ्या पद्धतीने विचारण्याचा प्रयत्न करा?",
                "क्षमस्व, याचे उत्तर माझ्याकडे नाही. तुम्हाला इतर काही मदत हवी आहे का?",
                "हम्म, सध्या माझ्याकडे ही माहिती नाही. तुम्ही वेगळ्या पद्धतीने विचारण्याचा प्रयत्न करू शकता का?"
            ],
            'ne': [
                "काश मसँग उत्तर हुन्थ्यो! के तपाईं फरक तरिकाले सोध्न सक्नुहुन्छ?",
                "माफ गर्नुहोस्, तर मैले उत्तर फेला पार्न सकिनँ। के तपाईं फेरि भन्न सक्नुहुन्छ?",
                "म हरेक दिन सिक्दैछु! शायद अर्को तरिकाले सोध्ने प्रयास गर्नुहोस्?",
                "माफ गर्नुहोस्, मसँग यसको उत्तर छैन। के तपाईंलाई अरु केहि कुरामा मद्दत चाहिन्छ?",
                "हम्म, मसँग अहिले यो जानकारी छैन। के तपाईं फरक तरिकाले सोध्ने प्रयास गर्न सक्नुहुन्छ?"
            ],
            'si': [
                "මට පිළිතුර තිබුණා නම් කොච්චර හොඳද! ඔබට වෙනත් ආකාරයකින් අසන්න පුළුවන්ද?",
                "සමාවන්න, නමුත් මට පිළිතුරක් සොයාගත නොහැකි විය. ඔබට නැවත සඳහන් කළ හැකිද?",
                "මම සෑම දිනකම ඉගෙන ගන්නවා! වෙනත් ක්‍රමයකින් අසන්න උත්සාහ කරන්න?",
                "සමාවන්න, මට ඒකට පිළිතුරක් නැහැ. ඔබට වෙනත් දෙයකින් උදව් අවශ්‍යද?",
                "හ්ම්, මට දැනට මෙම තොරතුරු නැත. ඔබට වෙනත් ආකාරයකින් අසන්න උත්සාහ කළ හැකිද?"
            ],
            'ta': [
                "என்னிடம் பதில் இருந்திருக்க வேண்டும்! வேறு விதமாகக் கேட்க முடியுமா?",
                "மன்னிக்கவும், ஆனால் எனக்கு பதில் கிடைக்கவில்லை. நீங்கள் மீண்டும் கூற முடியுமா?",
                "நான் ஒவ்வொரு நாளும் கற்றுக்கொள்கிறேன்! வேறு வழியில் கேட்க முயற்சிக்கவும்?",
                "மன்னிக்கவும், எனக்கு இதற்கு பதில் இல்லை. வேறு எதிலாவது உதவி வேண்டுமா?",
                "ஹ்ம்ம், எனக்கு இப்போது இந்த தகவல் இல்லை. வேறு விதமாகக் கேட்க முயற்சிக்க முடியுமா?"
            ],
            'te': [
                "నాకు సమాధానం తెలిసి ఉంటే బాగుండేది! మీరు వేరే విధంగా అడగగలరా?",
                "క్షమించండి, కానీ నేను సమాధానం కనుగొనలేకపోయాను. మీరు మళ్ళీ చెప్పగలరా?",
                "నేను ప్రతిరోజూ నేర్చుకుంటున్నాను! బహుశా మరో విధంగా అడిగే ప్రయత్నం చేయండి?",
                "క్షమించండి, దీనికి నాకు సమాధానం లేదు. మీకు వేరే విషయంలో సహాయం కావాలా?",
                "హ్మ్, ప్రస్తుతం నాకు ఈ సమాచారం లేదు. మీరు వేరే విధంగా అడిగే ప్రయత్నం చేయగలరా?"
            ],
            'ml': [
                "എനിക്ക് ഉത്തരം അറിയാമായിരുന്നെങ്കിൽ! നിങ്ങൾക്ക് വ്യത്യസ്തമായി ചോദിക്കാൻ കഴിയുമോ?",
                "ക്ഷമിക്കണം, എനിക്ക് ഉത്തരം കണ്ടെത്താൻ കഴിഞ്ഞില്ല. നിങ്ങൾക്ക് വീണ്ടും പറയാൻ കഴിയുമോ?",
                "ഞാൻ എല്ലാ ദിവസവും പഠിക്കുന്നു! മറ്റൊരു രീതിയിൽ ചോദിക്കാൻ ശ്രമിക്കുക?",
                "ക്ഷമിക്കണം, എനിക്ക് ഇതിന് ഉത്തരമില്ല. നിങ്ങൾക്ക് മറ്റെന്തെങ്കിലും സഹായം വേണോ?",
                "ഹ്മ്മ്, എനിക്ക് ഇപ്പോൾ ഈ വിവരങ്ങളില്ല. നിങ്ങൾക്ക് വ്യത്യസ്തമായി ചോദിക്കാൻ ശ്രമിക്കാമോ?"
            ],
            'kn': [
                "ನನಗೆ ಉತ್ತರ ಗೊತ್ತಿದ್ದರೆ ಎಷ್ಟು ಒಳ್ಳೆಯದು! ನೀವು ಬೇರೆ ರೀತಿಯಲ್ಲಿ ಕೇಳಬಹುದೇ?",
                "ಕ್ಷಮಿಸಿ, ಆದರೆ ನನಗೆ ಉತ್ತರ ಸಿಗಲಿಲ್ಲ. ನೀವು ಮತ್ತೊಮ್ಮೆ ಹೇಳಬಹುದೇ?",
                "ನಾನು ಪ್ರತಿದಿನ ಕಲಿಯುತ್ತೇನೆ! ಬಹುಶಃ ಬೇರೆ ರೀತಿಯಲ್ಲಿ ಕೇಳಲು ಪ್ರಯತ್ನಿಸಿ?",
                "ಕ್ಷಮಿಸಿ, ನನಗೆ ಇದಕ್ಕೆ ಉತ್ತರವಿಲ್ಲ. ನಿಮಗೆ ಬೇರೆ ಏನಾದರೂ ಸಹಾಯ ಬೇಕೇ?",
                "ಹ್ಮ್, ನನಗೆ ಈಗ ಈ ಮಾಹಿತಿ ಇಲ್ಲ. ನೀವು ಬೇರೆ ರೀತಿಯಲ್ಲಿ ಕೇಳಲು ಪ್ರಯತ್ನಿಸಬಹುದೇ?"
            ],
            'th': [
                "ฉันหวังว่าจะมีคำตอบ! คุณถามในรูปแบบอื่นได้ไหม?",
                "ขออภัย ฉันไม่พบคำตอบ คุณช่วยถามใหม่ได้ไหม?",
                "ฉันเรียนรู้ทุกวัน! ลองถามในอีกแบบไหม?",
                "ขออภัย ฉันไม่มีคำตอบสำหรับคำถามนี้ คุณต้องการความช่วยเหลือเรื่องอื่นไหม?",
                "อืม ฉันไม่มีข้อมูลนี้ตอนนี้ คุณลองถามในรูปแบบอื่นได้ไหม?"
            ],
            'zh': [
                "真希望我知道答案！您能换个方式提问吗？",
                "抱歉，我找不到答案。您能重新表述一下吗？",
                "我每天都在学习！也许试试用另一种方式提问？",
                "抱歉，我没有这个问题的答案。需要帮助解决其他问题吗？",
                "嗯，我现在没有这个信息。您能试着换种方式提问吗？"
            ],
            'zh-tw': [
                "真希望我知道答案！您能換個方式提問嗎？",
                "抱歉，我找不到答案。您能重新表述一下嗎？",
                "我每天都在學習！也許試試用另一種方式提問？",
                "抱歉，我沒有這個問題的答案。需要幫助解決其他問題嗎？",
                "嗯，我現在沒有這個資訊。您能試著換種方式提問嗎？"
            ],
            'ja': [
                "答えを知っていたらいいのに！違う言い方で質問できますか？",
                "申し訳ありませんが、答えが見つかりませんでした。言い換えていただけますか？",
                "日々学習中です！別の方法で質問してみませんか？",
                "すみません、それについての答えはありません。他に何かお手伝いできることはありますか？",
                "うーん、今はその情報がありません。別の言い方で質問してみていただけますか？"
            ],
            'ko': [
                "답을 알았으면 좋겠어요! 다르게 질문해 주실래요?",
                "죄송합니다만, 답을 찾을 수 없었습니다. 다시 말씀해 주시겠어요?",
                "저는 매일 배우고 있어요! 다른 방식으로 질문해 보시겠어요?",
                "죄송합니다, 그에 대한 답변이 없습니다. 다른 것으로 도움이 필요하신가요?",
                "음, 지금은 그 정보가 없습니다. 다른 방식으로 질문해 보시겠어요?"
            ],
            'vi': [
                "Ước gì tôi có câu trả lời! Bạn có thể hỏi khác đi không?",
                "Xin lỗi, nhưng tôi không tìm thấy câu trả lời. Bạn có thể diễn đạt lại không?",
                "Tôi học hỏi mỗi ngày! Có lẽ thử hỏi theo cách khác?",
                "Xin lỗi, tôi không có câu trả lời cho điều đó. Bạn cần giúp đỡ với điều gì khác không?",
                "Hmm, tôi không có thông tin đó ngay bây giờ. Bạn có thể thử hỏi theo cách khác không?"
            ],
            'id': [
                "Andai saja saya punya jawabannya! Bisakah Anda bertanya dengan cara berbeda?",
                "Maaf, tetapi saya tidak dapat menemukan jawaban. Bisakah Anda mengungkapkan ulang?",
                "Saya belajar setiap hari! Mungkin coba tanyakan dengan cara lain?",
                "Maaf, saya tidak punya jawaban untuk itu. Perlu bantuan dengan hal lain?",
                "Hmm, saya tidak memiliki informasi itu sekarang. Bisakah Anda mencoba bertanya dengan cara berbeda?"
            ],
            'ms': [
                "Saya berharap saya ada jawapannya! Bolehkah anda bertanya dengan cara berbeza?",
                "Maaf, tetapi saya tidak dapat mencari jawapan. Bolehkah anda menyatakan semula?",
                "Saya belajar setiap hari! Mungkin cuba bertanya dengan cara lain?",
                "Maaf, saya tidak mempunyai jawapan untuk itu. Perlukan bantuan dengan perkara lain?",
                "Hmm, saya tidak mempunyai maklumat itu sekarang. Bolehkah anda cuba bertanya dengan cara yang berbeza?"
            ],
            'sw': [
                "Laiti ningekuwa na jibu! Unaweza kuuliza tofauti?",
                "Samahani, lakini sikupata jibu. Unaweza kurudia tena?",
                "Ninajifunza kila siku! Labda jaribu kuuliza kwa njia nyingine?",
                "Samahani, sina jibu kwa hilo. Unahitaji usaidizi na jambo lingine?",
                "Hmm, sina habari hiyo sasa hivi. Unaweza kujaribu kuuliza kwa njia tofauti?"
            ],
            'ha': [
                "Da ma ina da amsa! Za ka iya tambaya da wani hali?",
                "Yi hakuri, amma ban sami amsa ba. Za ka iya maimaita?",
                "Ina koyo kowace rana! Wataƙila ƙoƙari tambaya ta wani hali?",
                "Yi hakuri, ban da amsa game da wannan. Kana buƙatar taimako da wani abu?",
                "Hmm, ban da wannan bayani a yanzu. Za ka iya ƙoƙarin tambaya da wani hali?"
            ],
            'ig': [
                "Ọ gara m maara azịza! Ị nwere ike ịjụ n'ụzọ dị iche?",
                "Ndo, mana enweghị m ike ịchọta azịza. Ị nwere ike ikwu ya ọzọ?",
                "M na-amụta kwa ụbọchị! Ikekwe nwaa ịjụ n'ụzọ ọzọ?",
                "Ndo, enweghị m azịza maka nke ahụ. Ị chọrọ enyemaka n'ihe ọzọ?",
                "Hmm, enweghị m ozi ahụ ugbu a. Ị nwere ike ịnwaa ịjụ n'ụzọ dị iche?"
            ],
            'ak': [
                "Anka mewɔ mmuae no! Wobetumi abisa no wɔ kwan foforɔ so?",
                "Mepa wo kyɛw, nanso manhu mmuae no. Wobetumi aka bio?",
                "Mesua dabiara! Ebia sɔ wɔbisa no wɔ kwan foforɔ so?",
                "Mepa wo kyɛw, menni mmuae mma eyi. Wohia mmoa wɔ biribi foforɔ ho?",
                "Hmm, menni saa nsɛm no seisei. Wobetumi asɔ wɔbisa no wɔ kwan foforɔ so?"
            ],
            'tw': [
                "Anka mewɔ mmuae no! Wobetumi abisa no wɔ kwan foforɔ so?",
                "Mepa wo kyɛw, nanso manhu mmuae no. Wobetumi aka bio?",
                "Mesua dabiara! Ebia sɔ wɔbisa no wɔ kwan foforɔ so?",
                "Mepa wo kyɛw, menni mmuae mma eyi. Wohia mmoa wɔ biribi foforɔ ho?",
                "Hmm, menni saa nsɛm no seisei. Wobetumi asɔ wɔbisa no wɔ kwan foforɔ so?"
            ],
            'sd': [
                "ڪاش مون وٽ جواب هجي ها! ڇا توهان مختلف نموني سان پڇي سگهو ٿا؟",
                "معاف ڪجو، پر مون کي جواب نه مليو. ڇا توهان ٻيهر چئي سگهو ٿا؟",
                "آئون هر ڏينهن سکان ٿو! شايد ٻئي طريقي سان پڇڻ جي ڪوشش ڪريو؟",
                "معاف ڪجو، مون وٽ ان جو جواب ناهي. ڇا توهان کي ڪنهن ٻئي شيء۾ مدد گهرجي؟",
                "هم، مون وٽ هن وقت اها معلومات ناهي. ڇا توهان مختلف طريقي سان پڇڻ جي ڪوشش ڪري سگهو ٿا؟"
            ],
            'ps': [
                "کاش چې زه ځواب لرم! ایا تاسو په بل ډول پوښتلی شئ؟",
                "بښنه غواړم، خو ما ځواب ونه موند. ایا تاسو بیا ویلی شئ؟",
                "زه هره ورځ زده کوم! شاید په بل ډول پوښتلو هڅه وکړئ؟",
                "بښنه غواړم، زه د دې لپاره ځواب نلرم. ایا تاسو په بل څه کې مرستې ته اړتیا لرئ؟",
                "هم، زه اوس دا معلومات نلرم. ایا تاسو په بل ډول پوښتلو هڅه کولی شئ؟"
            ]
        }
    

    def setup_greeting_message(self):
        """Setup for greeting message in multiple langauges"""
        self.greeting_responses = {
        "en": {
            "patterns": [
                "hello", "hi", "hey", "greetings", "good morning", "good afternoon",
                "good evening", "how are you", "howdy", "sup", "what's up", "hiya"
            ],
            "responses": [
                "Hello! How can I help you today?",
                "Hi there! What would you like to know?",
                "Hey! Feel free to ask me any questions.",
                "Welcome! How may I assist you?"
            ]
        },
        "fr": {
            "patterns": [
                "bonjour", "salut", "coucou", "bonsoir", "comment ça va", "comment vas-tu",
                "comment allez-vous", "ça va", "enchanté", "bienvenue"
            ],
            "responses": [
                "Bonjour! Comment puis-je vous aider aujourd'hui?",
                "Salut! Que voulez-vous savoir?",
                "Bonjour! N'hésitez pas à me poser des questions.",
                "Bienvenue! Comment puis-je vous aider?"
            ]
        },
        "es": {
            "patterns": [
                "hola", "buenos días", "buenas tardes", "buenas noches", 
                "cómo estás", "qué tal", "saludos", "qué pasa", "cómo va"
            ],
            "responses": [
                "¡Hola! ¿Cómo puedo ayudarte hoy?",
                "¡Saludos! ¿Qué te gustaría saber?",
                "¡Bienvenido! ¿En qué puedo asistirte?",
                "¡Hola! Estoy aquí para ayudarte."
            ]
        },
        "de": {
            "patterns": [
                "hallo", "guten tag", "guten morgen", "guten abend", "grüß gott",
                "grüß dich", "servus", "moin", "wie geht es dir", "wie geht's"
            ],
            "responses": [
                "Hallo! Wie kann ich Ihnen heute helfen?",
                "Guten Tag! Was möchten Sie wissen?",
                "Hallo! Fragen Sie mich gerne, was Sie möchten.",
                "Willkommen! Womit kann ich Ihnen behilflich sein?"
            ]
        },
        "it": {
            "patterns": [
                "ciao", "salve", "buongiorno", "buonasera", "buonanotte",
                "come stai", "come va", "come sta"
            ],
            "responses": [
                "Ciao! Come posso aiutarti oggi?",
                "Salve! Cosa vorresti sapere?",
                "Buongiorno! Sentiti libero di farmi qualsiasi domanda.",
                "Benvenuto! Come posso assisterti?"
            ]
        },
        "pt": {
            "patterns": [
                "olá", "oi", "bom dia", "boa tarde", "boa noite",
                "como vai", "como está", "tudo bem"
            ],
            "responses": [
                "Olá! Como posso ajudá-lo hoje?",
                "Oi! O que gostaria de saber?",
                "Olá! Sinta-se à vontade para fazer qualquer pergunta.",
                "Bem-vindo! Como posso ajudá-lo?"
            ]
        },
        "nl": {
            "patterns": [
                "hallo", "hoi", "goedemorgen", "goedemiddag", "goedenavond",
                "hoe gaat het", "alles goed"
            ],
            "responses": [
                "Hallo! Hoe kan ik u vandaag helpen?",
                "Hoi! Wat wilt u weten?",
                "Hallo! Stel gerust al uw vragen.",
                "Welkom! Hoe kan ik u van dienst zijn?"
            ]
        },
        "sv": {
            "patterns": [
                "hej", "hallå", "god morgon", "god dag", "god kväll",
                "hur mår du", "hur går det", "tjena"
            ],
            "responses": [
                "Hej! Hur kan jag hjälpa dig idag?",
                "Hallå! Vad vill du veta?",
                "Hej! Fråga mig gärna vad du vill.",
                "Välkommen! Hur kan jag hjälpa dig?"
            ]
        },
        "no": {
            "patterns": [
                "hei", "hallo", "god morgen", "god dag", "god kveld",
                "hvordan går det", "hvordan har du det"
            ],
            "responses": [
                "Hei! Hvordan kan jeg hjelpe deg i dag?",
                "Hallo! Hva vil du vite?",
                "Hei! Bare spør meg om det du lurer på.",
                "Velkommen! Hvordan kan jeg assistere deg?"
            ]
        },
        "da": {
            "patterns": [
                "hej", "goddag", "god morgen", "god aften", "hvordan går det",
                "hvordan har du det", "dav"
            ],
            "responses": [
                "Hej! Hvordan kan jeg hjælpe dig i dag?",
                "Goddag! Hvad vil du gerne vide?",
                "Hej! Du er velkommen til at stille mig spørgsmål.",
                "Velkommen! Hvordan kan jeg hjælpe dig?"
            ]
        },
        "fi": {
            "patterns": [
                "hei", "moi", "terve", "päivää", "huomenta", "iltaa",
                "mitä kuuluu", "miten menee"
            ],
            "responses": [
                "Hei! Kuinka voin auttaa sinua tänään?",
                "Moi! Mitä haluaisit tietää?",
                "Terve! Kysy minulta mitä vain.",
                "Tervetuloa! Kuinka voin olla avuksi?"
            ]
        },
        "pl": {
            "patterns": [
                "cześć", "witaj", "dzień dobry", "dobry wieczór", "hej",
                "jak się masz", "co słychać"
            ],
            "responses": [
                "Cześć! Jak mogę ci dziś pomóc?",
                "Witaj! Co chciałbyś wiedzieć?",
                "Dzień dobry! Śmiało, zadawaj pytania.",
                "Witamy! W czym mogę ci pomóc?"
            ]
        },
        "ru": {
            "patterns": [
                "привет", "здравствуйте", "доброе утро", "добрый день", 
                "добрый вечер", "как дела", "здорово"
            ],
            "responses": [
                "Привет! Чем я могу вам помочь сегодня?",
                "Здравствуйте! Что бы вы хотели узнать?",
                "Привет! Не стесняйтесь задавать любые вопросы.",
                "Добро пожаловать! Чем могу быть полезен?"
            ]
        },
        "uk": {
            "patterns": [
                "привіт", "здрастуйте", "добрий ранок", "добрий день", 
                "добрий вечір", "як справи", "вітаю"
            ],
            "responses": [
                "Привіт! Чим я можу вам допомогти сьогодні?",
                "Здрастуйте! Що б ви хотіли дізнатися?",
                "Привіт! Не соромтеся ставити будь-які запитання.",
                "Ласкаво просимо! Чим можу бути корисним?"
            ]
        },
        "cs": {
            "patterns": [
                "ahoj", "dobrý den", "dobré ráno", "dobrý večer", 
                "jak se máš", "jak se máte", "nazdar", "čau"
            ],
            "responses": [
                "Ahoj! Jak vám mohu dnes pomoci?",
                "Dobrý den! Co byste chtěli vědět?",
                "Ahoj! Neváhejte se mě na cokoliv zeptat.",
                "Vítejte! Jak vám mohu pomoci?"
            ]
        },
        "sk": {
            "patterns": [
                "ahoj", "dobrý deň", "dobré ráno", "dobrý večer", 
                "ako sa máš", "ako sa máte", "servus", "čau"
            ],
            "responses": [
                "Ahoj! Ako vám môžem dnes pomôcť?",
                "Dobrý deň! Čo by ste chceli vedieť?",
                "Ahoj! Neváhajte sa ma na čokoľvek opýtať.",
                "Vitajte! Ako vám môžem pomôcť?"
            ]
        },
        "sl": {
            "patterns": [
                "zdravo", "dober dan", "dobro jutro", "dober večer", 
                "kako si", "kako ste", "živjo"
            ],
            "responses": [
                "Zdravo! Kako vam lahko danes pomagam?",
                "Dober dan! Kaj bi radi vedeli?",
                "Zdravo! Vprašajte me kar koli.",
                "Dobrodošli! Kako vam lahko pomagam?"
            ]
        },
        "hr": {
            "patterns": [
                "bok", "zdravo", "dobar dan", "dobro jutro", "dobra večer", 
                "kako si", "kako ste"
            ],
            "responses": [
                "Bok! Kako vam mogu pomoći danas?",
                "Zdravo! Što biste željeli znati?",
                "Dobar dan! Slobodno me pitajte bilo što.",
                "Dobrodošli! Kako vam mogu pomoći?"
            ]
        },
        "bs": {
            "patterns": [
                "zdravo", "merhaba", "dobar dan", "dobro jutro", "dobra večer", 
                "kako si", "kako ste", "selam"
            ],
            "responses": [
                "Zdravo! Kako vam mogu pomoći danas?",
                "Merhaba! Šta biste željeli znati?",
                "Dobar dan! Slobodno me pitajte bilo šta.",
                "Dobrodošli! Kako vam mogu pomoći?"
            ]
        },
        "sr": {
            "patterns": [
                "здраво", "добар дан", "добро јутро", "добро вече", 
                "како си", "како сте", "ћао"
            ],
            "responses": [
                "Здраво! Како вам могу помоћи данас?",
                "Добар дан! Шта бисте желели да знате?",
                "Здраво! Слободно ме питајте било шта.",
                "Добродошли! Како вам могу помоћи?"
            ]
        },
        "ro": {
            "patterns": [
                "salut", "bună", "bună dimineața", "bună ziua", "bună seara", 
                "ce mai faci", "ce faci", "servus"
            ],
            "responses": [
                "Salut! Cum te pot ajuta astăzi?",
                "Bună! Ce ai dori să știi?",
                "Salut! Nu ezita să-mi pui orice întrebare.",
                "Bine ai venit! Cum te pot ajuta?"
            ]
        },
        "bg": {
            "patterns": [
                "здравей", "здравейте", "добро утро", "добър ден", "добър вечер", 
                "как си", "как сте", "привет"
            ],
            "responses": [
                "Здравейте! Как мога да ви помогна днес?",
                "Здравей! Какво бихте искали да знаете?",
                "Здравейте! Можете да ме попитате всичко.",
                "Добре дошли! Как мога да ви помогна?"
            ]
        },
        "mk": {
            "patterns": [
                "здраво", "добар ден", "добро утро", "добра вечер", 
                "како си", "како сте", "поздрав"
            ],
            "responses": [
                "Здраво! Како можам да ви помогнам денес?",
                "Добар ден! Што би сакале да знаете?",
                "Здраво! Слободно прашајте ме било што.",
                "Добредојдовте! Како можам да ви помогнам?"
            ]
        },
        "el": {
            "patterns": [
                "γεια", "γεια σας", "καλημέρα", "καλησπέρα", "καλό απόγευμα", 
                "τι κάνεις", "πώς είσαι", "χαίρετε"
            ],
            "responses": [
                "Γεια σας! Πώς μπορώ να σας βοηθήσω σήμερα;",
                "Γεια! Τι θα θέλατε να μάθετε;",
                "Καλημέρα! Μη διστάσετε να με ρωτήσετε οτιδήποτε.",
                "Καλώς ήρθατε! Πώς μπορώ να σας βοηθήσω;"
            ]
        },
        "tr": {
            "patterns": [
                "merhaba", "selam", "günaydın", "iyi günler", "iyi akşamlar", 
                "nasılsın", "naber", "selamlar"
            ],
            "responses": [
                "Merhaba! Bugün size nasıl yardımcı olabilirim?",
                "Selam! Ne öğrenmek istersiniz?",
                "Merhaba! Bana istediğiniz soruyu sorabilirsiniz.",
                "Hoş geldiniz! Size nasıl yardımcı olabilirim?"
            ]
        },
        "hu": {
            "patterns": [
                "szia", "helló", "jó reggelt", "jó napot", "jó estét", 
                "hogy vagy", "mi újság", "üdv"
            ],
            "responses": [
                "Szia! Hogyan segíthetek ma neked?",
                "Helló! Mit szeretnél tudni?",
                "Jó napot! Kérdezz nyugodtan bármit.",
                "Üdvözöllek! Hogyan segíthetek?"
            ]
        },
        "lt": {
            "patterns": [
                "labas", "sveikas", "sveiki", "laba diena", "labas rytas", "labas vakaras", 
                "kaip sekasi", "ką veiki"
            ],
            "responses": [
                "Labas! Kuo galiu jums padėti šiandien?",
                "Sveiki! Ką norėtumėte sužinoti?",
                "Labas! Drąsiai klauskite bet ko.",
                "Sveiki atvykę! Kuo galiu padėti?"
            ]
        },
        "ca": {
            "patterns": [
                "hola", "bon dia", "bona tarda", "bona nit", "com estàs", 
                "com va", "salutacions"
            ],
            "responses": [
                "Hola! Com puc ajudar-te avui?",
                "Bon dia! Què t'agradaria saber?",
                "Hola! No dubtis a fer-me qualsevol pregunta.",
                "Benvingut! Com puc assistir-te?"
            ]
        },
        "gl": {
            "patterns": [
                "ola", "bos días", "boas tardes", "boas noites", "como estás", 
                "que tal", "saúdos"
            ],
            "responses": [
                "Ola! Como podo axudarche hoxe?",
                "Bos días! Que che gustaría saber?",
                "Ola! Non dubides en facerme calquera pregunta.",
                "Benvido! Como podo asistirche?"
            ]
        },
        "af": {
            "patterns": [
                "hallo", "goeie dag", "goeie môre", "goeie naand", "hoe gaan dit", 
                "hoe gaan dit met jou", "groete"
            ],
            "responses": [
                "Hallo! Hoe kan ek jou vandag help?",
                "Goeie dag! Wat wil jy graag weet?",
                "Hallo! Voel vry om my enige vrae te vra.",
                "Welkom! Hoe kan ek jou help?"
            ]
        },
        "sq": {
            "patterns": [
                "përshëndetje", "tung", "mirëmëngjes", "mirëdita", "mirëmbrëma", 
                "si je", "si jeni"
            ],
            "responses": [
                "Përshëndetje! Si mund t'ju ndihmoj sot?",
                "Tung! Çfarë do të dëshironit të dinit?",
                "Përshëndetje! Mos hezitoni të më pyesni çdo gjë.",
                "Mirë se vini! Si mund t'ju ndihmoj?"
            ]
        },
        "az": {
            "patterns": [
                "salam", "sabahınız xeyir", "günortanız xeyir", "axşamınız xeyir", 
                "necəsən", "necəsiniz", "nə var nə yox"
            ],
            "responses": [
                "Salam! Bu gün sizə necə kömək edə bilərəm?",
                "Salam! Nə öyrənmək istərdiniz?",
                "Salam! Məndən istənilən sualı verməkdən çəkinməyin.",
                "Xoş gəldiniz! Sizə necə kömək edə bilərəm?"
            ]
        },
        "kk": {
            "patterns": [
                "сәлем", "қайырлы таң", "қайырлы күн", "қайырлы кеш", 
                "қалың қалай", "қалайсыз", "амансыз ба"
            ],
            "responses": [
                "Сәлем! Бүгін сізге қалай көмектесе аламын?",
                "Сәлеметсіз бе! Не білгіңіз келеді?",
                "Сәлем! Кез келген сұрақ қоюдан тартынбаңыз.",
                "Қош келдіңіз! Сізге қалай көмектесе аламын?"
            ]
        },
        "he": {
            "patterns": [
                "שלום", "היי", "בוקר טוב", "צהריים טובים", "ערב טוב", 
                "מה שלומך", "מה קורה", "מה נשמע"
            ],
            "responses": [
                "שלום! איך אני יכול לעזור לך היום?",
                "היי! מה תרצה לדעת?",
                "שלום! אל תהסס לשאול אותי כל שאלה.",
                "ברוך הבא! איך אני יכול לסייע לך?"
            ]
        },
        "ar": {
            "patterns": [
                "مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", 
                "كيف حالك", "كيف الحال", "أهلا"
            ],
            "responses": [
                "مرحبا! كيف يمكنني مساعدتك اليوم؟",
                "السلام عليكم! ماذا تود أن تعرف؟",
                "أهلا! لا تتردد في طرح أي سؤال.",
                "أهلا وسهلا! كيف يمكنني مساعدتك؟"
            ]
        },
        "fa": {
            "patterns": [
                "سلام", "درود", "صبح بخیر", "روز بخیر", "عصر بخیر", "شب بخیر",
                "حالت چطوره", "چطوری", "احوال شما"
            ],
            "responses": [
                "سلام! امروز چطور می‌توانم به شما کمک کنم؟",
                "درود! چه چیزی می‌خواهید بدانید؟",
                "سلام! لطفاً هر سؤالی دارید بپرسید.",
                "خوش آمدید! چطور می‌توانم به شما کمک کنم؟"
            ]
        },
        "ur": {
            "patterns": [
                "سلام", "السلام علیکم", "صبح بخیر", "شام بخیر", 
                "آپ کیسے ہیں", "کیا حال ہے", "ہیلو", "آداب"
            ],
            "responses": [
                "سلام! آج میں آپ کی کیسے مدد کر سکتا ہوں؟",
                "السلام علیکم! آپ کیا جاننا چاہتے ہیں؟",
                "ہیلو! بلا جھجک کوئی بھی سوال پوچھیں۔",
                "خوش آمدید! میں آپ کی کیسے مدد کر سکتا ہوں؟"
            ]
        },
        "hi": {
            "patterns": [
                "नमस्ते", "नमस्कार", "कैसे हैं", "कैसे हो", "आप कैसे हैं", "सुप्रभात", 
                "शुभ दिन", "शुभ संध्या", "कैसी हो", "प्रणाम"
            ],
            "responses": [
                "नमस्ते! मैं आपकी कैसे सहायता कर सकता हूं?",
                "नमस्कार! आप क्या जानना चाहते हैं?",
                "नमस्ते! आप मुझसे कुछ भी पूछ सकते हैं।",
                "स्वागत है! मैं आपकी कैसे सहायता कर सकता हूं?"
            ]
        },
        "bn": {
            "patterns": [
                "নমস্কার", "হ্যালো", "শুভ সকাল", "শুভ অপরাহ্ন", "শুভ সন্ধ্যা", 
                "কেমন আছেন", "কেমন আছো", "কি খবর"
            ],
            "responses": [
                "নমস্কার! আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
                "হ্যালো! আপনি কী জানতে চান?",
                "নমস্কার! আমাকে যে কোনো প্রশ্ন জিজ্ঞাসা করতে দ্বিধা করবেন না।",
                "স্বাগতম! আমি আপনাকে কীভাবে সাহায্য করতে পারি?"
            ]
        },
        "pa": {
            "patterns": [
                "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "ਨਮਸਤੇ", "ਹੈਲੋ", "ਸ਼ੁਭ ਸਵੇਰ", "ਸ਼ੁਭ ਦਿਨ", "ਸ਼ੁਭ ਸ਼ਾਮ", 
                "ਕਿਵੇਂ ਹੋ", "ਕੀ ਹਾਲ ਹੈ"
            ],
            "responses": [
                "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਅੱਜ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
                "ਨਮਸਤੇ! ਤੁਸੀਂ ਕੀ ਜਾਣਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
                "ਹੈਲੋ! ਮੈਨੂੰ ਕੋਈ ਵੀ ਸਵਾਲ ਪੁੱਛਣ ਤੋਂ ਨਾ ਝਿਜਕੋ।",
                "ਜੀ ਆਇਆਂ ਨੂੰ! ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਸਹਾਇਤਾ ਕਰ ਸਕਦਾ ਹਾਂ?"
            ]
        },
        "gu": {
            "patterns": [
                "નમસ્તે", "હેલો", "સુપ્રભાત", "શુભ સવાર", "શુભ સાંજ", 
                "કેમ છો", "શું હાલ છે", "શું ચાલે છે"
            ],
            "responses": [
                "નમસ્તે! આજે હું તમને કેવી રીતે મદદ કરી શકું?",
                "હેલો! તમે શું જાણવા માંગો છો?",
                "નમસ્તે! મને કોઈપણ પ્રશ્ન પૂછવામાં સંકોચ ન કરશો.",
                "આપનું સ્વાગત છે! હું તમને કેવી રીતે મદદ કરી શકું?"
            ]
        },
        "mr": {
            "patterns": [
                "नमस्कार", "नमस्ते", "हॅलो", "शुभ सकाळ", "शुभ संध्याकाळ", 
                "कसे आहात", "काय चालू आहे", "कसं काय"
            ],
            "responses": [
                "नमस्कार! मी आज आपली कशी मदत करू शकतो?",
                "नमस्ते! आपल्याला काय जाणून घ्यायचे आहे?",
                "हॅलो! माझ्याकडे कोणताही प्रश्न विचारण्यास संकोच करू नका.",
                "स्वागत आहे! मी आपली कशी मदत करू शकतो?"
            ]
        },
        "ne": {
            "patterns": [
                "नमस्ते", "नमस्कार", "शुभ बिहानी", "शुभ दिन", "शुभ सन्ध्या", 
                "कस्तो छ", "के छ हाल", "कस्तो हुनुहुन्छ"
            ],
            "responses": [
                "नमस्ते! म तपाईंलाई आज कसरी मद्दत गर्न सक्छु?",
                "नमस्कार! तपाईं के जान्न चाहनुहुन्छ?",
                "नमस्ते! मलाई कुनै पनि प्रश्न सोध्न नहिच्किचाउनुहोस्।",
                "स्वागतम्! म तपाईंलाई कसरी सहयोग गर्न सक्छु?"
            ]
        },
        "si": {
            "patterns": [
                "ආයුබෝවන්", "හෙලෝ", "සුභ උදෑසනක්", "සුභ දවසක්", "සුභ සන්ධ්යාවක්", 
                "කොහොමද", "ඔබ කොහොමද"
            ],
            "responses": [
                "ආයුබෝවන්! මට අද ඔබට උදව් කළ හැක්කේ කෙසේද?",
                "හෙලෝ! ඔබට දැනගැනීමට අවශ්‍ය කුමක්ද?",
                "ආයුබෝවන්! මගෙන් ඕනෑම ප්‍රශ්නයක් ඇසීමට පසුබට නොවන්න.",
                "සාදරයෙන් පිළිගනිමු! මට ඔබට උපකාර කළ හැක්කේ කෙසේද?"
            ]
        },
        "ta": {
            "patterns": [
                "வணக்கம்", "ஹலோ", "காலை வணக்கம்", "மாலை வணக்கம்", 
                "எப்படி இருக்கிறீர்கள்", "என்ன செய்கிறீர்கள்"
            ],
            "responses": [
                "வணக்கம்! இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
                "ஹலோ! நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?",
                "வணக்கம்! என்னிடம் எந்தக் கேள்வியையும் கேட்க தயங்க வேண்டாம்.",
                "வரவேற்கிறோம்! நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?"
            ]
        },
        "te": {
            "patterns": [
                "నమస్కారం", "హలో", "శుభోదయం", "శుభ మధ్యాహ్నం", "శుభ సాయంత్రం", 
                "ఎలా ఉన్నారు", "ఏం చేస్తున్నారు"
            ],
            "responses": [
                "నమస్కారం! నేను మీకు ఈరోజు ఎలా సహాయం చేయగలను?",
                "హలో! మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?",
                "నమస్కారం! నన్ను ఏదైనా ప్రశ్న అడగడానికి సంకోచించకండి.",
                "స్వాగతం! నేను మీకు ఎలా సహాయపడగలను?"
            ]
        },
        "ml": {
            "patterns": [
                "നമസ്കാരം", "ഹലോ", "സുപ്രഭാതം", "ശുഭ ദിവസം", "ശുഭ സന്ധ്യ", 
                "സുഖമാണോ", "എന്തൊക്കെ ഉണ്ട് വിശേഷം"
            ],
            "responses": [
                "നമസ്കാരം! ഇന്ന് എനിക്ക് നിങ്ങളെ എങ്ങനെ സഹായിക്കാൻ കഴിയും?",
                "ഹലോ! നിങ്ങൾക്ക് എന്താണ് അറിയേണ്ടത്?",
                "നമസ്കാരം! എന്നോട് എന്തെങ്കിലും ചോദിക്കാൻ മടിക്കേണ്ട.",
                "സ്വാഗതം! എനിക്ക് നിങ്ങളെ എങ്ങനെ സഹായിക്കാൻ കഴിയും?"
            ]
        },
        "kn": {
            "patterns": [
                "ನಮಸ್ಕಾರ", "ಹಲೋ", "ಶುಭೋದಯ", "ಶುಭ ಮಧ್ಯಾಹ್ನ", "ಶುಭ ಸಂಜೆ", 
                "ಹೇಗಿದ್ದೀರಾ", "ಏನು ಮಾಡುತ್ತಿದ್ದೀರಾ"
            ],
            "responses": [
                "ನಮಸ್ಕಾರ! ನಾನು ನಿಮಗೆ ಇಂದು ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
                "ಹಲೋ! ನೀವು ಏನನ್ನು ತಿಳಿದುಕೊಳ್ಳಲು ಬಯಸುತ್ತೀರಿ?",
                "ನಮಸ್ಕಾರ! ನನ್ನನ್ನು ಯಾವುದೇ ಪ್ರಶ್ನೆಯನ್ನು ಕೇಳಲು ಹಿಂಜರಿಯಬೇಡಿ.",
                "ಸ್ವಾಗತ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?"
            ]
        },
        "th": {
            "patterns": [
                "สวัสดี", "สวัสดีครับ", "สวัสดีค่ะ", "อรุณสวัสดิ์", "สวัสดีตอนเย็น", 
                "เป็นอย่างไรบ้าง", "สบายดีไหม"
            ],
            "responses": [
                "สวัสดีครับ/ค่ะ! วันนี้ผม/ดิฉันจะช่วยคุณได้อย่างไรบ้าง?",
                "สวัสดี! คุณอยากทราบอะไรบ้าง?",
                "สวัสดี! อย่าลังเลที่จะถามคำถามใดๆกับผม/ดิฉัน",
                "ยินดีต้อนรับ! ผม/ดิฉันจะช่วยคุณได้อย่างไร?"
            ]
        },
        "zh": {
            "patterns": [
                "你好", "早上好", "下午好", "晚上好", "嗨", "您好", 
                "喂", "吃了吗", "最近怎么样"
            ],
            "responses": [
                "你好！今天我能帮你什么忙？",
                "您好！你想了解什么？",
                "嗨！有什么问题都可以问我。",
                "欢迎！我能为您做些什么？"
            ]
        },
        "zh-tw": {
            "patterns": [
                "你好", "早安", "午安", "晚安", "嗨", "您好", 
                "喂", "吃飯了嗎", "最近如何"
            ],
            "responses": [
                "你好！今天我能幫你什麼忙？",
                "您好！你想了解什麼？",
                "嗨！有什麼問題都可以問我。",
                "歡迎！我能為您做些什麼？"
            ]
        },
        "ja": {
            "patterns": [
                "こんにちは", "おはよう", "こんばんは", "やあ", "どうも", 
                "おげんきですか", "元気", "調子はどう"
            ],
            "responses": [
                "こんにちは！今日はどのようにお手伝いできますか？",
                "やあ！何を知りたいですか？",
                "こんにちは！どうぞ、何でも質問してください。",
                "ようこそ！どのようにお手伝いできますか？"
            ]
        },
        "ko": {
            "patterns": [
                "안녕하세요", "안녕", "좋은 아침", "좋은 오후", "좋은 저녁", 
                "어떻게 지내세요", "잘 지내요", "반갑습니다"
            ],
            "responses": [
                "안녕하세요! 오늘 어떻게 도와드릴까요?",
                "안녕! 무엇을 알고 싶으신가요?",
                "안녕하세요! 언제든지 질문해 주세요.",
                "환영합니다! 어떻게 도와드릴까요?"
            ]
        },
        "vi": {
            "patterns": [
                "xin chào", "chào", "chào buổi sáng", "chào buổi chiều", "chào buổi tối", 
                "bạn khỏe không", "khỏe không", "dạo này thế nào"
            ],
            "responses": [
                "Xin chào! Hôm nay tôi có thể giúp gì cho bạn?",
                "Chào bạn! Bạn muốn biết điều gì?",
                "Xin chào! Đừng ngần ngại hỏi tôi bất cứ điều gì.",
                "Chào mừng! Tôi có thể giúp gì cho bạn?"
            ]
        },
        "id": {
            "patterns": [
                "halo", "hai", "selamat pagi", "selamat siang", "selamat sore", "selamat malam", 
                "apa kabar", "bagaimana kabarmu"
            ],
            "responses": [
                "Halo! Bagaimana saya bisa membantu Anda hari ini?",
                "Hai! Apa yang ingin Anda ketahui?",
                "Halo! Jangan ragu untuk bertanya apa saja kepada saya.",
                "Selamat datang! Bagaimana saya bisa membantu Anda?"
            ]
        },
        "ms": {
            "patterns": [
                "hai", "hello", "selamat pagi", "selamat tengahari", "selamat petang", "selamat malam", 
                "apa khabar", "macam mana khabar"
            ],
            "responses": [
                "Hai! Bagaimana saya boleh bantu anda hari ini?",
                "Hello! Apa yang anda ingin tahu?",
                "Hai! Jangan ragu untuk bertanya apa-apa kepada saya.",
                "Selamat datang! Bagaimana saya boleh bantu anda?"
            ]
        },
        "sw": {
            "patterns": [
                "jambo", "hujambo", "habari", "habari ya asubuhi", "habari ya mchana", 
                "habari ya jioni", "hujambo", "vipi"
            ],
            "responses": [
                "Jambo! Nawezaje kukusaidia leo?",
                "Hujambo! Ungependa kujua nini?",
                "Habari! Usisite kuniuliza swali lolote.",
                "Karibu! Nawezaje kukusaidia?"
            ]
        },
        "ha": {
            "patterns": [
                "sannu", "barka", "barka da safiya", "barka da rana", "barka da yamma", 
                "yaya kake", "yaya kike", "yaya lafiya"
            ],
            "responses": [
                "Sannu! Yaya zan taimaka maka yau?",
                "Barka! Mene ne kake son sanin?",
                "Sannu! Kada ka ji kunyar tambayar ta kowane tambaya.",
                "Barka da zuwa! Yaya zan taimaka maka?"
            ]
        },
        "ig": {
            "patterns": [
                "ndewo", "kedu", "nnọọ", "kedu ụtụtụ", "kedu ehihie", "kedu anyasị", 
                "kedu ka ị mere", "ị pụtara"
            ],
            "responses": [
                "Ndewo! Olee otú m ga-esi nyere gị aka taa?",
                "Kedu! Kedu ihe ị chọrọ ịma?",
                "Nnọọ! Ajụkwala ịjụ m ajụjụ ọ bụla.",
                "Nnọọ! Olee otú m ga-esi nyere gị aka?"
            ]
        },
        "ak": {
            "patterns": [
                "akwaaba", "ɛte sɛn", "maakye", "maaha", "maadwo", 
                "wo ho te sɛn", "sɛn"
            ],
            "responses": [
                "Akwaaba! Ɛbɛn na metumi aboa wo ɛnnɛ?",
                "Ɛte sɛn! Dɛn na wopɛ sɛ wohu?",
                "Akwaaba! Nsuro mma wo mmbisa me biribiara.",
                "Akwaaba! Ɛbɛn na metumi aboa wo?"
            ]
        },
        "tw": {
            "patterns": [
                "akwaaba", "ɛte sɛn", "maakye", "maaha", "maadwo", 
                "wo ho te sɛn", "sɛn"
            ],
            "responses": [
                "Akwaaba! Ɛbɛn na metumi aboa wo ɛnnɛ?",
                "Ɛte sɛn! Dɛn na wopɛ sɛ wohu?",
                "Akwaaba! Nsuro mma wo mmbisa me biribiara.",
                "Akwaaba! Ɛbɛn na metumi aboa wo?"
            ]
        },
        "sd": {
            "patterns": [
                "سلام", "السلام عليڪم", "صبح جو سلام", "شام جو سلام", 
                "ڪيئن آهيو", "حال ڪيئن آهي", "ڇا حال آهي"
            ],
            "responses": [
                "سلام! آئون اڄ توهان جي ڪيئن مدد ڪري سگھان ٿو؟",
                "السلام عليڪم! توهان ڇا ڄاڻڻ چاهيو ٿا؟",
                "سلام! مون کان ڪجھ به پڇڻ ۾ جھجھڪ نه ڪريو.",
                "ڀليڪار! آئون توهان جي ڪيئن مدد ڪري سگھان ٿو؟"
            ]
        },
        "ps": {
            "patterns": [
                "سلام", "السلام عليکم", "صبح پخير", "ماښام پخير", 
                "څنګه ياست", "څه حال دی", "ستړی مشئ"
            ],
            "responses": [
                "سلام! زه نن څنګه ستاسو سره مرسته کولی شم؟",
                "السلام عليکم! تاسو څه غواړئ وپوهيږئ؟",
                "سلام! له ما څخه د هر ډول پوښتنې پوښتلو څخه مه ويريږئ.",
                "ښه راغلاست! زه څنګه ستاسو سره مرسته کولی شم?"
            ]
        }
    }

    def handle_greeting(self, message, specified_language=None):
        """
        Checks if a message matches a greeting pattern in a specific language or any supported language.
        Returns a random appropriate response in the matched language if it's a greeting.
        
        Args:
            message (str): The message text to analyze
            specified_language (str, optional): Language code to restrict matching to a specific language
            
        Returns:
            str or None: A greeting response in the appropriate language if matched, otherwise None
        """
        # Convert message to lowercase for case-insensitive matching
        message_lower = message.lower()
        
        # If a specific language is provided, only check patterns for that language
        if specified_language and specified_language in self.greeting_responses:
            for pattern in self.greeting_responses[specified_language]['patterns']:
                if re.search(rf'\b{pattern}\b', message_lower, re.IGNORECASE):
                    # Return a random response in the matched language
                    return random.choice(self.greeting_responses[specified_language]['responses'])
            
            # No match found in the specified language
            return None
        
       
        # No greeting pattern matched in any language
        return None


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
    



   

    def get_no_results_message(self, language_code):
        """
        Returns a random 'no results' message in the specified language.
        Falls back to English if the language code isn't supported.
        
        Args:
            language_code (str): The language code (e.g., 'en', 'fr', 'es')
            
        Returns:
            str: A randomly selected 'no results' message in the appropriate language
        """
        # Get the lowercase language code, strip any region-specific part if not directly supported
        lang = language_code.lower()
        
        # If the specific language code isn't found, try the base language code
        if lang not in self.no_results_responses and '-' in lang:
            lang = lang.split('-')[0]
        
        # Default to English if language not supported
        if lang not in self.no_results_responses:
            lang = 'en'
        
        # Select a random message from the list of messages for this language
        return random.choice(self.no_results_responses[lang])


