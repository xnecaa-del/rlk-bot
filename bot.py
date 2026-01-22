import telebot
from telebot import types
import mercadopago
import os
import logging
import qrcode
from io import BytesIO
import threading
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
            return {
                "qr_code": r["response"]["point_of_interaction"]["transaction_data"]["qr
