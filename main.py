import os
import re
import logging
import psycopg
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from google import genai

# ─────────────────────────────────────────────
# Configuración inicial
# ─────────────────────────────────────────────
load_dotenv()
os.environ.pop("GOOGLE_API_KEY", None)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL   = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_USERNAME   = os.getenv("BOT_USERNAME", "@utm_help_bot").lower()

for var_name, var_val in [("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
                           ("DATABASE_URL",   DATABASE_URL),
                           ("GEMINI_API_KEY", GEMINI_API_KEY)]:
    if not var_val:
        raise EnvironmentError(f"Falta la variable de entorno: {var_name}")

# ─────────────────────────────────────────────
# Cliente Gemini
# ─────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
# Conexión PostgreSQL con reconexión automática
# ─────────────────────────────────────────────
_conn = None

def get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise Exception("Conexión cerrada")
        _conn.execute("SELECT 1")
    except Exception:
        logger.warning("Reconectando a PostgreSQL...")
        _conn = psycopg.connect(DATABASE_URL)
        logger.info("✅ Reconexión exitosa")
    return _conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            nombre TEXT,
            advertencias INT DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS info_utm (
            clave TEXT PRIMARY KEY,
            valor TEXT,
            actualizado TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()

    info_base = {
        "admisiones": (
            "Admisiones UTM 2026:\n"
            "• Inscripciones: 24 enero - 01 febrero\n"
            "• Aceptacion de cupos: 03 - 06 de abril (desde las 10:00)\n"
            "• Plataforma: postulacion.utm.edu.ec\n\n"
            "WhatsApp UTM:\n"
            "• 0969238552\n"
            "• 0990181188\n"
            "Horario: 08:00-12:00 y 14:00-17:00"
        ),
        "matricula": (
            "Matricula UTM:\n"
            "1. Ingresa a app.utm.edu.ec/sga\n"
            "2. Usa tu correo institucional y contrasena\n"
            "3. Ve a Inscripciones o Solicitudes\n"
            "4. Selecciona tu carrera y paralelos\n"
            "5. Clic en Agregar para cada materia\n"
            "6. Guarda los cambios\n"
            "7. Descarga el certificado en PDF\n\n"
            "Importante:\n"
            "• Sigue el cronograma por ultimo digito de cedula\n"
            "• Si no hay cupos, usa el boton solicitar\n"
            "• El proceso es GRATUITO\n"
            "• Para primer semestre: carga documentos en el SGA"
        ),
        "carreras_web": (
            "• Ingenieria Civil\n"
            "• Ingenieria Industrial\n"
            "• Ingenieria Quimica\n"
            "• Electronica y Automatizacion\n"
            "• Electricidad\n"
            "• Biotecnologia\n"
            "• Geologia\n"
            "• Mecatronica\n"
            "• Biologia\n"
            "• Quimica\n"
            "• Fisica\n"
            "• Medicina\n"
            "• Enfermeria\n"
            "• Odontologia\n"
            "• Nutricion y Dietetica\n"
            "• Bioquimica y Farmacia\n"
            "• Medicina Veterinaria\n"
            "• Agroindustria\n"
            "• Agronegocios (Modalidad Hibrida)\n"
            "• Biodiversidad y Recursos Geneticos\n"
            "• Sistemas de Informacion\n"
            "• Tecnologias de la Informacion\n"
            "• Tecnologias de la Informacion (En Linea)\n"
            "• Realidad Virtual y Videojuegos (Hibrida)\n"
            "• Economia (Hibrida)\n"
            "• Economia (En Linea)\n"
            "• Contabilidad y Auditoria (Hibrida)\n"
            "• Administracion de Empresas (Hibrida)\n"
            "• Administracion de Empresas (En Linea)\n"
            "• Turismo (Hibrida)\n"
            "• Turismo (En Linea)\n"
            "• Negocios Digitales (En Linea)\n"
            "• Logistica y Transporte\n"
            "• Gastronomia\n"
            "• Educacion Basica (En Linea)\n"
            "• Educacion Inicial (En Linea)\n"
            "• Pedagogia de los Idiomas Nacionales y Extranjeros\n"
            "• Pedagogia de las Ciencias Experimentales (Quimica y Biologia)\n"
            "• Pedagogia de las Ciencias Experimentales (Matematicas y Fisica)\n"
            "• Pedagogia de Actividad Fisica y Deporte\n"
            "• Pedagogia de la Lengua y Literatura\n"
            "• Entrenamiento Deportivo\n"
            "• Psicologia (En Linea)\n"
            "• Trabajo Social\n"
            "• Derecho (Hibrida)\n"
            "• Derecho (En Linea)\n"
            "• Sociologia (Hibrida)\n"
            "• Tecnologias Geoespaciales"
        ),
    }
    for clave, valor in info_base.items():
        conn.execute("""
            INSERT INTO info_utm (clave, valor, actualizado)
            VALUES (%s, %s, NOW())
            ON CONFLICT (clave) DO UPDATE
            SET valor = EXCLUDED.valor, actualizado = NOW()
        """, (clave, valor))
    conn.commit()
    logger.info("✅ Tablas e info base listas")

def guardar_usuario(user):
    try:
        conn = get_conn()
        conn.execute("""
            INSERT INTO usuarios (telegram_id, nombre)
            VALUES (%s, %s)
            ON CONFLICT (telegram_id) DO NOTHING
        """, (user.id, user.first_name))
        conn.commit()
    except Exception as e:
        logger.error(f"Error al guardar usuario: {e}")

def advertir_usuario(user_id):
    try:
        conn = get_conn()
        result = conn.execute("""
            UPDATE usuarios
            SET advertencias = advertencias + 1
            WHERE telegram_id = %s
            RETURNING advertencias
        """, (user_id,)).fetchone()
        conn.commit()
        return result[0] if result else 1
    except Exception as e:
        logger.error(f"Error al advertir: {e}")
        return 1

def obtener_info(clave):
    try:
        conn = get_conn()
        result = conn.execute(
            "SELECT valor FROM info_utm WHERE clave = %s", (clave,)
        ).fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error al obtener info: {e}")
        return None

# ─────────────────────────────────────────────
# Menú principal
# ─────────────────────────────────────────────
def menu_principal():
    teclado = [
        [
            InlineKeyboardButton("📅 Admisiones", callback_data="admision"),
            InlineKeyboardButton("🧾 Matricula",  callback_data="matricula"),
        ],
        [
            InlineKeyboardButton("🎓 Carreras",   callback_data="carreras"),
            InlineKeyboardButton("💰 Costos",     callback_data="costo"),
        ],
        [
            InlineKeyboardButton("🕐 Horarios",   callback_data="horario"),
            InlineKeyboardButton("📍 Ubicacion",  callback_data="ubicacion"),
        ],
        [
            InlineKeyboardButton("📞 Contacto",   callback_data="contacto"),
            InlineKeyboardButton("🌐 Sitio UTM",  url="https://www.utm.edu.ec"),
        ],
    ]
    return InlineKeyboardMarkup(teclado)

# ─────────────────────────────────────────────
# Comandos
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guardar_usuario(update.effective_user)
    await update.message.reply_text(
        "Hola! Soy el asistente virtual de la UTM\n\n"
        "Puedo ayudarte con informacion sobre:\n"
        "Admisiones y matricula\n"
        "Carreras disponibles\n"
        "Horarios y costos\n"
        "Contacto\n\n"
        "Elige una opcion o escribe tu pregunta:",
        reply_markup=menu_principal()
    )

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n\n"
        "/start - Menu principal\n"
        "/ayuda - Ver esta ayuda\n"
        "/admisiones - Info de admisiones 2026\n"
        "/matricula - Como matricularse\n"
        "/carreras - Lista de carreras\n"
        "/contacto - Datos de contacto\n"
        "/horarios - Horarios de atencion\n\n"
        "Tambien puedes escribir tu pregunta directamente.",
        reply_markup=menu_principal()
    )

async def cmd_admisiones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = obtener_info("admisiones")
    await update.message.reply_text(
        f"Admisiones UTM\n\n{info}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Postulacion UTM", url="https://postulacion.utm.edu.ec")
        ]])
    )

async def cmd_matricula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = obtener_info("matricula")
    await update.message.reply_text(
        f"Matricula UTM\n\n{info}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Ir al SGA", url="https://app.utm.edu.ec/sga")
        ]])
    )

async def cmd_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    carreras = obtener_info("carreras_web")
    await update.message.reply_text(
        f"Carreras UTM\n\n{carreras}\n\nVer todas en utm.edu.ec",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Ver facultades", url="https://www.utm.edu.ec/oferta-academica/grado/facultades")
        ]])
    )

async def cmd_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Contacto UTM\n\n"
        "Web: www.utm.edu.ec\n"
        "Email: info@utm.edu.ec\n"
        "Direccion: Av. Urbina y Che Guevara, Portoviejo, Manabi\n\n"
        "WhatsApp:\n"
        "0969238552\n"
        "0990181188\n"
        "Horario: 08:00-12:00 y 14:00-17:00\n\n"
        "Redes sociales:\n"
        "Twitter: @UTMManabi\n"
        "Instagram: @utm_manabi\n"
        "Facebook: utmmanabi\n"
        "TikTok: @utm_manabi",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Visitar utm.edu.ec", url="https://www.utm.edu.ec")
        ]])
    )

async def cmd_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Horarios UTM\n\n"
        "Lunes a viernes 08h00 - 17h00"
    )

# ─────────────────────────────────────────────
# Botones interactivos
# ─────────────────────────────────────────────
async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dato = query.data

    if dato == "admision":
        info = obtener_info("admisiones")
        await query.message.reply_text(
            f"Admisiones UTM\n\n{info}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Postulacion UTM", url="https://postulacion.utm.edu.ec")
            ]])
        )

    elif dato == "matricula":
        info = obtener_info("matricula")
        await query.message.reply_text(
            f"Matricula UTM\n\n{info}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ir al SGA", url="https://app.utm.edu.ec/sga")
            ]])
        )

    elif dato == "carreras":
        carreras = obtener_info("carreras_web")
        await query.message.reply_text(
            f"Carreras UTM\n\n{carreras}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver facultades", url="https://www.utm.edu.ec/oferta-academica/grado/facultades")
            ]])
        )

    elif dato == "costo":
        await query.message.reply_text(
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver utm.edu.ec", url="https://www.utm.edu.ec")
            ]])
        )

    elif dato == "horario":
        await query.message.reply_text(
            "Horarios UTM\n\n"
            "Lunes a viernes 08h00 - 17h00\n"
            "Telefono: (593 5) 263-2677"
        )

    elif dato == "ubicacion":
        await query.message.reply_text(
            "Ubicacion UTM\n\n"
            "Av. Urbina y Che Guevara\n"
            "Portoviejo, Manabi, Ecuador",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver en Google Maps", url="https://maps.google.com/?q=Universidad+Tecnica+de+Manabi+Portoviejo")
            ]])
        )

    elif dato == "contacto":
        await query.message.reply_text(
            "Contacto UTM\n\n"
            "Web: www.utm.edu.ec\n"
            "Email: info@utm.edu.ec\n"
            "Portoviejo, Manabi\n\n"
            "WhatsApp:\n"
            "0969238552\n"
            "0990181188\n"
            "Horario: 08:00-12:00 y 14:00-17:00",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Visitar utm.edu.ec", url="https://www.utm.edu.ec")
            ]])
        )

# ─────────────────────────────────────────────
# Bienvenida
# ─────────────────────────────────────────────
async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for user in update.message.new_chat_members:
            await update.message.reply_text(
                f"Bienvenido {user.first_name}!\n\n"
                "Grupo de estudio UTM\n\n"
                f"Escribe {BOT_USERNAME} seguido de tu pregunta\n"
                "o usa /start para ver el menu.\n\n"
                "Reglas:\n"
                "No spam\n"
                "No enlaces\n"
                "Respeto mutuo"
            )

# ─────────────────────────────────────────────
# Manejador de mensajes
# ─────────────────────────────────────────────
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto    = update.message.text
    user     = update.effective_user
    es_grupo = update.effective_chat.type in ["group", "supergroup"]

    guardar_usuario(user)

    # Detectar enlaces en grupos
    if es_grupo and re.search(r"http[s]?://", texto):
        adv = advertir_usuario(user.id)
        try:
            await update.message.delete()
        except Exception:
            pass
        if adv >= 2:
            try:
                await context.bot.ban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user.id
                )
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{user.first_name} fue baneado por enviar enlaces."
                )
            except Exception as e:
                logger.error(f"No se pudo banear: {e}")
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Advertencia {adv}/2 para {user.first_name}: No se permiten enlaces."
            )
        return

    # En grupos solo responder si mencionan al bot
    if es_grupo and BOT_USERNAME not in texto.lower():
        return

    texto_lower = texto.lower()

    # Admisiones
    if any(p in texto_lower for p in ["admis", "inscripci", "ingreso", "postula"]):
        info = obtener_info("admisiones")
        await update.message.reply_text(
            f"Admisiones UTM\n\n{info}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Postulacion UTM", url="https://postulacion.utm.edu.ec")
            ]])
        )
        return

    # Matricula
    if any(p in texto_lower for p in ["matricula", "matrícula", "materias", "paralelo", "sga"]):
        info = obtener_info("matricula")
        await update.message.reply_text(
            f"Matricula UTM\n\n{info}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ir al SGA", url="https://app.utm.edu.ec/sga")
            ]])
        )
        return

    # Carreras
    if any(p in texto_lower for p in ["carrera", "facultad", "oferta"]):
        carreras = obtener_info("carreras_web")
        await update.message.reply_text(
            f"Carreras UTM\n\n{carreras}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver facultades", url="https://www.utm.edu.ec/oferta-academica/grado/facultades")
            ]])
        )
        return

    # Contacto
    if any(p in texto_lower for p in ["contacto", "whatsapp", "telefono", "teléfono"]):
        await update.message.reply_text(
            "Contacto UTM\n\n"
            "WhatsApp:\n"
            "0969238552\n"
            "0990181188\n"
            "Horario: 08:00-12:00 y 14:00-17:00\n\n"
            "Email: info@utm.edu.ec",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Visitar utm.edu.ec", url="https://www.utm.edu.ec")
            ]])
        )
        return

    # Horarios
    if any(p in texto_lower for p in ["horario", "atencion", "atención"]):
        await update.message.reply_text(
            "Horarios UTM\n\n"
            "Lunes a viernes 08h00 - 17h00\n"
            "Telefono: (593 5) 263-2677"
        )
        return

    # Costos
    if any(p in texto_lower for p in ["costo", "precio", "gratis", "gratuito", "pagar"]):
        await update.message.reply_text(
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo."
        )
        return

    # Ubicacion
    if any(p in texto_lower for p in ["ubicacion", "ubicación", "donde", "dónde", "direccion"]):
        await update.message.reply_text(
            "Ubicacion UTM\n\n"
            "Av. Urbina y Che Guevara\n"
            "Portoviejo, Manabi, Ecuador",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver en Google Maps", url="https://maps.google.com/?q=Universidad+Tecnica+de+Manabi+Portoviejo")
            ]])
        )
        return

    # Menu
    if any(p in texto_lower for p in ["menu", "menú", "opciones", "ayuda", "help"]):
        await update.message.reply_text(
            "Elige una opcion:",
            reply_markup=menu_principal()
        )
        return

    # Gemini AI
    try:
        admisiones = obtener_info("admisiones") or ""
        matricula  = obtener_info("matricula")  or ""
        carreras   = obtener_info("carreras_web") or ""

        prompt = (
            "Eres un asistente oficial de la Universidad Tecnica de Manabi (UTM)"
            "Respondes de forma clara, corta y precisa en espanol. "
            "No inventes informacion. Si no sabes algo, sugiere visitar www.utm.edu.ec "
            "o contactar por WhatsApp al 0969238552.\n\n"
            f"Admisiones UTM:\n{admisiones}\n\n"
            f"Matricula UTM:\n{matricula}\n\n"
            f"Carreras UTM:\n{carreras}\n\n"
            f"Usuario: {texto}"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        await update.message.reply_text(
            response.text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Mas info en utm.edu.ec", url="https://www.utm.edu.ec")
            ]])
        )

    except Exception as e:
        logger.error(f"Error Gemini: {e}")
        await update.message.reply_text(
            "No pude procesar tu pregunta.\n"
            "Visita utm.edu.ec o contactanos por WhatsApp al 0969238552.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("utm.edu.ec", url="https://www.utm.edu.ec")
            ]])
        )

# ─────────────────────────────────────────────
# Arranque
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("ayuda",      cmd_ayuda))
    app.add_handler(CommandHandler("help",       cmd_ayuda))
    app.add_handler(CommandHandler("admisiones", cmd_admisiones))
    app.add_handler(CommandHandler("matricula",  cmd_matricula))
    app.add_handler(CommandHandler("carreras",   cmd_carreras))
    app.add_handler(CommandHandler("contacto",   cmd_contacto))
    app.add_handler(CommandHandler("horarios",   cmd_horarios))

    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    logger.info("🤖 Bot UTM corriendo...")
    app.run_polling()