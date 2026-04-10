import os
from aiogram import types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto
from dispatcher import dp
from downloader import VideoDownloader
from keyboards import crear_botones_descarga, crear_botones_navegacion
from config import logger
from models import cache
from utils import formatear_duracion, escape_markdown, formatear_vistas

downloader = VideoDownloader()

@dp.message(Command("yd"))
@dp.message(Command("descargar"))
async def cmd_descargar(message: types.Message):
    args = message.text.replace("/yd", "").replace("/descargar", "").strip()
    if not args:
        await message.answer("📥 *Descargar video*\nUsa: `/yd <url>`", parse_mode="Markdown")
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
        markup = crear_botones_descarga(info, url)
        duracion = formatear_duracion(info['duration'])
        texto = f"📥 *{info['title'][:200]}*\n👤 {info['uploader']}\n⏱️ {duracion}\n\n*Selecciona calidad:*"
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:150]}")

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
        msg = await callback.message.answer("🔍 Analizando opciones...")
        info = await downloader.obtener_formatos_descarga(video['url'])
        markup = crear_botones_descarga(info, video['url'])
        await msg.edit_text(f"📥 *{info['title'][:200]}*\n\nSelecciona calidad:", parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("dl|"))
async def procesar_descarga(callback: types.CallbackQuery):
    try:
        _, tipo, selector, url = callback.data.split("|", 3)
        await callback.answer()
        msg = await callback.message.edit_text(f"⏳ Descargando... puede tomar minutos.", reply_markup=None)
        
        archivo = await downloader.descargar_video(url, selector, tipo)
        tamaño_mb = os.path.getsize(archivo) / (1024 * 1024)
        
        if tamaño_mb > 50:
            await msg.edit_text(f"❌ Archivo muy grande ({tamaño_mb:.1f}MB > 50MB)")
            os.remove(archivo)
            return
        
        await msg.edit_text("📤 Subiendo archivo...")
        with open(archivo, 'rb') as f:
            if tipo == 'audio':
                await callback.message.reply_audio(
                    audio=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    title=os.path.splitext(os.path.basename(archivo))[0]
                )
            else:
                await callback.message.reply_video(
                    video=types.BufferedInputFile(f.read(), filename=os.path.basename(archivo)),
                    supports_streaming=True
                )
        await msg.edit_text("✅ ¡Descarga completada!")
        os.remove(archivo)
    except Exception as e:
        logger.error(f"Error en descarga: {e}")
        await callback.message.edit_text(f"❌ Error: {str(e)[:150]}")

@dp.callback_query(lambda c: c.data == "close_msg")
async def cerrar_mensaje_descarga(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

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

@dp.errors()
async def error_global(update, exception):
    logger.error(f"Error global: {exception}")
    return True