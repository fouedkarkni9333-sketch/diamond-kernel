import os
import sqlite3
import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# تخطي فحص شهادات الأمان لتجنب تعليق الاتصال
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

try:
    from flask import Flask, render_template_string, request, redirect, url_for, send_file, session, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

app = Flask("DiamondAgentGlobalPro")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "diamond_global_ultra_secure_agent_2026")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "diamond_agent_pro.db")

def initialize_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                item_type TEXT,
                query_text TEXT,
                content TEXT,
                blueprint_data TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠ خطأ في تهيئة قاعدة البيانات: {e}")

def load_history_for_user(user_email):
    registry = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_type, query_text, content, blueprint_data, timestamp FROM agent_registry WHERE user_email = ? ORDER BY id DESC LIMIT 50", (user_email,))
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
        print(f"⚠️ خطأ في تحميل السجل: {e}")
    return registry

def persist_to_db(user_email, item_type, query, content, blueprint=""):
    t_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_id = 0
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_registry (user_email, item_type, query_text, content, blueprint_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_email, item_type, query, content, blueprint, t_now))
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        print(f"⚠️ خطأ الحفظ في القاعدة: {e}")
        
    return {
        "id": row_id,
        "type": item_type,
        "query": query,
        "content": content,
        "blueprint": blueprint,
        "time": t_now
    }

def generate_ai_agent_response(req_type, user_query):
    result_text = ""
    blueprint_code = ""
    
    system_instructions = {
        "research": "أنت وكيل بحث استراتيجي ذكي وعالمي المستوى. قم بالبحث العميق والتحليل الشامل ودعم الإجابة بالأدلة والمعلومات الحية الحديثة. إذا تطلب الأمر مخططاً أو هيكلاً مرئياً، قم بتضمين كود SVG صحيح وجميل داخل الوسم <svg ...>...</svg>.",
        "blueprint": "أنت خبير هندسي ومعماري عالمي. قدم تفاصيل هندسية دقيقة، ويجب إرفاق مخطط هندسي مرئي كامل مصمم بلغة SVG حصرياً داخل الوسم <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300'>...</svg>.",
        "image": "أنت مصمم بصري متقدم. صف التصميم بدقة تامة، وتضمن إجابتك كود SVG مرئي يعبر عن التصميم داخل الوسم <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300'>...</svg>.",
        "threat": "أنت محلل أمني وسيبراني متطور. قم بتحليل التهديد المرصود واقترح خطوات الفحص مع تضمين مخطط شبكي أو مسار هجومي بلغة SVG داخل الوسم <svg>...</svg>."
    }
    
    sys_prompt = system_instructions.get(req_type, "أنت مساعد ذكي وعالمي متخصص.")
    
    # استخدام مفتاح الخادم التلقائي بحيث لا يُطلب من المستخدم إدخال أي مفتاح يدوي
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not api_key:
        return "⚠️ تنبيه من النظام: مفتاح الـ API غير مُعد على الخادم. يرجى ضبط المتغير البيئي GEMINI_API_KEY.", ""

    try:
        # استخدام نموذج gemini-1.5-flash مع تفعيل أداة البحث الحي (Google Search Grounding)
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"التوجيه السياقي: {sys_prompt}\n\nطلب المستخدم والبحث المطلوب: {user_query}"}]
            }],
            "tools": [{"googleSearch": {}}] # تفعيل الوكيل للبحث الحي في الإنترنت لحظياً
        }
        
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'}, method='POST')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            if response.status == 200:
                res_body = response.read().decode('utf-8')
                data = json.loads(res_body)
                
                try:
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    return "⚠️ استجاب الخادم ولكن المحتوى عاد فارغاً أو تم حظره بواسطة سياسة الأمان.", ""
                
                cleaned_text = raw_text
                if "<svg" in cleaned_text and "</svg>" in cleaned_text:
                    start_idx = cleaned_text.find("<svg")
                    end_idx = cleaned_text.rfind("</svg>") + 6
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        blueprint_code = cleaned_text[start_idx:end_idx]
                        blueprint_code = blueprint_code.replace("```xml", "").replace("```html", "").replace("```", "").strip()
                        result_text = cleaned_text[:start_idx].strip() + "\n\n[✅ تم تنفيذ البحث الذكي وتوليد المخطط بنجاح]\n\n" + cleaned_text[end_idx:].strip()
                
                if not result_text:
                    result_text = raw_text
            else:
                result_text = f"⚠️ خطأ من الخادم برمز الاستجابة: {response.status}"
    except urllib.error.HTTPError as e:
        error_message = e.read().decode('utf-8', errors='ignore')
        result_text = f"⚠ خطأ API: {error_message[:150]}"
    except urllib.error.URLError as e:
        result_text = f"⚠️ خطأ في الاتصال بالشبكة العالمية."
    except Exception as e:
        result_text = f"⚠ حدث خطأ داخلي في الوكيل: {str(e)}"

    return result_text, blueprint_code

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        if email:
            session['user_email'] = email
            return redirect(url_for('dashboard'))
    
    login_html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>تسجيل الدخول - الوكيل الذكي 💎</title>
        <style>
            body { background-color: #090d16; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-card { background: #111827; border: 1px solid #1f2937; padding: 30px; border-radius: 12px; width: 100%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; }
            h2 { color: #60a5fa; margin-bottom: 20px; }
            input { width: 100%; padding: 14px; background: #030712; border: 1px solid #1f2937; color: #fff; border-radius: 8px; box-sizing: border-box; font-size: 15px; margin-bottom: 15px; outline: none; }
            input:focus { border-color: #3b82f6; }
            button { width: 100%; padding: 14px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 15px; }
            button:hover { opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2>💎 منصة الوكيل الذكي</h2>
            <p style="color: #9ca3af; font-size: 13px; margin-bottom: 20px;">أدخل بريدك الإلكتروني للبدء فوراً دون تعقيد مفاتيح الـ API</p>
            <form method="POST">
                <input type="email" name="email" placeholder="example@gmail.com" required autocomplete="email">
                <button type="submit">دخول إلى النظام</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(login_html)

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
            content, blueprint = generate_ai_agent_response(req_type, query)
            item_data = persist_to_db(user_email, req_type, query, content, blueprint)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or (request.content_type and 'application/json' in request.content_type):
                return jsonify({"status": "success", "item": item_data})
            
        return redirect(url_for('dashboard'))

    user_registry = load_history_for_user(user_email)
    
    html_template = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>منصة الوكيل الذكي الشاملة 💎</title>
        <style>
            :root {
                --bg-main: #090d16;
                --bg-card: #111827;
                --border-color: #1f2937;
                --accent-blue: #3b82f6;
                --accent-green: #10b981;
                --accent-purple: #8b5cf6;
                --accent-red: #ef4444;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
            }
            body { background-color: var(--bg-main); color: var(--text-main); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; margin: 0; }
            .container { max-width: 950px; margin: auto; }
            header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }
            h1 { color: #60a5fa; font-size: 24px; margin: 0; text-shadow: 0 0 15px rgba(59, 130, 246, 0.4); }
            .user-info { font-size: 13px; color: var(--text-muted); }
            .logout-link { color: var(--accent-red); text-decoration: none; font-weight: bold; margin-left: 10px; }
            .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
            label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 14px; color: #d1d5db; }
            
            select, textarea { width: 100%; padding: 14px; background: #030712; border: 1px solid var(--border-color); color: #fff; border-radius: 8px; box-sizing: border-box; font-size: 15px; margin-bottom: 15px; outline: none; transition: all 0.3s ease; }
            select:focus, textarea:focus { border-color: var(--accent-blue); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }
            textarea { resize: vertical; height: 100px; }
            
            .btn-group { display: flex; gap: 12px; }
            button { flex: 1; padding: 14px; background: var(--accent-green); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 15px; transition: all 0.2s; }
            button.mic-btn { background: var(--accent-red); flex: 0.4; }
            button.speak-btn { background: var(--accent-purple); margin-top: 10px; width: 100%; }
            button.export-btn { background: var(--accent-blue); margin-top: 5px; width: 100%; }
            button.svg-download-btn { background: #d97706; margin-top: 5px; width: 100%; }
            button:hover { opacity: 0.92; transform: translateY(-1px); }
            .output-box { background: #030712; border: 1px solid var(--border-color); padding: 15px; border-radius: 8px; margin-top: 10px; white-space: pre-wrap; color: #34d399; font-family: 'Courier New', Courier, monospace; font-size: 13.5px; line-height: 1.6; }
            .blueprint-container { margin-top: 15px; background: #ffffff; padding: 15px; border-radius: 8px; text-align: center; overflow-x: auto; }
            .blueprint-container svg { max-width: 100%; height: auto; }
            .history-item { border-bottom: 1px solid var(--border-color); padding-bottom: 20px; margin-bottom: 20px; }
            .tag { background: var(--accent-blue); color: white; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; }
            #sys-status { font-weight: bold; text-align: center; margin-bottom: 15px; font-size: 14px; color: var(--accent-green); background: rgba(16, 185, 129, 0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2); }
            #status-mic { font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 13px; color: #f87171; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1>💎🧠 منصة الوكيل الذكي الشامل</h1>
                    <p style="color: var(--text-muted); font-size: 13px; margin: 0;">بحث حي، تحليل متقدم، وتوليد ملفات فورية</p>
                </div>
                <div class="user-info">
                    المستخدم: <b>{{ session['user_email'] }}</b> 
                    <a href="/logout" class="logout-link">خروج</a>
                </div>
            </header>
            
            <div id="sys-status">🟢 الوكيل الذكي متصل وجاهز لتنفيذ طلباتك عبر الإنترنت لحظياً</div>
            
            <div class="card">
                <h3>🛠 لوحة توجيه الوكيل</h3>
                <div id="ai-form">
                    <label><b>اختر نمط المهمة:</b></label>
                    <select name="req_type" id="req-type-select">
                        <option value="research">📚 بحث شامل وعميق بالإنترنت والأدلة الحية</option>
                        <option value="blueprint">📐 مخطط هندسي وتصميم هيكلي (SVG)</option>
                        <option value="image">🎨 تصميم وصف ورسومات بصرية (SVG)</option>
                        <option value="threat">🛡 تحليل استراتيجي أو سيبراني متطور</option>
                    </select>
                    
                    <label><b>ماذا تريد من الوكيل أن ينفذ اليوم؟ (اكتب طلبك بالتفصيل):</b></label>
                    <textarea name="query" id="query-input" placeholder="مثال: قم ببحث شامل حول أحدث تقنيات تخزين الطاقة لعام 2026 مع مقارنة الأسعار والأدلة..." required></textarea>
                    
                    <div id="status-mic"></div>

                    <div class="btn-group">
                        <button type="button" class="mic-btn" onclick="startVoiceRecognition()">🎤 إدخال صوتي</button>
                        <button type="button" id="submit-btn" onclick="executeAjaxSubmit()">🚀 تنفيذ الطلب عبر الوكيل</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>📜 سجل المهام والتقارير الجاهزة</h3>
                <div id="registry-container">
                    {% if registry %}
                        {% for item in registry %}
                            <div class="history-item" id="history-item-{{ item.id }}">
                                <span class="tag">{{ item.type }}</span> <b style="color: var(--text-muted);">[{{ item.time }}]</b>
                                <p><b>الطلب:</b> {{ item.query }}</p>
                                <div class="output-box">{{ item.content }}</div>
                                
                                {% if item.blueprint %}
                                    <div class="blueprint-container" id="svg-box-{{ item.id }}">
                                        <p style="color: #1f2937; font-size: 13px; margin-bottom: 5px; font-weight: bold;"><b>📊 المخطط الهندسي / الرسم المرئي:</b></p>
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
                        <p id="no-registry-msg" style="color: var(--text-muted); text-align: center; padding: 20px;">لا توجد مهام مسجلة حتى الآن. اكتب طلبك بالأعلى ودع الوكيل يبدأ!</p>
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
                    alert("يرجى كتابة الطلب أولاً.");
                    queryInput.focus();
                    return;
                }

                const formData = new FormData();
                formData.append('req_type', reqTypeSelect.value);
                formData.append('query', queryVal);
                
                btn.disabled = true;
                btn.innerText = "⏳ الوكيل يقوم بالبحث والتنفيذ الآن...";
                sysStatus.innerText = "⏳ جاري استعراض الإنترنت وجلب أحدث الأدلة والمعلومات...";

                fetch('/', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    btn.disabled = false;
                    btn.innerText = "🚀 تنفيذ الطلب عبر الوكيل";
                    sysStatus.innerText = "🟢 الوكيل الذكي متصل وجاهز لتنفيذ طلباتك عبر الإنترنت لحظياً";

                    if(data.status === "success") {
                        const item = data.item;
                        const container = document.getElementById('registry-container');
                        const noMsg = document.getElementById('no-registry-msg');
                        if(noMsg) noMsg.remove();

                        let blueprintHTML = '';
                        if(item.blueprint) {
                            blueprintHTML = `
                                <div class="blueprint-container" id="svg-box-${item.id}">
                                    <p style="color: #1f2937; font-size: 13px; margin-bottom: 5px; font-weight: bold;"><b>📊 المخطط الهندسي / الرسم المرئي:</b></p>
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
                    btn.innerText = "🚀 تنفيذ الطلب عبر الوكيل";
                    sysStatus.innerText = "⚠ حدث خطأ أثناء الاتصال بالوكيل.";
                });
            }

            function escapeHtml(text) {
                return text
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }

            function startVoiceRecognition() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) { alert("متصفحك لا يدعم التعرف على الصوت."); return; }
                const recognition = new SpeechRecognition();
                recognition.lang = 'ar-SA';
                document.getElementById('status-mic').innerText = "🔴 جاري الاستماع لصوتك بتركيز...";
                recognition.onresult = function(event) {
                    document.getElementById('query-input').value = event.results[0][0].transcript;
                    document.getElementById('status-mic').innerText = "✅ تم التقاط الصوت وتحويله بنجاح.";
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
                a.download = `agent_blueprint_${itemId}.svg`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, registry=user_registry)

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
    
    filename = f"agent_report_{item_id}.txt"
    file_content = f"========================================\n" \
                   f"💎 تقرير الوكيل الذكي الشامل\n" \
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
    initialize_database()
    port = int(os.environ.get("PORT", 5080))
    print("=" * 70)
    print("💎🧠 خادم منصة الوكيل الذكي الشامل - يعمل بكفاءة تامة")
    print(f"🌍 منفذ التشغيل النشط: {port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
