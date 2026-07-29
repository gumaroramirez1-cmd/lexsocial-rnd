from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
# (Asegúrate de mantener aquí las librerías que usabas para Playwright, por ejemplo: from playwright.async_api import async_playwright)

app = FastAPI(title="LexSocial - Motor de Urgencias y RND")

# Base de datos en memoria para el registro
searches_log = []

# --- MODELOS ---
class ChatMessage(BaseModel):
    user_id: str
    message: str
    ip_address: Optional[str] = None

class SearchRecord(BaseModel):
    id: int
    timestamp: str
    user_id: str
    detainee_name: str
    status: str
    package_offered: str

class AmparoRequest(BaseModel):
    promovente_nombre: str
    domicilio_promovente: str
    detainee_name: str
    autoridad_responsable: str

# Palabras clave que disparan el protocolo de urgencia
URGENCY_TRIGGERS = ["detenida", "detenido", "cateo", "arresto", "retenido", "fiscalia", "policia"]


# --- 1. TUS ENDPOINTS DE SCRAPING / RND ANTERIORES ---
@app.post("/api/rnd/consultar")
async def consultar_rnd(query: dict):
    try:
        # Aquí va tu lógica de Playwright para consultar el RND
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. NUEVO ENDPOINT: INTERCEPTOR DE CHAT DE URGENCIA ---
@app.post("/api/chat/interceptor")
async def chat_interceptor(payload: ChatMessage):
    msg_lower = payload.message.lower()
    is_emergency = any(trigger in msg_lower for trigger in URGENCY_TRIGGERS)
    
    if is_emergency:
        detainee_placeholder = "Pendiente de confirmación por el usuario"
        
        record = {
            "id": len(searches_log) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": payload.user_id,
            "detainee_name": detainee_placeholder,
            "trigger_detected": payload.message,
            "status": "Búsqueda RND Iniciada",
            "package_offered": "$11,999 MXN (RND + Asesoría + Estrategia + Amparo)"
        }
        searches_log.append(record)
        
        response_text = (
            "🚨 **Protocolo de Urgencia Penal Activado - LexSocial** 🚨\n\n"
            "He detectado una situación de riesgo legal. Para salvaguardar los derechos de la persona afectada, "
            "nuestro sistema y equipo de especialistas ponen a tu disposición el **Paquete Integral de Urgencia Penal** por **$11,999 MXN**, el cual incluye:\n\n"
            "1. **Búsqueda y localización oficial en tiempo real en el RND (Registro Nacional de Detenciones).**\n"
            "2. **Asesoría jurídica especializada inmediata.**\n"
            "3. **Estrategia legal de contención.**\n"
            "4. **Módulo de Amparo Exprés Automatizado** (con todas las causales críticas y guía paso a paso para su presentación en el Juzgado de Distrito).\n\n"
            "Por favor, confírmanos el **nombre completo de la persona detenida** y la corporación o lugar de los hechos para proceder con el rastreo inmediato en el RND."
        )
        
        return {
            "status": "alert_triggered",
            "ai_response": response_text,
            "master_panel_record": record
        }
    
    return {
            "status": "normal_flow",
            "ai_response": "Entendido. Continuamos con el flujo normal de asistencia en LexSocial."
    }


# --- 3. NUEVO ENDPOINT: GENERADOR DE AMPARO EXPRÉS ---
@app.post("/api/legal/generar-amparo-expres")
async def generar_amparo_expres(payload: AmparoRequest):
    abogado_autorizado = "Lic. Gumaro Ramírez Reyes"
    cedulas_autorizadas = "Cédulas Profesionales Federal y Estatal registradas"
    
    documento_contenido = (
        f"JUICIO DE AMPARO INDIRECTO - URGENTE\n\n"
        f"PROMOVENTE: {payload.promovente_nombre}\n"
        f"DOMICILIO PARA OÍR Y RECIBIR NOTIFICACIONES: {payload.domicilio_promovente}\n\n"
        f"AUTORIZADO EN TÉRMINOS AMPLIO/LIMITADOS: Se autoriza con ambas cédulas al {abogado_autorizado} ({cedulas_autorizadas}).\n\n"
        f"ACTO RECLAMADO: Privación ilegal de la libertad / Detención de {payload.detainee_name} atribuida a {payload.autoridad_responsable}.\n"
    )
    
    return {
        "status": "success",
        "message": "Amparo generado correctamente con datos de promovente y cédulas del Lic. Gumaro Ramírez Reyes.",
        "preview_text": documento_contenido
    }


# --- 4. ENDPOINT DEL PANEL MAESTRO ---
@app.get("/api/master-panel/searches", response_model=List[dict])
async def get_master_panel_data():
    return searches_log
