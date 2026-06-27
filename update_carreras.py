import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

carreras = """Ingenieria Civil
Ingenieria Industrial
Ingenieria Quimica
Electronica y Automatizacion
Electricidad
Biotecnologia
Geologia
Mecatronica
Biologia
Quimica
Fisica
Medicina
Enfermeria
Odontologia
Nutricion y Dietetica
Bioquimica y Farmacia
Medicina Veterinaria
Agroindustria
Agronegocios (Modalidad Hibrida)
Biodiversidad y Recursos Geneticos
Sistemas de Informacion
Tecnologias de la Informacion
Tecnologias de la Informacion (En Linea)
Realidad Virtual y Videojuegos (Hibrida)
Economia (Hibrida)
Economia (En Linea)
Contabilidad y Auditoria (Hibrida)
Administracion de Empresas (Hibrida)
Administracion de Empresas (En Linea)
Turismo (Hibrida)
Turismo (En Linea)
Negocios Digitales (En Linea)
Logistica y Transporte
Gastronomia
Educacion Basica (En Linea)
Educacion Inicial (En Linea)
Pedagogia de los Idiomas Nacionales y Extranjeros
Pedagogia de las Ciencias Experimentales (Quimica y Biologia)
Pedagogia de las Ciencias Experimentales (Matematicas y Fisica)
Pedagogia de Actividad Fisica y Deporte
Pedagogia de la Lengua y Literatura
Entrenamiento Deportivo
Psicologia (En Linea)
Trabajo Social
Derecho (Hibrida)
Derecho (En Linea)
Sociologia (Hibrida)
Tecnologias Geoespaciales"""

def _db_url():
    url = os.getenv("DATABASE_URL", "")
    if "sslmode=" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    return url

with psycopg.connect(_db_url()) as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS info_utm (
            clave TEXT PRIMARY KEY,
            valor TEXT,
            actualizado TIMESTAMP DEFAULT NOW()
        )
        """
    )
    conn.execute(
        """
        INSERT INTO info_utm (clave, valor, actualizado)
        VALUES ('carreras_web', %s, NOW())
        ON CONFLICT (clave) DO UPDATE
        SET valor = EXCLUDED.valor, actualizado = NOW()
        """,
        (carreras,),
    )
    conn.commit()

print("Listo")