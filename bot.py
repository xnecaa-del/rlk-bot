import telebot
from telebot import types
import mercadopago
import os
import logging
import qrcode
from io import BytesIO
from flask import Flask, request, jsonify

# --- CONFIGURAÇÕES ---
TOKEN = '8219509702:AAEQThWquHwt5e4V2YSL7vZdcCsdYVpwsW4'
MP_TOKEN = 'APP_USR-6894935873237030-012111-0bf28881a74fe3acc533c3b83cc0dfbc-1680044822'
ADMIN_ID = 8337105439
SUPPORT_USER = "RLKDATROPADOSAN"
GRUPO_LINK = "https://t.me/+qRi9ljZuHgRiYTMx"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
sdk = mercadopago.SDK(MP_TOKEN)
logging.basicConfig(level=logging.INFO)

compras_pendentes = {}

def safe_send_message(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logging.error(f"Erro ao enviar para {chat_id}: {e}")
        return None

def obter_valor_cc(idx=0):
    return 0.90 if idx == 0 else 35.00

def listar_estoque(arquivo):
    if not os.path.exists(arquivo):
        return []
    with open(arquivo, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if "|" in l]

def remover_item(arquivo, indice):
    itens = listar_estoque(arquivo)
    if 0 <= indice < len(itens):
        del itens[indice]
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write("\n".join(itens) + ("\n" if itens else ""))

def obter_dados_completos(indice):
    ccs = listar_estoque("CC's.txt")
    ful = listar_estoque("CC ful dados.txt")
    if indice < len(ccs) and indice < len(ful):
        num = ccs[indice].split("|")[0]
        dados_ful = ful[indice].split("|")
        return {
            "numero": num,
            "nome": dados_ful[0] if len(dados_ful) > 0 else "",
            "cpf": dados_ful[1] if len(dados_ful) > 1 else "",
            "banco": dados_ful[2] if len(dados_ful) > 2 else "",
            "endereco": "|".join(dados_ful[3:]) if len(dados_ful) > 3 else ""
        }
    return None

def gerar_cobranca(valor, descricao, chat_id, tipo, indice):
    try:
        data = {
            "transaction_amount": float(valor),
            "description": f"RLK DATROPADOSAN - {descricao}",
            "payment_method_id": "pix",
            "payer": {
                "email": f"user{chat_id}@rlk.com",
                "first_name": "Cliente",
                "last_name": "RLK",
                "identification": {"type": "CPF", "number": "19119119100"}
            },
            "notification_url": "https://rlk-bot-production.up.railway.app/webhook"
        }
        r = sdk.payment().create(data)
        if r.get("status") == 201:
            payment_id = str(r["response"]["id"])
            compras_pendentes[payment_id] = {
                "chat_id": chat_id,
                "tipo": tipo,
                "indice": indice
            }
            # Garantir que os campos existem
            qr_code = r["response"]["point_of_interaction"]["transaction_data"].get("qr_code", "")
            init_point = r["response"].get("init_point", "")
            return {
                "qr_code": qr_code,
                "init_point": init_point
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

def liberar_produto(chat_id, tipo, indice):
    try:
        if tipo == "CC":
            dados = obter_dados_completos(indice)
            if not dados:
                return
            txt = (
                "🔓 *DADO LIBERADO*\n"
                "──────────────\n\n"
                f"🏦 `{dados['banco']}`\n"
                f"🔢 `{dados['numero']}`\n"
                f"👤 `{dados['nome']}`\n"
                f"🆔 `{dados['cpf']}`\n"
                f"🏠 `{dados['endereco']}`"
            )
            remover_item("CC's.txt", indice)
            remover_item("CC ful dados.txt", indice)
        else:
            consultaveis = listar_estoque("Consultaveis ful Dados.txt")
            if indice >= len(consultaveis):
                return
            item = consultaveis[indice]
            banco, valor = item.split("|", 1)
            txt = (
                "🔓 *CONSULTAVEL LIBERADA*\n"
                "──────────────\n\n"
                f"🏦 `{banco}`\n"
                f"💰 `{valor}`"
            )
            remover_item("Consultaveis ful Dados.txt", indice)
        
        safe_send_message(chat_id, txt)
    except Exception as e:
        logging.error(f"Erro liberação: {e}")

# --- FLASK WEBHOOK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot RLK DATROPADOSAN Online"

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
                    liberar_produto(info["chat_id"], info["tipo"], info["indice"])
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
        types.InlineKeyboardButton("💳 CC's", callback_data="listar_CC"),
        types.InlineKeyboardButton("🛒 Consultáveis", callback_data="listar_CONSUL"),
        types.InlineKeyboardButton("👥 Grupo RLK", url=GRUPO_LINK),
        types.InlineKeyboardButton("🛠️ Suporte", url=f"https://t.me/{SUPPORT_USER}")
    )
    safe_send_message(
        message.chat.id,
        "🔥 *RLK DATROPADOSAN*\n\nAS MELHORES CC's e Consultaveis da dark/web Coletadas com admin de motel 5 estrelas.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("listar_"))
def listar(c):
    tipo = c.data.split("_")[1]
    if tipo == "CC":
        arquivo = "CC's.txt"
        icone = "💳"
    else:
        arquivo = "Consultaveis ful Dados.txt"
        icone = "🛒"
    
    itens = listar_estoque(arquivo)
    if not itens:
        bot.answer_callback_query(c.id, "⚠️ SEM ESTOQUE AGORA PAE , AGUARDE REPOSIÇÃO.", show_alert=True)
        return
    
    if tipo == "CC":
        mostrar_cc(c.message.chat.id, 0, c.message.message_id)
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, item in enumerate(itens[:50]):
            lbl = f"{icone} {item}"
            markup.add(types.InlineKeyboardButton(lbl, callback_data=f"buy_CONSUL_{i}"))
        markup.add(types.InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
        bot.edit_message_text(f"📦 *{tipo}*", c.message.chat.id, c.message.message_id, reply_markup=markup)

def mostrar_cc(chat_id, indice, message_id=None):
    ccs = listar_estoque("CC's.txt")
    if not ccs or indice >= len(ccs):
        bot.send_message(chat_id, "⚠️ Estoque vazio.")
        return
    
    num = ccs[indice].split("|")[0]
    mascarado = f"{num[:6]}******{num[-4:]}"
    
    botoes = []
    if indice > 0:
        botoes.append(types.InlineKeyboardButton("◀️ Anterior", callback_data=f"navegar_CC_{indice-1}"))
    botoes.append(types.InlineKeyboardButton("🛒 Comprar", callback_data=f"buy_CC_{indice}"))
    if indice < len(ccs) - 1:
        botoes.append(types.InlineKeyboardButton("Próximo ▶️", callback_data=f"navegar_CC_{indice+1}"))
    botoes.append(types.InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*botoes)
    
    texto = (
        "💳 *CC SANSTORE*\n"
        "──────────────\n\n"
        f"`{mascarado}`\n\n"
        "ℹ️ *NÃO POSSUI DADOS DE BICO.*\n"
        "*SOMENTE CC's COM GARANTIA DE LIVE, MAS NÃO DE SALDO.*"
    )
    
    try:
        with open("cartao.jpg", "rb") as photo:
            if message_id:
                bot.edit_message_caption(chat_id, message_id, caption=texto, reply_markup=markup)
            else:
                bot.send_photo(chat_id, photo, caption=texto, reply_markup=markup)
    except Exception as e:
        logging.error(f"Erro ao enviar imagem: {e}")
        if message_id:
            bot.edit_message_text(texto, chat_id, message_id, reply_markup=markup)
        else:
            safe_send_message(chat_id, texto, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("navegar_CC_"))
def navegar_cc(c):
    indice = int(c.data.split("_")[2])
    mostrar_cc(c.message.chat.id, indice, c.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def comprar(c):
    partes = c.data.split("_")
    tipo = partes[1]
    indice = int(partes[2])
    
    if tipo == "CC":
        arquivo = "CC's.txt"
        itens = listar_estoque(arquivo)
        if indice >= len(itens):
            bot.answer_callback_query(c.id, "⚠️ Item indisponível.", show_alert=True)
            return
        num = itens[indice].split("|")[0]
        mascarado = f"{num[:6]}******{num[-4:]}"
        valor = obter_valor_cc(indice)
        descricao = f"CC {mascarado}"
    else:
        arquivo = "Consultaveis ful Dados.txt"
        itens = listar_estoque(arquivo)
        if indice >= len(itens):
            bot.answer_callback_query(c.id, "⚠️ Item indisponível.", show_alert=True)
            return
        item = itens[indice]
        banco, val_str = item.split("|", 1)
        try:
            valor = float(val_str.replace("R$", "").replace(",", "."))
        except:
            valor = 120.00
        descricao = f"CONSUL {banco}"
    
    cobranca = gerar_cobranca(valor, descricao, c.message.chat.id, tipo, indice)
    if not cobranca:
        safe_send_message(c.message.chat.id, "❌ PIX FORA DO AR TENTA DENOVO DEPOIS PAE.")
        return
    
    qr_img = gerar_qr_code(cobranca["qr_code"])
    caption = (
        "✅ *PAGAMENTO GERADO BIGODE, LIBERAÇÃO INSTANTÂNEA!*\n"
        "──────────────\n\n"
        f"💰 `R$ {valor:.2f}`\n\n"
        "👇 *Copie o código PIX abaixo*:\n\n"
        f"`{cobranca['qr_code']}`\n\n"
        f"💳 *Ou pague com cartão aqui*:\n"
        f"{cobranca['init_point']}\n\n"
        "🤖 *Liberação automática após pagamento!*"
    )
    bot.send_photo(c.message.chat.id, qr_img, caption=caption)

@bot.callback_query_handler(func=lambda c: c.data == "voltar_menu")
def voltar(c):
    menu_principal(c.message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False)).start()
    bot.polling(none_stop=True)
