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

app = Flask("DiamondKernelGlobalEngine")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "diamond_global_ultra_secure_key_2026_9333")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "diamond_kernel_global.db")

def initialize_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diamond_core_global (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
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

def load_history_for_session(session_id):
    registry = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_type, query_text, content, blueprint_data, timestamp FROM diamond_core_global WHERE session_id = ? ORDER BY id DESC LIMIT 50", (session_id,))
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

def persist_to_db(session_id, item_type, query, content, blueprint=""):
    t_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row_id = 0
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO diamond_core_global (session_id, item_type, query_text, content, blueprint_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                       (session_id, item_type, query, content, blueprint, t_now))
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

def generate_ai_response(req_type, user_query, user_api_key=""):
    result_text = ""
    blueprint_code = ""
    
    system_instructions = {
        "research": "أنت نواة تحليلية ذكية ومتخصصة وعالمية المستوى. قدم تحليلاً تقنياً وعميقاً ودقيقاً للغاية باللغة العربية. إذا كان الموضوع يتطلب رسماً توضيحياً أو هيكلياً، قم بتضمين كود SVG صحيح وجميل بالكامل داخل الوسم <svg ...>...</svg>.",
        "blueprint": "أنت خبير هندسي ومعماري عالمي. قدم تفاصيل هندسية دقيقة ومحترفة، ويجب عليك إرفاق مخطط هندسي مرئي كامل مصمم بلغة SVG حصرياً داخل الوسم <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300'>...</svg> لتمثيل المخطط بوضوح تام وبتصميم هندسي جذاب.",
        "image": "أنت مصمم بصري ورسومات هندسية متقدم. صف التصميم بدقة تامة، ويجب أن تتضمن إجابتك كود SVG مرئي وملون يعبر بدقة متناهية عن التصميم داخل الوسم <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300'>...</svg>.",
        "threat": "أنت محلل أمني ودفاعي اصطناعي سيبراني متطور. قم بتحليل التهديد المرصود واقترح خطوات الفحص وأتمتة الدفاع مع تضمين مخطط شبكي أو مسار هجومي بلغة SVG داخل الوسم <svg>...</svg>."
    }
    
    sys_prompt = system_instructions.get(req_type, "أنت مساعد ذكي وعالمي متخصص.")
    api_key = user_api_key.strip() if user_api_key else os.environ.get("GEMINI_API_KEY", "").strip()

    if not api_key:
        return "⚠️ تنبيه من النواة: لم يتم العثور على أي مفتاح API نشط. يرجى إدخال مفتاح Gemini الخاص بك في الحقل المخصص بالأعلى.", ""

    try:
        # استخدام الإصدار v1 والموديل المدعوم بشكل كامل على الحسابات المجانية
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"التوجيه السياقي العالمي: {sys_prompt}\n\nطلب المستخدم: {user_query}"}]
            }]
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
                    return "⚠️ استجاب الخادم بنجاح ولكن المحتوى عاد فارغاً أو تم حظره بواسطة سياسة الأمان.", ""
                
                cleaned_text = raw_text
                if "<svg" in cleaned_text and "</svg>" in cleaned_text:
                    start_idx = cleaned_text.find("<svg")
                    end_idx = cleaned_text.rfind("</svg>") + 6
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        blueprint_code = cleaned_text[start_idx:end_idx]
                        blueprint_code = blueprint_code.replace("```xml", "").replace("```html", "").replace("```", "").strip()
                        result_text = cleaned_text[:start_idx].strip() + "\n\n[✅ تم توليد واستخراج المخطط الهندسي المرئي بنجاح تام]\n\n" + cleaned_text[end_idx:].strip()
                
                if not result_text:
                    result_text = raw_text
            else:
                result_text = f"⚠️ خطأ من الخادم برمز الاستجابة: {response.status}"
    except urllib.error.HTTPError as e:
        error_message = e.read().decode('utf-8', errors='ignore')
        result_text = f"⚠ خطأ API (رمز {e.code}): تحقق من صلاحية مفتاح الـ API. التفاصيل: {error_message[:150]}"
    except urllib.error.URLError as e:
        result_text = f"⚠️️ خطأ في الشبكة العالمية أو تعذر الوصول للخادم."
    except Exception as e:
        result_text = f"⚠ حدث خطأ داخلي في النواة: {str(e)}"

    return result_text, blueprint_code

@app.route("/", methods=['GET', 'POST'])
def dashboard():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
    if request.method == 'POST':
        user_api_key = request.form.get("gemini_token_x", "").strip()
        req_type = request.form.get("req_type", "research")
        query = request.form.get("query", "").strip()
        
        if user_api_key:
            session['saved_api_key'] = user_api_key 

        content, blueprint = "", ""
        if query:
            content, blueprint = generate_ai_response(req_type, query, user_api_key)
            item_data = persist_to_db(session['session_id'], req_type, query, content, blueprint)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or (request.content_type and 'application/json' in request.content_type):
                return jsonify({"status": "success", "item": item_data})
            
        return redirect(url_for('dashboard'))

    user_registry = load_history_for_session(session['session_id'])
    saved_api_key = session.get('saved_api_key', '')
    
    html_template = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>النواة الماسية العالمية المتقدمة 💎</title>
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
            header { text-align: center; margin-bottom: 25px; }
            h1 { color: #60a5fa; font-size: 26px; margin-bottom: 5px; text-shadow: 0 0 15px rgba(59, 130, 246, 0.4); }
            p.sub-title { color: var(--text-muted); font-size: 14px; margin: 0; }
            .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
            label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 14px; color: #d1d5db; }
            
            .input-wrapper { display: flex; align-items: center; background: #030712; border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 15px; overflow: hidden; transition: all 0.3s ease; }
            .input-wrapper:focus-within { border-color: var(--accent-blue); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }
            .input-wrapper input { flex: 1; padding: 14px; background: transparent; border: none; color: #fff; font-size: 15px; outline: none; }
            
            .toggle-view-btn { background: transparent; border: none; color: var(--accent-blue); padding: 0 15px; cursor: pointer; font-size: 14px; font-weight: bold; }
            .toggle-view-btn:hover { opacity: 0.8; transform: none; }

            input[type="text"], select { width: 100%; padding: 14px; background: #030712; border: 1px solid var(--border-color); color: #fff; border-radius: 8px; box-sizing: border-box; font-size: 15px; margin-bottom: 15px; transition: all 0.3s ease; }
            input[type="text"]:focus, select:focus { border-color: var(--accent-blue); outline: none; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }
            
            .btn-group { display: flex; gap: 12px; }
            button { flex: 1; padding: 14px; background: var(--accent-green); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 15px; transition: all 0.2s; }
            button.mic-btn { background: var(--accent-red); flex: 0.4; }
            button.speak-btn { background: var(--accent-purple); margin-top: 10px; width: 100%; }
            button.export-btn { background: var(--accent-blue); margin-top: 5px; width: 100%; }
            button.svg-download-btn { background: #d97706; margin-top: 5px; width: 100%; }
            button:hover { opacity: 0.92; transform: translateY(-1px); }
            .output-box { background: #030712; border: 1px solid var(--border-color); padding: 15px; border-radius: 8px; margin-top: 10px; white-space: pre-wrap; color: #34d399; font-family: 'Courier New', Courier, monospace; font-size: 13.5px; line-height: 1.6; }
            .blueprint-container { margin-top: 15px; background: #ffffff; padding: 15px; border-radius: 8px; text-align: center; overflow-x: auto; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1); }
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
                <h1>💎🧠 النواة الماسية العالمية المتقدمة</h1>
                <p class="sub-title">منظومة ذكاء اصطناعي سيبرانية وهندسية فائقة الأداء لتوليد التحليلات والمخططات</p>
            </header>
            
            <div id="sys-status">🟢 النظام العالمي متصل، مؤمن، ومستعد للعمل بالسرعة القصوى</div>
            
            <div class="card">
                <h3>🛠 لوحة التحكم والعمليات المتقدمة</h3>
                <div id="ai-form">
                    <label><b>🔑 مفتاح الـ API:</b></label>
                    <div class="input-wrapper">
                        <input type="text" name="gemini_token_x" id="api-key-input" value="{{ saved_api_key }}" placeholder="ألصق مفتاح Gemini الخاص بك هنا..." autocomplete="off" data-lpignore="true" spellcheck="false">
                        <button type="button" class="toggle-view-btn" onclick="maskApiKeyToggle()">👁️ إخفاء/إظهار</button>
                    </div>

                    <label><b>اختر نمط التشغيل المتقدم:</b></label>
                    <select name="req_type" id="req-type-select">
                        <option value="blueprint">📐 مخطط هندسي ومعماري ذكي متقدم (SVG)</option>
                        <option value="image">🎨 تصميم بصري ورسومات هندسية دقيقة (SVG)</option>
                        <option value="research">📚 تحليل وبحث استراتيجي وعميق</option>
                        <option value="threat">🛡 فحص أمني سيبراني وأتمتة دفاعية</option>
                    </select>
                    
                    <label><b>أدخل طلبك، سؤالك، أو المشروع الهندسي:</b></label>
                    <input type="text" name="query" id="query-input" placeholder="مثال: تصميم مخطط تفصيلي لمحطة طاقة شمسية ذكية" autocomplete="off" required>
                    
                    <div id="status-mic"></div>

                    <div class="btn-group">
                        <button type="button" class="mic-btn" onclick="startVoiceRecognition()">🎤 إدخال صوتي</button>
                        <button type="button" id="submit-btn" onclick="executeAjaxSubmit()">🚀 تشغيل المعالجة فائقة السرعة</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>📜 سجل العمليات والمخرجات الذكية</h3>
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
                                    <button class="svg-download-btn" type="button" onclick="downloadSVG('svg-box-{{ item.id }}', {{ item.id }})">📥 تنزيل المخطط حصرياً كملف SVG جاهز</button>
                                {% endif %}
                                
                                <button class="speak-btn" type="button" onclick="speakTextFromElement('history-item-{{ item.id }}')">🗣 الاستماع للتقرير صوتياً</button>
                                <a href="/export/{{ item.id }}" target="_blank">
                                    <button class="export-btn" type="button">📥 تصدير التقرير النصي الكامل (TXT)</button>
                                </a>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p id="no-registry-msg" style="color: var(--text-muted); text-align: center; padding: 20px;">لا توجد مخرجات مسجلة في هذه الجلسة بعد. ابدأ بإدخال طلبك بالأعلى!</p>
                    {% endif %}
                </div>
            </div>
        </div>

        <script>
            let isMasked = false;
            function maskApiKeyToggle() {
                const input = document.getElementById('api-key-input');
                isMasked = !isMasked;
                if (isMasked) {
                    input.style.webkitTextSecurity = 'disc';
                } else {
                    input.style.webkitTextSecurity = 'none';
                }
            }

            function executeAjaxSubmit() {
                const apiKeyInput = document.getElementById('api-key-input');
                const reqTypeSelect = document.getElementById('req-type-select');
                const queryInput = document.getElementById('query-input');
                const btn = document.getElementById('submit-btn');
                const sysStatus = document.getElementById('sys-status');
                
                const queryVal = queryInput.value.trim();
                if(!queryVal) {
                    alert("يرجى إدخال السؤال أو الطلب أولاً.");
                    queryInput.focus();
                    return;
                }

                const formData = new FormData();
                formData.append('gemini_token_x', apiKeyInput.value.trim());
                formData.append('req_type', reqTypeSelect.value);
                formData.append('query', queryVal);
                
                btn.disabled = true;
                btn.innerText = "⏳ جاري إرسال الطلب والمعالجة...";
                sysStatus.innerText = "⏳ النظام يعمل بأقصى طاقة، يرجى الانتظار...";

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
                    btn.innerText = "🚀 تشغيل المعالجة فائقة السرعة";
                    sysStatus.innerText = "🟢 النظام العالمي متصل، مؤمن، ومستعد للعمل بالسرعة القصوى";

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
                                <button class="svg-download-btn" type="button" onclick="downloadSVG('svg-box-${item.id}', ${item.id})">📥 تنزيل المخطط حصرياً كملف SVG جاهز</button>
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
                                    <button class="export-btn" type="button">📥 تصدير التقرير النصي الكامل (TXT)</button>
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
                    btn.innerText = "🚀 تشغيل المعالجة فائقة السرعة";
                    sysStatus.innerText = "⚠ حدث خطأ أثناء الاتصال بالخادم الداخلي.";
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
                if (!svgElement) {
                    alert("لم يتم العثور على عنصر SVG صالح للتنزيل.");
                    return;
                }
                const serializer = new XMLSerializer();
                let source = serializer.serializeToString(svgElement);
                if(!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)){
                    source = source.replace(/^<svg/, '<svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)"');
                }
                if(!source.match(/^<\?xml/)){
                    source = '<?xml version="1.0" encoding="utf-8"?>\\r\\n' + source;
                }
                const blob = new Blob([source], {type: "image/svg+xml;charset=utf-8"});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `diamond_blueprint_${itemId}.svg`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, registry=user_registry, saved_api_key=saved_api_key)

@app.route("/export/<int:item_id>")
def export_item(item_id):
    target_item = None
    user_registry = load_history_for_session(session.get('session_id', 'default'))
    for item in user_registry:
        if item["id"] == item_id:
            target_item = item
            break
    
    if not target_item:
        return "العنصر المطلوب غير موجود أو انتهت صلاحية الجلسة", 404
    
    filename = f"diamond_global_report_{item_id}.txt"
    file_content = f"========================================\\n" \
                   f"💎 تقرير النواة الماسية العالمية المتقدمة\\n" \
                   f"========================================\\n" \
                   f"نوع الطلب: {target_item['type']}\\n" \
                   f"وقت التوليد: {target_item['time']}\\n" \
                   f"نص الاستعلام: {target_item['query']}\\n\\n" \
                   f"النتيجة والتحليل التقني:\\n{target_item['content']}\\n"
    
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(file_content)
        
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    initialize_database()
    port = int(os.environ.get("PORT", 5080))
    print("=" * 70)
    print("💎🧠 خادم النواة الماسية العالمية المتقدمة - يعمل بكفاءة تامة على الإنتاج")
    print(f"🌍 منفذ التشغيل النشط: {port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
