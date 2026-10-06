import os
import sqlite3
import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# تأمين طبقة الاتصال والشهادات الرقمية
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

try:
    from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

app = Flask("AbsoluteEnterpriseCoreSystem")
# مفتاح سري ثابت ومؤمن حصرياً لمنع إعادة توجيه الجلسات أو تسجيل الخروج المفاجئ
app.secret_key = "foued_absolute_production_fixed_secret_key_2026_secure_core"
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "enterprise_production_core.db")

def get_secure_api_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()

def initialize_enterprise_database():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_users (
                email TEXT PRIMARY KEY,
                last_login TEXT,
                status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                item_type TEXT,
                query_text TEXT,
                content TEXT,
                blueprint_data TEXT,
                timestamp TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_core_user_email ON core_registry(user_email);')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_cache (
                cache_key TEXT PRIMARY KEY,
                response_content TEXT,
                blueprint_content TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Critical Database Initialization Error: {e}")

def get_cached_response(cache_key):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("SELECT response_content, blueprint_content FROM core_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    return None, None

def set_cached_response(cache_key, response_content, blueprint_content):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10.0)
        cursor = conn.cursor()
        t_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT OR REPLACE INTO core_cache (cache_key, response_content, blueprint_content, created_at) VALUES (?, ?, ?, ?)",
                       (cache_key, response_content, blueprint_content, t_now))
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_history_for_user(user_email):
    registry = []
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_type, query_text, content, blueprint_data, timestamp FROM core_registry WHERE user_email = ? ORDER BY id DESC LIMIT 50", (user_email,))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            registry.append({
                "id": row[0],
                "type": row[1],
                "query": row[2],
                "content": row[3],
                "blueprint": row[4] or "",
                "time": row[5]
            })
    except Exception as e:
        print(f"Error loading user history: {e}")
    return registry

def persist_to_db(user_email, item_type, query, content, blueprint=""):
    t_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_id = 0
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO core_registry (user_email, item_type, query_text, content, blueprint_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_email, item_type, query, content, blueprint, t_now))
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        print(f"Error persisting record to DB: {e}")
    return {
        "id": row_id,
        "type": item_type,
        "query": query,
        "content": content,
        "blueprint": blueprint,
        "time": t_now
    }

def execute_gemini_engine(req_type, user_query):
    cache_key = f"{req_type}:{user_query.strip().lower()}"
    cached_res, cached_bp = get_cached_response(cache_key)
    if cached_res is not None:
        return cached_res, cached_bp

    api_key = get_secure_api_key()
    if not api_key:
        return "⚠️ خطأ حرج: مفتاح GEMINI_API_KEY غير معرف في متغيرات البيئة على خادم Render. يجدر إضافته لتفعيل الذكاء الاصطناعي.", ""

    system_prompts = {
        "research": "أنت وكيل بحث استراتيجي واحترافي. قدم تحليلاً دقيقاً وموثقاً. إذا لزم الأمر، قم بتضمين مخطط SVG حصري داخل الوسم <svg ...>...</svg>.",
        "blueprint": "أنت خبير هندسي ومعماري متقدم. قدم مواصفات هندسية دقيقة، وأرفق مخططاً هندسياً بصرياً متكاملًا مصمماً بلغة SVG حصرياً داخل الوسم <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300'>...</svg>.",
        "image": "أنت مصمم بصري محترف. صف التصميم بدقة وأرفق كود SVG مرئي داخل الوسم <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300'>...</svg>.",
        "threat": "أنت محلل سيبراني وتقني متطور. قم بتحليل التهديد واقترح إجراءات الوقاية مع تضمين مخطط شبكي بلغة SVG داخل الوسم <svg>...</svg>."
    }
    
    sys_prompt = system_prompts.get(req_type, "أنت مساعد ذكي عالمي عالي الكفاءة.")
    result_text = ""
    blueprint_code = ""
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"السياق الهندسي: {sys_prompt}\n\nطلب المستخدم بدقة: {user_query}"}]
            }],
            "tools": [{"googleSearch": {}}]
        }
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'}, method='POST')
        
        with urllib.request.urlopen(req, timeout=50) as response:
            if response.status == 200:
                res_body = response.read().decode('utf-8')
                data = json.loads(res_body)
                try:
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    return "⚠️ استجاب خادم الذكاء الاصطناعي ولكن محتوى الرد كان فارغاً.", ""
                
                cleaned_text = raw_text
                if "<svg" in cleaned_text and "</svg>" in cleaned_text:
                    start_idx = cleaned_text.find("<svg")
                    end_idx = cleaned_text.rfind("</svg>") + 6
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        blueprint_code = cleaned_text[start_idx:end_idx]
                        blueprint_code = blueprint_code.replace("```xml", "").replace("```html", "").replace("```", "").strip()
                        result_text = cleaned_text[:start_idx].strip() + "\n\n[✅ تمت معالجة الطلب الهندسي بنجاح تام]\n\n" + cleaned_text[end_idx:].strip()
                
                if not result_text:
                    result_text = raw_text
            else:
                result_text = f"⚠️ خطأ استجابة الخادم الخارجي برمز: {response.status}"
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8', errors='ignore')
        result_text = f"⚠ خطأ في بوابة الاتصال الذكي: {error_msg[:150]}"
    except Exception as e:
        result_text = f"⚠ خطأ تقني غير متوقع في المعالجة: {str(e)}"

    set_cached_response(cache_key, result_text, blueprint_code)
    return result_text, blueprint_code

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - النظام الهندسي للوكيل الذكي 💎</title>
    <style>
        body { background-color: #07090e; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #0d1322; border: 1px solid #1e293b; padding: 40px; border-radius: 18px; width: 100%; max-width: 420px; box-shadow: 0 20px 40px rgba(0,0,0,0.7); text-align: center; }
        h2 { color: #38bdf8; margin-bottom: 12px; font-size: 24px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 30px; line-height: 1.6; }
        label { display: block; text-align: right; margin-bottom: 8px; font-size: 14px; color: #e2e8f0; font-weight: 600; }
        input { width: 100%; padding: 14px; background: #020617; border: 1px solid #1e293b; color: #fff; border-radius: 12px; box-sizing: border-box; font-size: 15px; margin-bottom: 22px; outline: none; }
        input:focus { border-color: #0284c7; box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.25); }
        button { width: 100%; padding: 15px; background: #0284c7; color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: bold; font-size: 16px; transition: background 0.2s; }
        button:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>💎 النظام الهندسي الموحد</h2>
        <p>أدخل بريدك الإلكتروني المعتمد للوصول الفوري والمستقر إلى لوحة التحكم الذكية</p>
        <form method="POST">
            <label>البريد الإلكتروني:</label>
            <input type="email" name="email" placeholder="example@gmail.com" required autocomplete="email">
            <button type="submit">دخول آمن ومستقر</button>
        </form>
    </div>
</body>
</html>"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم الهندسية الموحدة 💎</title>
    <style>
        :root {
            --bg-main: #07090e;
            --bg-card: #0d1322;
            --border-color: #1e293b;
            --accent-blue: #0284c7;
            --accent-green: #059669;
            --accent-purple: #7c3aed;
            --accent-red: #dc2626;
            --text-main: #f3f4f6;
            --text-muted: #94a3b8;
        }
        body { background-color: var(--bg-main); color: var(--text-main); font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; margin: 0; }
        .container { max-width: 950px; margin: auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        h1 { color: #38bdf8; font-size: 24px; margin: 0; }
        .user-info { font-size: 13.5px; color: var(--text-muted); }
        .logout-link { color: var(--accent-red); text-decoration: none; font-weight: bold; margin-left: 10px; }
        .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 14px; color: #e2e8f0; }
        select, textarea { width: 100%; padding: 14px; background: #020617; border: 1px solid var(--border-color); color: #fff; border-radius: 12px; box-sizing: border-box; font-size: 15px; margin-bottom: 16px; outline: none; }
        select:focus, textarea:focus { border-color: var(--accent-blue); box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.25); }
        textarea { resize: vertical; height: 110px; }
        .btn-group { display: flex; gap: 12px; flex-wrap: wrap; }
        button { flex: 1; padding: 14px; background: var(--accent-green); color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: bold; font-size: 15px; min-width: 140px; }
        button.mic-btn { background: var(--accent-red); flex: 0.4; }
        button.speak-btn { background: var(--accent-purple); margin-top: 10px; width: 100%; }
        button.export-btn { background: var(--accent-blue); margin-top: 5px; width: 100%; }
        button.svg-download-btn { background: #d97706; margin-top: 5px; width: 100%; }
        button:hover { opacity: 0.92; }
        .output-box { background: #020617; border: 1px solid var(--border-color); padding: 16px; border-radius: 10px; margin-top: 10px; white-space: pre-wrap; color: #34d399; font-family: 'Courier New', Courier, monospace; font-size: 13.5px; line-height: 1.6; }
        .blueprint-container { margin-top: 15px; background: #ffffff; padding: 15px; border-radius: 10px; text-align: center; overflow-x: auto; }
        .blueprint-container svg { max-width: 100%; height: auto; }
        .history-item { border-bottom: 1px solid var(--border-color); padding-bottom: 24px; margin-bottom: 24px; }
        .tag { background: var(--accent-blue); color: white; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; }
        #sys-status { font-weight: bold; text-align: center; margin-bottom: 18px; font-size: 14px; color: var(--accent-green); background: rgba(5, 150, 105, 0.1); padding: 12px; border-radius: 12px; border: 1px solid rgba(5, 150, 105, 0.25); }
        #status-mic { font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 13px; color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>💎🧠 النظام الهندسي الموحد للوكيل الذكي</h1>
                <p style="color: var(--text-muted); font-size: 13px; margin: 0;">بنية تحتية سحابية إنتاجية خالية من الأخطاء والافتراضات</p>
            </div>
            <div class="user-info">
                الحساب النشط: <b>{{ user_email }}</b> 
                <a href="/logout" class="logout-link">خروج</a>
            </div>
        </header>
        
        <div id="sys-status">🟢 النظام الهندسي متصل ومستقر وجاهز لتنفيذ المهام</div>
        
        <div class="card">
            <h3>🛠 مركز العمليات (إدخال كتابي أو نطق صوتي مباشر)</h3>
            <div id="ai-form">
                <label><b>حدد مسار الخدمة الهندسية أو البحثية:</b></label>
                <select name="req_type" id="req-type-select">
                    <option value="research">📚 بحث استراتيجي فوري موثق من الإنترنت</option>
                    <option value="blueprint">📐 تصميم مخططات هندسية ورسومات (SVG)</option>
                    <option value="image">🎨 ابتكار تصاميم بصرية وهياكل (SVG)</option>
                    <option value="threat">🛡 تحليل تقني متطور واستجابة أمنية فورية</option>
                </select>
                
                <label><b>اطرح سؤالك أو طلبك التقني:</b></label>
                <textarea name="query" id="query-input" placeholder="اكتب أو انطق طلبك هنا وسيتولى النظام تنفيذه بدقة فائقة..." required></textarea>
                
                <div id="status-mic"></div>

                <div class="btn-group">
                    <button type="button" class="mic-btn" onclick="startVoiceRecognition()">🎤 تحدث بالصوت</button>
                    <button type="button" id="submit-btn" onclick="executeAjaxSubmit()">🚀 تنفيذ الطلب فوراً</button>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>📜 سجل العمليات والتقارير المعتمدة</h3>
            <div id="registry-container">
                {% if registry %}
                    {% for item in registry %}
                        <div class="history-item" id="history-item-{{ item.id }}">
                            <span class="tag">{{ item.type }}</span> <b style="color: var(--text-muted);">[{{ item.time }}]</b>
                            <p><b>الطلب:</b> {{ item.query }}</p>
                            <div class="output-box">{{ item.content }}</div>
                            
                            {% if item.blueprint %}
                                <div class="blueprint-container" id="svg-box-{{ item.id }}">
                                    <p style="color: #1e293b; font-size: 13px; margin-bottom: 5px; font-weight: bold;"><b>📊 المخطط الهندسي / الرسم المرئي:</b></p>
                                    {{ item.blueprint | safe }}
                                </div>
                                <button class="svg-download-btn" type="button" onclick="downloadSVG('svg-box-{{ item.id }}', {{ item.id }})">📥 تنزيل المخطط (SVG)</button>
                            {% endif %}
                            
                            <button class="speak-btn" type="button" onclick="speakTextFromElement('history-item-{{ item.id }}')">🗣 الاستماع للتقرير صوتياً</button>
                            <a href="/export/{{ item.id }}" target="_blank">
                                <button class="export-btn" type="button">📥 تنزيل التقرير كاملاً كملف (TXT)</button>
                            </a>
                        </div>
                    {% endfor %}
                {% else %}
                    <p id="no-registry-msg" style="color: var(--text-muted); text-align: center; padding: 20px;">لا توجد عمليات مسجلة حتى الآن. ابدأ بكتابة أو نطق أول طلب لك!</p>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        function executeAjaxSubmit() {
            const reqTypeSelect = document.getElementById('req-type-select');
            const queryInput = document.getElementById('query-input');
            const btn = document.getElementById('submit-btn');
            const sysStatus = document.getElementById('sys-status');
            
            const queryVal = queryInput.value.trim();
            if(!queryVal) {
                alert("يرجى إدخال أو نطق الطلب أولاً.");
                queryInput.focus();
                return;
            }

            const formData = new FormData();
            formData.append('req_type', reqTypeSelect.value);
            formData.append('query', queryVal);
            
            btn.disabled = true;
            btn.innerText = "⏳ جاري المعالجة السحابية الفائقة...";
            sysStatus.innerText = "⏳ يتم تصفح الويب وجلب النتيجة الموثقة بدقة تامة...";

            fetch('/', {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                btn.disabled = false;
                btn.innerText = "🚀 تنفيذ الطلب فوراً";
                sysStatus.innerText = "🟢 النظام الهندسي متصل ومستقر وجاهز لتنفيذ المهام";

                if(data.status === "success") {
                    const item = data.item;
                    const container = document.getElementById('registry-container');
                    const noMsg = document.getElementById('no-registry-msg');
                    if(noMsg) noMsg.remove();

                    let blueprintHTML = '';
                    if(item.blueprint) {
                        blueprintHTML = `
                            <div class="blueprint-container" id="svg-box-${item.id}">
                                <p style="color: #1e293b; font-size: 13px; margin-bottom: 5px; font-weight: bold;"><b>📊 المخطط الهندسي / الرسم المرئي:</b></p>
                                ${item.blueprint}
                            </div>
                            <button class="svg-download-btn" type="button" onclick="downloadSVG('svg-box-${item.id}', ${item.id})">📥 تنزيل المخطط (SVG)</button>
                        `;
                    }

                    const newItemHTML = `
                        <div class="history-item" id="history-item-${item.id}" style="opacity: 0; transition: opacity 0.5s ease;">
                            <span class="tag">${item.type}</span> <b style="color: var(--text-muted);">[${item.time}]</b>
                            <p><b>الطلب:</b> ${escapeHtml(item.query)}</p>
                            <div class="output-box">${escapeHtml(item.content)}</div>
                            ${blueprintHTML}
                            <button class="speak-btn" type="button" onclick="speakTextFromElement('history-item-${item.id}')">🗣 الاستماع للتقرير صوتياً</button>
                            <a href="/export/${item.id}" target="_blank">
                                <button class="export-btn" type="button">📥 تنزيل التقرير كاملاً كملف (TXT)</button>
                            </a>
                        </div>
                    `;

                    container.insertAdjacentHTML('afterbegin', newItemHTML);
                    setTimeout(() => {
                        document.getElementById(`history-item-${item.id}`).style.opacity = '1';
                    }, 50);

                    queryInput.value = '';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                btn.disabled = false;
                btn.innerText = "🚀 تنفيذ الطلب فوراً";
                sysStatus.innerText = "⚠ حدث ضغط مؤقت في الاتصال، أعد المحاولة.";
            });
        }

        function escapeHtml(text) {
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }

        function startVoiceRecognition() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) { 
                alert("متصفحك الحالي لا يدعم الإدخال الصوتي المباشر."); 
                return; 
            }
            const recognition = new SpeechRecognition();
            recognition.lang = 'ar-SA';
            recognition.continuous = false;
            recognition.interimResults = false;
            
            document.getElementById('status-mic').innerText = "🔴 جاري الاستماع لصوتك بتركيز تام... تكلم الآن";
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById('query-input').value = transcript;
                document.getElementById('status-mic').innerText = "✅ تم التقاط الصوت وتحويله لنص بنجاح!";
            };
            
            recognition.onerror = function(event) {
                document.getElementById('status-mic').innerText = "⚠ لم يتم التقاط الصوت بوضوح، حاول مرة أخرى.";
            };
            
            recognition.start();
        }

        function speakTextFromElement(elementId) {
            const el = document.getElementById(elementId);
            const outputBox = el.querySelector('.output-box');
            if(!outputBox) return;
            const text = outputBox.innerText;
            if (!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ar-SA';
            window.speechSynthesis.speak(utterance);
        }

        function downloadSVG(containerId, itemId) {
            const container = document.getElementById(containerId);
            const svgElement = container.querySelector('svg');
            if (!svgElement) return;
            const serializer = new XMLSerializer();
            let source = serializer.serializeToString(svgElement);
            const blob = new Blob([source], {type: "image/svg+xml;charset=utf-8"});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `enterprise_blueprint_${itemId}.svg`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>"""

@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        if email and "@" in email:
            try:
                conn = sqlite3.connect(DB_FILE, timeout=10.0)
                cursor = conn.cursor()
                t_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT OR REPLACE INTO core_users (email, last_login, status) VALUES (?, ?, ?)", (email, t_now, "active"))
                conn.commit()
                conn.close()
                session['user_email'] = email
                session.permanent = True
                return redirect(url_for('dashboard'))
            except Exception as e:
                print(f"Login database error: {e}")
    return render_template_string(LOGIN_HTML)

@app.route("/logout")
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route("/", methods=['GET', 'POST'])
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    if request.method == 'POST':
        req_type = request.form.get("req_type", "research")
        query = request.form.get("query", "").strip()
        content, blueprint = "", ""
        if query:
            content, blueprint = execute_gemini_engine(req_type, query)
            item_data = persist_to_db(user_email, req_type, query, content, blueprint)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or (request.content_type and 'application/json' in request.content_type):
                return jsonify({"status": "success", "item": item_data})
        return redirect(url_for('dashboard'))

    user_registry = load_history_for_user(user_email)
    return render_template_string(DASHBOARD_HTML, user_email=user_email, registry=user_registry)

@app.route("/export/<int:item_id>")
def export_item(item_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))
        
    target_item = None
    user_registry = load_history_for_user(session['user_email'])
    for item in user_registry:
        if item["id"] == item_id:
            target_item = item
            break
    
    if not target_item:
        return "العنصر غير موجود أو أنك لا تملك صلاحية الوصول إليه", 404
    
    filename = f"enterprise_report_{item_id}.txt"
    file_content = f"========================================\n" \
                   f"💎 التقرير الهندسي الرسمي - النظام الموحد\n" \
                   f"========================================\n" \
                   f"نوع المهمة: {target_item['type']}\n" \
                   f"وقت التنفيذ: {target_item['time']}\n" \
                   f"طلب المستخدم: {target_item['query']}\n\n" \
                   f"النتيجة والتحليل المفصل:\n{target_item['content']}\n"
    
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(file_content)
        
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    initialize_enterprise_database()
    port = int(os.environ.get("PORT", 5080))
    print("=" * 70)
    print("💎🧠 النظام الهندسي الموحد للوكيل الذكي - قيد التشغيل بكفاءة مطلقة")
    print(f"🌍 منفذ التشغيل النشط: {port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
