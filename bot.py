import asyncio
import logging
import os
import shutil
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL

# ============ CONFIGURACIÓN ============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "TU_BOT_TOKEN_AQUI")
DOWNLOAD_PATH = "/tmp/downloads"

# Crear carpeta de descargas
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Diccionario para cache de búsquedas
search_cache = {}

# ============ MANEJO DE COOKIES PARA RENDER ============

def get_cookie_file():
    """
    Busca el archivo de cookies en diferentes ubicaciones posibles
    Retorna la ruta si existe, o None si no
    """
    # Posibles ubicaciones del archivo de cookies
    possible_paths = [
        '/etc/secrets/cookies.txt',      # Secret File en Render
        '/opt/render/project/src/cookies.txt',  # Directorio del proyecto
        'cookies.txt',                   # Directorio actual
        os.path.join(tempfile.gettempdir(), 'cookies.txt')  # Temp dir
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.R_OK):
            logger.info(f"Cookies encontradas en: {path}")
            return path
    
    logger.warning("No se encontró archivo de cookies")
    return None

# ============ CONFIGURACIÓN DE YT-DLP ============

def get_ydl_opts():
    """Opciones para búsqueda y extracción"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'no_color': True,
        'extract_flat_in_playlist': True,
        'playlistend': 20,
        'socket_timeout': 30,
        'retries': 5,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Intentar cargar cookies
    cookie_file = get_cookie_file()
    if cookie_file:
        opts['cookiefile'] = cookie_file
        logger.info("Cookies cargadas correctamente")
    
    return opts

def get_download_opts():
    """Opciones para descarga de videos"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'no_color': True,
        'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
        'restrictfilenames': True,
        'retries': 5,
        'fragment_retries': 5,
        'socket_timeout': 30,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    cookie_file = get_cookie_file()
    if cookie_file:
        opts['cookiefile'] = cookie_file
    
    return opts

# ============ RESTO DE FUNCIONES (igual que antes) ============

async def search_videos(query: str, limit=20):
    """Busca videos por título"""
    try:
        search_url = f"ytsearch{limit}:{query}"
        
        with YoutubeDL(get_ydl_opts()) as ydl:
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
    """Obtiene últimos videos de un canal"""
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
        
        with YoutubeDL(get_ydl_opts()) as ydl:
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

async def download_video(url: str, quality: str, format_type: str):
    """Descarga un video de YouTube"""
    try:
        opts = get_download_opts()
        
        if format_type == 'audio':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            opts['outtmpl'] = f'{DOWNLOAD_PATH}/%(title)s.%(ext)s'
        else:
            if quality == 'low':
                opts['format'] = 'worst[ext=mp4]'
            elif quality == 'medium':
                opts['format'] = 'best[height<=480][ext=mp4]'
            elif quality == 'high':
                opts['format'] = 'best[height<=720][ext=mp4]'
            else:
                opts['format'] = 'best[ext=mp4]'
        
        with YoutubeDL(opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ydl.extract_info(url, download=True)
            )
            
            filename = ydl.prepare_filename(info)
            
            if format_type == 'audio':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            if os.path.exists(filename):
                return filename
            else:
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

def format_duration(seconds):
    """Formatea duración del video"""
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
    except:
        return "⏱️ N/A"

def format_views(views):
    """Formatea número de vistas"""
    try:
        if not views:
            return "👁️ N/A"
        views = int(views)
        if views >= 1_000_000:
            return f"👁️ {views/1_000_000:.1f}M"
        elif views >= 1_000:
            return f"👁️ {views/1_000:.1f}K"
        return f"👁️ {views}"
    except:
        return "👁️ N/A"

def create_video_card(video, index, total, search_id):
    """Crea la tarjeta de información del video"""
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
        return f"❌ Error\n\n🔗 {video.get('url', '#')}"

def create_navigation_keyboard(search_id, current_index, total_videos, video_url=None, video_title=None):
    """Crea teclado de navegación"""
    try:
        builder = InlineKeyboardBuilder()
        
        if current_index > 0:
            builder.button(text="◀️ Anterior", callback_data=f"nav|{search_id}|{current_index - 1}")
        
        builder.button(text=f"📄 {current_index + 1}/{total_videos}", callback_data="none")
        
        if current_index < total_videos - 1:
            builder.button(text="Siguiente ▶️", callback_data=f"nav|{search_id}|{current_index + 1}")
        
        if video_url:
            builder.button(text="⬇️ DESCARGAR ⬇️", callback_data=f"show_dl|{video_url}|{video_title[:50] if video_title else 'Video'}")
        
        builder.button(text="🔄 Nueva búsqueda", callback_data=f"new|{search_id}")
        builder.button(text="❌ Cerrar", callback_data="close")
        
        if total_videos > 1:
            builder.adjust(3, 1, 2)
        else:
            builder.adjust(1, 2)
        
        return builder.as_markup()
    except Exception as e:
        logger.error(f"Error en create_navigation_keyboard: {e}")
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cerrar", callback_data="close")]])

def create_download_keyboard(video_url: str, video_title: str):
    """Crea teclado de opciones de descarga"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 480p (Baja)", callback_data=f"dl|{video_url}|low|video|{video_title[:50]}")
    builder.button(text="🎬 720p (Media)", callback_data=f"dl|{video_url}|medium|video|{video_title[:50]}")
    builder.button(text="🎬 1080p (Alta)", callback_data=f"dl|{video_url}|high|video|{video_title[:50]}")
    builder.button(text="🎵 MP3 (Audio)", callback_data=f"dl|{video_url}|best|audio|{video_title[:50]}")
    builder.button(text="❌ Cancelar", callback_data="close")
    builder.adjust(1)
    return builder.as_markup()

def create_main_menu():
    """Crea menú principal"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Buscar videos", callback_data="menu_search")
    builder.button(text="📺 Buscar canal", callback_data="menu_channel")
    builder.button(text="⬇️ Descargar por URL", callback_data="menu_download")
    builder.button(text="🔄 Test conexión", callback_data="menu_test")
    builder.button(text="❓ Ayuda", callback_data="menu_help")
    builder.adjust(1)
    return builder.as_markup()

# ============ COMANDOS ============

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer_photo(
        photo="https://cdn-icons-png.flaticon.com/512/1384/1384060.png",
        caption=(
            "✨ *¡Bienvenido a YouTube Bot!* ✨\n\n"
            "🎯 *¿Qué puedes hacer?*\n"
            "• 🔍 Buscar videos por título\n"
            "• 📺 Ver últimos videos de canales\n"
            "• ⬇️ DESCARGAR videos y música\n"
            "• 📱 Navegar entre resultados\n\n"
            "💡 *Usa el menú para comenzar*\n"
            "🔧 *Comandos:* /buscar, /canal, /download, /test"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_menu()
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📖 *Guía de uso*\n\n"
        "*Comandos:*\n"
        "• `/start` - Iniciar bot\n"
        "• `/buscar <título>` - Buscar videos\n"
        "• `/canal <nombre>` - Ver canal\n"
        "• `/download <url>` - Descargar video\n"
        "• `/test` - Probar conexión\n\n"
        "*Ejemplos:*\n"
        "• `/buscar música relajante`\n"
        "• `/canal midudev`\n"
        "• Envía `@midudev` directamente\n"
        "• Envía una URL de YouTube para descargar\n\n"
        "*Calidades disponibles:*\n"
        "• 480p - Tamaño pequeño\n"
        "• 720p - Recomendado\n"
        "• 1080p - Alta calidad\n"
        "• MP3 - Solo audio",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_menu()
    )

@dp.message(Command("test"))
async def test_command(message: Message):
    """Prueba de conexión con YouTube"""
    status_msg = await message.answer("🔄 Probando conexión con YouTube...")
    
    # Mostrar info de cookies
    cookie_file = get_cookie_file()
    if cookie_file:
        await status_msg.edit_text(f"🔄 Cookies encontradas en: {cookie_file}\nProbando conexión...")
        status_msg = await message.answer("🔄 Probando con cookies...")
    
    try:
        with YoutubeDL(get_ydl_opts()) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            )
            
            if info:
                await status_msg.edit_text(
                    f"✅ *Conexión exitosa!*\n\n"
                    f"📹 Video de prueba: {info.get('title', 'N/A')}\n"
                    f"📺 Canal: {info.get('channel', 'N/A')}\n"
                    f"⏱️ Duración: {format_duration(info.get('duration', 0))}\n\n"
                    f"✨ El bot está funcionando correctamente",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await status_msg.edit_text("❌ No se pudo obtener información")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")

@dp.message(Command("buscar"))
async def search_command(message: Message):
    try:
        query = message.text.replace("/buscar", "").strip()
        
        if not query:
            await message.answer("❌ Ejemplo: `/buscar tutorial python`", parse_mode=ParseMode.MARKDOWN)
            return
        
        loading_msg = await message.answer(f"🔍 Buscando: *{query}*...", parse_mode=ParseMode.MARKDOWN)
        
        videos = await search_videos(query, limit=20)
        
        if not videos:
            await loading_msg.edit_text(f"❌ No se encontraron videos para: `{query}`")
            return
        
        search_id = f"{message.from_user.id}_{hash(query)}_{int(asyncio.get_event_loop().time())}"
        search_cache[search_id] = {'videos': videos, 'query': query, 'type': 'search'}
        
        # Limpiar caché antiguo
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
        await message.answer("❌ Error en la búsqueda. Intenta de nuevo.")

@dp.message(Command("canal"))
async def channel_command(message: Message):
    try:
        channel_input = message.text.replace("/canal", "").strip()
        
        if not channel_input:
            await message.answer("❌ Ejemplo: `/canal midudev`", parse_mode=ParseMode.MARKDOWN)
            return
        
        loading_msg = await message.answer(f"📡 Buscando canal: *{channel_input}*...", parse_mode=ParseMode.MARKDOWN)
        
        videos = await get_channel_videos(channel_input, limit=20)
        
        if not videos:
            await loading_msg.edit_text(f"❌ No se encontró el canal: `{channel_input}`")
            return
        
        search_id = f"{message.from_user.id}_channel_{hash(channel_input)}_{int(asyncio.get_event_loop().time())}"
        search_cache[search_id] = {'videos': videos, 'query': channel_input, 'type': 'channel'}
        
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
        await message.answer("❌ Error al buscar canal. Intenta de nuevo.")

@dp.message(Command("download"))
async def download_command(message: Message):
    url = message.text.replace("/download", "").strip()
    
    if not url:
        await message.answer("❌ Envía: `/download https://youtube.com/watch?v=...`", parse_mode=ParseMode.MARKDOWN)
        return
    
    keyboard = create_download_keyboard(url, "Video")
    await message.answer("🎬 *Elige la calidad para descargar:*", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message()
async def handle_auto(message: Message):
    user_input = message.text.strip()
    
    # Detectar URL de video
    if 'youtube.com/watch' in user_input or 'youtu.be/' in user_input:
        keyboard = create_download_keyboard(user_input, "Video")
        await message.answer("🎬 *Video detectado. Elige calidad:*", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif user_input.startswith('@'):
        await channel_command(message)
    elif 'youtube.com' in user_input:
        await channel_command(message)
    elif len(user_input) > 3 and not user_input.startswith('/'):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Buscar videos", callback_data=f"suggest_search|{user_input}")],
            [InlineKeyboardButton(text="📺 Buscar canal", callback_data=f"suggest_channel|{user_input}")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="close")]
        ])
        await message.answer(f"💡 *¿Qué quieres hacer con:*\n\n\"{user_input}\"", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

# ============ CALLBACKS ============

@dp.callback_query(lambda c: c.data.startswith("nav|"))
async def navigate_video(callback: CallbackQuery):
    try:
        _, search_id, index_str = callback.data.split("|")
        index = int(index_str)
        
        search_data = search_cache.get(search_id)
        if not search_data:
            await callback.answer("❌ Resultados expirados. Haz nueva búsqueda.", show_alert=True)
            return
        
        videos = search_data['videos']
        if index >= len(videos):
            await callback.answer("📄 No hay más videos", show_alert=True)
            return
        
        video = videos[index]
        card = create_video_card(video, index, len(videos), search_id)
        
        if search_data.get('type') == 'channel':
            card = f"📺 *Canal: {search_data['query']}*\n\n{card}"
        
        await callback.message.edit_media(
            types.InputMediaPhoto(
                media=video['thumbnail'],
                caption=card,
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=create_navigation_keyboard(search_id, index, len(videos), video['url'], video['title'])
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en navigate_video: {e}")
        await callback.answer("❌ Error al navegar", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("show_dl|"))
async def show_download_options(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) < 3:
            await callback.answer("❌ Error", show_alert=True)
            return
        
        video_url = parts[1]
        video_title = parts[2] if len(parts) > 2 else "Video"
        
        keyboard = create_download_keyboard(video_url, video_title)
        await callback.message.answer("⬇️ *Opciones de descarga:*", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en show_download_options: {e}")

@dp.callback_query(lambda c: c.data.startswith("dl|"))
async def download_video_callback(callback: CallbackQuery):
    try:
        parts = callback.data.split("|")
        if len(parts) != 5:
            await callback.answer("❌ Error en formato", show_alert=True)
            return
        
        _, video_url, quality, format_type, video_title = parts
        
        await callback.answer("⏳ Descargando...")
        
        status_msg = await callback.message.answer(
            f"⬇️ *Descargando:* {video_title[:40]}...\n"
            f"🎯 Calidad: {quality.upper()} - {format_type.upper()}\n"
            f"⏳ Esto puede tomar varios segundos...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        filepath = await download_video(video_url, quality, format_type)
        
        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text("❌ Error en la descarga. Intenta otra calidad.")
            return
        
        file_size = get_file_size_mb(filepath)
        video_file = FSInputFile(filepath)
        
        if format_type == 'audio':
            await callback.message.answer_audio(
                audio=video_file,
                title=video_title[:50],
                caption=f"🎵 {video_title[:50]}\n📦 {file_size}\n⬇️ Descargado por YouTube Bot"
            )
        else:
            await callback.message.answer_video(
                video=video_file,
                caption=f"🎬 {video_title[:50]}\n📦 {file_size}\n⬇️ Descargado por YouTube Bot",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Limpiar archivo
        try:
            os.remove(filepath)
        except:
            pass
        
        await status_msg.delete()
        await callback.answer("✅ Descarga completada!")
        
    except Exception as e:
        logger.error(f"Error en download_video_callback: {e}")
        await callback.message.answer("❌ Error en la descarga. Intenta de nuevo.")

@dp.callback_query(lambda c: c.data.startswith("new|"))
async def new_search(callback: CallbackQuery):
    try:
        _, search_id = callback.data.split("|")
        search_data = search_cache.get(search_id)
        
        if search_data:
            query = search_data['query']
            await callback.message.delete()
            
            fake_msg = types.Message(
                message_id=callback.message.message_id,
                from_user=callback.from_user,
                chat=callback.message.chat,
                text=f"/{search_data.get('type', 'buscar')} {query}",
                date=callback.message.date
            )
            
            if search_data.get('type') == 'search':
                await search_command(fake_msg)
            else:
                await channel_command(fake_msg)
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error en new_search: {e}")

@dp.callback_query(lambda c: c.data.startswith("suggest_search|"))
async def suggest_search(callback: CallbackQuery):
    _, query = callback.data.split("|")
    await callback.message.delete()
    fake_msg = types.Message(
        message_id=callback.message.message_id,
        from_user=callback.from_user,
        chat=callback.message.chat,
        text=f"/buscar {query}",
        date=callback.message.date
    )
    await search_command(fake_msg)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("suggest_channel|"))
async def suggest_channel(callback: CallbackQuery):
    _, query = callback.data.split("|")
    await callback.message.delete()
    fake_msg = types.Message(
        message_id=callback.message.message_id,
        from_user=callback.from_user,
        chat=callback.message.chat,
        text=f"/canal {query}",
        date=callback.message.date
    )
    await channel_command(fake_msg)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_search")
async def menu_search(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🔍 Envía: `/buscar tu consulta`", parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_channel")
async def menu_channel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📺 Envía: `/canal nombre` o `@nombre`", parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_download")
async def menu_download(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("⬇️ Envía el enlace de YouTube", parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_test")
async def menu_test(callback: CallbackQuery):
    await test_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_help")
async def menu_help(callback: CallbackQuery):
    await help_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "close")
async def close_message(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@dp.callback_query(lambda c: c.data == "none")
async def none_callback(callback: CallbackQuery):
    await callback.answer()

# ============ LIMPIEZA DE ARCHIVOS ============

async def cleanup_old_downloads():
    """Limpia archivos de descarga viejos (más de 1 hora)"""
    while True:
        try:
            await asyncio.sleep(3600)  # Cada hora
            for filename in os.listdir(DOWNLOAD_PATH):
                filepath = os.path.join(DOWNLOAD_PATH, filename)
                if os.path.isfile(filepath):
                    import time
                    if time.time() - os.path.getctime(filepath) > 3600:
                        os.remove(filepath)
                        logger.info(f"Limpiado archivo viejo: {filename}")
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

# ============ MAIN ============

async def main():
    print("🎬 YouTube Bot Iniciado!")
    print("=" * 50)
    print("✅ Bot funcionando correctamente")
    print("📱 Comandos: /start, /buscar, /canal, /download, /test")
    print("⬇️ Sistema de descargas ACTIVADO")
    print("🎵 Soporte para MP3 y video")
    print("=" * 50)
    
    # Mostrar estado de cookies
    cookie_file = get_cookie_file()
    if cookie_file:
        print(f"🍪 Cookies cargadas desde: {cookie_file}")
    else:
        print("⚠️ Sin cookies - Puede haber límites de YouTube")
    
    # Eliminar webhook existente (modo polling)
    await bot.delete_webhook(drop_pending_updates=True)
    
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
        shutil.rmtree(DOWNLOAD_PATH, ignore_errors=True)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
