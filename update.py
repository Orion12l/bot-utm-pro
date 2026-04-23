import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
admisiones = "Admisiones UTM 2026:\n- Inscripciones: 24 enero - 01 febrero\n- Aceptacion de cupos: 03 al 06 de abril (desde las 10:00)\n- Plataforma: postulacion.utm.edu.ec\n\nWhatsApp UTM:\n- 0986616388\n- 0999304713\n- 0969238552\n- 0990181188\nHorario: 08:00-12:00 y 14:00-18:00"
cursor.execute("INSERT INTO info_utm (clave, valor, actualizado) VALUES ('admisiones', %s, NOW()) ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado = NOW()", (admisiones,))
conn.commit()
print('Listo')
conn.close()
