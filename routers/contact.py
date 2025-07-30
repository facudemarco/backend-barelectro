from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

class FormData(BaseModel):
    full_name: str
    email: str
    phone: str
    message: str

def sendEmail(form_data: FormData):
    sender_email = "SENDER"
    sender_password = os.environ.get("SENDER_PASSWORD")
    
    if not sender_password:
        raise HTTPException(status_code=500, detail="La contraseña del remitente no está configurada")
        
    receiver_email = "RECEIVER"
    subject = f"{form_data.full_name} - Contacto"
    body = f"Nombre completo: {form_data.full_name}\nTeléfono: {form_data.phone}\nEmail: {form_data.email}\nMensaje: {form_data.message}\nZona: {form_data.zone}\nFecha de inicio: {form_data.startDate}\nComentarios: {form_data.comments}"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Correo enviado exitosamente")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        raise HTTPException(status_code=500, detail="Error al enviar el correo")

@router.post("/formContact")
async def send_email(form_data: FormData):
    sendEmail(form_data)
    return {"message": "Formulario enviado exitosamente"}
