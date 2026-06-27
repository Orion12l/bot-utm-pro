import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

admisiones = (
    "Admisiones UTM 2026:\n"
    "- Inscripciones: 24 enero - 01 febrero\n"
    "- Aceptacion de cupos: 03 al 06 de abril (desde las 10:00)\n"
    "- Plataforma: postulacion.utm.edu.ec\n\n"
    "WhatsApp UTM:\n"
    "- 0986616388\n"
    "- 0999304713\n"
    "- 0969238552\n"
    "- 0990181188\n"
    "Horario: 08:00-12:00 y 14:00-18:00"
)

with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
    conn.execute(
        """
        INSERT INTO info_utm (clave, valor, actualizado)
        VALUES ('admisiones', %s, NOW())
        ON CONFLICT (clave) DO UPDATE
        SET valor = EXCLUDED.valor, actualizado = NOW()
        """,
        (admisiones,),
    )
    conn.commit()

print("Listo")