import re
import time

def escape_markdown(texto):
    """Escapa caracteres especiales de Markdown"""
    if not texto:
        return ""
    caracteres_especiales = r'([_*\[\]()~`>#+\-=|{}.!\\])'
    return re.sub(caracteres_especiales, r'\\\1', str(texto))

def formatear_duracion(segundos):
    """Formatea duración en segundos a formato HH:MM:SS"""
    if not segundos or segundos <= 0:
        return "🎦 En vivo"
    segundos = int(segundos)
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    if horas > 0:
        return f"{horas}:{minutos:02d}:{segs:02d}"
    return f"{minutos}:{segs:02d}"

def formatear_vistas(numero):
    """Formatea el número de vistas (K, M, B)"""
    if not numero or numero <= 0:
        return "0"
    if numero >= 1_000_000_000:
        return f"{numero/1_000_000_000:.1f}B"
    if numero >= 1_000_000:
        return f"{numero/1_000_000:.1f}M"
    if numero >= 1_000:
        return f"{numero/1_000:.1f}K"
    return str(numero)

def formatear_tamaño(bytes_size):
    """Formatea el tamaño en bytes a MB/GB"""
    if not bytes_size or bytes_size <= 0:
        return ""
    mb = bytes_size / (1024 * 1024)
    if mb >= 1024:
        return f" ({mb/1024:.1f}GB)"
    return f" ({mb:.1f}MB)"

def generar_id_busqueda(user_id, consulta):
    """Genera un ID único para cada búsqueda"""
    return f"{user_id}_{hash(consulta)}_{int(time.time())}"