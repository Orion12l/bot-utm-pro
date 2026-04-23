import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS info_utm (clave TEXT PRIMARY KEY, valor TEXT, actualizado TIMESTAMP DEFAULT NOW())")
carreras = """Ingenieria Industrial
Electronica y Automatizacion
Nutricion y Dietetica
Bioquimica y Farmacia
Agronegocios (Modalidad Hibrida)
Biodiversidad y Recursos Geneticos
Administracion de Empresas (Modalidad Hibrida)
Administracion de Empresas (Modalidad En Linea)
Contabilidad y Auditoria (Modalidad Hibrida)
Economia (Modalidad Hibrida)
Economia (Modalidad En Linea)
Turismo (Modalidad Hibrida)
Turismo (Modalidad En Linea)
Negocios Digitales (Modalidad En Linea)
Educacion Basica (Modalidad En Linea)
Educacion Inicial (Modalidad En Linea)
Pedagogia de los Idiomas Nacionales y Extranjeros
Pedagogia de las Ciencias Experimentales Quimica y Biologia
Pedagogia de las Ciencias Experimentales Matematicas y Fisica
Pedagogia de Actividad Fisica y Deporte
Pedagogia de la Lengua y Literatura
Entrenamiento Deportivo
Sistemas de Informacion
Tecnologias de la Informacion
Tecnologias de la Informacion (Modalidad En Linea)
Realidad Virtual y Videojuegos (Modalidad Hibrida)
Ingenieria Civil
Ingenieria Quimica
Medicina Veterinaria
Agroindustria
Medicina
Enfermeria
Odontologia"""
valor = "\n".join([f"• {c}" for c in carreras.strip().split("\n")])
cursor.execute("INSERT INTO info_utm (clave, valor, actualizado) VALUES ('carreras_web', %s, NOW()) ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado = NOW()", (valor,))
conn.commit()
print("Listo")
conn.close()
