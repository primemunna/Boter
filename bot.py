import os
import sqlite3
import time
from datetime import datetime, timedelta
import telebot
from telebot import types

TOKEN = "9249303434:AAF3Afl8_O5TH_lVNezCQsGX4iMgpXeC8oI"
ADMIN_ID = 9118052534

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        username TEXT, 
                        name TEXT, 
                        rs_balance REAL DEFAULT 0.0, 
                        coin_balance INTEGER DEFAULT 0,
                        raffles_count INTEGER DEFAULT 0)''')
    
    # Channels table
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT)''')
    
    # Admins table
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    
    # Products table
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        type TEXT, title TEXT, description TEXT, 
                        image TEXT, file TEXT, tutorial TEXT, price REAL)''')
    
    # Purchases table
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, product_id INTEGER, type TEXT)''')
    
    # Raffles table
    cursor.execute('''CREATE TABLE IF NOT EXISTS raffles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, link TEXT, username TEXT, name TEXT)''')
    
    # Payments table
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, amount REAL, image TEXT, 
                        status TEXT, timestamp REAL)''')
    
    # Promo Codes table
    cursor.execute('''CREATE TABLE IF NOT EXISTS codes (
                        code TEXT PRIMARY KEY, type TEXT, amount INTEGER, limit_count INTEGER, used_count INTEGER DEFAULT 0)''')
    
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def get_db():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    return conn, conn.cursor()

def is_admin(user_id):
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def check_channels(user_id):
    conn, cursor = get_db()
    cursor.execute("SELECT link FROM channels")
    channels = cursor.fetchall()
    conn.close()
    
    for ch in channels:
        channel_username = ch[0].split("/")[-1]
        if not channel_username.startswith("@"):
            channel_username = "@" + channel_username
        try:
            member = bot.get_chat_member(channel_username, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            pass
    return True

# --- START & FORCE SUBSCRIBE ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    name = message.from_user.first_name
    
    conn, cursor = get_db()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, name) VALUES (?, ?, ?)", (user_id, username, name))
    conn.commit()
    conn.close()
    
    if not check_channels(user_id):
        conn, cursor = get_db()
        cursor.execute("SELECT link FROM channels")
        channels = cursor.fetchall()
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in channels:
            markup.add(types.InlineKeyboardButton("📢 Join Channel", url=ch[0]))
        markup.add(types.InlineKeyboardButton("🔄 Verify Joined", callback_data="verify_join"))
        bot.send_message(user_id, "⚠️ Please join all our channels to use this bot!", reply_markup=markup)
        return
    
    send_main_menu(message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_join(call):
    if check_channels(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels!", show_alert=True)

def send_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("🎁 Free Products")
    b2 = types.KeyboardButton("🛍️ Paid Products")
    b3 = types.KeyboardButton("🎟️ Raffle Status")
    b4 = types.KeyboardButton("📦 Purchase History")
    b5 = types.KeyboardButton("🎫 Raffle History")
    b6 = types.KeyboardButton("💰 Wallet")
    b7 = types.KeyboardButton("🛠️ Developer")
    b8 = types.KeyboardButton("🌐 Language Change")
    b9 = types.KeyboardButton("🆘 Help Support")
    b10 = types.KeyboardButton("🤖 Create Own Bot")
    b11 = types.KeyboardButton("🏆 Raffle Leaderboard")
    
    markup.add(b1, b2)
    markup.add(b3)
    markup.add(b4, b5)
    markup.add(b6)
    markup.add(b7, b8)
    markup.add(b9, b10)
    markup.add(b11)
    
    if is_admin(user_id):
        markup.add(types.KeyboardButton("👑 Admin Panel"))
        
    bot.send_message(chat_id, "✨ Welcome to the Main Menu:", reply_markup=markup)

# --- USER PANELS HANDLERS ---
@bot.message_handler(func=lambda msg: msg.text in ["🎁 Free Products", "🛍️ Paid Products", "🎟️ Raffle Status", "📦 Purchase History", "🎫 Raffle History", "💰 Wallet", "🛠️ Developer", "🌐 Language Change", "🆘 Help Support", "🤖 Create Own Bot", "🏆 Raffle Leaderboard", "👑 Admin Panel"])
def handle_menu_text(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "🎁 Free Products":
        conn, cursor = get_db()
        cursor.execute("SELECT id, title FROM products WHERE type = 'free'")
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            bot.send_message(user_id, "No free products available right now.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            markup.add(types.InlineKeyboardButton(p[1], callback_data=f"free_prod_{p[0]}"))
        bot.send_message(user_id, "🎁 Free Products List:", reply_markup=markup)
        
    elif text == "🛍️ Paid Products":
        conn, cursor = get_db()
        cursor.execute("SELECT id, title FROM products WHERE type = 'paid'")
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            bot.send_message(user_id, "No paid products available right now.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            markup.add(types.InlineKeyboardButton(p[1], callback_data=f"paid_prod_{p[0]}"))
        bot.send_message(user_id, "🛍️ Paid Products List:", reply_markup=markup)

    elif text == "🎟️ Raffle Status":
        msg = (
            "🎟️ **Raffle Information & Status**\n\n"
            "• Per Raffle Cost: 1 🪙\n"
            "• Send your Raffle link to participate!"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 Submit Raffle Link", callback_data="submit_raffle"))
        bot.send_message(user_id, msg, reply_markup=markup)

    elif text == "📦 Purchase History":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("Free Purchases", callback_data="history_free"),
                   types.InlineKeyboardButton("Paid Purchases", callback_data="history_paid"))
        bot.send_message(user_id, "📦 Select Purchase History Type:", reply_markup=markup)

    elif text == "🎫 Raffle History":
        conn, cursor = get_db()
        cursor.execute("SELECT username, name, link FROM raffles")
        raffles = cursor.fetchall()
        conn.close()
        
        if not raffles:
            bot.send_message(user_id, "No raffle history found.")
            return
        
        text_out = "🎫 **Raffle History:**\n\n"
        for r in raffles:
            text_out += f"👤 @{r[0]} ({r[1]})\n🔗 {r[2]}\n\n"
        bot.send_message(user_id, text_out)

    elif text == "💰 Wallet":
        conn, cursor = get_db()
        cursor.execute("SELECT rs_balance, coin_balance FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        
        rs, coin = res[0], res[1]
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("➕ Add Rs.", callback_data="add_rs"),
                   types.InlineKeyboardButton("🎟️ Redeem Code", callback_data="redeem_code"))
        
        bot.send_message(user_id, f"💰 **Your Wallet:**\n\nRs. Balance: ₹{rs}\n🪙 Coin Balance: {coin}", reply_markup=markup)

    elif text == "🛠️ Developer":
        bot.send_message(user_id, "👨‍💻 Developer: @ai_brain_box_2")

    elif text == "🌐 Language Change":
        bot.send_message(user_id, "🌐 Language change feature is coming soon!")

    elif text == "🆘 Help Support":
        bot.send_message(user_id, "🆘 For support, contact admin or developer @ai_brain_box_2")

    elif text == "🤖 Create Own Bot":
        bot.send_message(user_id, "🤖 Want to create your own bot? Contact developer: @ai_brain_box_2")

    elif text == "🏆 Raffle Leaderboard":
        conn, cursor = get_db()
        cursor.execute("SELECT username, name, raffles_count FROM users ORDER BY raffles_count DESC LIMIT 10")
        top_users = cursor.fetchall()
        
        cursor.execute("SELECT raffles_count FROM users WHERE user_id = ?", (user_id,))
        my_count = cursor.fetchone()[0]
        conn.close()
        
        msg = "🏆 **Raffle Leaderboard**\n\n"
        for i, u in enumerate(top_users, 1):
            msg += f"{i}. @{u[0]} ({u[1]}) - {u[2]} Raffles\n"
        msg += f"\n👉 Your Total Raffles: {my_count}"
        bot.send_message(user_id, msg)

    elif text == "👑 Admin Panel":
        if not is_admin(user_id):
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("➕ Add Product", callback_data="adm_add_prod"),
                   types.InlineKeyboardButton("📦 Manage Products", callback_data="adm_manage_prod"))
        markup.add(types.InlineKeyboardButton("📊 Dashboard", callback_data="adm_dashboard"),
                   types.InlineKeyboardButton("👥 Users", callback_data="adm_users"))
        markup.add(types.InlineKeyboardButton("💸 Payment Requests", callback_data="adm_payments"),
                   types.InlineKeyboardButton("📢 Add Channels", callback_data="adm_channels"))
        markup.add(types.InlineKeyboardButton("➕ Add Admin", callback_data="adm_add_admin"),
                   types.InlineKeyboardButton("🎁 Send Bonus / Promo", callback_data="adm_promo"))
        markup.add(types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"))
        
        bot.send_message(user_id, "👑 **Admin Panel:**", reply_markup=markup)

# --- PRODUCT PURCHASE FLOW ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("free_prod_") or call.data.startswith("paid_prod_"))
def product_details(call):
    parts = call.data.split("_")
    p_type = parts[0]
    p_id = parts[1]
    
    conn, cursor = get_db()
    cursor.execute("SELECT title, description, image, price FROM products WHERE id = ?", (p_id,))
    prod = cursor.fetchone()
    conn.close()
    
    title, desc, img, price = prod[0], prod[1], prod[2], prod[3]
    
    msg = f"📌 **{title}**\n\n📝 {desc}\n\n💰 Price: {price} " + ("🪙 Coins" if p_type == "free" else "Rs.")
    
    markup = types.InlineKeyboardMarkup()
    if p_type == "free":
        markup.add(types.InlineKeyboardButton("🪙 Earn Coin", callback_data=f"earn_coin_{p_id}"))
        markup.add(types.InlineKeyboardButton("🛒 Buy Product", callback_data=f"buy_free_{p_id}"))
    else:
        markup.add(types.InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_paid_{p_id}"))
        
    if img and img != "skip":
        bot.send_photo(call.message.chat.id, img, caption=msg, reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("earn_coin_"))
def earn_coin_handler(call):
    bot.answer_callback_query(call.id, "🎟️ Submit your raffle link in Raffle Status to earn coins!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_free_") or call.data.startswith("buy_paid_"))
def buy_product_handler(call):
    user_id = call.from_user.id
    parts = call.data.split("_")
    p_type = parts[1] # free or paid
    p_id = parts[2]
    
    conn, cursor = get_db()
    cursor.execute("SELECT price, file, tutorial FROM products WHERE id = ?", (p_id,))
    prod = cursor.fetchone()
    price, file_link, tutorial = prod[0], prod[1], prod[2]
    
    if p_type == "free":
        cursor.execute("SELECT coin_balance FROM users WHERE user_id = ?", (user_id,))
        coin = cursor.fetchone()[0]
        if coin < price:
            bot.answer_callback_query(call.id, f"❌ Not enough coins! You need {price} 🪙", show_alert=True)
            conn.close()
            return
        new_coin = coin - price
        cursor.execute("UPDATE users SET coin_balance = ? WHERE user_id = ?", (new_coin, user_id))
    else:
        cursor.execute("SELECT rs_balance FROM users WHERE user_id = ?", (user_id,))
        rs = cursor.fetchone()[0]
        if rs < price:
            bot.answer_callback_query(call.id, f"❌ Not enough balance! You need ₹{price}", show_alert=True)
            conn.close()
            return
        new_rs = rs - price
        cursor.execute("UPDATE users SET rs_balance = ? WHERE user_id = ?", (new_rs, user_id))
        
    cursor.execute("INSERT INTO purchases (user_id, product_id, type) VALUES (?, ?, ?)", (user_id, p_id, p_type))
    conn.commit()
    conn.close()
    
    msg = f"✅ **Purchase Successful!**\n\n📂 File: {file_link}"
    markup = types.InlineKeyboardMarkup()
    if tutorial and tutorial != "skip":
        markup.add(types.InlineKeyboardButton("📺 Tutorial Video", url=tutorial))
        
    bot.send_message(user_id, msg, reply_markup=markup)

# --- RAFFLE SUBMISSION ---
@bot.callback_query_handler(func=lambda call: call.data == "submit_raffle")
def submit_raffle_prompt(call):
    msg = bot.send_message(call.message.chat.id, "Send your Raffle link now:")
    bot.register_next_step_handler(msg, save_raffle_link)

def save_raffle_link(message):
    user_id = message.from_user.id
    link = message.text
    username = message.from_user.username or "None"
    name = message.from_user.first_name
    
    conn, cursor = get_db()
    cursor.execute("INSERT INTO raffles (user_id, link, username, name) VALUES (?, ?, ?, ?)", (user_id, link, username, name))
    cursor.execute("UPDATE users SET coin_balance = coin_balance + 1, raffles_count = raffles_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, "✅ Raffle link submitted successfully! You earned +1 🪙")

# --- PURCHASE HISTORY ---
@bot.callback_query_handler(func=lambda call: call.data in ["history_free", "history_paid"])
def show_history(call):
    user_id = call.from_user.id
    p_type = "free" if call.data == "history_free" else "paid"
    
    conn, cursor = get_db()
    cursor.execute("SELECT p.title, p.file FROM purchases pur JOIN products p ON pur.product_id = p.id WHERE pur.user_id = ? AND pur.type = ?", (user_id, p_type))
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        bot.send_message(user_id, f"No {p_type} purchase history found.")
        return
    
    text = f"📦 **Your {p_type.capitalize()} Purchases:**\n\n"
    for item in items:
        text += f"📌 {item[0]}\n📂 {item[1]}\n\n"
    bot.send_message(user_id, text)

# --- WALLET & ADD MONEY WITH TIMER ---
@bot.callback_query_handler(func=lambda call: call.data == "add_rs")
def add_rs_handler(call):
    msg = bot.send_message(call.message.chat.id, "Enter amount to add (Rs.):")
    bot.register_next_step_handler(msg, process_payment_amount)

def process_payment_amount(message):
    try:
        amount = float(message.text)
    except:
        bot.send_message(message.chat.id, "Invalid amount!")
        return
    
    user_id = message.from_user.id
    
    # Send QR code & UPI ID (Placeholder UPI & QR)
    qr_caption = (
        f"💳 **Payment Gateway**\n\n"
        f"Amount: ₹{amount}\n"
        f"UPI ID: `merchant@upi`\n\n"
        f"⚠️ Pay using any UPI app and send the payment screenshot within **10 minutes**!"
    )
    
    # We send a dummy/text QR representation or prompt for image
    msg = bot.send_message(user_id, qr_caption)
    bot.send_message(user_id, "📸 Now send the payment screenshot image:")
    bot.register_next_step_handler(msg, lambda m: receive_payment_screenshot(m, amount))

def receive_payment_screenshot(message, amount):
    user_id = message.from_user.id
    if not message.photo:
        bot.send_message(user_id, "❌ Please send a valid image screenshot!")
        return
    
    file_id = message.photo[-1].file_id
    
    conn, cursor = get_db()
    cursor.execute("INSERT INTO payments (user_id, amount, image, status, timestamp) VALUES (?, ?, ?, 'pending', ?)", 
                   (user_id, amount, file_id, time.time()))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, "⏳ Payment request submitted! Status: Pending. Admin will check it soon.")
    
    # Send to Admin
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"pay_app_{payment_id}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_rej_{payment_id}"))
    
    admin_msg = f"💸 **New Payment Request!**\n\nUser ID: {user_id}\nAmount: ₹{amount}"
    bot.send_photo(ADMIN_ID, file_id, caption=admin_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_app_") or call.data.startswith("pay_rej_"))
def handle_payment_action(call):
    if not is_admin(call.from_user.id):
        return
    
    parts = call.data.split("_")
    action = parts[1]
    pay_id = parts[2]
    
    conn, cursor = get_db()
    cursor.execute("SELECT user_id, amount FROM payments WHERE id = ?", (pay_id,))
    pay = cursor.fetchone()
    
    if not pay:
        bot.answer_callback_query(call.id, "Payment not found!")
        return
    
    user_id, amount = pay[0], pay[1]
    
    if action == "app":
        cursor.execute("UPDATE users SET rs_balance = rs_balance + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("UPDATE payments SET status = 'approved' WHERE id = ?", (pay_id,))
        conn.commit()
        bot.send_message(user_id, f"✅ Your payment of ₹{amount} has been approved and added to your wallet!")
        bot.edit_message_caption(caption=call.message.caption + "\n\nSTATUS: APPROVED", chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        cursor.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (pay_id,))
        conn.commit()
        bot.send_message(user_id, f"❌ Your payment of ₹{amount} was rejected.")
        bot.edit_message_caption(caption=call.message.caption + "\n\nSTATUS: REJECTED", chat_id=call.message.chat.id, message_id=call.message.message_id)
    conn.close()
    bot.answer_callback_query(call.id, "Done!")

# --- REDEEM CODE ---
@bot.callback_query_handler(func=lambda call: call.data == "redeem_code")
def redeem_prompt(call):
    msg = bot.send_message(call.message.chat.id, "Enter Promo Code:")
    bot.register_next_step_handler(msg, process_redeem)

def process_redeem(message):
    code = message.text.strip()
    user_id = message.from_user.id
    
    conn, cursor = get_db()
    cursor.execute("SELECT type, amount, limit_count, used_count FROM codes WHERE code = ?", (code,))
    c_data = cursor.fetchone()
    
    if not c_data:
        bot.send_message(user_id, "❌ Invalid Promo Code!")
        conn.close()
        return
    
    c_type, amount, limit_count, used_count = c_data
    if used_count >= limit_count:
        bot.send_message(user_id, "❌ Code limit exceeded!")
        conn.close()
        return
    
    if c_type == "rs":
        cursor.execute("UPDATE users SET rs_balance = rs_balance + ? WHERE user_id = ?", (amount, user_id))
    else:
        cursor.execute("UPDATE users SET coin_balance = coin_balance + ? WHERE user_id = ?", (amount, user_id))
        
    cursor.execute("UPDATE codes SET used_count = used_count + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, f"✅ Successfully redeemed! Added {amount} {c_type.upper()}")

# --- ADMIN PANEL FEATURES ---
# Product Addition Wizard State (Simple multi-step via temp dict)
admin_temp_data = {}

@bot.callback_query_handler(func=lambda call: call.data == "adm_add_prod")
def adm_add_prod(call):
    if not is_admin(call.from_user.id): return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Free Product", callback_data="prod_type_free"),
               types.InlineKeyboardButton("Paid Product", callback_data="prod_type_paid"))
    bot.send_message(call.message.chat.id, "Select Product Type:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("prod_type_"))
def prod_type_selected(call):
    p_type = call.data.split("_")[2]
    admin_temp_data[call.from_user.id] = {"type": p_type}
    msg = bot.send_message(call.message.chat.id, "Enter Product Title:")
    bot.register_next_step_handler(msg, adm_get_title)

def adm_get_title(message):
    admin_temp_data[message.from_user.id]["title"] = message.text
    msg = bot.send_message(message.chat.id, "Enter Product Description:")
    bot.register_next_step_handler(msg, adm_get_desc)

def adm_get_desc(message):
    admin_temp_data[message.from_user.id]["desc"] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Skip Image", callback_data="skip_image"))
    msg = bot.send_message(message.chat.id, "Upload Image or click Skip:", reply_markup=markup)
    bot.register_next_step_handler(msg, adm_get_image)

def adm_get_image(message):
    if message.photo:
        admin_temp_data[message.from_user.id]["image"] = message.photo[-1].file_id
    else:
        admin_temp_data[message.from_user.id]["image"] = "skip"
    
    msg = bot.send_message(message.chat.id, "Upload File or send file link:")
    bot.register_next_step_handler(msg, adm_get_file)

def adm_get_file(message):
    admin_temp_data[message.from_user.id]["file"] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Skip Tutorial", callback_data="skip_tutorial"))
    msg = bot.send_message(message.chat.id, "Enter Tutorial Link or Skip:", reply_markup=markup)
    bot.register_next_step_handler(msg, adm_get_tutorial)

def adm_get_tutorial(message):
    admin_temp_data[message.from_user.id]["tutorial"] = message.text
    msg = bot.send_message(message.chat.id, "Enter Price (Number only):")
    bot.register_next_step_handler(msg, adm_get_price)

def adm_get_price(message):
    try:
        price = float(message.text)
    except:
        bot.send_message(message.chat.id, "Invalid price!")
        return
    
    data = admin_temp_data[message.from_user.id]
    
    conn, cursor = get_db()
    cursor.execute("INSERT INTO products (type, title, description, image, file, tutorial, price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (data["type"], data["title"], data["desc"], data["image"], data["file"], data["tutorial"], price))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Product Added Successfully!")

# Dashboard & Users
@bot.callback_query_handler(func=lambda call: call.data == "adm_dashboard")
def adm_dashboard(call):
    if not is_admin(call.from_user.id): return
    conn, cursor = get_db()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM purchases")
    total_purchases = cursor.fetchone()[0]
    conn.close()
    
    bot.send_message(call.message.chat.id, f"📊 **Dashboard:**\n\nTotal Users: {total_users}\nTotal Purchases: {total_purchases}")

@bot.callback_query_handler(func=lambda call: call.data == "adm_users")
def adm_users(call):
    if not is_admin(call.from_user.id): return
    conn, cursor = get_db()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    bot.send_message(call.message.chat.id, f"👥 Total Registered Users: {count}")

# Channels Management
@bot.callback_query_handler(func=lambda call: call.data == "adm_channels")
def adm_channels(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.message.chat.id, "Enter Channel Link (e.g., https://t.me/yourchannel):")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    link = message.text.strip()
    conn, cursor = get_db()
    cursor.execute("INSERT INTO channels (link) VALUES (?)", (link,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Channel added successfully!")

# Broadcast
@bot.callback_query_handler(func=lambda call: call.data == "adm_broadcast")
def adm_broadcast(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.message.chat.id, "Enter Broadcast Message:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    text = message.text
    conn, cursor = get_db()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    success, error = 0, 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **Announcement:**\n\n{text}")
            success += 1
        except:
            error += 1
            
    bot.send_message(message.chat.id, f"✅ Broadcast Complete!\n\nSent: {success}\nFailed: {error}")

# Promo Code Generation by Admin
@bot.callback_query_handler(func=lambda call: call.data == "adm_promo")
def adm_promo(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.message.chat.id, "Enter Promo Code details in format:\n`CODE TYPE(rs/coin) AMOUNT LIMIT`\n\nExample: `FREE100 rs 50 100`")
    bot.register_next_step_handler(msg, save_promo_code)

def save_promo_code(message):
    try:
        parts = message.text.split()
        code, c_type, amount, limit = parts[0], parts[1], int(parts[2]), int(parts[3])
        
        conn, cursor = get_db()
        cursor.execute("INSERT INTO codes (code, type, amount, limit_count) VALUES (?, ?, ?, ?)", (code, c_type, amount, limit))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ Promo Code Created Successfully!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: Invalid format.")

# Add Admin
@bot.callback_query_handler(func=lambda call: call.data == "adm_add_admin")
def adm_add_admin(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.message.chat.id, "Enter User ID to make Admin:")
    bot.register_next_step_handler(msg, save_admin)

def save_admin(message):
    try:
        new_admin = int(message.text.strip())
        conn, cursor = get_db()
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ User {new_admin} is now an Admin!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid User ID!")

# --- BOT POLLING ---
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
