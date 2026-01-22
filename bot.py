import telebot
from telebot import types
import mercadopago
import os
import logging
import qrcode
from io import BytesIO
from flask import Flask, request, jsonify
import threading

# --- CONFIGURAÇÕES ---
TOKEN = '8219509702:AAEQThWquHwt5e4V2YSL7vZdcCsdYVpwsW4'
MP_TOKEN = 'APP_USR-6894935873237030-012111-0bf28881a74fe3acc533c3b83cc0dfbc-1680044822'
ADMIN_ID = 8337105439
SUPPORT_USER = "RLKDATROPADOSAN"
GRUPO_LINK = "https://t.me/+qRi9ljZuHgRiYTMx"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
sdk = mercadopago.SDK(MP_TOKEN)
logging.basicConfig(level=logging.INFO)

# Armazenar referências de compra
compras_pendentes = {}

def safe_send_message(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logging.error(f"Erro ao enviar para {chat_id}: {e}")
        return None

def obter_valor_cc(tipo, idx=0):
    if idx == 0:
        return 0.90
    t = tipo.upper()
    precos = {
        "NUBANK BLACK": 35.00,
        "BLACK": 60.00,
        "INFINITE": 40.00,
        "NUBANK GOLD": 15.00,
        "GOLD": 50.00,
        "NUBANK PLATINUM": 50.00,
        "PLATINUM": 50.00,
        "SIGNATURE": 58.00,
        "WORLD ELITE": 60.00,
        "CLASSIC": 25.00,
        "STANDARD": 40.00
    }
    for k, v in precos.items():
        if k in t:
            return v
    return 50.00

def listar_estoque(cat_solic):
    arqs = ["ccs.txt", "consul.txt"]
    linhas = []
    for a in arqs:
        if os.path.exists(a):
            with open(a, "r", encoding="utf-8") as f:
                linhas.extend([l.strip() for l in f if "|" in l])
    res = []
    for l in linhas:
        eh_consul = "CONSUL" in l.upper() or "SALDO" in l.upper()
        if cat_solic == "CONSUL" and eh_consul:
            res.append(l)
        elif cat_solic == "CCS" and not eh_consul:
            res.append(l)
    return res

def gerar_cobranca(valor, descricao, chat_id, cat, idx):
    try:
        data = {
            "transaction_amount": float(valor),
            "description": f"RLK DATROPADOSAN - {descricao}",
            "payment_method_id": "pix",
            "payer": {
                "email": f"user{chat_id}@rlk.com",
                "first_name": "Cliente",
                "last_name": "RLK"
            },
            "notification_url": "https://ardath-unflattered-sheldon.ngrok-free.dev/webhook"
        }
        r = sdk.payment().create(data)
        if r.get("status") == 201:
            payment_id = str(r["response"]["id"])
            compras_pendentes[payment_id] = {
                "chat_id": chat_id,
                "cat": cat,
                "idx": idx
            }
            return {
                "qr_code": r["response"]["point_of_interaction"]["transaction_data"]["qr_code"],
                "init_point": r["response"]["init_point"]
            }
    except Exception as e:
        logging.error(f"Erro cobrança: {e}")
    return None

def gerar_qr_code(pix_code):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(pix_code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio

def liberar_produto(chat_id, cat, idx):
    try:
        itens = listar_estoque(cat)
        if idx >= len(itens):
            return
        item = itens[idx]
        p = item.split("|", 3)
        banco = p[0].strip()
        tipo = p[1].strip() if len(p) > 1 else ""
        extras = "|".join(p[2:]) if len(p) > 2 else ""
        txt = (
            "🔓 *PRODUTO LIBERADO AUTOMATICAMENTE*\n"
            "──────────────\n\n"
            f"🏦 `{banco}`\n"
            f"🏷️ `{tipo}`\n"
            f"🔢 `{extras}`"
        )
        safe_send_message(chat_id, txt)
    except Exception as e:
        logging.error(f"Erro liberação: {e}")

# --- FLASK WEBHOOK ---
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and "type" in data and data["type"] == "payment":
            payment_id = str(data["data"]["id"])
            if payment_id in compras_pendentes:
                info = compras_pendentes[payment_id]
                payment_info = sdk.payment().get(payment_id)
                if payment_info["response"]["status"] == "approved":
                    liberar_produto(info["chat_id"], info["cat"], info["idx"])
                    del compras_pendentes[payment_id]
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.error(f"Webhook erro: {e}")
        return jsonify({"error": "invalid"}), 400

# --- TELEGRAM BOT ---
@bot.message_handler(commands=['start', 'menu'])
def menu_principal(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💳 Comprar CCS", callback_data="listar_CCS"),
        types.InlineKeyboardButton("🛒 Comprar CONSUL", callback_data="listar_CONSUL"),
        types.InlineKeyboardButton("👥 Grupo RLK", url=GRUPO_LINK),
        types.InlineKeyboardButton("🛠️ Suporte", url=f"https://t.me/{SUPPORT_USER}")
    )
    safe_send_message(
        message.chat.id,
        "🔥 *RLK DATROPADOSAN*\n\n"
        "Pagamento automático via PIX.\n"
        "✅ Primeiro item por apenas R$0,90!",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("listar_"))
def listar(c):
    cat = c.data.split("_")[1]
    itens = listar_estoque(cat)
    if not itens:
        bot.answer_callback_query(c.id, "⚠️ Estoque vazio.", show_alert=True)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, l in enumerate(itens[:50]):
        p = l.split("|", 2)
        banco = p[0].strip()
        if cat == "CONSUL":
            try: v = float(p[1].replace("R$", "").replace(",", ".").strip())
            except: v = 120.00
            lbl = f"🛒 {banco} • R$ {v:.2f}"
        else:
            tipo = p[1].strip()
            v = obter_valor_cc(tipo, i)
            lbl = f"💳 {banco} • {tipo} • R$ {v:.2f}"
        markup.add(types.InlineKeyboardButton(lbl, callback_data=f"buy_{cat}_{i}"))
    markup.add(types.InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
    bot.edit_message_text(f"📦 *{cat}*", c.message.chat.id, c.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def comprar(c):
    bot.answer_callback_query(c.id, "⏳ Gerando pagamento...")

    try:
        cat, idx = c.data.split("_")[1], int(c.data.split("_")[2])
        itens = listar_estoque(cat)
        if idx >= len(itens):
            raise IndexError
        item = itens[idx]
        p = item.split("|", 2)
        banco = p[0].strip()

        if cat == "CCS" and idx == 0:
            pix_code = "00020126450014br.gov.bcb.pix0123bsnkconceitos@gmail.com52040000530398654040.905802BR5918DEKA202402112136586009Sao Paulo62250521mpqrinter14293823316663046DA6"
            valor = 0.90
            qr_img = gerar_qr_code(pix_code)
            caption = (
                "✅ *PAGAMENTO GERADO (R$0,90)*\n"
                "──────────────\n\n"
                f"🏦 `{banco}`\n\n"
                "👇 *Copie o código abaixo*:\n\n"
                f"`{pix_code}`\n\n"
                f"📨 Após pagar, envie comprovante para @{SUPPORT_USER}"
            )
            bot.send_photo(c.message.chat.id, qr_img, caption=caption)
        else:
            if cat == "CONSUL":
                try: valor = float(p[1].replace("R$", "").replace(",", ".").strip())
                except: valor = 120.00
            else:
                tipo = p[1].strip()
                valor = obter_valor_cc(tipo, idx)
            
            cobranca = gerar_cobranca(valor, f"{cat} - {banco}", c.message.chat.id, cat, idx)
            if not cobranca:
                safe_send_message(c.message.chat.id, "❌ Erro ao gerar pagamento.")
                return

            qr_img = gerar_qr_code(cobranca["qr_code"])
            caption = (
                "✅ *PAGAMENTO GERADO*\n"
                "──────────────\n\n"
                f"🏦 `{banco}`\n"
                f"💰 `R$ {valor:.2f}`\n\n"
                "👇 *Copie o código PIX abaixo*:\n\n"
                f"`{cobranca['qr_code']}`\n\n"
                f"💳 *Ou pague com cartão aqui*:\n"
                f"{cobranca['init_point']}\n\n"
                "🤖 *Liberação automática após pagamento!*"
            )
            bot.send_photo(c.message.chat.id, qr_img, caption=caption)

    except Exception as e:
        logging.error(f"Erro compra: {e}")
        safe_send_message(c.message.chat.id, "⚠️ Erro interno.")

@bot.callback_query_handler(func=lambda c: c.data == "voltar_menu")
def voltar(c):
    menu_principal(c.message)

@bot.message_handler(commands=['add'])
def add_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        partes = msg.text.split(" ", 2)
        cat = partes[1].lower()
        if cat not in ["ccs", "consul"]:
            safe_send_message(ADMIN_ID, "⚠️ Use 'ccs' ou 'consul'.")
            return
        with open(f"{cat}.txt", "a", encoding="utf-8") as f:
            f.write(partes[2] + "\n")
        safe_send_message(ADMIN_ID, "✅ Adicionado.")
    except:
        safe_send_message(ADMIN_ID, "⚠️ Uso: /add [ccs/consul] dados")

# --- INICIAR TUDO ---
if __name__ == "__main__":
    print("🚀 Iniciando servidor webhook...")
    threading.Thread(target=lambda: app.run(port=5000, debug=False)).start()
    print("✅ Servidor webhook ativo na porta 5000")
    print("➡️ Certifique-se de que o ngrok está rodando: ngrok http 5000")
    bot.polling(none_stop=True)