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
        """Obtiene información del video y genera selectores de calidad"""
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
            
            formatos = {}
            
            # Calidades disponibles (usando selectores dinámicos)
            calidades = [144, 240, 360, 480, 720, 1080, 1440, 2160]
            for altura in calidades:
                # Selector: mejor video con altura <= altura + mejor audio, o mejor formato simple con esa altura
                selector = f'bestvideo[height<={altura}]+bestaudio/best[height<={altura}]'
                formatos[altura] = {
                    'selector': selector,
                    'desc': f'{altura}p'
                }
            
            # Selector para mejor calidad disponible (sin límite de altura)
            formatos['best'] = {
                'selector': 'bestvideo+bestaudio/best',
                'desc': '⭐ Mejor calidad'
            }
            
            # Selector para solo audio
            formatos['audio'] = {
                'selector': 'bestaudio/best',
                'desc': '🎵 MP3 (Audio)'
            }
            
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
                'formats': formatos
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo formatos: {e}")
            raise
    
    async def descargar_video(self, url, selector, tipo='video'):
        """Descarga usando el selector de formato (nunca falla)"""
        archivo = None
        cookies_path = None
        try:
            cookies_path = self._get_cookies_path()
            
            # Opciones base
            ydl_opts = {
                'cookiefile': cookies_path,
                'quiet': True,
                'no_warnings': True,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
            }
            
            if tipo == 'audio':
                ydl_opts.update({
                    'format': selector,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }]
                })
            else:
                ydl_opts.update({
                    'format': selector,
                    'merge_output_format': 'mp4'
                })
            
            def _descargar():
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    if tipo == 'audio':
                        base = os.path.splitext(filename)[0]
                        filename = base + '.mp3'
                    return filename
            
            loop = asyncio.get_event_loop()
            archivo = await loop.run_in_executor(None, _descargar)
            
            if not os.path.exists(archivo):
                # Buscar variaciones de extensión
                base = os.path.splitext(archivo)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                    prueba = base + ext
                    if os.path.exists(prueba):
                        archivo = prueba
                        break
            
            return archivo
            
        except Exception as e:
            logger.error(f"Error descargando con selector {selector}: {e}")
            # Fallback: si el selector específico falla, usar 'best'
            if selector != 'bestvideo+bestaudio/best' and 'Requested format is not available' in str(e):
                logger.warning("Reintentando con selector 'best'...")
                return await self.descargar_video(url, 'bestvideo+bestaudio/best', tipo)
            raise
        finally:
            if cookies_path and os.path.exists(cookies_path):
                try:
                    os.remove(cookies_path)
                except:
                    pass