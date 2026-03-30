import sqlite3
import os

def generate_postgres_script(sqlite_db_path="bot_adeptos.db", output_file="postgres_insert.sql"):
    """
    Reads leads from SQLite and generates a PostgreSQL-compatible INSERT script.
    """
    if not os.path.exists(sqlite_db_path):
        print(f"Error: No se encontró la base de datos SQLite en {sqlite_db_path}")
        return

    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, nombre, cargo, empresa, ubicacion, industria, perfil_url, tier, query_origen, ultimo_mensaje, estado, fecha_creacion FROM leads")
        rows = cursor.fetchall()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("-- Script de inserción PostgreSQL para SAAM Bot\n")
            f.write("-- Generado automáticamente desde SQLite\n\n")
            
            # Template for table creation (optional but helpful)
            f.write("/*\nCREATE TABLE IF NOT EXISTS leads (\n")
            f.write("    id SERIAL PRIMARY KEY,\n")
            f.write("    nombre VARCHAR(255),\n")
            f.write("    cargo VARCHAR(255),\n")
            f.write("    empresa VARCHAR(255),\n")
            f.write("    ubicacion VARCHAR(255),\n")
            f.write("    industria VARCHAR(255),\n")
            f.write("    perfil_url VARCHAR(500) UNIQUE,\n")
            f.write("    tier VARCHAR(20),\n")
            f.write("    query_origen VARCHAR(500),\n")
            f.write("    ultimo_mensaje TEXT,\n")
            f.write("    estado VARCHAR(50),\n")
            f.write("    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n")
            f.write(");\n*/\n\n")

            for row in rows:
                # Clean strings for SQL
                clean_row = []
                for val in row:
                    if val is None:
                        clean_row.append("NULL")
                    elif isinstance(val, (int, float)):
                        clean_row.append(str(val))
                    else:
                        # Escape single quotes for SQL
                        escaped = str(val).replace("'", "''")
                        clean_row.append(f"'{escaped}'")

                vals = ", ".join(clean_row)
                f.write(f"INSERT INTO leads (id, nombre, cargo, empresa, ubicacion, industria, perfil_url, tier, query_origen, ultimo_mensaje, estado, fecha_creacion) \n")
                f.write(f"VALUES ({vals}) ON CONFLICT (perfil_url) DO NOTHING;\n\n")

        print(f"✅ Script generado exitosamente: {output_file}")
        print(f"📄 Contiene {len(rows)} leads registrados.")

    except Exception as e:
        print(f"Error generando script: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_postgres_script()
