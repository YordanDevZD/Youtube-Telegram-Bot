import os
from aiogram import types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto
from dispatcher import dp
from downloader import VideoDownloader
from keyboards import crear_botones_navegacion
from config import logger
from models import cache
from utils import formatear_duracion, escape_markdown, formatear_vistas

downloader = VideoDownloader()

@dp.message(Command("yd"))
@dp.message(Command("descargar"))
async def cmd_descargar(message: types.Message):
    args = message.text.replace("/yd", "").replace("/descargar", "").strip()
    if not args:
        await message.answer("📥 *Descargar video en 360p*\nUsa: `/yd <url>`", parse_mode="Markdown")
        return
    
    url = args.split()[0]
    if '&' in url:
        url = url.split('&')[0]
    
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ URL inválida")
        return
    
    msg = await message.answer("🔍 Analizando video...")
    try:
        info = await downloader.obtener_formatos_descarga(url)
        duracion = formatear_duracion(info['duration'])
        
        # Preguntar si quiere descargar en 360p
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Descargar en 360p", callback_data=f"download_360p|{url}")],
            [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="close_msg")]
        ])
        
        texto = f"""
📥 *{info['title'][:200]}*
👤 {info['uploader']}
⏱️ {duracion}

🎬 *Calidad: 360p (recomendada, siempre funciona)*
📦 Tamaño moderado, compatible con Telegram
"""
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:150]}")

@dp.callback_query(lambda c: c.data.startswith("download_360p|"))
async def procesar_descarga_360p(callback: types.CallbackQuery):
    try:
        _, url = callback.data.split("|", 1)
        await callback.answer()
        msg = await callback.message.edit_text("⏳ Descargando video en 360p... puede tomar unos segundos.", reply_markup=None)
        
        archivo = await downloader.descargar_video_360p(url)
        tamaño_mb = os.path.getsize(archivo) / (1024 * 1024)
        
        if tamaño_mb > 50:
            await msg.edit_text(f"❌ Archivo muy grande ({tamaño_mb:.1f}MB > 50MB)")
            os.remove(archivo)
            return
        
        await msg.edit_text("📤 Subiendo archivo a Telegram...")
        with open(archivo, 'rb') as f:
            # Enviar como video (si es mp4) o como documento si no se puede reproducir
            if archivo.endswith('.mp4'):
                await callback.message.reply_video(
                    video=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    supports_streaming=True
                )
            else:
                await callback.message.reply_document(
                    document=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo))
                )
        await msg.edit_text("✅ ¡Descarga completada!")
        os.remove(archivo)
    except Exception as e:
        logger.error(f"Error en descarga 360p: {e}")
        await callback.message.edit_text(f"❌ Error: {str(e)[:150]}")

@dp.callback_query(lambda c: c.data == "close_msg")
async def cerrar_mensaje_descarga(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# Los demás handlers (búsqueda, navegación, etc.) se mantienen igual
@dp.callback_query(lambda c: c.data.startswith("download_menu|"))
async def menu_descarga_video(callback: types.CallbackQuery):
    # Redirigir directamente a descarga 360p
    try:
        _, search_id, indice = callback.data.split("|")
        datos = cache.get(search_id)
        if not datos:
            await callback.answer("❌ Video no encontrado", show_alert=True)
            return
        video = datos['videos'][int(indice)]
        await callback.answer()
        # Llamar directamente a la descarga 360p
        await procesar_descarga_360p(callback, url=video['url'])
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

# Añadir esta función auxiliar
async def procesar_descarga_360p(callback: types.CallbackQuery, url: str):
    await callback.answer()
    msg = await callback.message.edit_text("⏳ Descargando video en 360p...", reply_markup=None)
    
    archivo = await downloader.descargar_video_360p(url)
    tamaño_mb = os.path.getsize(archivo) / (1024 * 1024)
    
    if tamaño_mb > 50:
        await msg.edit_text(f"❌ Archivo muy grande ({tamaño_mb:.1f}MB > 50MB)")
        os.remove(archivo)
        return
    
    await msg.edit_text("📤 Subiendo archivo...")
    with open(archivo, 'rb') as f:
        if archivo.endswith('.mp4'):
            await callback.message.reply_video(
                video=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                supports_streaming=True
            )
        else:
            await callback.message.reply_document(
                document=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo))
            )
    await msg.edit_text("✅ ¡Descarga completada!")
    os.remove(archivo)

# El resto de handlers (buscar, navegar, etc.) se mantienen igual
# ... (copiar el resto de handlers de búsqueda y navegación del código anterior)
