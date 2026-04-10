import asyncio
from dispatcher import dp, bot
from handlers.subscription import verificar_nuevos_videos
import handlers.search
import handlers.download
import handlers.subscription
import handlers.general

async def main():
    print("=" * 40)
    print("🎬 YouTube Bot Iniciado!")
    print("✅ Sistema modular implementado")
    print("=" * 40)
    
    # Iniciar verificador de canales
    asyncio.create_task(verificar_nuevos_videos(bot))
    print("✅ Verificador de canales iniciado (cada 10 minutos)")
    
    # Iniciar polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")