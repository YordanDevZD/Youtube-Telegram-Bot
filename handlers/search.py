from aiogram import types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dispatcher import dp
from models import cache
from utils import generar_id_busqueda, escape_markdown, formatear_duracion, formatear_vistas
from keyboards import crear_botones_navegacion
from youtube_client import YouTubeClient
from config import limite, logger

youtube_client = YouTubeClient()

@dp.message(Command("buscar"))
@dp.message(Command("b"))
async def cmd_buscar(message: types.Message):
    consulta = message.text.replace("/buscar", "").replace("/b", "").strip()
    
    if not consulta:
        await message.answer("Usa el comando /buscar <Titulo del video>")
        return 
    
    mensaje_carga = await message.answer(f"🔍 Buscando {consulta}...")
    
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
    
    if len(cache) > 50:
        keys_antiguas = list(cache.keys())[:-40]
        for key in keys_antiguas:
            del cache[key]
    
    await mostrar_video(message, search_id, 0, mensaje_carga)

async def mostrar_video(message, search_id, indice, mensaje_carga=None):
    datos = cache.get(search_id)
    if not datos:
        if mensaje_carga:
            await mensaje_carga.edit_text("❌ Resultados expirados. Haz una nueva búsqueda.")
        else:
            await message.answer("❌ Resultados expirados. Haz una nueva búsqueda.")
        return
    
    v = datos['videos'][indice]
    duracion_str = formatear_duracion(v['duracion'])
    vistas_str = formatear_vistas(v['vistas'])
    
    titulo_seguro = escape_markdown(v['titulo'])
    canal_seguro = escape_markdown(v['canal'])
    
    respuesta = f"""
🎬 *{titulo_seguro}*

📺 *Canal:* {canal_seguro}
🔗 *URL:* `{v['url']}`

⏰ *Duración:* {duracion_str}
👁️ *Vistas:* {vistas_str}

🆔 *ID:* `{v['id']}`

📊 *Video {indice + 1} de {datos['total']}*
"""
    
    if mensaje_carga:
        await mensaje_carga.delete()
    
    markup = crear_botones_navegacion(search_id, indice, datos['total'])
    
    try:
        await message.answer_photo(
            photo=v['miniatura'] or v['miniatura_media'],
            caption=respuesta,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except:
        await message.answer(
            respuesta,
            parse_mode="Markdown",
            reply_markup=markup
        )