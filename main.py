from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from playwright.async_api import async_playwright

app = FastAPI(title="LexSocial - Motor de Urgencias y RND")

# --- CONFIGURACIÓN DE CORS (Soluciona el Failed to fetch en Lovable) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# --- 1. ENDPOINT RND CON SCRAPING DE PLAYWRIGHT INTEGRADO ---
@app.post("/api/rnd/consultar")
async def consultar_rnd(query: dict):
    try:
        nombre_detenido = query.get("nombre") or query.get("detainee_name")
        if not nombre_detenido:
            raise HTTPException(status_code=400, detail="El nombre es obligatorio para realizar la búsqueda en el RND.")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navegar al portal oficial del RND
            await page.goto("https://consultasdetencion.sspc.gob.mx/", timeout=60000)
            
            # Identificar e interactuar con el campo de búsqueda
            input_selector = "input[type='text'], input[placeholder*='nombre'], input[id*='nombre']"
            await page.wait_for_selector(input_selector, timeout=15000)
            await page.fill(input_selector, nombre_detenido)
            
            # Ejecutar clic en buscar
            button_selector = "button[type='submit'], button:has-text('Buscar'), input[type='submit']"
            await page.click(button_selector)
            
            # Esperar resultados
            await page.wait_for_timeout(5000)
            
            # Extraer la información
            resultados = []
            cards = await page.locator(".resultado-item, tr, .card").all()
            
            for card in cards:
                texto_card = await card.inner_text()
                if texto_card.strip():
                    resultados.append(texto_card.strip())
            
            await browser.close()
            
            return {
                "status": "success",
                "query": nombre_detenido,
                "resultados_encontrados": resultados if resultados else ["No se detectaron registros visibles directos o se requiere verificar selectores en el portal."]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. INTERCEPTOR DE CHAT DE URGENCIA ---
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
            "4. **Módulo de Amparo Exprés Automatizado** (con cédulas profesionales del **Lic. Gumaro Ramírez Reyes**).\n\n"
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


# --- 3. GENERADOR DE AMPARO EXPRÉS ---
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
