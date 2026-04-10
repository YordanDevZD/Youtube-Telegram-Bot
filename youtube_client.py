import asyncio
from functools import partial
from yt_dlp import YoutubeDL
from config import logger, COOKIES, DOWNLOAD_DIR
import os

class YouTubeClient:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'no_warnings': True,
        }
    
    def _get_cookies_path(self):
        """Crea archivo temporal de cookies"""
        cookies_path = os.path.join(DOWNLOAD_DIR, "temp_cookies.txt")
        with open(cookies_path, "w", encoding="utf-8") as f:
            f.write(COOKIES)
        return cookies_path
    
    async def obtener_canal(self, url_nombre):
        def _obtener():
            with YoutubeDL(self.ydl_opts) as ydl:
                if not url_nombre.startswith('http'):
                    if url_nombre.startswith('@'):
                        url = f"https://www.youtube.com/{url_nombre}"
                    else:
                        url = f"https://www.youtube.com/@{url_nombre}"
                else:
                    url = url_nombre
                try:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'id': info.get('channel_id') or info.get('id'),
                        'name': info.get('channel') or info.get('uploader') or info.get('title'),
                        'url': url
                    }
                except:
                    return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _obtener)
    
    async def obtener_ultimos_videos(self, canal_url, limite=3):
        def _obtener():
            with YoutubeDL(self.ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(canal_url, download=False)
                    videos = []
                    for entry in info.get('entries', [])[:limite]:
                        if entry:
                            videos.append({
                                'id': entry['id'],
                                'titulo': entry.get('title', 'Sin titulo'),
                                'url': f"https://youtube.com/watch?v={entry['id']}",
                                'canal': entry.get('channel', 'Desconocido'),
                                'duracion': entry.get('duration', 0),
                                'vistas': entry.get('view_count', 0),
                                'miniatura_media': f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                                'miniatura': f"https://img.youtube.com/vi/{entry['id']}/maxresdefault.jpg"
                            })
                    return videos
                except:
                    return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _obtener)
    
    async def buscar_videos(self, query, limite):
        def _buscar():
            with YoutubeDL(self.ydl_opts) as ydl:
                url = f"ytsearch{limite}:{query}"
                info = ydl.extract_info(url, download=False)
                
                videos = []
                for entry in info.get('entries', []):
                    if entry:
                        videos.append({
                            'id': entry['id'],
                            'titulo': entry.get('title', 'Sin titulo'),
                            'url': f"https://youtube.com/watch?v={entry['id']}",
                            'canal': entry.get('channel', 'Desconocido'),
                            'duracion': entry.get('duration', 0),
                            'vistas': entry.get('view_count', 0),
                            'miniatura_media': f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'miniatura': f"https://img.youtube.com/vi/{entry['id']}/maxresdefault.jpg"
                        })
                return videos if videos else None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _buscar)