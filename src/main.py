"""
AI Marketing Co-Pilot — Application Entry Point.
Implements App Factory pattern and OOP initialization.
"""
from flask import Flask
from src.core.config import Config
from src.core.database import db_manager
from src.api.routes import webhook_bp

def create_app():
    """Application Factory."""
    app = Flask(__name__)
    
    # Initialize the database logic
    print("--- Inicializando Base de Datos PostgreSQL ---")
    try:
        db_manager.init_db()
        print("✅ Base de datos conectada e inicializada correctamente.")
    except Exception as e:
        print(f"⚠️ Error al conectar con la base de datos: {e}")
        print("Asegúrate de configurar DATABASE_URL en tu archivo .env o ejecutar migration.sql")
    
    # Register blueprints (routes)
    app.register_blueprint(webhook_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"🚀 SAAM Bot iniciado — escuchando en el puerto {Config.PORT}...")
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)
