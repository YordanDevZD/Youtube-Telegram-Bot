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
        try:
            cookies_path = self._get_cookies_path()
            
            ydl_opts_info = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookies_path,
                'extract_flat': False,
            }
            
            with YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
            
            formatos = {}
            mejor_video = {}
            mejor_audio = None
            
            for f in info.get('formats', []):
                height = f.get('height')
                # Videos con audio y video juntos
                if height and f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                    if height not in formatos:
                        formatos[height] = {
                            'format_id': f['format_id'],
                            'ext': f.get('ext', 'mp4'),
                            'filesize': f.get('filesize', 0),
                            'fps': f.get('fps', 30),
                            'vcodec': f.get('vcodec', '')
                        }
                    else:
                        if f.get('filesize', 0) > formatos[height].get('filesize', 0):
                            formatos[height]['format_id'] = f['format_id']
                            formatos[height]['filesize'] = f.get('filesize', 0)
                
                # Solo video (sin audio)
                elif height and f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                    if height not in mejor_video or f.get('filesize', 0) > mejor_video.get(height, {}).get('filesize', 0):
                        mejor_video[height] = {
                            'format_id': f['format_id'],
                            'filesize': f.get('filesize', 0),
                            'ext': f.get('ext', 'mp4')
                        }
                
                # Solo audio
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    abr = f.get('abr', 0)
                    if mejor_audio is None or abr > mejor_audio.get('abr', 0):
                        mejor_audio = {
                            'format_id': f['format_id'],
                            'abr': abr,
                            'filesize': f.get('filesize', 0),
                            'ext': f.get('ext', 'm4a')
                        }
            
            # Si no hay formatos con audio integrado, crear combinaciones
            if not formatos and mejor_video and mejor_audio:
                for height, vinfo in mejor_video.items():
                    format_id_combo = f"{vinfo['format_id']}+{mejor_audio['format_id']}"
                    formatos[height] = {
                        'format_id': format_id_combo,
                        'ext': 'mp4',
                        'filesize': (vinfo.get('filesize', 0) + mejor_audio.get('filesize', 0)),
                        'fps': 30,
                        'vcodec': 'avc1'
                    }
            
            # Agregar opción de solo audio
            if mejor_audio:
                formatos['audio'] = {
                    'format_id': mejor_audio['format_id'],
                    'abr': mejor_audio['abr'],
                    'filesize': mejor_audio.get('filesize', 0),
                    'ext': 'mp3'
                }
            
            # Opción de mejor calidad combinada
            if formatos:
                mejor_calidad = max([h for h in formatos.keys() if isinstance(h, int)], default=None)
                if mejor_calidad:
                    formatos['best'] = formatos[mejor_calidad].copy()
                    formatos['best']['description'] = 'Mejor calidad'
            
            try:
                os.remove(cookies_path)
            except:
                pass
            
            if not formatos:
                raise ValueError("No se encontraron formatos disponibles")
            
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
    
    async def descargar_video(self, url, format_id, tipo='video'):
        archivo = None
        cookies_path = None
        try:
            cookies_path = self._get_cookies_path()
            
            if tipo == 'audio':
                ydl_opts_download = {
                    'format': format_id,
                    'cookiefile': cookies_path,
                    'quiet': True,
                    'no_warnings': True,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }],
                    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
                }
            else:
                ydl_opts_download = {
                    'format': format_id,
                    'cookiefile': cookies_path,
                    'quiet': True,
                    'no_warnings': True,
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
                }
            
            def _descargar():
                with YoutubeDL(ydl_opts_download) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    if tipo == 'audio':
                        base = os.path.splitext(filename)[0]
                        filename = base + '.mp3'
                    return filename
            
            loop = asyncio.get_event_loop()
            archivo = await loop.run_in_executor(None, _descargar)
            
            if not os.path.exists(archivo):
                raise FileNotFoundError(f"No se encontró el archivo: {archivo}")
            
            return archivo
            
        except Exception as e:
            logger.error(f"Error descargando: {e}")
            if archivo and os.path.exists(archivo):
                try:
                    os.remove(archivo)
                except:
                    pass
            raise
        finally:
            if cookies_path and os.path.exists(cookies_path):
                try:
                    os.remove(cookies_path)
                except:
                    pass
