import asyncio
import logging
import os
import shutil
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL

# Configuración
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = "8617963508:AAHU4Bh6yy2gJkmTQWPA055FzxwSxBqc1j4"
DOWNLOAD_PATH = "downloads"  # Carpeta para descargas temporales

# Crear carpeta de descargas si no existe
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Configuración de yt-dlp
ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': True,
    'ignoreerrors': True,
    'no_color': True,
    'extract_flat_in_playlist': True,
    'playlistend': 20,
    'socket_timeout': 15,
}

# Configuración para descargas
download_opts = {
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'no_color': True,
    'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',  # Plantilla de nombre
    'restrictfilenames': True,  # Nombres seguros
    'progress_hooks': [],  # Para progreso
}

# Diccionarios
search_cache = {}
download_queue = {}  # Para seguimiento de descargas

# ============ FUNCIONES DE DESCARGA ============

async def download_video(url: str, quality: str, format_type: str):
    """
    Descarga un video de YouTube
    quality: 'low', 'medium', 'high'
    format_type: 'video', 'audio'
    """
    try:
        opts = download_opts.copy()
        
        if format_type == 'audio':
            # Solo audio (MP3)
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            opts['outtmpl'] = f'{DOWNLOAD_PATH}/%(title)s.%(ext)s'
        else:
            # Video con calidad específica
            if quality == 'low':
                opts['format'] = 'worst[ext=mp4]'
            elif quality == 'medium':
                opts['format'] = 'best[height<=480][ext=mp4]'
            elif quality == 'high':
                opts['format'] = 'best[height<=720][ext=mp4]'
            else:  # best
                opts['format'] = 'best[ext=mp4]'
        
        with YoutubeDL(opts) as ydl:
            # Extraer información
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ydl.extract_info(url, download=True)
            )
            
            # Obtener nombre del archivo descargado
            filename = ydl.prepare_filename(info)
            
            # Para audio, ajustar extensión
            if format_type == 'audio':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            # Verificar si el archivo existe
            if os.path.exists(filename):
                return filename
            else:
                # Buscar archivo similar
                for file in os.listdir(DOWNLOAD_PATH):
                    if info.get('title') in file:
                        return os.path.join(DOWNLOAD_PATH, file)
                return None
                
    except Exception as e:
        logger.error(f"Error en download_video: {e}")
        return None

def get_file_size_mb(filepath):
    """Obtiene tamaño del archivo en MB"""
    try:
        size_bytes = os.path.getsize(filepath)
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.1f} MB"
    except:
        return "Desconocido"

def create_download_keyboard(video_url: str, video_title: str):
    """Crea teclado con opciones de descarga"""
    builder = InlineKeyboardBuilder()
    
    # Opciones de video
    builder.button(text="🎬 Video Baja (480p)", callback_data=f"dl|{video_url}|low|video|{video_title[:50]}")
    builder.button(text="🎬 Video Media (720p)", callback_data=f"dl|{video_url}|medium|video|{video_title[:50]}")
    builder.button(text="🎬 Video Alta (1080p)", callback_data=f"dl|{video_url}|high|video|{video_title[:50]}")
    builder.button(text="🎵 Solo Audio (MP3)", callback_data=f"dl|{video_url}|best|audio|{video_title[:50]}")
    builder.button(text="❌ Cancelar", callback_data="close")
    
    builder.adjust(1, 1, 1, 1, 1)
    return builder.as_markup()

def create_video_card(video, index, total, search_id):
    try:
        duration_str = format_duration(video['duration'])
        views_str = format_views(video['views'])
        
        progress = int((index + 1) / total * 10) if total > 0 else 0
        progress_bar = "█" * progress + "░" * (10 - progress)
        
        card = (
            f"🎬 *{video['title'][:70]}*\n\n"
            f"{progress_bar} `Video {index + 1} de {total}`\n\n"
            f"📺 *Canal:* {video.get('channel', 'Desconocido')}\n"
            f"{duration_str} | {views_str}\n"
        )
        
        if video['published'] != 'N/A' and len(video['published']) >= 8:
            year = video['published'][:4]
            month = video['published'][4:6]
            day = video['published'][6:8]
            card += f"📅 *Publicado:* {day}/{month}/{year}\n"
        
        card += f"\n🔗 [Ver en YouTube]({video['url']})\n"
        
        return card
    except Exception as e:
        logger.error(f"Error en create_video_card: {e}")
        return f"❌ Error mostrando video\n\n🔗 {video.get('url', '#')}"

def create_navigation_keyboard(search_id, current_index, total_videos, video_url=None, video_title=None):
    try:
        builder = InlineKeyboardBuilder()
        
        # Botones de navegación
        if current_index > 0:
            builder.button(text="◀️ Anterior", callback_data=f"nav|{search_id}|{current_index - 1}")
        
        builder.button(text=f"📄 {current_index + 1}/{total_videos}", callback_data="none")
        
        if current_index < total_videos - 1:
            builder.button(text="Siguiente ▶️", callback_data=f"nav|{search_id}|{current_index + 1}")
        
        # Botón de descarga
        if video_url:
            builder.button(text="⬇️ DESCARGAR VIDEO ⬇️", callback_data=f"show_dl|{video_url}|{video_title[:50]}")
        
        builder.button(text="🔄 Nueva búsqueda", callback_data=f"new|{search_id}")
        builder.button(text="❌ Cerrar", callback_data="close")
        
        # Ajustar layout
        if total_videos > 1:
            builder.adjust(3, 1, 2)  # Navegación, descarga, acciones
        else:
            builder.adjust(1, 2)  # Descarga, acciones
        
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Error en create_navigation_keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cerrar", callback_data="close")]])

def format_duration(seconds):
    try:
        if not seconds or seconds <= 0:
            return "🔴 EN VIVO" if seconds == 0 else "❓ N/A"
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"🕐 {hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"⏱️ {minutes}:{secs:02d}"
    except Exception as e:
        logger.error(f"Error en format_duration: {e}")
        return "⏱️ N/A"

def format_views(views):
    try:
        if not views:
            return "👁️ N/A"
        views = int(views)
        if views >= 1_000_000:
            return f"👁️ {views/1_000_000:.1f}M"
        elif views >= 1_000:
            return f"👁️ {views/1_000:.1f}K"
        return f"👁️ {views}"
    except Exception as e:
        logger.error(f"Error en format_views: {e}")
        return "👁️ N/A"

# ============ FUNCIONES DE BÚSQUEDA ============

async def search_videos(query: str, limit=20):
    try:
        search_url = f"ytsearch{limit}:{query}"
        
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: ydl.extract_info(search_url, download=False)
            )
            
            videos = []
            if info and 'entries' in info:
                for idx, entry in enumerate(info['entries']):
                    if entry and entry.get('id'):
                        try:
                            duration = entry.get('duration')
                            if duration is not None:
                                duration = float(duration) if isinstance(duration, (int, float)) else 0
                            
                            views = entry.get('view_count')
                            if views is not None:
                                views = int(views) if isinstance(views, (int, float)) else 0
                            
                            channel = entry.get('channel') or entry.get('uploader') or 'Desconocido'
                            
                            videos.append({
                                'id': idx,
                                'video_id': entry['id'],
                                'title': entry.get('title', 'Sin título')[:100],
                                'url': f"https://youtube.com/watch?v={entry['id']}",
                                'channel': channel,
                                'duration': duration,
                                'views': views,
                                'published': entry.get('upload_date', 'N/A'),
                                'thumbnail': f"https://img.youtube.com/vi/{entry['id']}/mqdefault.jpg"
                            })
                        except Exception as e:
                            logger.error(f"Error procesando video {idx}: {e}")
                            continue
            
            return videos
    except Exception as e:
        logger.error(f"Error en search_videos: {e}")
        return None

async def get_channel_videos(channel_input: str, limit=20):
    try:
        channel_input = channel_input.strip()
        
        if not channel_input.startswith('http'):
            if channel_input.startswith('@'):
                channel_url = f"https://www.youtube.com/{channel_input}"
            else:
                channel_url = f"https://www.youtube.com/@{channel_input}"
        else:
            channel_url = channel_input
        
        logger.info(f"Procesando canal: {channel_url}")
        
        channel_opts = ydl_opts.copy()
        channel_opts['playlistend'] = limit
        
        with YoutubeDL(channel_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ydl.extract_info(channel_url, download=False)
            )
            
            videos = []
            if info:
                entries = info.get('entries', [])
                if not entries and info.get('id'):
                    entries = [info]
                
                for idx, entry in enumerate(entries[:limit]):
                    if entry and entry.get('id'):
                        try:
                            duration = entry.get('duration')
                            if duration is not None:
                                duration = float(duration) if isinstance(duration, (int, float)) else 0
                            
                            views = entry.get('view_count')
                            if views is not None:
                                views = int(views) if isinstance(views, (int, float)) else 0
                            
                            videos.append({
                                'id': idx,
                                'video_id': entry['id'],
                                'title': entry.get('title', 'Sin título')[:100],
                                'url': f"https://youtube.com/watch?v={entry['id']}",
                                'duration': duration,
                                'views': views,
                                'published': entry.get('upload_date', 'N/A'),
                                'thumbnail': f"https://img.youtube.com/vi/{entry['id']}/mqdefault.jpg"
                            })
                        except Exception as e:
                            logger.error(f"Error procesando video {idx}: {e}")
                            continue
            
            logger.info(f"Encontrados {len(videos)} videos")
            return videos
            
    except Exception as e:
        logger.error(f"Error en get_channel_videos: {e}")
        return None

def create_main_menu():
    try:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔍 Buscar videos", callback_data="menu_search")
        builder.button(text="📺 Buscar canal", callback_data="menu_channel")
        builder.button(text="⬇️ Descargar por URL", callback_data="menu_download")
        builder.button(text="❓ Ayuda", callback_data="menu_help")
        builder.adjust(1)
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Error en create_main_menu: {e}")
        return None

# ============ COMANDOS ============

@dp.message(Command("start"))
async def start_command(message: Message):
    try:
        await message.answer_photo(
            photo="https://cdn-icons-png.flaticon.com/512/1384/1384060.png",
            caption=(
                "✨ *¡Bienvenido a YouTube Bot!* ✨\n\n"
                "🎯 Tu asistente completo para YouTube\n\n"
                "🔹 *¿Qué puedes hacer?*\n"
                "• Buscar videos por título\n"
                "• Ver últimos videos de canales\n"
                "• ⬇️ *DESCARGAR videos y música* ⬇️\n"
                "• Navegar entre resultados\n\n"
                "💡 *Usa el menú para comenzar*"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_menu()
        )
    except Exception as e:
        logger.error(f"Error en start_command: {e}")
        await message.answer("❌ Error al iniciar. Por favor intenta de nuevo.")

@dp.message(Command("download"))
async def download_command(message: Message):
    """Comando para descargar video por URL"""
    args = message.text.replace("/download", "").strip()
    
    if not args:
        await message.answer(
            "📥 *Descargar video*\n\n"
            "Envía la URL del video:\n"
            "`/download https://youtube.com/watch?v=...`\n\n"
            "O simplemente envía el enlace del video",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Mostrar opciones de descarga
    keyboard = create_download_keyboard(args, "Video")
    await message.answer(
        "🎬 *Elige la calidad para descargar:*\n\n"
        "• **Video Baja**: 480p (tamaño pequeño)\n"
        "• **Video Media**: 720p (recomendado)\n"
        "• **Video Alta**: 1080p (tamaño grande)\n"
        "• **Solo Audio**: MP3 (solo música)\n\n"
        "⏳ La descarga puede tomar unos segundos",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

@dp.message(Command("buscar"))
async def search_command(message: Message):
    try:
        query = message.text.replace("/buscar", "").strip()
        
        if not query:
            await message.answer(
                "❓ *¿Qué quieres buscar?*\n\n"
                "Ejemplo: `/buscar tutorial python`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        loading_msg = await message.answer(
            f"🔍 *Buscando:* {query}\n⏳ Esto puede tomar unos segundos...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        videos = await search_videos(query, limit=20)
        
        if not videos:
            await loading_msg.edit_text(
                f"❌ *No se encontraron videos*\n\nPara: `{query}`\n\n💡 Intenta con otros términos.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        search_id = f"{message.from_user.id}_{hash(query)}_{int(asyncio.get_event_loop().time())}"
        search_cache[search_id] = {
            'videos': videos,
            'query': query,
            'type': 'search'
        }
        
        # Limpiar caché
        if len(search_cache) > 50:
            keys = list(search_cache.keys())
            for key in keys[:-40]:
                del search_cache[key]
        
        video = videos[0]
        card = create_video_card(video, 0, len(videos), search_id)
        
        await loading_msg.delete()
        await message.answer_photo(
            photo=video['thumbnail'],
            caption=card,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_navigation_keyboard(search_id, 0, len(videos), video['url'], video['title'])
        )
    except Exception as e:
        logger.error(f"Error en search_command: {e}")
        await message.answer("❌ Error en la búsqueda. Por favor intenta de nuevo.")

@dp.message(Command("canal"))
async def channel_command(message: Message):
    try:
        channel_input = message.text.replace("/canal", "").strip()
        
        if not channel_input:
            await message.answer(
                "❓ *¿Qué canal quieres ver?*\n\nEjemplo: `/canal midudev`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        loading_msg = await message.answer(
            f"📡 *Buscando canal:* {channel_input}\n⏳ Obteniendo videos...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        videos = await get_channel_videos(channel_input, limit=20)
        
        if not videos:
            await loading_msg.edit_text(
                f"❌ *No se encontró el canal*\n\nPara: `{channel_input}`\n\n💡 Verifica el nombre.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        search_id = f"{message.from_user.id}_channel_{hash(channel_input)}_{int(asyncio.get_event_loop().time())}"
        search_cache[search_id] = {
            'videos': videos,
            'query': channel_input,
            'type': 'channel'
        }
        
        video = videos[0]
        card = f"📺 *Canal: {channel_input}*\n\n{create_video_card(video, 0, len(videos), search_id)}"
        
        await loading_msg.delete()
        await message.answer_photo(
            photo=video['thumbnail'],
            caption=card,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_navigation_keyboard(search_id, 0, len(videos), video['url'], video['title'])
        )
    except Exception as e:
        logger.error(f"Error en channel_command: {e}")
        await message.answer("❌ Error al buscar canal. Por favor intenta de nuevo.")

@dp.message()
async def handle_auto(message: Message):
    try:
        user_input = message.text.strip()
        
        # Detectar si es URL de video
        if 'youtube.com/watch' in user_input or 'youtu.be/' in user_input:
            keyboard = create_download_keyboard(user_input, "Video")
            await message.answer(
                "🎬 *Video detectado*\n\nElige la calidad para descargar:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        elif user_input.startswith('@') or 'youtube.com' in user_input:
            await channel_command(message)
        elif len(user_input) > 3:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Buscar videos", callback_data=f"suggest_search|{user_input}")],
                [InlineKeyboardButton(text="📺 Buscar canal", callback_data=f"suggest_channel|{user_input}")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="close")]
            ])
            
            await message.answer(
                f"💡 *¿Qué quieres hacer con:*\n\n\"{user_input}\"\n\nElige una opción:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error en handle_auto: {e}")

# ============ CALLBACK HANDLERS ============

@dp.callback_query(lambda c: c.data.startswith("show_dl|"))
async def show_download_options(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) < 3:
            await callback.answer("❌ Error", show_alert=True)
            return
        
        _, video_url, video_title = parts[0], parts[1], "|".join(parts[2:]) if len(parts) > 2 else "Video"
        
        keyboard = create_download_keyboard(video_url, video_title)
        await callback.message.answer(
            "⬇️ *Opciones de descarga*\n\n"
            "Elige la calidad:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en show_download_options: {e}")
        await callback.answer("❌ Error al mostrar opciones", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("dl|"))
async def download_video_callback(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) != 5:
            await callback.answer("❌ Formato inválido", show_alert=True)
            return
        
        _, video_url, quality, format_type, video_title = parts
        
        # Notificar inicio de descarga
        await callback.answer("⏳ Iniciando descarga...")
        
        status_msg = await callback.message.answer(
            f"⬇️ *Descargando...*\n\n"
            f"📹 *Video:* {video_title[:50]}...\n"
            f"🎯 *Calidad:* {quality.upper()} - {format_type.upper()}\n"
            f"⏳ Esto puede tomar varios segundos...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Descargar el video
        filepath = await download_video(video_url, quality, format_type)
        
        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text(
                "❌ *Error en la descarga*\n\n"
                "Posibles causas:\n"
                "• El video es privado o no existe\n"
                "• La calidad seleccionada no está disponible\n"
                "• Problemas de conexión\n\n"
                "💡 Intenta con otra calidad o formato",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Obtener tamaño
        file_size = get_file_size_mb(filepath)
        
        # Enviar el archivo
        await status_msg.edit_text(
            f"✅ *Descarga completada!*\n\n"
            f"📹 *Video:* {video_title[:50]}...\n"
            f"📦 *Tamaño:* {file_size}\n"
            f"🎯 *Formato:* {format_type.upper()}\n\n"
            f"📤 Enviando archivo...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Crear objeto de archivo
        video_file = FSInputFile(filepath)
        
        # Enviar según tipo
        if format_type == 'audio':
            await callback.message.answer_audio(
                audio=video_file,
                title=video_title[:50],
                performer="YouTube Bot",
                caption=f"🎵 *{video_title[:50]}*\n\n⬇️ Descargado por YouTube Bot"
            )
        else:
            await callback.message.answer_video(
                video=video_file,
                caption=f"🎬 *{video_title[:50]}*\n\n📦 Tamaño: {file_size}\n⬇️ Descargado por YouTube Bot",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Limpiar archivo descargado
        try:
            os.remove(filepath)
            await callback.message.answer("🧹 Archivo temporal eliminado")
        except:
            pass
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error en download_video_callback: {e}")
        await callback.message.answer("❌ Error durante la descarga. Por favor intenta de nuevo.")

@dp.callback_query(lambda c: c.data.startswith("nav|"))
async def navigate_video(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) != 3:
            await callback.answer("❌ Formato inválido", show_alert=True)
            return
        
        _, search_id, index_str = parts
        index = int(index_str)
        
        search_data = search_cache.get(search_id)
        if not search_data:
            await callback.answer("❌ Los resultados expiraron. Haz una nueva búsqueda.", show_alert=True)
            await callback.message.delete()
            return
        
        videos = search_data['videos']
        if index >= len(videos):
            await callback.answer("📄 No hay más videos", show_alert=True)
            return
        
        video = videos[index]
        card = create_video_card(video, index, len(videos), search_id)
        
        if search_data.get('type') == 'channel':
            card = f"📺 *Canal: {search_data['query']}*\n\n{card}"
        
        try:
            if callback.message.photo:
                await callback.message.edit_media(
                    types.InputMediaPhoto(
                        media=video['thumbnail'],
                        caption=card,
                        parse_mode=ParseMode.MARKDOWN
                    ),
                    reply_markup=create_navigation_keyboard(search_id, index, len(videos), video['url'], video['title'])
                )
            else:
                await callback.message.edit_text(
                    card,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=create_navigation_keyboard(search_id, index, len(videos), video['url'], video['title']),
                    disable_web_page_preview=False
                )
        except Exception as e:
            logger.error(f"Error editando mensaje: {e}")
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en navigate_video: {e}")
        await callback.answer("❌ Error al navegar", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("new|"))
async def new_search(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) != 2:
            await callback.answer("❌ Formato inválido", show_alert=True)
            return
        
        _, search_id = parts
        search_data = search_cache.get(search_id)
        
        if search_data:
            query = search_data['query']
            await callback.message.delete()
            
            fake_message = types.Message(
                message_id=callback.message.message_id,
                from_user=callback.from_user,
                chat=callback.message.chat,
                text=f"/{search_data.get('type', 'buscar')} {query}",
                date=callback.message.date
            )
            
            if search_data.get('type') == 'search':
                await search_command(fake_message)
            else:
                await channel_command(fake_message)
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en new_search: {e}")

@dp.callback_query(lambda c: c.data.startswith("suggest_search|"))
async def suggest_search(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) != 2:
            await callback.answer("❌ Formato inválido", show_alert=True)
            return
        
        _, query = parts
        await callback.message.delete()
        
        fake_message = types.Message(
            message_id=callback.message.message_id,
            from_user=callback.from_user,
            chat=callback.message.chat,
            text=f"/buscar {query}",
            date=callback.message.date
        )
        await search_command(fake_message)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en suggest_search: {e}")

@dp.callback_query(lambda c: c.data.startswith("suggest_channel|"))
async def suggest_channel(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) != 2:
            await callback.answer("❌ Formato inválido", show_alert=True)
            return
        
        _, query = parts
        await callback.message.delete()
        
        fake_message = types.Message(
            message_id=callback.message.message_id,
            from_user=callback.from_user,
            chat=callback.message.chat,
            text=f"/canal {query}",
            date=callback.message.date
        )
        await channel_command(fake_message)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en suggest_channel: {e}")

@dp.callback_query(lambda c: c.data == "menu_search")
async def menu_search(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.message.answer(
            "🔍 *Búsqueda de videos*\n\nEnvía: `/buscar tu consulta`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_menu()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en menu_search: {e}")

@dp.callback_query(lambda c: c.data == "menu_channel")
async def menu_channel(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.message.answer(
            "📺 *Búsqueda de canales*\n\nEnvía: `/canal nombre` o `@nombre`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_menu()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en menu_channel: {e}")

@dp.callback_query(lambda c: c.data == "menu_download")
async def menu_download(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.message.answer(
            "⬇️ *Descargar video*\n\n"
            "Envía el enlace de YouTube:\n"
            "• `https://youtube.com/watch?v=...`\n"
            "• `https://youtu.be/...`\n\n"
            "O usa el botón de descarga en cualquier resultado de búsqueda",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_menu()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en menu_download: {e}")

@dp.callback_query(lambda c: c.data == "menu_help")
async def menu_help(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.message.answer(
            "📖 *Guía de uso*\n\n"
            "*Comandos:*\n"
            "• `/start` - Iniciar bot\n"
            "• `/buscar <título>` - Buscar videos\n"
            "• `/canal <nombre>` - Ver canal\n"
            "• `/download <url>` - Descargar video\n\n"
            "*Características:*\n"
            "• ⬇️ Descarga videos en 480p, 720p, 1080p\n"
            "• 🎵 Descarga solo audio MP3\n"
            "• 📱 Navegación con botones\n"
            "• 🖼️ Miniaturas de videos\n\n"
            "*Límites:*\n"
            "• Archivos menores a 50MB para Telegram\n"
            "• Videos largos pueden tardar más",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_menu()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en menu_help: {e}")

@dp.callback_query(lambda c: c.data == "close")
async def close_message(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en close_message: {e}")

@dp.callback_query(lambda c: c.data == "none")
async def none_callback(callback: CallbackQuery):
    await callback.answer()

# ============ ERROR HANDLER GLOBAL ============

@dp.errors()
async def global_error_handler(update, exception):
    logger.error(f"Error global: {exception}", exc_info=True)
    return True

# ============ MAIN ============

async def cleanup_old_downloads():
    """Limpia archivos de descarga viejos (más de 1 hora)"""
    while True:
        try:
            await asyncio.sleep(3600)  # Cada hora
            for filename in os.listdir(DOWNLOAD_PATH):
                filepath = os.path.join(DOWNLOAD_PATH, filename)
                if os.path.isfile(filepath):
                    # Borrar archivos con más de 1 hora
                    if asyncio.get_event_loop().time() - os.path.getctime(filepath) > 3600:
                        os.remove(filepath)
                        logger.info(f"Limpiado archivo viejo: {filename}")
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

async def main():
    print("🎬 YouTube Bot con Descargas Iniciado!")
    print("=" * 50)
    print("✅ Bot funcionando correctamente")
    print("📱 Comandos: /start, /buscar, /canal, /download")
    print("⬇️ Sistema de descargas ACTIVADO")
    print("🎵 Soporte para MP3 y video")
    print("=" * 50)
    
    # Iniciar tarea de limpieza
    asyncio.create_task(cleanup_old_downloads())
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error fatal: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
        # Limpiar descargas pendientes
        shutil.rmtree(DOWNLOAD_PATH, ignore_errors=True)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
