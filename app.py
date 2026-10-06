from flask import Flask, render_template_string, request, jsonify
import urllib.request
import json
import os

app = Flask(__name__)

# إعداد مفتاح API الخاص بـ Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

def call_gemini_ultra_engine(prompt, agent_role):
    """
    محرك الذكاء الاصطناعي الفائق المرتبط بالوكلاء الأربعة المتقدمين (متوافق مع الهيكل الصحيح لـ Gemini API)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = f"""
    أنت جزء من نظام 'Diamond Kernel Global Engine' العالمي. 
    الدور الحالي المخصص لك هو: {agent_role}.
    عليك تقديم أعلى مستوى من الدقة، الاحترافية، والسرعة، وبدون أي أخطاء. استجب باللغة العربية الفصحى بدقة متناهية، وقدم تفاصيل شاملة ودقيقة لكل طلب يتعلق بالصور، الأشكال الهندسية، التصاميم، أو الأكواد التقنية.
    """
    
    # البنية الصحيحة المعتمدة لـ Google Gemini API
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"تعليمات النظام الأساسية: {system_instruction}\n\nطلب المستخدم: {prompt}"}
                ]
            }
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
            # استخراج النص بدقة من استجابة Gemini
            return res_json['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as e:
        error_message = e.read().decode('utf-8')
        return f"خطأ من خادم Google (HTTP {e.code}): {error_message}"
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
