import os
import re
import asyncio
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

def _parse_admins():
    raw = os.getenv("ADMIN_IDS", "5504260343,6501594656")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]

ADMINS = _parse_admins()

CONTACTO_WHATSAPP = (
    "0986616388\n"
    "0999304713\n"
    "0969238552\n"
    "0990181188"
)
HORARIO_ATENCION = "08:00-12:00 y 14:00-18:00"

INFO_ADMISIONES = (
    "Admisiones UTM 2026:\n"
    "- Inscripciones: 24 enero - 01 febrero\n"
    "- Aceptacion de cupos: 03 al 06 de abril (desde las 10:00)\n"
    "- Plataforma: postulacion.utm.edu.ec\n\n"
    "WhatsApp UTM:\n"
    "- 0986616388\n"
    "- 0999304713\n"
    "- 0969238552\n"
    "- 0990181188\n"
    f"Horario: {HORARIO_ATENCION}"
)

INFO_MATRICULA = (
    "Matricula UTM - SGU (S1-2026):\n"
    "La UTM utiliza el Sistema de Gestion Universitaria (SGU). El antiguo SGA ya no esta en uso.\n"
    "Acceso: https://sgu.utm.edu.ec/auth/login\n\n"
    "Pasos:\n"
    "1. Ingresa al SGU\n"
    "   - Ve a sgu.utm.edu.ec/auth/login\n"
    "   - Usuario: inicial del primer nombre + primer apellido completo + ultimos 4 digitos de cedula\n"
    "     Ejemplo: Juan Perez 1234567890 -> jperez7890\n"
    "   - Correo institucional: jperez7890@utm.edu.ec\n"
    "   - Contrasena: numero de cedula completo\n"
    "   - Si olvidaste tu contrasena, usa 'Olvide mi contrasena' en el SGU\n"
    "   - Escoge Rol: Aspirante (nuevos) o Estudiante (ya matriculados antes)\n\n"
    "2. Completa tus datos personales\n"
    "   - Foto tipo carnet (fondo blanco)\n"
    "   - PDF cedula (anverso y reverso en un solo archivo)\n"
    "   - Certificado de votacion vigente\n"
    "   - Titulo de Bachiller en PDF\n\n"
    "3. Selecciona la matricula\n"
    "   - Ve a: Pregrado > Matricula / Inscripcion a Semestre\n"
    "   - Elige carrera, modalidad y periodo S1-2026\n"
    "   - Revisa y confirma tu horario de clases\n\n"
    "4. Genera tu comprobante\n"
    "   - Descarga o imprime el comprobante de matricula\n\n"
    "El proceso es 100% gratuito y en linea.\n"
    f"Soporte WhatsApp: {CONTACTO_WHATSAPP.replace(chr(10), ' / ')}\n"
    f"Horario: {HORARIO_ATENCION}"
)

INFO_CARRERAS = (
    "Ingenieria Civil\n"
    "Ingenieria Industrial\n"
    "Ingenieria Quimica\n"
    "Electronica y Automatizacion\n"
    "Electricidad\n"
    "Biotecnologia\n"
    "Geologia\n"
    "Mecatronica\n"
    "Biologia\n"
    "Quimica\n"
    "Fisica\n"
    "Medicina\n"
    "Enfermeria\n"
    "Odontologia\n"
    "Nutricion y Dietetica\n"
    "Bioquimica y Farmacia\n"
    "Medicina Veterinaria\n"
    "Agroindustria\n"
    "Agronegocios (Modalidad Hibrida)\n"
    "Biodiversidad y Recursos Geneticos\n"
    "Sistemas de Informacion\n"
    "Tecnologias de la Informacion\n"
    "Tecnologias de la Informacion (En Linea)\n"
    "Realidad Virtual y Videojuegos (Hibrida)\n"
    "Economia (Hibrida)\n"
    "Economia (En Linea)\n"
    "Contabilidad y Auditoria (Hibrida)\n"
    "Administracion de Empresas (Hibrida)\n"
    "Administracion de Empresas (En Linea)\n"
    "Turismo (Hibrida)\n"
    "Turismo (En Linea)\n"
    "Negocios Digitales (En Linea)\n"
    "Logistica y Transporte\n"
    "Gastronomia\n"
    "Educacion Basica (En Linea)\n"
    "Educacion Inicial (En Linea)\n"
    "Pedagogia de los Idiomas Nacionales y Extranjeros\n"
    "Pedagogia de las Ciencias Experimentales (Quimica y Biologia)\n"
    "Pedagogia de las Ciencias Experimentales (Matematicas y Fisica)\n"
    "Pedagogia de Actividad Fisica y Deporte\n"
    "Pedagogia de la Lengua y Literatura\n"
    "Entrenamiento Deportivo\n"
    "Psicologia (En Linea)\n"
    "Trabajo Social\n"
    "Derecho (Hibrida)\n"
    "Derecho (En Linea)\n"
    "Sociologia (Hibrida)\n"
    "Tecnologias Geoespaciales"
)

INFO_BASE = {
    "admisiones": INFO_ADMISIONES,
    "matricula": INFO_MATRICULA,
    "carreras_web": INFO_CARRERAS,
}

SECCIONES_DB = {
    "admision": ("Admisiones UTM", "admisiones", [("Postulacion UTM", "https://postulacion.utm.edu.ec")]),
    "matricula": ("Matricula UTM - SGU", "matricula", [("Ir al SGU", "https://sgu.utm.edu.ec/auth/login")]),
    "carreras": ("Carreras UTM", "carreras_web", [("Ver facultades", "https://www.utm.edu.ec/oferta-academica/grado/facultades")]),
}

for var_name, var_val in [("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
                           ("DATABASE_URL",   DATABASE_URL),
                           ("GEMINI_API_KEY", GEMINI_API_KEY)]:
    if not var_val:
        raise EnvironmentError(f"Falta la variable de entorno: {var_name}")

client = genai.Client(api_key=GEMINI_API_KEY)

_conn = None

def get_conn():
    global _conn
    try:
        if _conn is None or _conn.closed:
            raise Exception("Conexion cerrada")
        _conn.execute("SELECT 1")
    except Exception:
        logger.warning("Reconectando a PostgreSQL...")
        _conn = psycopg.connect(DATABASE_URL)
        logger.info("Reconexion exitosa")
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

    for clave, valor in INFO_BASE.items():
        conn.execute("""
            INSERT INTO info_utm (clave, valor, actualizado)
            VALUES (%s, %s, NOW())
            ON CONFLICT (clave) DO NOTHING
        """, (clave, valor))
    conn.commit()
    logger.info("Tablas e info base listas")

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
        return result[0] if result else INFO_BASE.get(clave)
    except Exception as e:
        logger.error(f"Error al obtener info: {e}")
        return INFO_BASE.get(clave)

def markup_botones(botones):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(texto, url=url) for texto, url in botones]
    ])

def texto_contacto(completo=False):
    texto = (
        "Contacto UTM\n\n"
        "Web: www.utm.edu.ec\n"
        "Email: info@utm.edu.ec\n"
    )
    if completo:
        texto += "Direccion: Av. Urbina y Che Guevara, Portoviejo, Manabi\n\n"
    else:
        texto += "Portoviejo, Manabi\n\n"
    texto += (
        f"WhatsApp:\n{CONTACTO_WHATSAPP}\n"
        f"Horario: {HORARIO_ATENCION}"
    )
    if completo:
        texto += (
            "\n\nRedes sociales:\n"
            "Twitter: @UTMManabi\n"
            "Instagram: @utm_manabi\n"
            "Facebook: utmmanabi\n"
            "TikTok: @utm_manabi"
        )
    return texto

async def enviar_seccion_db(message, seccion, footer=""):
    titulo, clave, botones = SECCIONES_DB[seccion]
    info = obtener_info(clave) or "Informacion no disponible. Visita www.utm.edu.ec"
    await message.reply_text(
        f"{titulo}\n\n{info}{footer}",
        reply_markup=markup_botones(botones)
    )

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
        "/horarios - Horarios de atencion\n"
        "Tambien puedes escribir tu pregunta directamente.",
        reply_markup=menu_principal()
    )

async def cmd_miid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Tu ID de Telegram es: {update.effective_user.id}")

async def cmd_admisiones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, "admision")

async def cmd_matricula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, "matricula")

async def cmd_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_seccion_db(update.message, "carreras", footer="\n\nVer todas en utm.edu.ec")

async def cmd_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        texto_contacto(completo=True),
        reply_markup=markup_botones([("Visitar utm.edu.ec", "https://www.utm.edu.ec")])
    )

async def cmd_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Horarios UTM\n\n"
        "Lunes a viernes 08h00 - 17h00"
    )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dato = query.data

    if dato in SECCIONES_DB:
        await enviar_seccion_db(query.message, dato)
    elif dato == "costo":
        await query.message.reply_text(
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo.",
            reply_markup=markup_botones([("Ver utm.edu.ec", "https://www.utm.edu.ec")])
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
            reply_markup=markup_botones([("Ver en Google Maps", "https://maps.google.com/?q=Universidad+Tecnica+de+Manabi+Portoviejo")])
        )
    elif dato == "contacto":
        await query.message.reply_text(
            texto_contacto(),
            reply_markup=markup_botones([("Visitar utm.edu.ec", "https://www.utm.edu.ec")])
        )

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

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto    = update.message.text
    user     = update.effective_user
    es_grupo = update.effective_chat.type in ["group", "supergroup"]

    guardar_usuario(user)

    if es_grupo and re.search(r"http[s]?://", texto):
        if user.id not in ADMINS:
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

    if es_grupo and BOT_USERNAME not in texto.lower():
        return

    texto_lower = texto.lower()

    if any(p in texto_lower for p in ["admis", "inscripci", "ingreso", "postula"]):
        await enviar_seccion_db(update.message, "admision")
        return

    if any(p in texto_lower for p in ["matricula", "matrícula", "materias", "paralelo", "sgu", "sga", "sistema de gestion", "como matricul"]):
        await enviar_seccion_db(update.message, "matricula")
        return

    if any(p in texto_lower for p in ["carrera", "facultad", "oferta"]):
        await enviar_seccion_db(update.message, "carreras")
        return

    if any(p in texto_lower for p in ["contacto", "whatsapp", "telefono", "teléfono"]):
        await update.message.reply_text(
            texto_contacto(),
            reply_markup=markup_botones([("Visitar utm.edu.ec", "https://www.utm.edu.ec")])
        )
        return

    if any(p in texto_lower for p in ["horario", "atencion", "atención"]):
        await update.message.reply_text(
            "Horarios UTM\n\n"
            "Lunes a viernes 08h00 - 17h00\n"
            "Telefono: (593 5) 263-2677"
        )
        return

    if any(p in texto_lower for p in ["costo", "precio", "gratis", "gratuito", "pagar"]):
        await update.message.reply_text(
            "Costos UTM\n\n"
            "La UTM es universidad publica y gratuita.\n"
            "La matriculacion no tiene ningun costo."
        )
        return

    if any(p in texto_lower for p in ["ubicacion", "ubicación", "donde", "dónde", "direccion"]):
        await update.message.reply_text(
            "Ubicacion UTM\n\n"
            "Av. Urbina y Che Guevara\n"
            "Portoviejo, Manabi, Ecuador",
            reply_markup=markup_botones([("Ver en Google Maps", "https://maps.google.com/?q=Universidad+Tecnica+de+Manabi+Portoviejo")])
        )
        return

    if any(p in texto_lower for p in ["menu", "menú", "opciones", "ayuda", "help"]):
        await update.message.reply_text(
            "Elige una opcion:",
            reply_markup=menu_principal()
        )
        return

    try:
        admisiones = obtener_info("admisiones") or ""
        matricula  = obtener_info("matricula")  or ""
        carreras   = obtener_info("carreras_web") or ""

        prompt = (
            "Eres un asistente oficial de la Universidad Tecnica de Manabi (UTM). "
            "Respondes de forma clara, corta y precisa en espanol. "
            "IMPORTANTE: La UTM ya NO usa el SGA (Sistema de Gestion Academica). "
            "Ahora usa el SGU (Sistema de Gestion Universitaria) en sgu.utm.edu.ec. "
            "Si alguien pregunta por el SGA, corrigelo y dirige al SGU. "
            "No inventes informacion. Si no sabes algo, sugiere visitar www.utm.edu.ec "
            "o contactar por WhatsApp al 0986616388.\n\n"
            f"Admisiones UTM:\n{admisiones}\n\n"
            f"Matricula UTM (SGU):\n{matricula}\n\n"
            f"Carreras UTM:\n{carreras}\n\n"
            f"Usuario: {texto}"
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt
        )
        respuesta = response.text or "No pude generar una respuesta. Visita www.utm.edu.ec"
        await update.message.reply_text(
            respuesta,
            reply_markup=markup_botones([("Mas info en utm.edu.ec", "https://www.utm.edu.ec")])
        )

    except Exception as e:
        logger.error(f"Error Gemini: {e}")
        await update.message.reply_text(
            "No pude procesar tu pregunta.\n"
            "Visita utm.edu.ec o contactanos por WhatsApp al 0986616388.",
            reply_markup=markup_botones([("utm.edu.ec", "https://www.utm.edu.ec")])
        )

if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("ayuda",      cmd_ayuda))
    app.add_handler(CommandHandler("help",       cmd_ayuda))
    app.add_handler(CommandHandler("miid",       cmd_miid))
    app.add_handler(CommandHandler("admisiones", cmd_admisiones))
    app.add_handler(CommandHandler("matricula",  cmd_matricula))
    app.add_handler(CommandHandler("carreras",   cmd_carreras))
    app.add_handler(CommandHandler("contacto",   cmd_contacto))
    app.add_handler(CommandHandler("horarios",   cmd_horarios))

    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    logger.info("Bot UTM corriendo...")
    app.run_polling()