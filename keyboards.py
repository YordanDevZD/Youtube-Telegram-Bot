from aiogram.utils.keyboard import InlineKeyboardBuilder

def crear_botones_navegacion(search_id, indice_actual, total_videos):
    builder = InlineKeyboardBuilder()
    if indice_actual > 0:
        builder.button(text="◀️ Anterior", callback_data=f"nav|{search_id}|{indice_actual - 1}")
    builder.button(text=f"📄 {indice_actual + 1}/{total_videos}", callback_data="ignore")
    if indice_actual < total_videos - 1:
        builder.button(text="Siguiente ▶️", callback_data=f"nav|{search_id}|{indice_actual + 1}")
    builder.button(text="⬇️ Descargar 360p", callback_data=f"download_menu|{search_id}|{indice_actual}")
    builder.button(text="❌ Cerrar", callback_data="close")
    builder.adjust(3, 1, 1)
    return builder.as_markup()
