import os
import tempfile
import json
import time

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic

from agent import extract_pdf, generate_zener, build_zener_code

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

client = anthropic.Anthropic()

HOSTED = os.environ.get('TRACE_HOSTED', '0') == '1'


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/generate', methods=['POST'])
def generate():
    if HOSTED:
        return jsonify({
            'success': False,
            'error': "datasheet → zener requires the local pcb toolchain and isn't available in the hosted demo. Clone the repo from github to run it locally."
        }), 503

    if 'file' not in request.files:
        return jsonify({'error': 'There is no file, upload one dumbass'}), 400

    file = request.files['file']

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        file.save(tmp.name)
        datasheet_text = extract_pdf(tmp.name)
        os.unlink(tmp.name)

    errors = None
    for attempt in range(3):
        zen_code = generate_zener(client, datasheet_text, errors)
        success, errors = build_zener_code(zen_code)
        if success:
            return jsonify({'success': True, 'code': zen_code})
        time.sleep(6.9)

    return jsonify({'success': False, 'error': errors})


@app.route('/schematic', methods=['POST'])
@limiter.limit("20 per day", exempt_when=lambda: not HOSTED)
def schematic():
    data = request.get_json()
    prompt = data.get('prompt', '')

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8000,
        system="""You are an electrical engineer. Given a natural language description of a circuit, return ONLY a valid JSON object. Keep it concise — max 10 components. Use this exact structure, no markdown, no backticks, no explanation before or after:
{
  "components": [
    {"id": "U1", "name": "ESP32", "type": "ic", "x": 300, "y": 200}
  ],
  "connections": [
    {"from": "U1", "to": "C1", "label": "VCC"}
  ],
  "bom": [
    {"ref": "U1", "component": "ESP32-D0WD-V3", "value": "ESP32", "qty": 1, "unit_price": 2.50, "url": "https://www.digikey.com/en/products/result?keywords=ESP32-D0WD-V3", "notes": "Main MCU"}
  ]
}""",
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{'role': 'user', 'content': f"Design a circuit for: {prompt}. Keep it to the essential components only, max 10."}]
    )

    try:
        text = ""
        for block in message.content:
            if block.type == "text":
                text += block.text

        text = text.strip()

        start = text.find('{')
        end = text.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        text = text[start:end]
        result = json.loads(text)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Parse error: {str(e)}, raw: {text[:200]}'})


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'error': "Rate limit reached (20 requests per day per IP on the hosted demo). Clone the repo to run it locally without limits."
    }), 429


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5700))
    app.run(host='0.0.0.0', port=port, debug=not HOSTED)
