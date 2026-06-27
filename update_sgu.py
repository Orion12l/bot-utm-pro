import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

matricula = """Matricula UTM - SGU (S1-2026):
La UTM utiliza el Sistema de Gestion Universitaria (SGU). El antiguo SGA ya no esta en uso.
Acceso: https://sgu.utm.edu.ec/auth/login

Pasos:
1. Ingresa al SGU
   - Ve a sgu.utm.edu.ec/auth/login
   - Usuario: inicial del primer nombre + primer apellido completo + ultimos 4 digitos de cedula
     Ejemplo: Juan Perez 1234567890 -> jperez7890
   - Correo institucional: jperez7890@utm.edu.ec
   - Contrasena: numero de cedula completo
   - Si olvidaste tu contrasena, usa 'Olvide mi contrasena' en el SGU
   - Escoge Rol: Aspirante (nuevos) o Estudiante (ya matriculados antes)

2. Completa tus datos personales
   - Foto tipo carnet (fondo blanco)
   - PDF cedula (anverso y reverso en un solo archivo)
   - Certificado de votacion vigente
   - Titulo de Bachiller en PDF

3. Selecciona la matricula
   - Ve a: Pregrado > Matricula / Inscripcion a Semestre
   - Elige carrera, modalidad y periodo S1-2026
   - Revisa y confirma tu horario de clases

4. Genera tu comprobante
   - Descarga o imprime el comprobante de matricula

El proceso es 100% gratuito y en linea.
Soporte WhatsApp: 0986616388 / 0999304713 / 0969238552 / 0990181188
Horario: 08:00-12:00 y 14:00-18:00"""

with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
    conn.execute(
        """
        UPDATE info_utm SET valor = %s, actualizado = NOW()
        WHERE clave = 'matricula'
        """,
        (matricula,),
    )
    conn.commit()

print("Listo")