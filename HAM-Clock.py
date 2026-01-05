import threading
import time
import os
import webview
import tkinter as tk
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# --- LOGICA PROPAGAZIONE ---
def get_detailed_prop():
    hour = datetime.utcnow().hour
    if 7 <= hour <= 16:
        return {
            "title": "DIURNA",
            "trend": "In miglioramento",
            "best_band": "10m - 20m",
            "noise": "Basso",
            "desc": "Strato F2 ionizzato. Ottime aperture DX verso Est (mattina) e Ovest (pomeriggio)."
        }
    elif 17 <= hour <= 19 or 5 <= hour <= 6:
        return {
            "title": "GREYLINE",
            "trend": "Picco Transitorio",
            "best_band": "30m - 40m",
            "noise": "Variabile",
            "desc": "Fase critica: aumento della copertura sulle medie frequenze."
        }
    else:
        return {
            "title": "NOTTURNA",
            "trend": "Stabile",
            "best_band": "40m - 160m",
            "noise": "Moderato",
            "desc": "Assenza strato D. Le bande basse permettono QSO a lunga distanza."
        }

# --- INTERFACCIA HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; border-left: 1px solid #30363d; overflow: hidden; height: 100vh; }
        .title-bar { background: #21262d; height: 35px; display: flex; justify-content: space-between; align-items: center; padding: 0 10px; -webkit-app-region: drag; cursor: move; }
        .close-btn { background: #f8514933; color: #f85149; border: 1px solid #f85149; font-size: 14px; cursor: pointer; -webkit-app-region: no-drag; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
        .close-btn:hover { background: #f85149; color: white; }
        
        .clock-section { padding: 25px 10px; text-align: center; border-bottom: 1px solid #30363d; background: #161b22; }
        .label { color: #8b949e; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-top: 10px; }
        .time-main { font-family: 'Consolas', monospace; font-size: 36px; color: #58a6ff; font-weight: bold; margin: 5px 0; }
        .time-utc { font-family: 'Consolas', monospace; font-size: 32px; color: #d29922; font-weight: bold; margin: 5px 0; }
        .date-sub { font-size: 11px; color: #8b949e; margin-bottom: 5px; }

        .prop-section { padding: 15px; }
        .prop-card { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-top: 10px; }
        .status-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; background: #238636; color: white; margin-bottom: 10px; }
        
        .info-row { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 8px; border-bottom: 1px solid #21262d; padding-bottom: 4px; }
        .info-val { color: #58a6ff; font-weight: bold; }
        .advice-text { font-size: 11px; color: #8b949e; line-height: 1.4; font-style: italic; }
    </style>
</head>
<body>
    <div class="title-bar">
        <span style="font-size: 10px; font-weight: bold; color: #8b949e;">DX STATION CLOCK</span>
        <button class="close-btn" onclick="closeApp()">x</button>
    </div>

    <div class="clock-section">
        <div class="label">LOCAL TIME</div>
        <div class="time-main" id="local-clock">00:00:00</div>
        <div class="date-sub" id="local-date">-- --- ----</div>

        <div class="label">UTC TIME</div>
        <div class="time-utc" id="utc-clock">00:00:00</div>
        <div class="date-sub" id="utc-date">-- --- ----</div>
    </div>

    <div class="prop-section">
        <div class="label">PROPAGAZIONE HF</div>
        <div class="prop-card">
            <div id="p-tag" class="status-tag">--</div>
            <div class="info-row"><span>Bande:</span> <span class="info-val" id="p-bands">--</span></div>
            <div class="info-row"><span>Trend:</span> <span class="info-val" id="p-trend">--</span></div>
            <div class="info-row"><span>QRN:</span> <span class="info-val" id="p-noise">--</span></div>
            <div class="advice-text" id="p-desc">Aggiornamento...</div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>
        function closeApp() {
            // Chiamata all'API Python per chiudere la finestra
            window.pywebview.api.close_window();
        }

        function updateTime() {
            const now = new Date();
            $('#local-clock').text(now.toLocaleTimeString('it-IT', {hour12: false}));
            $('#local-date').text(now.toLocaleDateString('it-IT', {day:'2-digit', month:'short', year:'numeric'}).toUpperCase());

            const utcStr = now.getUTCHours().toString().padStart(2, '0') + ":" + 
                           now.getUTCMinutes().toString().padStart(2, '0') + ":" +
                           now.getUTCSeconds().toString().padStart(2, '0');
            $('#utc-clock').text(utcStr);
            
            const utcDate = now.getUTCDate().toString().padStart(2, '0') + " " + 
                            now.toLocaleString('en-US', {month: 'short', timeZone: 'UTC'}).toUpperCase() + " " + 
                            now.getUTCFullYear();
            $('#utc-date').text(utcDate + " (UTC)");
        }

        function updateProp() {
            $.getJSON('/api/prop', function(data) {
                $('#p-tag').text(data.title);
                $('#p-bands').text(data.best_band);
                $('#p-trend').text(data.trend);
                $('#p-noise').text(data.noise);
                $('#p-desc').text(data.desc);
            });
        }

        setInterval(updateTime, 1000);
        setInterval(updateProp, 30000);
        updateTime();
        updateProp();
    </script>
</body>
</html>
"""

class API:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def close_window(self):
        if self._window:
            self._window.destroy()

@app.route('/api/prop')
def prop_api():
    return jsonify(get_detailed_prop())

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    api = API()
    # Usiamo la porta 5002 per evitare conflitti 404
    threading.Thread(target=lambda: app.run(port=5002, use_reloader=False, debug=False), daemon=True).start()
    
    # Attendiamo un secondo per assicurarci che Flask sia attivo
    time.sleep(1)

    root = tk.Tk()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.destroy()

    w_width = 280 
    screen_h = 540
    
    window = webview.create_window(
        'Ham Station Clock', 
        'http://127.0.0.1:5002', 
        width=w_width, 
        height=screen_h, 
        x=screen_w - w_width,
        y=0,
        frameless=True, 
        on_top=True, 
        js_api=api
    )
    
    api.set_window(window)
    webview.start()
