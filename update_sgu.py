import psycopg, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg.connect(os.getenv('DATABASE_URL'))
matricula = """Matricula UTM - SGU (S1-2026):
La UTM migro al nuevo Sistema de Gestion Universitaria (SGU).
Acceso: https://sgu.utm.edu.ec/auth/login

Pasos:
1. Ingresa al SGU
   - Ve a sgu.utm.edu.ec/auth/login
   - Usa las mismas credenciales del antiguo SGA
   - Si eres nuevo: usuario = inicial nombre + apellido + ultimos 4 digitos cedula
   - Si no recuerdas, usa Olvide mi contrasena

2. Completa tus datos personales
   - Sube foto tipo carnet
   - Carga PDF de cedula (anverso y reverso)
   - Certificado de votacion
   - Informacion de estudios secundarios

3. Selecciona la matricula
   - Ve a Pregrado o Matricula / Inscripcion a Semestre
   - Elige carrera, modalidad y periodo S1-2026
   - Revisa tu horario de clases

4. Confirma y genera comprobante
   - Revisa toda la informacion
   - Guarda o imprime el comprobante de matricula

El proceso es 100% gratuito y en linea."""
conn.execute("UPDATE info_utm SET valor = %s, actualizado = NOW() WHERE clave = 'matricula'", (matricula,))
conn.commit()
print('Listo')
conn.close()
