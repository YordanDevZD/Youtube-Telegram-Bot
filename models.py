import json
import time
import os
from config import SUSCRIPCIONES_FILE, logger

class SubscriptionManager:
    def __init__(self):
        self.suscripciones = self._cargar_suscripciones()
    
    def _cargar_suscripciones(self):
        if os.path.exists(SUSCRIPCIONES_FILE):
            with open(SUSCRIPCIONES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def guardar_suscripciones(self):
        with open(SUSCRIPCIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.suscripciones, f, indent=2, ensure_ascii=False)
    
    async def agregar_suscripcion(self, user_id, canal_info, ultimo_video_id):
        user_id_str = str(user_id)
        if user_id_str not in self.suscripciones:
            self.suscripciones[user_id_str] = {}
        
        self.suscripciones[user_id_str][canal_info['id']] = {
            'nombre': canal_info['name'],
            'url': canal_info['url'],
            'ultimo_video': ultimo_video_id,
            'fecha_suscripcion': time.time()
        }
        
        self.guardar_suscripciones()
        return True
    
    async def eliminar_suscripcion(self, user_id, canal_id):
        user_id_str = str(user_id)
        if user_id_str in self.suscripciones and canal_id in self.suscripciones[user_id_str]:
            nombre = self.suscripciones[user_id_str][canal_id]['nombre']
            del self.suscripciones[user_id_str][canal_id]
            if not self.suscripciones[user_id_str]:
                del self.suscripciones[user_id_str]
            self.guardar_suscripciones()
            return True, nombre
        return False, None
    
    def listar_suscripciones(self, user_id):
        user_id_str = str(user_id)
        if user_id_str not in self.suscripciones:
            return []
        return list(self.suscripciones[user_id_str].values())
    
    def get_user_subscriptions(self, user_id):
        user_id_str = str(user_id)
        return self.suscripciones.get(user_id_str, {})
    
    def get_all_subscriptions(self):
        return self.suscripciones

# Cache para búsquedas
cache = {}