import asyncio
import os
import subprocess
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
        """Solo obtiene información básica, sin intentar listar formatos problemáticos"""
        try:
            cookies_path = self._get_cookies_path()
            
            # Usar extract_flat para evitar problemas con formatos
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookies_path,
                'extract_flat': True,  # Importante: no extraer formatos detallados
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
    
    async def descargar_video(self, url):
        """Descarga usando el método más simple y confiable"""
        archivo = None
        cookies_path = None
        try:
            cookies_path = self._get_cookies_path()
            
            # La configuración más simple que funciona SIEMPRE
            ydl_opts = {
                'cookiefile': cookies_path,
                'quiet': False,  # Temporal para ver errores
                'no_warnings': False,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'format': 'best',  # Mejor formato disponible (video+audio juntos)
                'ignoreerrors': True,
                'nooverwrites': True,
                'continuedl': True,
            }
            
            def _descargar():
                with YoutubeDL(ydl_opts) as ydl:
                    # Descargar directamente
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    # Verificar si el archivo existe
                    if not os.path.exists(filename):
                        # Buscar con otras extensiones
                        base = os.path.splitext(filename)[0]
                        for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                            if os.path.exists(base + ext):
                                return base + ext
                    return filename
            
            loop = asyncio.get_event_loop()
            archivo = await loop.run_in_executor(None, _descargar)
            
            if not archivo or not os.path.exists(archivo):
                raise Exception("No se pudo descargar el archivo")
            
            return archivo
            
        except Exception as e:
            logger.error(f"Error descargando: {e}")
            # Último intento: usar subprocess directamente
            try:
                return await self._descargar_con_subprocess(url)
            except:
                raise
        finally:
            if cookies_path and os.path.exists(cookies_path):
                try:
                    os.remove(cookies_path)
                except:
                    pass
    
    async def _descargar_con_subprocess(self, url):
        """Método alternativo usando subprocess (más robusto)"""
        cookies_path = self._get_cookies_path()
        
        cmd = [
            'yt-dlp',
            '--cookies', cookies_path,
            '-f', 'best',
            '-o', os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            url
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Error en subprocess: {stderr.decode()}")
            
            # Buscar el archivo descargado
            files = os.listdir(DOWNLOAD_DIR)
            video_files = [f for f in files if f.endswith(('.mp4', '.mkv', '.webm'))]
            
            if not video_files:
                raise Exception("No se encontró el archivo descargado")
            
            # Obtener el archivo más reciente
            archivos = [os.path.join(DOWNLOAD_DIR, f) for f in video_files]
            archivo = max(archivos, key=os.path.getctime)
            
            return archivo
            
        except Exception as e:
            logger.error(f"Error en subprocess: {e}")
            raise
        finally:
            if os.path.exists(cookies_path):
                os.remove(cookies_path)
