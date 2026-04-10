from aiogram.utils.keyboard import InlineKeyboardBuilder

def crear_botones_navegacion(search_id, indice_actual, total_videos):
    builder = InlineKeyboardBuilder()
    
    if indice_actual > 0:
        builder.button(
            text="◀️ Anterior",
            callback_data=f"nav|{search_id}|{indice_actual - 1}"
        )
    
    builder.button(
        text=f"📄 {indice_actual + 1}/{total_videos}",
        callback_data="ignore"
    )
    
    if indice_actual < total_videos - 1:
        builder.button(
            text="Siguiente ▶️",
            callback_data=f"nav|{search_id}|{indice_actual + 1}"
        )
    
    builder.button(
        text="⬇️ Descargar",
        callback_data=f"download_menu|{search_id}|{indice_actual}"
    )
    
    builder.button(
        text="❌ Cerrar",
        callback_data="close"
    )
    
    builder.adjust(3, 1, 1)
    
    return builder.as_markup()

def crear_botones_descarga(info, url):
    builder = InlineKeyboardBuilder()
    
    alturas = sorted([h for h in info['formats'].keys() if isinstance(h, int)], reverse=True)
    
    for altura in alturas:
        fmt = info['formats'][altura]
        from utils import formatear_tamaño
        tamaño = formatear_tamaño(fmt.get('filesize', 0))
        fps = fmt.get('fps', '')
        fps_text = f" {fps}fps" if fps else ""
        button_text = f"🎬 {altura}p{fps_text}{tamaño}"
        builder.button(
            text=button_text,
            callback_data=f"dl|video|{fmt['format_id']}|{url}"
        )
    
    if 'best' in info['formats']:
        fmt = info['formats']['best']
        tamaño = formatear_tamaño(fmt.get('filesize', 0))
        builder.button(
            text=f"⭐ Mejor calidad{tamaño}",
            callback_data=f"dl|video|{fmt['format_id']}|{url}"
        )
    
    if 'audio' in info['formats']:
        fmt = info['formats']['audio']
        tamaño = formatear_tamaño(fmt.get('filesize', 0))
        calidad_audio = fmt.get('abr', 0)
        calidad_text = f" {calidad_audio}kbps" if calidad_audio else ""
        builder.button(
            text=f"🎵 MP3{calidad_text}{tamaño}",
            callback_data=f"dl|audio|{fmt['format_id']}|{url}"
        )
    
    builder.button(
        text="❌ Cancelar",
        callback_data="close_msg"
    )
    
    builder.adjust(2)
    
    return builder.as_markup()
