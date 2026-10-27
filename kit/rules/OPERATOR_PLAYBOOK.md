# OPERATOR PLAYBOOK — دروس تشغيل واجهات ويندوز 11

1) تطبيقات ويندوز 11 قد تكون حزمية (مثل Notepad): العملية المُطلقة قد لا تملك أي نافذة. تتبع دائما العملية ذات النافذة عبر win_app_ops.app_pids. لا تثق بـ PID عملية Popen.
2) المفكرة تستعيد الجلسة السابقة بمحتوى قديم. بعد كل إطلاق نفّذ: safe_gui_ctl.py clear <key> قبل أي إدخال نص.
3) إدخال النص يكون فقط عبر الحافظة: safe_gui_ctl.py type <key> <text> (نقرة حقيقية في منتصف النافذة ثم Ctrl+V). ممنوع SendInput حرفا بحرف للنصوص.
4) التحقق يكون فقط عبر: safe_gui_ctl.py verify <key> <expected> لأنه يضع حاجز VERIFY_SENTINEL في الحافظة قبل Ctrl+A وCtrl+C. MATCH=true مقبولة فقط إذا كان READ مساويا للنص المتوقع وليس الحاجز.
5) جلب التركيز عبر restore_and_focus (AttachThreadInput). خدعة Alt ملاذ أخير فقط لأنها تسلّح القوائم.
6) الإغلاق فقط عبر WM_CLOSE من safe_gui_ctl.py close <key>. ممنوع taskkill أو terminate أو kill.
7) كل عمليات الواجهة لتطبيقات المسجل تكون فقط عبر: C:/agent-work/lib/safe_gui_ctl.py بالأوامر: list, status, launch, clear, type, verify, close, test.
8) الدليل قبل الإنجاز: أي ادعاء واجهة يجب أن يحمل واحدا على الأقل: verify MATCH=true، أو لقطة شاشة مع قراءة رؤية لعدّاد الأحرف، أو قراءة ملف. ممنوع ترك حقول التقرير مثل SCREENSHOT_SENT فارغة: املأها yes أو no دائما.
9) computer_use用途: لقطات الشاشة، النقر خارج نطاق ctl، قراءة حالة الواجهة. terminal用途: أوامر ctl، عمليات الملفات، الفحوص.
10) توقع دورتين: بوابة محلية ثم تنفيذ المهمة؛ كلتاهما تفتح وتغلق التطبيق. تكرار المشاهد عند المستخدم طبيعي.
11) إذا أرجع أي أمر ctl نتيجة FAIL: توقف، أرسل الخرج الخام، ولا ترتجل تلاعب واجهة بديلا.
12) ممنوع لمس: model، provider، Omniroute، OpenRouter، مفاتيح API، /model.
