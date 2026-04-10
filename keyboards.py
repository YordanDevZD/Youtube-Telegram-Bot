from aiogram.utils.keyboard import InlineKeyboardBuilder

def crear_botones_navegacion(search_id, indice_actual, total_videos):
    builder = InlineKeyboardBuilder()
    if indice_actual > 0:
        builder.button(text="◀️ Anterior", callback_data=f"nav|{search_id}|{indice_actual - 1}")
    builder.button(text=f"📄 {indice_actual + 1}/{total_videos}", callback_data="ignore")
    if indice_actual < total_videos - 1:
        builder.button(text="Siguiente ▶️", callback_data=f"nav|{search_id}|{indice_actual + 1}")
    builder.button(text="⬇️ Descargar", callback_data=f"download_menu|{search_id}|{indice_actual}")
    builder.button(text="❌ Cerrar", callback_data="close")
    builder.adjust(3, 1, 1)
    return builder.as_markup()

def crear_botones_descarga(info, url):
    builder = InlineKeyboardBuilder()
    
    # Mostrar primero las calidades numéricas (ordenadas descendente)
    calidades = [h for h in info['formats'].keys() if isinstance(h, int)]
    for altura in sorted(calidades, reverse=True):
        fmt = info['formats'][altura]
        builder.button(
            text=fmt['desc'],
            callback_data=f"dl|video|{fmt['selector']}|{url}"
        )
    
    # Mejor calidad
    if 'best' in info['formats']:
        builder.button(
            text=info['formats']['best']['desc'],
            callback_data=f"dl|video|{info['formats']['best']['selector']}|{url}"
        )
    
    # Audio
    if 'audio' in info['formats']:
        builder.button(
            text=info['formats']['audio']['desc'],
            callback_data=f"dl|audio|{info['formats']['audio']['selector']}|{url}"
        )
    
    builder.button(text="❌ Cancelar", callback_data="close_msg")
    builder.adjust(2)
    return builder.as_markup()