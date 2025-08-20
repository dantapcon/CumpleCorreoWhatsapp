from enviar_whatsapp import enviar_whatsapp_directo
import sys

def main():
    """
    Herramienta para probar el envío de WhatsApp directamente desde la línea de comandos.
    Uso: python probar_whatsapp.py <número> [mensaje]
    """
    print("🧪 Herramienta de prueba de envío de WhatsApp")
    print("=" * 50)
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("❌ Error: Debes proporcionar al menos un número de teléfono")
        print("Uso: python probar_whatsapp.py <número> [mensaje]")
        print("Ejemplo: python probar_whatsapp.py 612345678")
        print("Ejemplo: python probar_whatsapp.py +593987654321 'Mensaje de prueba'")
        return
    
    # Obtener número y mensaje
    numero = sys.argv[1]
    mensaje = sys.argv[2] if len(sys.argv) > 2 else "Mensaje de prueba desde Python 🐍"
    
    # Mostrar información
    print(f"📱 Probando número: {numero}")
    print(f"💬 Mensaje: {mensaje}")
    
    # Intentar enviar mensaje
    print("\n⏳ Intentando enviar mensaje...\n")
    success, result = enviar_whatsapp_directo(numero, mensaje)
    
    # Mostrar resultado
    if success:
        print(f"\n✅ Resultado: {result}")
    else:
        print(f"\n❌ Error: {result}")
        
    print("\n🔍 Consejos adicionales:")
    print("  - Si WhatsApp Web muestra 'número no válido', el formato o el número está incorrecto")
    print("  - Los números de España comienzan con +34, seguidos de 9 dígitos")
    print("  - Los números de Ecuador comienzan con +593, seguidos de 9 dígitos (sin el 0 inicial)")
    print("  - Ejemplo España: +34612345678")
    print("  - Ejemplo Ecuador: +593987654321")

if __name__ == "__main__":
    main()
