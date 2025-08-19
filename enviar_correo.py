from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from datetime import datetime, date
import threading
import time
import schedule

app = Flask(__name__)
CORS(app)

# Configuración del correo
CORREO_ORIGEN = "dantapcon@gmail.com"
CONTRASEÑA = "tskk jlei hsms hedu"

# Configuración de la base de datos
DB_NAME = "cumpleanos.db"

def init_database():
    """Inicializar la base de datos SQLite"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crear tabla de contactos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            fecha_nacimiento DATE NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_correo_enviado DATE
        )
    ''')
    
    # Crear tabla de historial de correos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_correos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contacto_id INTEGER,
            fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL,
            asunto TEXT,
            mensaje TEXT,
            estado TEXT DEFAULT 'enviado',
            FOREIGN KEY (contacto_id) REFERENCES contactos (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada")

def validar_email(email):
    """Validar formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def enviar_correo(destinatario, asunto, mensaje):
    """Función para enviar correo electrónico"""
    try:
        msg = MIMEMultipart()
        msg["From"] = CORREO_ORIGEN
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg.attach(MIMEText(mensaje, "plain"))

        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(CORREO_ORIGEN, CONTRASEÑA)
        texto = msg.as_string()
        servidor.sendmail(CORREO_ORIGEN, destinatario, texto)
        servidor.quit()
        
        return True, "Correo enviado exitosamente"
    
    except Exception as e:
        return False, str(e)

def es_cumpleanos_hoy(fecha_nacimiento):
    """Verificar si una fecha de nacimiento corresponde a hoy"""
    hoy = date.today()
    fecha_nac = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
    return (fecha_nac.month == hoy.month and fecha_nac.day == hoy.day)

def calcular_edad(fecha_nacimiento):
    """Calcular la edad actual"""
    hoy = date.today()
    fecha_nac = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
    edad = hoy.year - fecha_nac.year
    
    if hoy.month < fecha_nac.month or (hoy.month == fecha_nac.month and hoy.day < fecha_nac.day):
        edad -= 1
    
    return edad

def crear_mensaje_cumpleanos(nombre, apellido, edad):
    """Crear mensaje personalizado de cumpleaños"""
    return f"""¡Feliz Cumpleaños {nombre} {apellido}! 🎂

¡Esperamos que tengas un día maravilloso lleno de alegría y celebración!

Hoy cumples {edad} años y queremos desearte:
🎉 Muchas felicidades
🎈 Que todos tus deseos se cumplan
🎁 Un año lleno de éxitos y bendiciones
❤️ Salud y prosperidad

¡Que tengas un cumpleaños inolvidable!

Con cariño,
Sistema Automático de Cumpleaños"""

@app.route('/')
def index():
    """Servir la página principal"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sistema de Cumpleaños</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; text-align: center; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                h1 { color: #333; }
                .status { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎂 Sistema de Cumpleaños Automático</h1>
                <div class="status">
                    <strong>✅ Servidor funcionando</strong><br>
                    Guarda el frontend HTML como <code>index.html</code> en esta carpeta.
                </div>
            </div>
        </body>
        </html>
        '''

@app.route('/registrar-contacto', methods=['POST'])
def registrar_contacto():
    """Registrar un nuevo contacto"""
    print("\n👤 Nueva solicitud de registro de contacto")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400

        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        correo = data.get('correo', '').strip()
        fecha_nacimiento = data.get('fechaNacimiento', '').strip()

        # Validaciones
        if not all([nombre, apellido, correo, fecha_nacimiento]):
            return jsonify({'success': False, 'error': 'Todos los campos son obligatorios'}), 400

        if not validar_email(correo):
            return jsonify({'success': False, 'error': 'Email inválido'}), 400

        # Verificar si ya existe el contacto
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contactos WHERE correo = ?", (correo,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Ya existe un contacto con este correo'}), 400

        # Insertar contacto
        cursor.execute("""
            INSERT INTO contactos (nombre, apellido, correo, fecha_nacimiento)
            VALUES (?, ?, ?, ?)
        """, (nombre, apellido, correo, fecha_nacimiento))
        
        contacto_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✅ Contacto registrado: {nombre} {apellido} ({correo})")

        # Verificar si es cumpleaños hoy
        if es_cumpleanos_hoy(fecha_nacimiento):
            print("🎂 ¡Es cumpleaños hoy! Enviando correo...")
            edad = calcular_edad(fecha_nacimiento)
            asunto = f"¡Feliz Cumpleaños {nombre}! 🎂"
            mensaje = crear_mensaje_cumpleanos(nombre, apellido, edad)
            
            success, result = enviar_correo(correo, asunto, mensaje)
            
            if success:
                # Registrar en historial
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                    VALUES (?, ?, ?, ?)
                """, (contacto_id, 'cumpleanos', asunto, mensaje))
                
                cursor.execute("""
                    UPDATE contactos SET ultimo_correo_enviado = ? WHERE id = ?
                """, (date.today().isoformat(), contacto_id))
                
                conn.commit()
                conn.close()
                
                return jsonify({
                    'success': True, 
                    'message': f'¡Contacto registrado y correo de cumpleaños enviado a {nombre}! 🎂'
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': f'Contacto registrado, pero error al enviar correo: {result}'
                }), 500
        else:
            return jsonify({
                'success': True, 
                'message': f'Contacto {nombre} {apellido} registrado exitosamente. Se enviará correo automático en su cumpleaños.'
            })

    except Exception as e:
        print(f"💥 Error al registrar contacto: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/revisar-cumpleanos', methods=['POST'])
def revisar_cumpleanos():
    """Revisar cumpleaños de hoy manualmente"""
    print("\n🔍 Revisión manual de cumpleaños")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Obtener contactos con cumpleaños hoy que no hayan recibido correo hoy
        hoy = date.today()
        cursor.execute("""
            SELECT id, nombre, apellido, correo, fecha_nacimiento
            FROM contactos 
            WHERE strftime('%m-%d', fecha_nacimiento) = ?
            AND (ultimo_correo_enviado IS NULL OR ultimo_correo_enviado != ?)
        """, (hoy.strftime('%m-%d'), hoy.isoformat()))
        
        cumpleañeros = cursor.fetchall()
        conn.close()

        if not cumpleañeros:
            return jsonify({
                'success': True, 
                'message': 'No hay cumpleaños pendientes para hoy.'
            })

        enviados = 0
        errores = []

        for contacto in cumpleañeros:
            contacto_id, nombre, apellido, correo, fecha_nacimiento = contacto
            
            try:
                edad = calcular_edad(fecha_nacimiento)
                asunto = f"¡Feliz Cumpleaños {nombre}! 🎂"
                mensaje = crear_mensaje_cumpleanos(nombre, apellido, edad)
                
                success, result = enviar_correo(correo, asunto, mensaje)
                
                if success:
                    # Registrar en historial y actualizar fecha
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                        VALUES (?, ?, ?, ?)
                    """, (contacto_id, 'cumpleanos', asunto, mensaje))
                    
                    cursor.execute("""
                        UPDATE contactos SET ultimo_correo_enviado = ? WHERE id = ?
                    """, (hoy.isoformat(), contacto_id))
                    
                    conn.commit()
                    conn.close()
                    
                    enviados += 1
                    print(f"✅ Correo enviado a {nombre} {apellido}")
                    
                else:
                    errores.append(f"{nombre} {apellido}: {result}")
                    print(f"❌ Error enviando a {nombre}: {result}")
                    
            except Exception as e:
                errores.append(f"{nombre} {apellido}: {str(e)}")
                print(f"💥 Excepción enviando a {nombre}: {str(e)}")

        # Preparar respuesta
        mensaje_respuesta = f"✅ {enviados} correo(s) de cumpleaños enviado(s)"
        if errores:
            mensaje_respuesta += f". ❌ {len(errores)} error(es): {', '.join(errores[:3])}"
            if len(errores) > 3:
                mensaje_respuesta += "..."

        return jsonify({
            'success': True, 
            'message': mensaje_respuesta
        })

    except Exception as e:
        print(f"💥 Error en revisión de cumpleaños: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/obtener-contactos', methods=['GET'])
def obtener_contactos():
    """Obtener lista de contactos y estadísticas"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Obtener todos los contactos
        cursor.execute("""
            SELECT id, nombre, apellido, correo, fecha_nacimiento, fecha_registro
            FROM contactos 
            ORDER BY nombre, apellido
        """)
        contactos_raw = cursor.fetchall()
        
        # Formatear contactos
        contactos = []
        cumpleanos_hoy = 0
        hoy = date.today()
        
        for contacto in contactos_raw:
            contacto_data = {
                'id': contacto[0],
                'nombre': contacto[1],
                'apellido': contacto[2],
                'correo': contacto[3],
                'fecha_nacimiento': contacto[4],
                'fecha_registro': contacto[5]
            }
            
            if es_cumpleanos_hoy(contacto[4]):
                cumpleanos_hoy += 1
            
            contactos.append(contacto_data)
        
        # Estadísticas
        estadisticas = {
            'total': len(contactos),
            'cumpleanos_hoy': cumpleanos_hoy
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'contactos': contactos,
            'estadisticas': estadisticas
        })

    except Exception as e:
        print(f"💥 Error obteniendo contactos: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/historial', methods=['GET'])
def obtener_historial():
    """Obtener historial de correos enviados"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT h.fecha_envio, c.nombre, c.apellido, c.correo, h.tipo, h.asunto, h.estado
            FROM historial_correos h
            JOIN contactos c ON h.contacto_id = c.id
            ORDER BY h.fecha_envio DESC
            LIMIT 50
        """)
        
        historial_raw = cursor.fetchall()
        conn.close()
        
        historial = []
        for item in historial_raw:
            historial.append({
                'fecha_envio': item[0],
                'nombre_completo': f"{item[1]} {item[2]}",
                'correo': item[3],
                'tipo': item[4],
                'asunto': item[5],
                'estado': item[6]
            })
        
        return jsonify({
            'success': True,
            'historial': historial
        })

    except Exception as e:
        print(f"💥 Error obteniendo historial: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

def revisar_cumpleanos_automatico():
    """Función que se ejecuta automáticamente para revisar cumpleaños"""
    print(f"\n🔄 Revisión automática de cumpleaños - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        hoy = date.today()
        cursor.execute("""
            SELECT id, nombre, apellido, correo, fecha_nacimiento
            FROM contactos 
            WHERE strftime('%m-%d', fecha_nacimiento) = ?
            AND (ultimo_correo_enviado IS NULL OR ultimo_correo_enviado != ?)
        """, (hoy.strftime('%m-%d'), hoy.isoformat()))
        
        cumpleañeros = cursor.fetchall()
        conn.close()

        if cumpleañeros:
            print(f"🎂 Encontrados {len(cumpleañeros)} cumpleaños para hoy")
            
            for contacto in cumpleañeros:
                contacto_id, nombre, apellido, correo, fecha_nacimiento = contacto
                
                try:
                    edad = calcular_edad(fecha_nacimiento)
                    asunto = f"¡Feliz Cumpleaños {nombre}! 🎂"
                    mensaje = crear_mensaje_cumpleanos(nombre, apellido, edad)
                    
                    success, result = enviar_correo(correo, asunto, mensaje)
                    
                    if success:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                            VALUES (?, ?, ?, ?)
                        """, (contacto_id, 'cumpleanos_automatico', asunto, mensaje))
                        
                        cursor.execute("""
                            UPDATE contactos SET ultimo_correo_enviado = ? WHERE id = ?
                        """, (hoy.isoformat(), contacto_id))
                        
                        conn.commit()
                        conn.close()
                        
                        print(f"✅ Correo automático enviado a {nombre} {apellido}")
                    else:
                        print(f"❌ Error enviando correo automático a {nombre}: {result}")
                        
                except Exception as e:
                    print(f"💥 Error procesando {nombre}: {str(e)}")
        else:
            print("📅 No hay cumpleaños para hoy")

    except Exception as e:
        print(f"💥 Error en revisión automática: {str(e)}")

def iniciar_programador():
    """Iniciar el programador de tareas automáticas"""
    # Programar revisión diaria a las 9:00 AM
    schedule.every().day.at("09:00").do(revisar_cumpleanos_automatico)
    
    # También revisar cada hora durante el día laboral
    schedule.every().hour.do(revisar_cumpleanos_automatico)
    
    def ejecutar_programador():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto
    
    # Ejecutar programador en hilo separado
    hilo_programador = threading.Thread(target=ejecutar_programador, daemon=True)
    hilo_programador.start()
    print("⏰ Programador automático iniciado")

@app.route('/test')
def test():
    """Endpoint de prueba"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contactos")
    total_contactos = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        'message': 'Sistema de cumpleaños funcionando correctamente',
        'status': 'OK',
        'base_datos': 'Conectada',
        'total_contactos': total_contactos,
        'correo_origen': CORREO_ORIGEN
    })

if __name__ == '__main__':
    print("🚀 Iniciando Sistema de Cumpleaños Automático...")
    
    # Inicializar base de datos
    init_database()
    
    # Iniciar programador automático
    iniciar_programador()
    
    print("📧 Correo origen configurado:", CORREO_ORIGEN)
    print("🌐 Servidor disponible en: http://localhost:5000")
    print("📋 Endpoints disponibles:")
    print("   GET  / - Frontend principal")
    print("   POST /registrar-contacto - Registrar nuevo contacto")
    print("   POST /revisar-cumpleanos - Revisar cumpleaños manualmente")
    print("   GET  /obtener-contactos - Listar contactos")
    print("   GET  /historial - Ver historial de correos")
    print("   GET  /test - Probar sistema")
    print("⏰ Revisión automática programada cada hora y a las 9:00 AM")
    print("=" * 60)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Sistema detenido por el usuario")