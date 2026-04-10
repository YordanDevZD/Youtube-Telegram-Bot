import psutil
import platform
from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dispatcher import dp
from config import VERSION, limite
from youtube_client import YouTubeClient
from models import cache
from utils import generar_id_busqueda
from handlers.search import mostrar_video

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"🎬 *YouTube Bot*\n\n"
        f"📌 *Comandos disponibles:*\n"
        f"• `/buscar <titulo>` o `/b <titulo>` - Busca en YouTube\n"
        f"• `/yd <url>` o `/descargar` - Descarga videos/audio\n"
        f"• `/addchannel <@canal>` o `/ad` - Suscribirse a un canal\n"
        f"• `/channels` o `/cls` - Ver canales suscritos\n"
        f"• `/removechannel <n>` o `/rc` - Eliminar suscripción\n"
        f"• `/limite <numero>` - Cambia límite de resultados (1-50)\n"
        f"• `/status` - Estado del servidor\n"
        f"• `youtube <titulo>` o `y <titulo>` - Búsqueda rápida\n\n"
        f"📊 *Límite actual:* {limite} videos\n\n"
        f"⚒️ *Versión:* v{VERSION}\n"
        f"👨‍💻 *Desarrollado por:* @YordanDev",
        parse_mode="Markdown"
    )

@dp.message(Command("limite"))
async def cmd_limite(message: types.Message):
    global limite
    
    partes = message.text.replace("/limite", "").strip()
    
    if not partes:
        await message.answer(f"📊 El límite actual es: *{limite}* videos", parse_mode="Markdown")
        return
    
    try:
        nuevo_limite = int(partes)
        if 1 <= nuevo_limite <= 50:
            limite = nuevo_limite
            await message.answer(f"✅ Ahora el límite de videos es de: *{limite}*", parse_mode="Markdown")
        else:
            await message.answer("❌ El límite debe estar entre 1 y 50")
    except ValueError:
        await message.answer("❌ Envía un número válido. Ejemplo: `/limite 15`", parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    try:
        cpu = psutil.cpu_percent(interval=.5)
        ram = psutil.virtual_memory()
        disco = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        net_mb_recibidos = net.bytes_recv / (1024**2)
        net_mb_enviados = net.bytes_sent / (1024**2)
        
        status = f"""
📊 *Estado del servidor*

💻 *Sistema:* {platform.system()}
⚡ *CPU:* {cpu}%
💾 *RAM:* {ram.used / (1024**3):.1f}GB / {ram.total / (1024**3):.1f}GB ({ram.percent}%)
💿 *Disco:* {disco.used / (1024**3):.1f}GB / {disco.total / (1024**3):.1f}GB
🌐 *Red:* 📤 {net_mb_enviados:.1f}MB | 📥 {net_mb_recibidos:.1f}MB
"""
        await message.answer(status, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error al obtener estado: {str(e)[:100]}")

@dp.message(lambda msg: msg.text and (msg.text.startswith("youtube ") or msg.text.startswith("y ")))
async def cmd_inline_buscar(message: types.Message):
    texto = message.text.strip()
    
    if texto.startswith("youtube "):
        consulta = texto.replace("youtube ", "", 1).strip()
    elif texto.startswith("y "):
        consulta = texto.replace("y ", "", 1).strip()
    else:
        return
    
    if not consulta:
        await message.answer("Usa: `youtube <título>` o `y <título>`", parse_mode="Markdown")
        return 
    
    mensaje_carga = await message.answer(f"🔍 Buscando {consulta}...")
    
    youtube_client = YouTubeClient()
    
    resultados = await youtube_client.buscar_videos(consulta, limite)
    
    if not resultados or len(resultados) == 0:
        await mensaje_carga.edit_text("❌ No se encontró información")
        return
    
    search_id = generar_id_busqueda(message.from_user.id, consulta)
    cache[search_id] = {
        'videos': resultados,
        'consulta': consulta,
        'total': len(resultados)
    }
    
    await mostrar_video(message, search_id, 0, mensaje_carga)