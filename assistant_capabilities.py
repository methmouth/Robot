import subprocess
import time
from datetime import datetime, timedelta
import json

class AssistantCapabilities:
    """
    Todas las capacidades que el asistente puede realizar
    Organizado por categorías
    """
    
    def __init__(self, control, vision, voice):
        self.control = control
        self.vision = vision
        self.voice = voice
        
        # Registro de apps instaladas
        self.installed_apps = self._scan_installed_apps()
        
        print(f"[🎯] {len(self.installed_apps)} apps detectadas")
    
    # ===== COMUNICACIÓN =====
    
    def send_whatsapp_message(self, contact: str, message: str) -> dict:
        """Envía mensaje por WhatsApp"""
        print(f"[💬] Enviando WhatsApp a {contact}: {message}")
        
        try:
            # Abrir WhatsApp
            self.control._open_app('com.whatsapp')
            time.sleep(2)
            
            # Buscar contacto
            frame = self._capture_screen()
            search_bar = self.vision.find_element(frame, "barra de búsqueda")
            
            if search_bar.get('found'):
                self.control.click(search_bar['x'], search_bar['y'], 1080, 1920)
                time.sleep(0.5)
                
                # Escribir nombre del contacto
                self.control._type_text(contact)
                time.sleep(1)
                
                # Click en primer resultado
                self.control.click(540, 300, 1080, 1920)
                time.sleep(1)
                
                # Escribir mensaje
                frame = self._capture_screen()
                input_box = self.vision.find_element(frame, "cuadro de texto para mensaje")
                
                if input_box.get('found'):
                    self.control.click(input_box['x'], input_box['y'], 1080, 1920)
                    time.sleep(0.3)
                    self.control._type_text(message)
                    time.sleep(0.5)
                    
                    # Enviar
                    send_btn = self.vision.find_element(frame, "botón enviar")
                    if send_btn.get('found'):
                        self.control.click(send_btn['x'], send_btn['y'], 1080, 1920)
                        
                        self.voice.speak(f"Mensaje enviado a {contact}")
                        return {'success': True}
            
            return {'success': False, 'reason': 'no_se_pudo_encontrar_interfaz'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def make_phone_call(self, contact: str) -> dict:
        """Realiza llamada telefónica"""
        print(f"[📞] Llamando a {contact}")
        
        try:
            # Abrir teléfono
            self.control._open_app('com.android.dialer')
            time.sleep(1)
            
            # Buscar contacto
            frame = self._capture_screen()
            search = self.vision.find_element(frame, "buscar contacto")
            
            if search.get('found'):
                self.control.click(search['x'], search['y'], 1080, 1920)
                time.sleep(0.5)
                self.control._type_text(contact)
                time.sleep(1)
                
                # Click en contacto
                self.control.click(540, 300, 1080, 1920)
                time.sleep(0.5)
                
                # Botón llamar
                call_btn = self.vision.find_element(frame, "botón llamar")
                if call_btn.get('found'):
                    self.control.click(call_btn['x'], call_btn['y'], 1080, 1920)
                    self.voice.speak(f"Llamando a {contact}")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def read_notifications(self) -> dict:
        """Lee notificaciones pendientes"""
        print("[🔔] Leyendo notificaciones")
        
        try:
            # Abrir panel de notificaciones
            self.control.swipe(540, 10, 540, 500, duration=0.3)
            time.sleep(1)
            
            # Capturar y analizar
            frame = self._capture_screen()
            analysis = self.vision.read_screen_text(frame)
            
            notifications = analysis.get('structured', {}).get('messages', [])
            
            if notifications:
                self.voice.speak(f"Tienes {len(notifications)} notificaciones")
                for notif in notifications[:3]:  # Solo primeras 3
                    self.voice.speak(notif)
                
                return {'success': True, 'count': len(notifications)}
            else:
                self.voice.speak("No tienes notificaciones")
                return {'success': True, 'count': 0}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===== PRODUCTIVIDAD =====
    
    def create_calendar_event(self, title: str, date: str, time_str: str, duration: int = 60) -> dict:
        """Crea evento en calendario"""
        print(f"[📅] Creando evento: {title} el {date} a las {time_str}")
        
        try:
            # Parsear fecha y hora
            event_datetime = self._parse_datetime(date, time_str)
            
            if not event_datetime:
                return {'success': False, 'reason': 'fecha_invalida'}
            
            # Abrir calendario
            self.control._open_app('com.google.android.calendar')
            time.sleep(2)
            
            # Buscar botón +
            frame = self._capture_screen()
            add_btn = self.vision.find_element(frame, "botón crear evento o más")
            
            if add_btn.get('found'):
                self.control.click(add_btn['x'], add_btn['y'], 1080, 1920)
                time.sleep(1)
                
                # Llenar formulario
                # Título
                title_field = self.vision.find_element(frame, "campo título")
                if title_field.get('found'):
                    self.control.click(title_field['x'], title_field['y'], 1080, 1920)
                    time.sleep(0.3)
                    self.control._type_text(title)
                
                # Fecha y hora (esto varía por app de calendario)
                # ... implementación específica ...
                
                # Guardar
                save_btn = self.vision.find_element(frame, "guardar o confirmar")
                if save_btn.get('found'):
                    self.control.click(save_btn['x'], save_btn['y'], 1080, 1920)
                    
                    self.voice.speak(f"Evento '{title}' creado")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def set_reminder(self, task: str, when: str) -> dict:
        """Establece recordatorio"""
        print(f"[⏰] Recordatorio: {task} - {when}")
        
        # Usar Google Assistant para recordatorios
        command = f"Recordarme {task} {when}"
        return self._use_google_assistant(command)
    
    def take_note(self, content: str, title: str = None) -> dict:
        """Toma una nota"""
        print(f"[📝] Nota: {content}")
        
        try:
            # Abrir app de notas (Google Keep)
            self.control._open_app('com.google.android.keep')
            time.sleep(2)
            
            # Crear nota nueva
            frame = self._capture_screen()
            new_note = self.vision.find_element(frame, "nueva nota o botón más")
            
            if new_note.get('found'):
                self.control.click(new_note['x'], new_note['y'], 1080, 1920)
                time.sleep(1)
                
                # Escribir contenido
                self.control._type_text(content)
                time.sleep(0.5)
                
                # Guardar (generalmente automático)
                self.control._press_back()
                
                self.voice.speak("Nota guardada")
                return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===== ENTRETENIMIENTO =====
    
    def play_music(self, query: str, app: str = 'spotify') -> dict:
        """Reproduce música"""
        print(f"[🎵] Reproduciendo: {query}")
        
        app_packages = {
            'spotify': 'com.spotify.music',
            'youtube_music': 'com.google.android.apps.youtube.music'
        }
        
        package = app_packages.get(app, 'com.spotify.music')
        
        try:
            # Abrir app de música
            self.control._open_app(package)
            time.sleep(2)
            
            # Buscar
            frame = self._capture_screen()
            search_btn = self.vision.find_element(frame, "búsqueda o lupa")
            
            if search_btn.get('found'):
                self.control.click(search_btn['x'], search_btn['y'], 1080, 1920)
                time.sleep(0.5)
                
                self.control._type_text(query)
                time.sleep(1)
                
                # Click en primer resultado
                self.control.click(540, 400, 1080, 1920)
                time.sleep(0.5)
                
                # Play
                play_btn = self.vision.find_element(frame, "reproducir o play")
                if play_btn.get('found'):
                    self.control.click(play_btn['x'], play_btn['y'], 1080, 1920)
                    
                    self.voice.speak(f"Reproduciendo {query}")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_youtube(self, query: str, autoplay: bool = False) -> dict:
        """Busca en YouTube"""
        print(f"[📺] YouTube: {query}")
        
        try:
            self.control._open_app('com.google.android.youtube')
            time.sleep(2)
            
            frame = self._capture_screen()
            search = self.vision.find_element(frame, "buscar")
            
            if search.get('found'):
                self.control.click(search['x'], search['y'], 1080, 1920)
                time.sleep(0.5)
                
                self.control._type_text(query)
                time.sleep(0.5)
                
                # Enter para buscar
                subprocess.run("adb shell input keyevent 66", shell=True)  # ENTER
                time.sleep(2)
                
                if autoplay:
                    # Click en primer video
                    self.control.click(540, 400, 1080, 1920)
                    self.voice.speak(f"Reproduciendo {query}")
                else:
                    self.voice.speak(f"Resultados de {query}")
                
                return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===== INFORMACIÓN =====
    
    def web_search(self, query: str, browser: str = 'chrome') -> dict:
        """Busca en la web"""
        print(f"[🔍] Buscando: {query}")
        
        browser_packages = {
            'chrome': 'com.android.chrome',
            'firefox': 'org.mozilla.firefox',
            'brave': 'com.brave.browser'
        }
        
        package = browser_packages.get(browser, 'com.android.chrome')
        
        try:
            self.control._open_app(package)
            time.sleep(2)
            
            # Click en barra de búsqueda
            self.control.click(540, 150, 1080, 1920)
            time.sleep(0.5)
            
            # Escribir búsqueda
            self.control._type_text(query)
            time.sleep(0.5)
            
            # Enter
            subprocess.run("adb shell input keyevent 66", shell=True)
            
            self.voice.speak(f"Buscando {query}")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_weather(self) -> dict:
        """Obtiene el clima"""
        print("[🌤️] Consultando clima")
        
        # Usar Google Assistant
        return self._use_google_assistant("¿qué tiempo hace?")
    
    def get_news(self, topic: str = None) -> dict:
        """Obtiene noticias"""
        query = f"noticias de {topic}" if topic else "noticias"
        print(f"[📰] {query}")
        
        return self.web_search(query)
    
```python
    # ===== SISTEMA =====
    
    def change_settings(self, setting: str, value: Any) -> dict:
        """Cambia configuraciones del sistema"""
        print(f"[⚙️] Cambiando {setting} a {value}")
        
        settings_map = {
            'wifi': self._toggle_wifi,
            'bluetooth': self._toggle_bluetooth,
            'brightness': self._set_brightness,
            'volume': self._set_volume,
            'airplane_mode': self._toggle_airplane_mode,
            'do_not_disturb': self._toggle_dnd,
            'rotation': self._toggle_rotation,
        }
        
        handler = settings_map.get(setting.lower())
        if handler:
            return handler(value)
        
        return {'success': False, 'reason': 'setting_not_supported'}
    
    def take_screenshot(self, save_where: str = 'gallery') -> dict:
        """Toma captura de pantalla"""
        print("[📸] Capturando pantalla")
        
        try:
            subprocess.run("adb shell input keyevent 120", shell=True)  # SCREENSHOT
            time.sleep(1)
            
            self.voice.speak("Captura tomada")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def share_current_screen(self, app: str = 'whatsapp') -> dict:
        """Comparte pantalla actual"""
        print(f"[📤] Compartiendo a {app}")
        
        try:
            # Tomar screenshot
            self.take_screenshot()
            time.sleep(1)
            
            # Abrir galería
            self.control._open_app('com.google.android.apps.photos')
            time.sleep(2)
            
            # Seleccionar última foto
            self.control.click(200, 300, 1080, 1920)
            time.sleep(1)
            
            # Botón compartir
            frame = self._capture_screen()
            share_btn = self.vision.find_element(frame, "compartir")
            
            if share_btn.get('found'):
                self.control.click(share_btn['x'], share_btn['y'], 1080, 1920)
                time.sleep(1)
                
                # Buscar app destino
                app_element = self.vision.find_element(frame, f"icono {app}")
                if app_element.get('found'):
                    self.control.click(app_element['x'], app_element['y'], 1080, 1920)
                    
                    self.voice.speak(f"Compartiendo por {app}")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def install_app(self, app_name: str) -> dict:
        """Instala aplicación desde Play Store"""
        print(f"[📦] Instalando: {app_name}")
        
        try:
            # Abrir Play Store
            self.control._open_app('com.android.vending')
            time.sleep(2)
            
            # Buscar
            frame = self._capture_screen()
            search = self.vision.find_element(frame, "buscar")
            
            if search.get('found'):
                self.control.click(search['x'], search['y'], 1080, 1920)
                time.sleep(0.5)
                
                self.control._type_text(app_name)
                time.sleep(0.5)
                
                # Enter
                subprocess.run("adb shell input keyevent 66", shell=True)
                time.sleep(2)
                
                # Click en primera app
                self.control.click(540, 400, 1080, 1920)
                time.sleep(2)
                
                # Botón instalar
                install_btn = self.vision.find_element(frame, "instalar")
                if install_btn.get('found'):
                    self.control.click(install_btn['x'], install_btn['y'], 1080, 1920)
                    
                    self.voice.speak(f"Instalando {app_name}. Te avisaré cuando termine")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def cleanup_storage(self) -> dict:
        """Limpia almacenamiento"""
        print("[🧹] Limpiando almacenamiento")
        
        try:
            # Abrir configuración de almacenamiento
            self.control._open_app('com.android.settings')
            time.sleep(2)
            
            # Buscar "Almacenamiento"
            frame = self._capture_screen()
            storage = self.vision.find_element(frame, "almacenamiento o storage")
            
            if storage.get('found'):
                self.control.click(storage['x'], storage['y'], 1080, 1920)
                time.sleep(2)
                
                # Liberar espacio
                free_space = self.vision.find_element(frame, "liberar espacio")
                if free_space.get('found'):
                    self.control.click(free_space['x'], free_space['y'], 1080, 1920)
                    
                    self.voice.speak("Limpiando almacenamiento")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===== NAVEGACIÓN =====
    
    def navigate_to(self, destination: str, app: str = 'google_maps') -> dict:
        """Navega a un destino"""
        print(f"[🗺️] Navegando a: {destination}")
        
        try:
            # Abrir Maps
            self.control._open_app('com.google.android.apps.maps')
            time.sleep(2)
            
            # Buscar destino
            frame = self._capture_screen()
            search = self.vision.find_element(frame, "buscar o destino")
            
            if search.get('found'):
                self.control.click(search['x'], search['y'], 1080, 1920)
                time.sleep(0.5)
                
                self.control._type_text(destination)
                time.sleep(1)
                
                # Seleccionar primer resultado
                self.control.click(540, 300, 1080, 1920)
                time.sleep(2)
                
                # Botón "Cómo llegar"
                directions_btn = self.vision.find_element(frame, "cómo llegar o direcciones")
                if directions_btn.get('found'):
                    self.control.click(directions_btn['x'], directions_btn['y'], 1080, 1920)
                    time.sleep(1)
                    
                    # Iniciar navegación
                    start_btn = self.vision.find_element(frame, "iniciar")
                    if start_btn.get('found'):
                        self.control.click(start_btn['x'], start_btn['y'], 1080, 1920)
                        
                        self.voice.speak(f"Navegando a {destination}")
                        return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def find_nearby(self, place_type: str) -> dict:
        """Encuentra lugares cercanos"""
        print(f"[📍] Buscando {place_type} cerca")
        
        return self.navigate_to(f"{place_type} cerca")
    
    # ===== AUTOMATIZACIÓN =====
    
    def execute_routine(self, routine_name: str) -> dict:
        """Ejecuta una rutina guardada"""
        print(f"[🔄] Ejecutando rutina: {routine_name}")
        
        # Obtener rutina del core
        if not hasattr(self, 'core'):
            return {'success': False, 'reason': 'no_core'}
        
        routine = self.core.routines.get(routine_name)
        if not routine:
            self.voice.speak(f"No conozco la rutina {routine_name}")
            return {'success': False, 'reason': 'routine_not_found'}
        
        actions = routine.get('actions', [])
        
        self.voice.speak(f"Ejecutando rutina {routine_name}")
        
        for action in actions:
            # Ejecutar cada acción
            result = self._execute_routine_action(action)
            if not result.get('success'):
                self.voice.speak(f"Error en paso: {action}")
                return result
            
            time.sleep(1)
        
        self.voice.speak("Rutina completada")
        return {'success': True}
    
    def create_shortcut(self, command: str, actions: List[dict]) -> dict:
        """Crea atajo personalizado"""
        print(f"[⚡] Creando atajo: {command}")
        
        # Guardar en core
        if hasattr(self, 'core'):
            self.core.routines[command.lower()] = {
                'actions': actions,
                'time_window': 'anytime',
                'occurrences': 0,
                'confidence': 1.0,
                'automated': True,
                'voice_trigger': command.lower()
            }
            
            self.core._save_memory()
            self.voice.speak(f"Atajo '{command}' creado")
            return {'success': True}
        
        return {'success': False}
    
    # ===== ACCESIBILIDAD =====
    
    def read_screen_aloud(self) -> dict:
        """Lee el contenido de la pantalla en voz alta"""
        print("[🔊] Leyendo pantalla")
        
        try:
            frame = self._capture_screen()
            analysis = self.vision.read_screen_text(frame)
            
            text = analysis.get('all_text', '')
            
            if text:
                self.voice.speak("En pantalla dice:")
                self.voice.speak(text)
                return {'success': True}
            else:
                self.voice.speak("No hay texto legible en pantalla")
                return {'success': False, 'reason': 'no_text'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def describe_screen(self) -> dict:
        """Describe lo que hay en pantalla"""
        print("[👁️] Describiendo pantalla")
        
        try:
            frame = self._capture_screen()
            
            # Usar Gemini Vision para descripción
            prompt = """Describe esta pantalla de Android de forma natural y útil.
            Menciona qué app es, qué se ve, y qué puede hacer el usuario.
            Sé breve pero informativo."""
            
            description = self.vision.vision.api_call_with_context(prompt, frame)
            
            self.voice.speak(description)
            return {'success': True, 'description': description}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def emergency_call(self, number: str = '911') -> dict:
        """Realiza llamada de emergencia"""
        print(f"[🚨] EMERGENCIA: Llamando al {number}")
        
        try:
            # Llamada directa
            subprocess.run(f'adb shell am start -a android.intent.action.CALL -d tel:{number}', 
                          shell=True)
            
            self.voice.speak(f"Llamando a emergencias {number}")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===== SOCIAL MEDIA =====
    
    def post_to_social(self, platform: str, content: str, image: bool = False) -> dict:
        """Publica en redes sociales"""
        print(f"[📱] Publicando en {platform}")
        
        platforms = {
            'twitter': 'com.twitter.android',
            'instagram': 'com.instagram.android',
            'facebook': 'com.facebook.katana',
            'tiktok': 'com.zhiliaoapp.musically'
        }
        
        package = platforms.get(platform.lower())
        if not package:
            return {'success': False, 'reason': 'platform_not_supported'}
        
        try:
            # Abrir app
            self.control._open_app(package)
            time.sleep(2)
            
            # Buscar botón de crear post
            frame = self._capture_screen()
            create_btn = self.vision.find_element(frame, "crear post o nueva publicación")
            
            if create_btn.get('found'):
                self.control.click(create_btn['x'], create_btn['y'], 1080, 1920)
                time.sleep(1)
                
                # Escribir contenido
                self.control._type_text(content)
                time.sleep(0.5)
                
                # Publicar
                publish_btn = self.vision.find_element(frame, "publicar o compartir")
                if publish_btn.get('found'):
                    self.control.click(publish_btn['x'], publish_btn['y'], 1080, 1920)
                    
                    self.voice.speak(f"Publicado en {platform}")
                    return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def like_current_post(self) -> dict:
        """Da like al contenido actual"""
        print("[❤️] Dando like")
        
        try:
            frame = self._capture_screen()
            like_btn = self.vision.find_element(frame, "me gusta o corazón o like")
            
            if like_btn.get('found'):
                self.control.click(like_btn['x'], like_btn['y'], 1080, 1920)
                self.voice.speak("Like dado")
                return {'success': True}
            
            return {'success': False, 'reason': 'like_button_not_found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ===== UTILIDADES PRIVADAS =====
    
    def _capture_screen(self):
        """Captura pantalla actual"""
        if hasattr(self, '_screen_capture'):
            return self._screen_capture.get_frame()
        return None
    
    def _scan_installed_apps(self) -> List[dict]:
        """Escanea apps instaladas"""
        try:
            result = subprocess.run(
                'adb shell pm list packages',
                shell=True,
                capture_output=True,
                text=True
            )
            
            packages = []
            for line in result.stdout.split('\n'):
                if line.startswith('package:'):
                    package = line.replace('package:', '').strip()
                    packages.append({'package': package})
            
            return packages
            
        except:
            return []
    
    def _use_google_assistant(self, query: str) -> dict:
        """Usa Google Assistant para comandos"""
        try:
            # Activar Assistant
            subprocess.run('adb shell input keyevent 231', shell=True)  # VOICE_ASSIST
            time.sleep(1)
            
            # El usuario hablaría aquí, pero podemos simular con texto
            self.control._type_text(query)
            subprocess.run("adb shell input keyevent 66", shell=True)  # ENTER
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _toggle_wifi(self, enable: bool) -> dict:
        """Activa/desactiva WiFi"""
        try:
            state = "enable" if enable else "disable"
            subprocess.run(f'adb shell svc wifi {state}', shell=True)
            
            status = "activado" if enable else "desactivado"
            self.voice.speak(f"WiFi {status}")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _toggle_bluetooth(self, enable: bool) -> dict:
        """Activa/desactiva Bluetooth"""
        try:
            state = "enable" if enable else "disable"
            subprocess.run(f'adb shell svc bluetooth {state}', shell=True)
            
            status = "activado" if enable else "desactivado"
            self.voice.speak(f"Bluetooth {status}")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _set_brightness(self, level: int) -> dict:
        """Ajusta brillo (0-255)"""
        try:
            level = max(0, min(255, level))
            subprocess.run(
                f'adb shell settings put system screen_brightness {level}',
                shell=True
            )
            
            self.voice.speak(f"Brillo ajustado a {int(level/255*100)}%")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _set_volume(self, level: int) -> dict:
        """Ajusta volumen (0-15)"""
        try:
            level = max(0, min(15, level))
            
            # Subir/bajar según nivel actual
            for _ in range(abs(level)):
                keycode = 24 if level > 0 else 25  # VOLUME_UP : VOLUME_DOWN
                subprocess.run(f'adb shell input keyevent {keycode}', shell=True)
                time.sleep(0.1)
            
            self.voice.speak(f"Volumen ajustado")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _toggle_airplane_mode(self, enable: bool) -> dict:
        """Activa/desactiva modo avión"""
        try:
            state = 1 if enable else 0
            subprocess.run(
                f'adb shell settings put global airplane_mode_on {state}',
                shell=True
            )
            subprocess.run(
                'adb shell am broadcast -a android.intent.action.AIRPLANE_MODE',
                shell=True
            )
            
            status = "activado" if enable else "desactivado"
            self.voice.speak(f"Modo avión {status}")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _toggle_dnd(self, enable: bool) -> dict:
        """Activa/desactiva No Molestar"""
        try:
            # Abrir configuración rápida
            self.control.swipe(540, 10, 540, 500, duration=0.3)
            time.sleep(1)
            
            # Buscar icono DND
            frame = self._capture_screen()
            dnd_btn = self.vision.find_element(frame, "no molestar")
            
            if dnd_btn.get('found'):
                self.control.click(dnd_btn['x'], dnd_btn['y'], 1080, 1920)
                
                status = "activado" if enable else "desactivado"
                self.voice.speak(f"No molestar {status}")
                return {'success': True}
            
            return {'success': False}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _toggle_rotation(self, enable: bool) -> dict:
        """Activa/desactiva rotación automática"""
        try:
            state = 1 if enable else 0
            subprocess.run(
                f'adb shell settings put system accelerometer_rotation {state}',
                shell=True
            )
            
            status = "activada" if enable else "desactivada"
            self.voice.speak(f"Rotación automática {status}")
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _parse_datetime(self, date_str: str, time_str: str):
        """Parsea fecha y hora natural"""
        # Implementación simple
        # En producción usar librería como dateparser
        
        try:
            # Ejemplos: "mañana", "en 2 horas", "el viernes", etc.
            now = datetime.now()
            
            # Parseo simple
            if 'mañana' in date_str.lower():
                target_date = now + timedelta(days=1)
            elif 'hoy' in date_str.lower():
                target_date = now
            else:
                # Formato ISO
                target_date = datetime.fromisoformat(date_str)
            
            # Parsear hora
            if ':' in time_str:
                hour, minute = map(int, time_str.split(':'))
                target_date = target_date.replace(hour=hour, minute=minute)
            
            return target_date
            
        except:
            return None
    
    def _execute_routine_action(self, action: str) -> dict:
        """Ejecuta una acción de rutina"""
        # Mapear string de acción a método
        # Ejemplo: "open_whatsapp" -> self.control._open_app('com.whatsapp')
        
        if action.startswith('open_'):
            app = action.replace('open_', '')
            # Buscar package
            for installed_app in self.installed_apps:
                if app in installed_app['package']:
                    self.control._open_app(installed_app['package'])
                    return {'success': True}
        
        return {'success': False}
    
    def inject_screen_capture(self, screen_capture):
        """Inyecta capturador de pantalla"""
        self._screen_capture = screen_capture
    
    def inject_core(self, core):
        """Inyecta núcleo del asistente"""
        self.core = core