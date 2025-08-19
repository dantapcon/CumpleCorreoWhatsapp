import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración del correo
correo_origen = "dantapcon@gmail.com"
contraseña = "tskk jlei hsms hedu"
correo_destino = "danunitap@gmail.com"
asunto = "Feliz cumpleaños"
mensaje = "Feliz cumpleaños"

# Crear el mensaje
msg = MIMEMultipart()
msg["From"] = correo_origen
msg["To"] = correo_destino
msg["Subject"] = asunto
msg.attach(MIMEText(mensaje, "plain"))

try:
    # Conexión con el servidor de Gmail
    servidor = smtplib.SMTP("smtp.gmail.com", 587)
    servidor.starttls()
    servidor.login(correo_origen, contraseña)
    texto = msg.as_string()
    servidor.sendmail(correo_origen, correo_destino, texto)
    servidor.quit()
    print("Correo enviado exitosamente.")
except Exception as e:
    print(f"Error al enviar el correo: {e}")
