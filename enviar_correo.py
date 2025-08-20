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
import random
from enviar_whatsapp import enviar_whatsapp_directo
import webbrowser
import urllib.parse

app = Flask(__name__)
CORS(app)

# Configuración del correo
CORREO_ORIGEN = "dantapcon@gmail.com"
CONTRASEÑA = "tskk jlei hsms hedu"

# Configuración de WhatsApp
# Prefijos de países soportados explícitamente
PREFIJOS_PAISES = {
    'ES': '+34',   # España
    'EC': '+593',  # Ecuador
    'MX': '+52',   # México
    'CO': '+57',   # Colombia
    'AR': '+54',   # Argentina
    'PE': '+51',   # Perú
    'CL': '+56',   # Chile
    'US': '+1'     # Estados Unidos
}

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
            celular TEXT,
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

def validar_celular(celular):
    """Validar y formatear número de celular"""
    if not celular or celular.strip() == '':
        return True, '', 'No se enviará mensaje de WhatsApp (número no proporcionado)'
    
    # Limpiar el número de espacios, guiones, paréntesis
    celular_limpio = re.sub(r'[\s\-()]', '', celular)
    
    # Si ya tiene formato internacional, verificar que sea válido
    if celular_limpio.startswith('+'):
        if not re.match(r'^\+[1-9]\d{6,14}$', celular_limpio):
            return False, '', f'Formato de número internacional incorrecto: {celular_limpio}'
        return True, celular_limpio, f'Número internacional válido: {celular_limpio}'
    
    # Validar por país
    if celular_limpio.startswith('09') and len(celular_limpio) >= 9:
        # Ecuador: formato 09xxxxxxxx
        return True, PREFIJOS_PAISES['EC'] + celular_limpio[1:], f'Formato Ecuador: {PREFIJOS_PAISES["EC"] + celular_limpio[1:]}'
    
    elif celular_limpio.startswith('6') or celular_limpio.startswith('7'):
        # España: formato 6xxxxxxxx o 7xxxxxxxx
        if len(celular_limpio) != 9:
            return False, '', f'Los números de España deben tener 9 dígitos: {celular_limpio}'
        return True, PREFIJOS_PAISES['ES'] + celular_limpio, f'Formato España: {PREFIJOS_PAISES["ES"] + celular_limpio}'
    
    else:
        # Si no podemos determinar el formato, asumir España por defecto
        return True, PREFIJOS_PAISES['ES'] + celular_limpio.lstrip('0'), f'Formato por defecto (España): {PREFIJOS_PAISES["ES"] + celular_limpio.lstrip("0")}'

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

def enviar_whatsapp(numero, mensaje):
    """
    Función para enviar mensaje de WhatsApp.
    Intenta primero el método directo (más confiable) y luego pywhatkit como respaldo.
    """
    try:
        print(f"📱 Preparando envío de WhatsApp a {numero}...")
        
        # Usar nuestro método directo (más confiable)
        return enviar_whatsapp_directo(numero, mensaje, PREFIJOS_PAISES)
        
    except Exception as e:
        print(f"💥 Error al enviar WhatsApp: {str(e)}")
        return False, f"Error al enviar WhatsApp: {str(e)}"

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
    """Crear mensaje personalizado de cumpleaños para correo"""
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

def crear_mensaje_whatsapp(nombre, apellido, edad):
    """Crear mensaje personalizado de cumpleaños para WhatsApp"""
    return f"""🎂 *¡FELIZ CUMPLEAÑOS {nombre.upper()}!* 🎂

¡Hoy cumples *{edad} años* y queremos enviarte nuestros mejores deseos! 

🎉 Que este día esté lleno de alegrías y sorpresas
🎁 Que todos tus sueños se cumplan
❤️ Mucha salud y prosperidad

_Este mensaje fue enviado automáticamente por el Sistema de Cumpleaños_"""

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
        celular = data.get('celular', '').strip()
        fecha_nacimiento = data.get('fechaNacimiento', '').strip()

        # Validaciones
        if not all([nombre, apellido, correo, fecha_nacimiento]):
            return jsonify({'success': False, 'error': 'Todos los campos son obligatorios'}), 400

        if not validar_email(correo):
            return jsonify({'success': False, 'error': 'Email inválido'}), 400
            
        # Validar y formatear el número de celular
        if celular and celular.strip():
            valido, celular_formateado, mensaje_celular = validar_celular(celular)
            if not valido:
                return jsonify({'success': False, 'error': f'Número de celular inválido: {mensaje_celular}'}), 400
            celular = celular_formateado
            print(f"📱 Celular validado: {mensaje_celular}")

        # Verificar si ya existe el contacto
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contactos WHERE correo = ?", (correo,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Ya existe un contacto con este correo'}), 400

        # Insertar contacto
        cursor.execute("""
            INSERT INTO contactos (nombre, apellido, correo, celular, fecha_nacimiento)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, apellido, correo, celular, fecha_nacimiento))
        
        contacto_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✅ Contacto registrado: {nombre} {apellido} ({correo})")

        # Verificar si es cumpleaños hoy
        if es_cumpleanos_hoy(fecha_nacimiento):
            print("🎂 ¡Es cumpleaños hoy! Enviando mensajes...")
            edad = calcular_edad(fecha_nacimiento)
            asunto = f"¡Feliz Cumpleaños {nombre}! 🎂"
            mensaje_correo = crear_mensaje_cumpleanos(nombre, apellido, edad)
            
            # Enviar correo electrónico
            success_correo, result_correo = enviar_correo(correo, asunto, mensaje_correo)
            
            # Inicializar variables para WhatsApp
            success_whatsapp = False
            result_whatsapp = "No se envió WhatsApp (celular no proporcionado)"
            
            # Enviar WhatsApp si hay un número de celular registrado
            if celular and celular.strip():
                mensaje_whatsapp = crear_mensaje_whatsapp(nombre, apellido, edad)
                success_whatsapp, result_whatsapp = enviar_whatsapp(celular, mensaje_whatsapp)
            
            if success_correo or success_whatsapp:
                # Registrar en historial
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                # Registrar el correo enviado
                if success_correo:
                    cursor.execute("""
                        INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                        VALUES (?, ?, ?, ?)
                    """, (contacto_id, 'correo_cumpleanos', asunto, mensaje_correo))
                
                # Registrar el WhatsApp enviado
                if success_whatsapp:
                    cursor.execute("""
                        INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                        VALUES (?, ?, ?, ?)
                    """, (contacto_id, 'whatsapp_cumpleanos', 'Mensaje WhatsApp', mensaje_whatsapp))
                
                cursor.execute("""
                    UPDATE contactos SET ultimo_correo_enviado = ? WHERE id = ?
                """, (date.today().isoformat(), contacto_id))
                
                conn.commit()
                conn.close()
                
                mensaje_respuesta = f'¡Contacto registrado!'
                if success_correo:
                    mensaje_respuesta += f' Correo de cumpleaños enviado a {nombre}.'
                if success_whatsapp:
                    mensaje_respuesta += f' WhatsApp de cumpleaños enviado al {celular}.'
                
                return jsonify({
                    'success': True, 
                    'message': mensaje_respuesta + ' 🎂'
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': f'Contacto registrado, pero error al enviar mensajes: Correo: {result_correo}, WhatsApp: {result_whatsapp}'
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
            SELECT id, nombre, apellido, correo, celular, fecha_nacimiento
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
            contacto_id, nombre, apellido, correo, celular, fecha_nacimiento = contacto
            
            try:
                edad = calcular_edad(fecha_nacimiento)
                asunto = f"¡Feliz Cumpleaños {nombre}! 🎂"
                mensaje_correo = crear_mensaje_cumpleanos(nombre, apellido, edad)
                
                # Enviar correo electrónico
                success_correo, result_correo = enviar_correo(correo, asunto, mensaje_correo)
                
                # Inicializar variables para WhatsApp
                success_whatsapp = False
                result_whatsapp = "No se envió WhatsApp (celular no proporcionado)"
                
                # Enviar WhatsApp si hay un número de celular registrado
                if celular and celular.strip():
                    mensaje_whatsapp = crear_mensaje_whatsapp(nombre, apellido, edad)
                    success_whatsapp, result_whatsapp = enviar_whatsapp(celular, mensaje_whatsapp)
                
                if success_correo or success_whatsapp:
                    # Registrar en historial y actualizar fecha
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    # Registrar el correo enviado
                    if success_correo:
                        cursor.execute("""
                            INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                            VALUES (?, ?, ?, ?)
                        """, (contacto_id, 'correo_cumpleanos', asunto, mensaje_correo))
                    
                    # Registrar el WhatsApp enviado
                    if success_whatsapp:
                        cursor.execute("""
                            INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                            VALUES (?, ?, ?, ?)
                        """, (contacto_id, 'whatsapp_cumpleanos', 'Mensaje WhatsApp', mensaje_whatsapp))
                    
                    # Actualizar la fecha de último envío
                    cursor.execute("""
                        UPDATE contactos SET ultimo_correo_enviado = ? WHERE id = ?
                    """, (hoy.isoformat(), contacto_id))
                    
                    conn.commit()
                    conn.close()
                    
                    enviados += 1
                    print(f"✅ Mensajes enviados a {nombre} {apellido}: Correo: {success_correo}, WhatsApp: {success_whatsapp}")
                    
                else:
                    errores.append(f"{nombre} {apellido}: Correo: {result_correo}, WhatsApp: {result_whatsapp}")
                    print(f"❌ Error enviando a {nombre}: Correo: {result_correo}, WhatsApp: {result_whatsapp}")
                    
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
            SELECT id, nombre, apellido, correo, celular, fecha_nacimiento, fecha_registro
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
                'celular': contacto[4],
                'fecha_nacimiento': contacto[5],
                'fecha_registro': contacto[6]
            }
            
            if es_cumpleanos_hoy(contacto[5]):
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
            SELECT id, nombre, apellido, correo, celular, fecha_nacimiento
            FROM contactos 
            WHERE strftime('%m-%d', fecha_nacimiento) = ?
            AND (ultimo_correo_enviado IS NULL OR ultimo_correo_enviado != ?)
        """, (hoy.strftime('%m-%d'), hoy.isoformat()))
        
        cumpleañeros = cursor.fetchall()
        conn.close()

        if cumpleañeros:
            print(f"🎂 Encontrados {len(cumpleañeros)} cumpleaños para hoy")
            
            for contacto in cumpleañeros:
                contacto_id, nombre, apellido, correo, celular, fecha_nacimiento = contacto
                
                try:
                    edad = calcular_edad(fecha_nacimiento)
                    asunto = f"¡Feliz Cumpleaños {nombre}! 🎂"
                    mensaje_correo = crear_mensaje_cumpleanos(nombre, apellido, edad)
                    
                    # Enviar correo electrónico
                    success_correo, result_correo = enviar_correo(correo, asunto, mensaje_correo)
                    
                    # Inicializar variables para WhatsApp
                    success_whatsapp = False
                    result_whatsapp = "No se envió WhatsApp (celular no proporcionado)"
                    
                    # Enviar WhatsApp si hay un número de celular registrado
                    if celular and celular.strip():
                        mensaje_whatsapp = crear_mensaje_whatsapp(nombre, apellido, edad)
                        success_whatsapp, result_whatsapp = enviar_whatsapp(celular, mensaje_whatsapp)
                    
                    if success_correo or success_whatsapp:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        
                        # Registrar el correo enviado
                        if success_correo:
                            cursor.execute("""
                                INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                                VALUES (?, ?, ?, ?)
                            """, (contacto_id, 'correo_cumpleanos_auto', asunto, mensaje_correo))
                        
                        # Registrar el WhatsApp enviado
                        if success_whatsapp:
                            cursor.execute("""
                                INSERT INTO historial_correos (contacto_id, tipo, asunto, mensaje)
                                VALUES (?, ?, ?, ?)
                            """, (contacto_id, 'whatsapp_cumpleanos_auto', 'Mensaje WhatsApp', mensaje_whatsapp))
                        
                        cursor.execute("""
                            UPDATE contactos SET ultimo_correo_enviado = ? WHERE id = ?
                        """, (hoy.isoformat(), contacto_id))
                        
                        conn.commit()
                        conn.close()
                        
                        print(f"✅ Mensajes automáticos enviados a {nombre} {apellido}: Correo: {success_correo}, WhatsApp: {success_whatsapp}")
                    else:
                        print(f"❌ Error enviando mensajes automáticos a {nombre}: Correo: {result_correo}, WhatsApp: {result_whatsapp}")
                        
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
        'correo_origen': CORREO_ORIGEN,
        'whatsapp': 'Configurado',
        'notificaciones': ['Correo electrónico', 'WhatsApp']
    })

if __name__ == '__main__':
    print("🚀 Iniciando Sistema de Cumpleaños Automático...")
    
    # Inicializar base de datos
    init_database()
    
    # Iniciar programador automático
    iniciar_programador()
    
    print("📧 Correo origen configurado:", CORREO_ORIGEN)
    print("📱 WhatsApp habilitado para contactos con celular")
    print("   - Prefijos soportados: España (+34), Ecuador (+593), México (+52), Colombia (+57), etc.")
    print("   - Formatos aceptados: +34612345678, 612345678 (España), 09XXXXXXXX (Ecuador)")
    print("   - NOTA: WhatsApp abre el navegador y requiere confirmar manualmente presionando Enter")
    print("   - Para probar números: python probar_whatsapp.py <numero>")
    print("🌐 Servidor disponible en: http://localhost:5000")
    print("📋 Endpoints disponibles:")
    print("   GET  / - Frontend principal")
    print("   POST /registrar-contacto - Registrar nuevo contacto")
    print("   POST /revisar-cumpleanos - Revisar cumpleaños manualmente")
    print("   GET  /obtener-contactos - Listar contactos")
    print("   GET  /historial - Ver historial de correos/mensajes")
    print("   GET  /test - Probar sistema")
    print("⏰ Revisión automática programada cada hora y a las 9:00 AM")
    print("💬 Los mensajes de WhatsApp necesitan WhatsApp Web activo")
    print("=" * 60)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Sistema detenido por el usuario")