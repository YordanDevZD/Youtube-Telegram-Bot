import asyncio
from aiogram import types, Bot
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dispatcher import dp
from models import SubscriptionManager
from youtube_client import YouTubeClient
from utils import escape_markdown, formatear_duracion
from config import logger

subscription_manager = SubscriptionManager()
youtube_client = YouTubeClient()

@dp.message(Command("addchannel"))
@dp.message(Command("ad"))
async def cmd_addchannel(message: types.Message):
    canal_input = message.text.replace("/addchannel", "").replace("/ad", "").strip()
    
    if not canal_input:
        await message.answer("📺 *Agregar canal*\n\nUsa:\n`/addchannel @midudev`\n`/ad @midudev`\n\nTambién puedes enviar la URL del canal", parse_mode="Markdown")
        return
    
    msg = await message.answer(f"🔍 Buscando canal `{canal_input}`...", parse_mode="Markdown")
    
    canal_info = await youtube_client.obtener_canal(canal_input)
    
    if not canal_info:
        await msg.delete()
        await message.answer("❌ No se encontró el canal")
        return
    
    user_id_str = str(message.from_user.id)
    if user_id_str in subscription_manager.suscripciones and canal_info['id'] in subscription_manager.suscripciones[user_id_str]:
        await msg.delete()
        await message.answer("❌ Ya estás suscrito al canal")
        return
    
    videos_recientes = await youtube_client.obtener_ultimos_videos(canal_info['url'], 1)
    ultimo_video_id = videos_recientes[0]['id'] if videos_recientes else None
    
    await subscription_manager.agregar_suscripcion(message.from_user.id, canal_info, ultimo_video_id)
    
    await msg.delete()
    await message.answer(f"✅ *Suscrito al canal:*\n📺 {canal_info['name']}\n\nRecibirás notificaciones cuando suba nuevos videos", parse_mode="Markdown")

@dp.message(Command("channels"))
@dp.message(Command("cls"))
async def cmd_channels(message: types.Message):
    suscripciones_user = subscription_manager.listar_suscripciones(message.from_user.id)
    
    if not suscripciones_user:
        await message.answer("📭 *No estás suscrito a ningún canal*\n\nUsa `/addchannel @canal` para suscribirte", parse_mode="Markdown")
        return
    
    respuesta = "📺 *Tus canales suscritos*\n\n"
    for i, canal in enumerate(suscripciones_user, 1):
        respuesta += f"{i}. **{canal['nombre']}**\n"
        respuesta += f"   🆔 `{canal['url']}`\n"
        respuesta += f"   🗑️ Para eliminar: `/removechannel {i}`\n\n"
    
    await message.answer(respuesta, parse_mode="Markdown")

@dp.message(Command("removechannel"))
@dp.message(Command("rc"))
async def cmd_removechannel(message: types.Message):
    args = message.text.replace("/removechannel", "").replace("/rc", "").strip()
    
    suscripciones_user = subscription_manager.listar_suscripciones(message.from_user.id)
    
    if not suscripciones_user:
        await message.answer("📭 No estás suscrito a ningún canal", parse_mode="Markdown")
        return
    
    if not args:
        respuesta = "🗑️ *Eliminar canal*\n\nTus canales:\n"
        for i, canal in enumerate(suscripciones_user, 1):
            respuesta += f"{i}. {canal['nombre']}\n"
        respuesta += f"\nEnvía: `/removechannel <número>`\nEjemplo: `/rc 1`"
        await message.answer(respuesta, parse_mode="Markdown")
        return
    
    try:
        if args.isdigit():
            indice = int(args) - 1
            if 0 <= indice < len(suscripciones_user):
                canal_id = list(subscription_manager.suscripciones[str(message.from_user.id)].keys())[indice]
                exito, nombre = await subscription_manager.eliminar_suscripcion(message.from_user.id, canal_id)
                if exito:
                    await message.answer(f"✅ Eliminado: **{nombre}**", parse_mode="Markdown")
                else:
                    await message.answer("❌ No se pudo eliminar", parse_mode="Markdown")
            else:
                await message.answer("❌ Número inválido", parse_mode="Markdown")
        else:
            await message.answer("❌ Envía un número válido", parse_mode="Markdown")
    except:
        await message.answer("❌ Error, usa el número del canal", parse_mode="Markdown")

async def verificar_nuevos_videos(bot: Bot):
    while True:
        try:
            print(f"🔍 Verificando canales... ({len(subscription_manager.suscripciones)} usuarios)")
            
            for user_id_str, canales in subscription_manager.suscripciones.items():
                for canal_id, canal_data in canales.items():
                    try:
                        videos_recientes = await youtube_client.obtener_ultimos_videos(canal_data['url'], 1)
                        
                        if videos_recientes:
                            video_nuevo = videos_recientes[0]
                            ultimo_video_guardado = canal_data.get('ultimo_video')
                            
                            if ultimo_video_guardado != video_nuevo['id']:
                                canal_data['ultimo_video'] = video_nuevo['id']
                                subscription_manager.guardar_suscripciones()
                                
                                duracion_str = formatear_duracion(video_nuevo['duracion'])
                                
                                notificacion = f"""
📢 *¡NUEVO VIDEO!* 📢

📺 *Canal:* {escape_markdown(canal_data['nombre'])}
🎬 *Título:* {escape_markdown(video_nuevo['titulo'])}
⏱️ *Duración:* {duracion_str}

🔗 {video_nuevo['url']}
"""
                                try:
                                    await bot.send_message(int(user_id_str), notificacion, parse_mode="Markdown")
                                    print(f"✅ Notificación enviada a usuario {user_id_str} - {video_nuevo['titulo'][:30]}")
                                except Exception as e:
                                    print(f"❌ Error al enviar a {user_id_str}: {e}")
                    except Exception as e:
                        print(f"❌ Error verificando canal {canal_id}: {e}")
        except Exception as e:
            print(f"❌ Error en verificador: {e}")
        
        await asyncio.sleep(600)