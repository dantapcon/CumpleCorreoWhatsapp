from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde el frontend

# Configuración del correo
CORREO_ORIGEN = "dantapcon@gmail.com"
CONTRASEÑA = "tskk jlei hsms hedu"  # ¡IMPORTANTE: Considera usar variables de entorno!

def validar_email(email):
    """Validar formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def enviar_correo(destinatario, asunto, mensaje):
    """Función para enviar correo electrónico"""
    try:
        # Crear el mensaje
        msg = MIMEMultipart()
        msg["From"] = CORREO_ORIGEN
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg.attach(MIMEText(mensaje, "plain"))

        # Conexión con el servidor de Gmail
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(CORREO_ORIGEN, CONTRASEÑA)
        texto = msg.as_string()
        servidor.sendmail(CORREO_ORIGEN, destinatario, texto)
        servidor.quit()
        
        return True, "Correo enviado exitosamente"
    
    except Exception as e:
        return False, str(e)

@app.route('/')
def index():
    """Servir la página principal"""
    try:
        # Si tienes el archivo HTML en la misma carpeta
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Servidor de Envío de Correos</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; }
                .status { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4caf50; }
                .instructions { background: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ff9800; }
                code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Servidor de Envío de Correos</h1>
                <div class="status">
                    <strong>✅ Servidor funcionando correctamente</strong><br>
                    El backend está listo para recibir peticiones de envío de correos.
                </div>
                <div class="instructions">
                    <strong>📋 Instrucciones:</strong><br>
                    1. Guarda el frontend HTML como <code>index.html</code> en esta carpeta<br>
                    2. O accede directamente a los endpoints de la API<br>
                    3. Endpoint: <code>POST /enviar-correo</code><br>
                    4. Test endpoint: <code>GET /test</code>
                </div>
                <p><strong>Endpoints disponibles:</strong></p>
                <ul>
                    <li><code>GET /</code> - Esta página</li>
                    <li><code>POST /enviar-correo</code> - Enviar correo</li>
                    <li><code>GET /test</code> - Probar servidor</li>
                </ul>
            </div>
        </body>
        </html>
        '''

@app.route('/enviar-correo', methods=['POST'])
def enviar_correo_endpoint():
    """Endpoint para enviar correos"""
    print("\n🔄 Nueva petición recibida en /enviar-correo")
    
    try:
        # Verificar que la petición tiene contenido
        if not request.is_json:
            print("❌ Error: La petición no contiene JSON válido")
            return jsonify({
                'success': False,
                'error': 'La petición debe contener JSON válido'
            }), 400
        
        # Obtener datos del JSON
        data = request.get_json()
        print(f"📨 Datos recibidos: {data}")
        
        if not data:
            print("❌ Error: No se recibieron datos")
            return jsonify({
                'success': False,
                'error': 'No se recibieron datos JSON'
            }), 400
        
        destinatario = data.get('destinatario', '').strip()
        asunto = data.get('asunto', '').strip()
        mensaje = data.get('mensaje', '').strip()
        
        print(f"🎯 Destinatario: {destinatario}")
        print(f"📋 Asunto: {asunto}")
        print(f"💬 Mensaje: {mensaje[:50]}...")
        
        # Validar datos
        if not destinatario:
            print("❌ Error: Destinatario vacío")
            return jsonify({
                'success': False,
                'error': 'El campo destinatario es obligatorio'
            }), 400
            
        if not validar_email(destinatario):
            print(f"❌ Error: Email inválido: {destinatario}")
            return jsonify({
                'success': False,
                'error': 'El formato del correo destinatario no es válido'
            }), 400
        
        if not asunto:
            print("❌ Error: Asunto vacío")
            return jsonify({
                'success': False,
                'error': 'El campo asunto es obligatorio'
            }), 400
            
        if not mensaje:
            print("❌ Error: Mensaje vacío")
            return jsonify({
                'success': False,
                'error': 'El campo mensaje es obligatorio'
            }), 400
        
        print("✅ Datos válidos, procediendo a enviar correo...")
        
        # Enviar correo
        success, result = enviar_correo(destinatario, asunto, mensaje)
        
        if success:
            print("✅ Correo enviado exitosamente")
            response_data = {
                'success': True,
                'message': result
            }
            print(f"📤 Respuesta de éxito: {response_data}")
            return jsonify(response_data)
        else:
            print(f"❌ Error al enviar: {result}")
            response_data = {
                'success': False,
                'error': result
            }
            print(f"📤 Respuesta de error: {response_data}")
            return jsonify(response_data), 500
            
    except Exception as e:
        error_msg = f'Error interno del servidor: {str(e)}'
        print(f"💥 Excepción capturada: {error_msg}")
        
        response_data = {
            'success': False,
            'error': error_msg
        }
        print(f"📤 Respuesta de excepción: {response_data}")
        
        return jsonify(response_data), 500

@app.route('/test')
def test():
    """Endpoint de prueba"""
    test_data = {
        'message': 'El servidor está funcionando correctamente',
        'status': 'OK',
        'correo_origen': CORREO_ORIGEN,
        'endpoints': [
            'GET /',
            'POST /enviar-correo',
            'GET /test'
        ]
    }
    print(f"🧪 Test endpoint llamado: {test_data}")
    return jsonify(test_data)

@app.route('/debug', methods=['POST'])
def debug_endpoint():
    """Endpoint para debugging"""
    try:
        print("🔍 Debug endpoint llamado")
        print(f"📨 Content-Type: {request.content_type}")
        print(f"📨 Is JSON: {request.is_json}")
        print(f"📨 Data: {request.get_data()}")
        print(f"📨 JSON: {request.get_json()}")
        
        return jsonify({
            'success': True,
            'message': 'Debug info logged',
            'content_type': request.content_type,
            'is_json': request.is_json,
            'has_data': bool(request.get_data())
        })
    except Exception as e:
        print(f"💥 Error en debug: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Iniciando servidor de envío de correos...")
    print("📧 Correo origen configurado:", CORREO_ORIGEN)
    print("🌐 Servidor disponible en: http://localhost:5000")
    print("📋 Endpoints:")
    print("   GET  / - Página principal") 
    print("   POST /enviar-correo - Enviar correo")
    print("   GET  /test - Probar servidor")
    print("=" * 50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido por el usuario")