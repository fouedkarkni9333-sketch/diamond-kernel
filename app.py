from flask import Flask, render_template_string, request, jsonify
import urllib.request
import json
import os

app = Flask(__name__)

# إعداد مفتاح API الخاص بـ Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

def call_gemini_ultra_engine(prompt, agent_role):
    """
    محرك الذكاء الاصطناعي الفائق المرتبط بالوكلاء الأربعة المتقدمين
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = f"""
    أنت جزء من نظام 'Diamond Kernel Global Engine' العالمي. 
    الدور الحالي المخصص لك هو: {agent_role}.
    عليك تقديم أعلى مستوى من الدقة، الاحترافية، والسرعة، وبدون أي أخطاء. استجب باللغة العربية الفصحى أو اللغة التي طلبها المستخدم بدقة متناهية، مع دعم الروابط، الصور، والأشكال الهندسية والتقنية عند الحاجة.
    """
    
    payload = {
        "contents": [
            {"parts": [{"text": system_instruction + "\n\nطلب المستخدم الأساسي: " + prompt}]}
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"حدث خطأ في الاتصال بمحرك الذكاء الاصطناعي الفائق: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process_request():
    data = request.json
    user_input = data.get('prompt', '')
    selected_agent = data.get('agent', 'The Master Developer & Coder')
    
    result = call_gemini_ultra_engine(user_input, selected_agent)
    return jsonify({"status": "success", "response": result})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diamond Kernel Global Engine - Ultra V4</title>
    <style>
        :root {
            --bg-color: #0d1117;
            --panel-bg: #161b22;
            --text-color: #c9d1d9;
            --accent-color: #58a6ff;
            --accent-hover: #1f6feb;
            --border-color: #30363d;
            --success-color: #238636;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            width: 100%;
            max-width: 1000px;
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        h1 {
            text-align: center;
            color: var(--accent-color);
            margin-bottom: 5px;
        }
        .subtitle {
            text-align: center;
            color: #8b949e;
            font-size: 14px;
            margin-bottom: 25px;
        }
        .agents-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .agent-card {
            background: #21262d;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }
        .agent-card.active {
            border-color: var(--accent-color);
            background: #1f242c;
        }
        .agent-card h3 {
            margin: 0 0 5px 0;
            font-size: 15px;
            color: var(--accent-color);
        }
        .agent-card p {
            margin: 0;
            font-size: 12px;
            color: #8b949e;
        }
        textarea {
            width: 100%;
            height: 120px;
            background: #0d1117;
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 8px;
            padding: 12px;
            font-size: 16px;
            resize: vertical;
            box-sizing: border-box;
            margin-bottom: 15px;
        }
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        button {
            background: var(--accent-color);
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 15px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }
        button:hover {
            background: var(--accent-hover);
        }
        button.mic-btn {
            background: #da3633;
        }
        button.mic-btn.listening {
            background: #f85149;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .output-box {
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            min-height: 150px;
            white-space: pre-wrap;
            line-height: 1.6;
        }
    </style>
</head>
<body>

    <div class="container">
        <h1>Diamond Kernel Global Engine</h1>
        <div class="subtitle">النظام السحابي الفائق المدعوم بالوكلاء الأربعة الأذكياء ومعالجة الصوت الفورية</div>

        <div class="agents-grid">
            <div class="agent-card active" onclick="selectAgent(this, 'The Strategist & Architect')">
                <h3>1. وكيل التحليل والتخطيط</h3>
                <p>تحليل المشاريع وهندسة الأفكار</p>
            </div>
            <div class="agent-card" onclick="selectAgent(this, 'The Master Developer & Coder')">
                <h3>2. وكيل التوليد والبرمجة</h3>
                <p>كتابة الأكواد والحلول التقنية</p>
            </div>
            <div class="agent-card" onclick="selectAgent(this, 'The Real-Time Voice & Multilingual Agent')">
                <h3>3. وكيل الصوت والترجمة</h3>
                <p>المعالجة الصوتية الفورية والترجمة</p>
            </div>
            <div class="agent-card" onclick="selectAgent(this, 'The Quality Assurance Agent')">
                <h3>4. وكيل الجودة والمراجعة</h3>
                <p>فحص واختبار المخرجات بدقة</p>
            </div>
        </div>

        <textarea id="userInput" placeholder="اكتب طلبك هنا، أو استخدم الإدخال الصوتي بالأسفل لتنفيذ أي شيء فوراً..."></textarea>

        <div class="controls">
            <button onclick="sendRequest()">تنفيذ الطلب الفائق</button>
            <button id="micBtn" class="mic-btn" onclick="toggleSpeechRecognition()">🎙️ تحدث بالصوت</button>
            <button onclick="speakOutput()" style="background: #238636;">🔊 الاستماع للرد</button>
        </div>

        <h3>نتائج التشغيل والوكيل الذكي:</h3>
        <div id="outputBox" class="output-box">النتائج ستظهر هنا فور اكتمال المعالجة السحابية...</div>
    </div>

    <script>
        let currentAgent = 'The Strategist & Architect';

        function selectAgent(element, agentName) {
            document.querySelectorAll('.agent-card').forEach(card => card.classList.remove('active'));
            element.classList.add('active');
            currentAgent = agentName;
        }

        async function sendRequest() {
            const prompt = document.getElementById('userInput').value;
            const outputBox = document.getElementById('outputBox');
            if (!prompt.trim()) {
                alert('الرجاء إدخال نص أو التحدث أولاً.');
                return;
            }

            outputBox.innerText = '⏳ جاري المعالجة السحابية عبر الوكلاء الأربعة ومحرك الذكاء الاصطناعي الفائق...';

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prompt: prompt, agent: currentAgent })
                });
                const data = await response.json();
                outputBox.innerText = data.response;
            } catch (error) {
                outputBox.innerText = 'حدث خطأ أثناء الاتصال بالخادم السحابي: ' + error;
            }
        }

        let recognition;
        let isListening = false;

        function toggleSpeechRecognition() {
            const micBtn = document.getElementById('micBtn');
            const userInput = document.getElementById('userInput');

            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('عذراً، متصفحك لا يدعم الإدخال الصوتي المباشر.');
                return;
            }

            if (isListening) {
                recognition.stop();
                return;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'ar-SA';
            recognition.continuous = false;
            recognition.interimResults = true;

            recognition.onstart = () => {
                isListening = true;
                micBtn.classList.add('listening');
                micBtn.innerText = '🔴 جاري الاستماع...';
            };

            recognition.onresult = (event) => {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                userInput.value = transcript;
            };

            recognition.onerror = (event) => {
                console.error(event.error);
                stopMicUI();
            };

            recognition.onend = () => {
                stopMicUI();
                if (userInput.value.trim()) {
                    sendRequest();
                }
            };

            recognition.start();
        }

        function stopMicUI() {
            isListening = false;
            const micBtn = document.getElementById('micBtn');
            micBtn.classList.remove('listening');
            micBtn.innerText = '🎙️ تحدث بالصوت';
        }

        function speakOutput() {
            const text = document.getElementById('outputBox').innerText;
            if (!text || text.startsWith('النتائج ستظهر')) return;
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ar-SA';
            window.speechSynthesis.speak(utterance);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
