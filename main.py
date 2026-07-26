import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright
from starlette.status import HTTP_403_FORBIDDEN

app = FastAPI(title="LexSocial RND Scraper API")

API_KEY_NAME = "X-RND-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
RND_SERVICE_TOKEN = os.getenv("RND_SERVICE_TOKEN", "LexSocial_Secret_Token_2026")

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == RND_SERVICE_TOKEN:
        return api_key_header
    raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Token inválido.")

class DetenidoQuery(BaseModel):
    nombre: str
    primer_apellido: str
    segundo_apellido: str = None
    curp: str = None

@app.post("/api/v1/buscar-detenido", dependencies=[Depends(get_api_key)])
async def buscar_detenido(query: DetenidoQuery):
    url_rnd = "https://consultasrnd.sspc.gob.mx/"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        try:
            await page.goto(url_rnd, timeout=30000)
            await page.fill("input#txtNombre", query.nombre)
            await page.fill("input#txtPaterno", query.primer_apellido)
            if query.segundo_apellido:
                await page.fill("input#txtMaterno", query.segundo_apellido)
            if query.curp:
                await page.fill("input#txtCurp", query.curp)
            await page.click("button#btnBuscar")
            await page.wait_for_load_state("networkidle")
            
            resultado_existente = await page.locator(".resultado-detencion").is_visible()
            if not resultado_existente:
                return {"encontrado": False, "status_riesgo": "ALTO"}
                
            autoridad = await page.locator("#lblAutoridad").inner_text()
            lugar_custodia = await page.locator("#lblLugar").inner_text()
            fecha_detencion = await page.locator("#lblFecha").inner_text()
            
            return {
                "encontrado": True,
                "datos": {
                    "fecha_detencion": fecha_detencion.strip(),
                    "autoridad_captora": autoridad.strip(),
                    "lugar_resguardo": lugar_custodia.strip()
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            await browser.close()
