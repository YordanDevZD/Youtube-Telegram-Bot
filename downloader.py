import asyncio
import os
from yt_dlp import YoutubeDL
from config import logger, DOWNLOAD_DIR, COOKIES

class VideoDownloader:
    def __init__(self):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    def _get_cookies_path(self):
        cookies_path = os.path.join(DOWNLOAD_DIR, "temp_cookies.txt")
        with open(cookies_path, "w", encoding="utf-8") as f:
            f.write(COOKIES)
        return cookies_path
    
    async def obtener_formatos_descarga(self, url):
        """Solo devuelve la opción 360p fija (no necesita selección)"""
        try:
            cookies_path = self._get_cookies_path()
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookies_path,
                'extract_flat': False,
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            # Limpiar cookies
            try:
                os.remove(cookies_path)
            except:
                pass
            
            return {
                'title': info.get('title', 'Sin título'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Desconocido'),
                'thumbnail': info.get('thumbnail', ''),
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información: {e}")
            raise
    
    async def descargar_video_360p(self, url):
        """Descarga siempre en 360p con video+audio juntos (no necesita FFmpeg)"""
        archivo = None
        cookies_path = None
        try:
            cookies_path = self._get_cookies_path()
            
            # Selector fijo: busca un formato con altura <= 360 que tenga video y audio
            # Si no existe, toma el mejor formato simple (que ya trae audio)
            format_selector = 'best[height<=360]/best'
            
            ydl_opts = {
                'format': format_selector,
                'cookiefile': cookies_path,
                'quiet': True,
                'no_warnings': True,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
            }
            
            def _descargar():
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return filename
            
            loop = asyncio.get_event_loop()
            archivo = await loop.run_in_executor(None, _descargar)
            
            if not os.path.exists(archivo):
                # Buscar variaciones de extensión
                base = os.path.splitext(archivo)[0]
                for ext in ['.mp4', '.mkv', '.webm']:
                    prueba = base + ext
                    if os.path.exists(prueba):
                        archivo = prueba
                        break
            
            return archivo
            
        except Exception as e:
            logger.error(f"Error descargando: {e}")
            raise
        finally:
            if cookies_path and os.path.exists(cookies_path):
                try:
                    os.remove(cookies_path)
                except:
                    pass
