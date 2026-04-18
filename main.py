import os
import re
import psycopg2
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes
)
import google.generativeai as genai

load_dotenv()

TELEGRAM_TOKEN = ("8631285868:AAHlfQoMlNjhKUs0uEr0zjs2-ERqMW3BI2g")
DATABASE_URL = ("postgresql://postgres:xdtOelxsphCtDlneNTdsydolftxmgLhY@postgres.railway.internal:5432/railway")

BOT_USERNAME = ("@utm_help_bot").lower()

genai.configure(api_key= ("AIzaSyA3vN45ogejQK-gmYxeumGkSceRAbJrGGU"))
model = genai.GenerativeModel("gemini-1.5-flash")



conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    nombre TEXT,
    advertencias INT DEFAULT 0
);
""")
conn.commit()

def guardar_usuario(user):
    cursor.execute("""
        INSERT INTO usuarios (telegram_id, nombre)
        VALUES (%s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
    """, (user.id, user.first_name))
    conn.commit()

def advertir_usuario(user_id):
    cursor.execute("""
        UPDATE usuarios
        SET advertencias = advertencias + 1
        WHERE telegram_id = %s
        RETURNING advertencias
    """, (user_id,))
    result = cursor.fetchone()
    conn.commit()
    return result[0] if result else 1

async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for user in update.message.new_chat_members:
            await update.message.reply_text(
                f"👋 Bienvenido {user.first_name}\n\n"
                "📚 Grupo de estudio UTM\n\n"
                "Usa @TuBot para preguntar\n\n"
                "📜 Reglas:\n"
                "❌ No spam\n"
                "❌ No enlaces\n"
                "✅ Respeto\n"
            )

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto = update.message.text
    user = update.message.from_user

    guardar_usuario(user)

    if re.search(r"http[s]?://", texto):
        adv = advertir_usuario(user.id)
        await update.message.delete()

        if adv >= 2:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.id
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🚫 Usuario baneado por enviar enlaces"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Advertencia {adv}/2: No se permiten enlaces"
            )
        return

    if BOT_USERNAME not in texto.lower():
        return

    try:
        texto_lower = texto.lower()

        if "admision" in texto_lower:
            reply = "📅 Admisiones UTM:\nInscripciones: 19 enero - 1 febrero"
        elif "matricula" in texto_lower:
            reply = "🧾 La matrícula se realiza después de ser admitido en el sistema de la UTM."
        elif "semestre" in texto_lower:
            reply = "📚 La UTM maneja 2 semestres al año."
        else:
            prompt = f"""
Eres un asistente de la Universidad Técnica de Manabí (UTM).
Respondes claro, corto y preciso.
No inventes información.

Usuario: {texto}
"""
            response = model.generate_content(prompt)
            reply = response.text

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("⚠️ Error al procesar la solicitud")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

print("🤖 Bot UTM corriendo...")
app.run_polling()
