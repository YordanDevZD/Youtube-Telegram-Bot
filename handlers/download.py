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
        await message.answer("📥 *Descargar video*\nUsa: `/yd <url>`\n\nEjemplo: `/yd https://youtube.com/watch?v=...`", parse_mode="Markdown")
        return
    
    url = args.split()[0]
    if '&' in url:
        url = url.split('&')[0]
    
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ URL inválida")
        return
    
    msg = await message.answer("🔍 Analizando video y descargando...\nEsto puede tomar unos segundos.")
    
    try:
        # Obtener información del video
        info = await downloader.obtener_formatos_descarga(url)
        
        # Descargar directamente (sin preguntar calidad)
        await msg.edit_text(f"⏳ Descargando: *{info['title'][:100]}*...\nCalidad: Mejor disponible", parse_mode="Markdown")
        
        archivo = await downloader.descargar_video(url)
        
        # Verificar tamaño
        tamaño_mb = os.path.getsize(archivo) / (1024 * 1024)
        if tamaño_mb > 50:
            await msg.edit_text(f"❌ Archivo muy grande ({tamaño_mb:.1f}MB > 50MB)\nNo se puede subir a Telegram")
            os.remove(archivo)
            return
        
        # Enviar el archivo
        await msg.edit_text("📤 Subiendo archivo a Telegram...")
        
        with open(archivo, 'rb') as f:
            if archivo.endswith('.mp4'):
                await message.reply_video(
                    video=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    caption=f"✅ *{info['title'][:100]}*",
                    parse_mode="Markdown",
                    supports_streaming=True
                )
            else:
                await message.reply_document(
                    document=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    caption=f"✅ *{info['title'][:100]}*",
                    parse_mode="Markdown"
                )
        
        await msg.edit_text("✅ ¡Descarga completada exitosamente!")
        
        # Limpiar archivo
        try:
            os.remove(archivo)
        except:
            pass
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error: {error_msg}")
        await msg.edit_text(f"❌ Error al descargar: {error_msg[:200]}\n\nPrueba con otro video o más tarde.")

# Mantener los demás handlers (búsqueda, navegación, suscripciones)
@dp.callback_query(lambda c: c.data.startswith("download_menu|"))
async def menu_descarga_video(callback: types.CallbackQuery):
    try:
        _, search_id, indice = callback.data.split("|")
        datos = cache.get(search_id)
        if not datos:
            await callback.answer("❌ Video no encontrado", show_alert=True)
            return
        video = datos['videos'][int(indice)]
        await callback.answer()
        
        # Simular el comando /yd con la URL del video
        await cmd_descargar(callback.message, url=video['url'])
        
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

# Función auxiliar para manejar la descarga desde callback
async def cmd_descargar(message, url=None):
    if not url:
        args = message.text.replace("/yd", "").replace("/descargar", "").strip()
        if not args:
            await message.answer("📥 Usa: `/yd <url>`", parse_mode="Markdown")
            return
        url = args.split()[0]
        if '&' in url:
            url = url.split('&')[0]
    
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ URL inválida")
        return
    
    msg = await message.answer("🔍 Descargando video...\nEsto puede tomar unos segundos.")
    
    try:
        info = await downloader.obtener_formatos_descarga(url)
        await msg.edit_text(f"⏳ Descargando: *{info['title'][:100]}*...", parse_mode="Markdown")
        
        archivo = await downloader.descargar_video(url)
        tamaño_mb = os.path.getsize(archivo) / (1024 * 1024)
        
        if tamaño_mb > 50:
            await msg.edit_text(f"❌ Archivo muy grande ({tamaño_mb:.1f}MB > 50MB)")
            os.remove(archivo)
            return
        
        await msg.edit_text("📤 Subiendo...")
        with open(archivo, 'rb') as f:
            if archivo.endswith('.mp4'):
                await message.reply_video(
                    video=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    caption=f"✅ *{info['title'][:100]}*",
                    parse_mode="Markdown",
                    supports_streaming=True
                )
            else:
                await message.reply_document(
                    document=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    caption=f"✅ *{info['title'][:100]}*",
                    parse_mode="Markdown"
                )
        
        await msg.edit_text("✅ ¡Descarga completada!")
        os.remove(archivo)
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:200]}")

# El resto de handlers (navegación, etc.) se mantienen igual
@dp.callback_query(lambda c: c.data.startswith("nav|"))
async def navegar_video(callback: types.CallbackQuery):
    try:
        _, search_id, indice_str = callback.data.split("|")
        nuevo_indice = int(indice_str)
        datos = cache.get(search_id)
        if not datos:
            await callback.answer("❌ Resultados expirados", show_alert=True)
            return
        v = datos['videos'][nuevo_indice]
        duracion_str = formatear_duracion(v['duracion'])
        vistas_str = formatear_vistas(v['vistas'])
        respuesta = f"🎬 *{escape_markdown(v['titulo'])}*\n\n📺 *Canal:* {escape_markdown(v['canal'])}\n🔗 `{v['url']}`\n⏰ {duracion_str}\n👁️ {vistas_str}\n\n📊 *Video {nuevo_indice+1} de {datos['total']}*"
        markup = crear_botones_navegacion(search_id, nuevo_indice, datos['total'])
        try:
            await callback.message.edit_media(InputMediaPhoto(media=v['miniatura'] or v['miniatura_media'], caption=respuesta, parse_mode="Markdown"), reply_markup=markup)
        except:
            await callback.message.edit_caption(caption=respuesta, parse_mode="Markdown", reply_markup=markup)
        await callback.answer()
    except Exception as e:
        await callback.answer("❌ Error", show_alert=True)

@dp.callback_query(lambda c: c.data == "close")
async def cerrar_mensaje(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data == "ignore")
async def ignorar_callback(callback: types.CallbackQuery):
    await callback.answer()

@dp.errors()
async def error_global(update, exception):
    logger.error(f"Error global: {exception}")
    return True
