# دفتر النجوم — فهرس مرجعي

هذا الفهرس يحول 140+ مستودع GitHub إلى بنية قابلة للاستعلام. كل مدخل موسوم بـ:
- الطبقة: ECON|MEM|SKILL|CTX|ORCH|WORLD|GOV|MOB|MEDIA|INFRA
- الرتبة: S (اعتمد الآن) | A (قريباً) | B (معزل) | C (مرجع) | X (ممنوع)

## 1) نواة الوكلاء (ORCH)
- hermes-agent (S): نواة Hermes
- hermes-operator-kit (S): kit مشغّل حاسوب بأمر واحد
- hermes-workspace (S): واجهة ويب أصلية
- oh-my-hermes (A): harness dag-ulw
- LiveAgent (A): سطح وكيل local-first
- mission-control (S): plane تحكم مستضاف ذاتياً

## 2) بوابة الاقتصاد (ECON)
- omniroute (S): بوابة متعددة المزودين بتوجيه وكاش وسياسات
- freellmapi (A): 7.4B tokens/شهر، 34 مزوداً
- free-claude-code (A): 1.3B+ tokens مجانية
- freebuff (A): وكيل مجاني ممول بالإعلانات
- tokscale (S): تتبع tokens عبر الوكلاء
- Bello (A): 3x استخدام بنفس الجودة

## 3) المهارات (SKILL)
- agents.md (S): تنسيق مفتوح لتوجيه وكلاء الترميز
- mattpocock/skills (S): مهارات مهندس حقيقي
- addyosmani/agent-skills (S): مهارات هندسة إنتاجية
- ponytail (S): اقتضاب مخرجات العمل الآلي
- humanizer (S): إزالة بصمات الكتابة الآلية
- graphify (S): knowledge graph للكودبيس

## 4) الذاكرة والسياق (MEM/CTX)
- hindsight (S): ذاكرة وكيل تتعلم عبر الجلسات
- repomix (S): حزم المستودع بملف واحد
- mcp-obsidian (S): MCP لقراءة/كتابة Obsidian

## 5) واجهة العالم (WORLD)
- Agent-Reach (S): قنوات منصات مسوّرة وفيديو وصينية
- obscura (B): متصفح headless للوكلاء

## 6) البنية (INFRA)
- databasement (S): مدير نسخ احتياطي لقواعد البيانات
- OfficeCLI (S): suite مكتبية للوكلاء
- colab-mcp (A): MCP لتشغيل Google Colab

## 7) الموبايل (MOB)
- termux (S): طرفية وخادم X على Android
- DroidDesk (A): هاتفك سطح Linux كامل

## 8) الأمن (GOV)
- strix (A): اختبار اختراق AI مفتوح
- T3MP3ST (B): منصة red teaming هجومية

## 9) ممنوع (X)
- qwencloud-generator: حصاد مفاتيح بتسجيل آلي
- تسريبات prompts لكسر أنظمة إنتاج
- MITM على حركة لا تملكها

## قاعدة الاستخدام
- S-tier: ثبّت في النواة، استخدم يومياً
- A-tier: ثبّت عند الحاجة الفعلية فقط
- B-tier: مختبر معزول (جهاز/حساب/شبكة منفصلة)
- C-tier: مرجع للقراءة فقط، لا تشغيل
- X-tier: ممنوع صراحة، لا تثبيت ولا استخدام

## كيفية الاستعلام
عند الحاجة لأداة، اقرأ:
C:\agent-work\policies\STARRED_REGISTRY.jsonl
وابحث عن الحقل "name" للحصول على: layer, tier, role, rule, install_notes.
