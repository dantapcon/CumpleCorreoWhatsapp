import re
import webbrowser
import urllib.parse
from datetime import datetime
import time
import random

def enviar_whatsapp_directo(numero, mensaje, prefijos_paises={'ES': '+34', 'EC': '+593'}):
    """
    Función que abre WhatsApp Web directamente con el chat usando la API web.
    Esta es una alternativa más confiable a pywhatkit.
    
    Args:
        numero: Número de teléfono (con o sin prefijo)
        mensaje: Mensaje a enviar
        prefijos_paises: Diccionario con prefijos de países
    
    Returns:
        tuple: (éxito, mensaje)
    """
    try:
        print(f"📱 Procesando número: '{numero}'")
        
        # Si el número está vacío o es None
        if not numero:
            print("⚠️ Número de teléfono vacío")
            return False, "Número de teléfono vacío o no proporcionado"
        
        # Limpiar el número de teléfono (eliminar espacios, guiones, paréntesis, etc.)
        numero_limpio = re.sub(r'[\s\-().+]', '', numero)
        print(f"📱 Después de limpiar caracteres especiales: '{numero_limpio}'")
        
        # Validar que el número tenga al menos 9 dígitos
        if len(numero_limpio) < 9:
            print(f"⚠️ Número demasiado corto: {len(numero_limpio)} dígitos")
            return False, f"Número de teléfono demasiado corto: {len(numero_limpio)} dígitos (mínimo 9)"
        
        # Añadir prefijo según el formato del número
        if numero.startswith('+'):
            # Si ya tiene formato internacional, solo limpiamos caracteres especiales
            numero_limpio = "+" + re.sub(r'[\s\-().+]', '', numero[1:])
        else:
            # Si comienza con '09', probablemente es un número de Ecuador
            if numero_limpio.startswith('09') and len(numero_limpio) >= 9:
                numero_limpio = prefijos_paises['EC'] + numero_limpio[1:]
                print(f"🇪🇨 Detectado número de Ecuador: {numero_limpio}")
            # Si comienza con '6' o '7' y tiene 9 dígitos, probablemente es un número de España
            elif (numero_limpio.startswith('6') or numero_limpio.startswith('7')) and len(numero_limpio) == 9:
                numero_limpio = prefijos_paises['ES'] + numero_limpio
                print(f"🇪🇸 Detectado número de España: {numero_limpio}")
            # Si comienza con '0' seguido de cualquier dígito entre 7-9 (formato Ecuador)
            elif numero_limpio.startswith('0') and len(numero_limpio) >= 9 and numero_limpio[1] in "789":
                numero_limpio = prefijos_paises['EC'] + numero_limpio[1:]
                print(f"🇪🇨 Detectado número de Ecuador: {numero_limpio}")
            # Para cualquier otro caso
            else:
                # Si no sabemos el país, mostramos un mensaje y usamos España por defecto
                print(f"⚠️ No se pudo determinar el país para {numero_limpio}, usando prefijo español por defecto")
                numero_limpio = prefijos_paises['ES'] + numero_limpio.lstrip('0')
        
        # Verificación final del formato del número
        if not re.match(r'^\+[1-9]\d{10,14}$', numero_limpio):
            print(f"⚠️ Advertencia: El formato del número {numero_limpio} podría no ser válido para WhatsApp")
            print("   El formato correcto debe ser: +[código de país][número sin ceros iniciales]")
            print("   Ejemplos: +34612345678 (España) o +593987654321 (Ecuador)")
        
        # Eliminar el signo "+" para la URL (WhatsApp Web API lo requiere así)
        numero_url = numero_limpio.lstrip('+')
        
        # Codificar el mensaje para URL
        mensaje_codificado = urllib.parse.quote(mensaje)
        
        # Crear URL para WhatsApp Web
        url = f"https://web.whatsapp.com/send?phone={numero_url}&text={mensaje_codificado}"
        
        print(f"🔗 URL de WhatsApp: {url}")
        
        # Abrir en el navegador predeterminado
        print(f"🌐 Abriendo navegador con WhatsApp Web...")
        webbrowser.open(url)
        
        print(f"✅ Chat de WhatsApp abierto para {numero_limpio}")
        print("⚠️ IMPORTANTE: Debes presionar Enter manualmente para enviar el mensaje")
        print("⏱️ El navegador se ha abierto con el mensaje pre-cargado")
        print("ℹ️ Si WhatsApp muestra 'número no válido', verifica que el país sea correcto")
        print("\n📝 INSTRUCCIONES EN ESPAÑOL:")
        print("1. Espera a que se abra WhatsApp Web en el navegador")
        print("2. Verifica que el chat se haya abierto correctamente con la persona correcta")
        print("3. Presiona la tecla Enter para enviar el mensaje")
        print("4. Si aparece 'El número de teléfono compartido a través de la dirección URL es inválido'")
        print("   significa que el número no está en el formato correcto o no es una cuenta de WhatsApp")
        
        return True, f"Chat de WhatsApp abierto para {numero_limpio}. Presiona Enter para enviar el mensaje."
        
    except Exception as e:
        print(f"❌ Error al abrir chat de WhatsApp: {str(e)}")
        # Dar consejos sobre posibles soluciones
        print("🔍 Posibles soluciones:")
        print("   1. Verifica que el número tenga el formato correcto (+[código país][número])")
        print("   2. Asegúrate de que el número pertenezca a una cuenta de WhatsApp")
        print("   3. Prueba con un navegador diferente")
        print("   4. Verifica tu conexión a Internet")
        return False, f"Error al abrir chat de WhatsApp: {str(e)}"
