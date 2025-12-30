import cv2
import time
import json
import sys
from assistant_core import AssistantCore
from conversation_manager import ConversationManager
from assistant_capabilities import AssistantCapabilities
from multimodal_fusion import MultimodalFusionSystem

# Importar todos los controladores
from eye_tracker import EyeTracker
from hand_gesture_controller import HandGestureController, HandGesture
from facial_expression_controller import FacialExpressionController, FacialExpression
from audio_gesture_controller import AudioGestureController, AudioGesture
from voice_manager import VoiceManager
from vision_gemini import GeminiVision
from screen_capture import ScreenCapture
from controlador_manager import ControladorHibrido
from smart_cache import SmartCache

class TotalAssistant:
    """
    ASISTENTE TOTAL - La integración definitiva
    Control completo de Android sin tocar nada
    """
    
    def __init__(self, config):
        print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🤖 ASISTENTE ANDROID TOTAL v5.0 🤖                  ║
║                                                              ║
║     "Tu compañero inteligente que hace TODO por ti"         ║
║                                                              ║
║  👁️ Mirada    ✋ Gestos    😊 Expresiones   🔊 Sonidos      ║
║  🎤 Voz       🧠 IA        💾 Memoria        🎯 Contexto     ║
║                                                              ║
║              "Simplemente pide lo que necesites"            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        self.config = config
        
        # === PASO 1: COMPONENTES BASE ===
        print("\n[⚙️] Inicializando componentes base...")
        
        # Conexión con dispositivo
        modo, url, ip = self._setup_connection()
        self.screen = ScreenCapture(modo=modo, url_stream=url)
        self.control = ControladorHibrido(modo=modo, ip=ip)
        
        # Visión y cache
        self.vision = GeminiVision(config['api_services']['openrouter'])
        self.cache = SmartCache(max_memory_mb=150)
        
        # Voz
        self.voice = VoiceManager()
        
        # === PASO 2: NÚCLEO INTELIGENTE ===
        print("[🧠] Inicializando núcleo cognitivo...")
        
        self.core = AssistantCore(self.vision, self.voice)
        self.conversation = ConversationManager(self.core, self.voice)
        self.capabilities = AssistantCapabilities(self.control, self.vision, self.voice)
        
        # Inyectar dependencias
        self.capabilities.inject_screen_capture(self.screen)
        self.capabilities.inject_core(self.core)
        self.conversation.inject_control_system(self)
        
        # === PASO 3: INPUTS MULTIMODALES ===
        print("[🎮] Inicializando controles multimodales...")
        
        self.eye_tracker = EyeTracker(webcam_id=0)
        self.hand_controller = HandGestureController()
        self.face_controller = FacialExpressionController()
        self.audio_controller = AudioGestureController()
        
        # Fusión multimodal
        self.fusion = MultimodalFusionSystem()
        self._register_fusion_callbacks()
        
        # === PASO 4: ESTADO ===
        self.webcam = cv2.VideoCapture(0)
        self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.running = False
        self.proactive_mode = True
        self.last_proactive_check = 0
        
        print("\n[✓] Sistema completo inicializado")
        print(f"[🤖] {self.core.personality['name']} listo para ayudarte\n")
    
    def _setup_connection(self):
        """Configurar conexión"""
        print("\n=== CONFIGURACIÓN DE CONEXIÓN ===")
        print("1. ADB (USB/WiFi - Recomendado)")
        print("2. WiFi Stream (ScreenStream + VNC)")
        
        choice = input("Selecciona (1/2): ")
        
        if choice == "2":
            ip = input("IP del dispositivo: ")
            return "network", f"http://{ip}:8080/stream.mjpeg", ip
        
        return "adb", None, None
    
    def _register_fusion_callbacks(self):
        """Registra callbacks del sistema de fusión"""
        
        # Mapear acciones del fusion a métodos del asistente
        action_map = {
            'click': self._handle_multimodal_click,
            'swipe': self._handle_multimodal_swipe,
            'scroll': self._handle_multimodal_scroll,
            'zoom': self._handle_multimodal_zoom,
            'system': self._handle_multimodal_system,
            'voice_command': self._handle_voice_command,
        }
        
        for action_name, handler in action_map.items():
            self.fusion.register_callback(action_name, handler)
    
    def start(self):
        """Inicia el asistente"""
        
        # Preguntar modo de operación
        print("\n=== MODO DE OPERACIÓN ===")
        print("1. Asistente Total (recomendado)")
        print("   - Control por voz, gestos, mirada")
        print("   - Conversación natural")
        print("   - Aprendizaje y sugerencias")
        print("\n2. Solo Voz")
        print("   - Control únicamente por comandos de voz")
        print("\n3. Solo Gestos")
        print("   - Control por mirada, manos y cara")
        
        mode = input("\nSelecciona modo (1/2/3): ")
        
        if mode == "2":
            self._voice_only_mode()
            return
        elif mode == "3":
            self._gesture_only_mode()
            return
        
        # Modo total (por defecto)
        self._total_mode()
    
    def _total_mode(self):
        """Modo asistente total"""
        
        # Calibración inicial
        if self._ask_yes_no("¿Realizar calibración inicial?"):
            self._full_calibration()
        
        # Iniciar todos los sistemas
        print("\n[🚀] Iniciando todos los sistemas...")
        
        self.eye_tracker.start()
        self.audio_controller.start(callback=self._handle_audio_gesture)
        
        # Iniciar conversación
        self.conversation.start_conversation()
        
        # Configurar escucha de voz continua
        self.voice.listen_continuous(self._handle_voice_input)
        
        # Main loop
        self.running = True
        self._main_loop_total()
    
    def _voice_only_mode(self):
        """Modo solo voz"""
        print("\n[🎤] Modo Solo Voz activado")
        
        self.conversation.start_conversation()
        self.voice.listen_continuous(self._handle_voice_input)
        
        self.running = True
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._cleanup()
    
    def _gesture_only_mode(self):
        """Modo solo gestos"""
        print("\n[👋] Modo Solo Gestos activado")
        
        if self._ask_yes_no("¿Calibrar eye tracking?"):
            self.eye_tracker.calibrate()
        
        self.eye_tracker.start()
        self.audio_controller.start(callback=self._handle_audio_gesture)
        
        self.running = True
        self._main_loop_gestures()
    
    def _main_loop_total(self):
        """Loop principal del modo total"""
        
        print("\n" + "="*70)
        print("🎮 ASISTENTE TOTAL ACTIVO")
        print("="*70)
        print("\nDi 'Hola " + self.core.personality['name'] + "' para activar comandos de voz")
        print("Usa gestos naturalmente")
        print("El asistente hará sugerencias proactivas")
        print("\nPresiona 'Q' para salir\n")
        fps_counter = 0
        fps_time = time.time()
        
        try:
            while self.running:
                # === CAPTURA DE INPUTS ===
                
                # 1. Webcam para gestos faciales y de mano
                ret, webcam_frame = self.webcam.read()
                if not ret:
                    continue
                
                webcam_frame = cv2.flip(webcam_frame, 1)
                
                # 2. Pantalla de Android
                android_frame = self.screen.get_frame()
                
                # === PROCESAMIENTO MULTIMODAL ===
                
                # Procesar gestos de mano
                hand_info = self.hand_controller.process_frame(webcam_frame.copy())
                if hand_info['gesture'] != HandGesture.NONE:
                    self.fusion.add_command(
                        'hand',
                        hand_info['gesture'].name.lower(),
                        hand_info['confidence'],
                        hand_info
                    )
                
                # Procesar expresiones faciales
                face_info = self.face_controller.process_frame(webcam_frame.copy())
                if face_info['expression'] != FacialExpression.NEUTRAL:
                    self.fusion.add_command(
                        'face',
                        face_info['expression'].name.lower(),
                        face_info['confidence'],
                        face_info
                    )
                
                # Procesar mirada
                eye_pos = self.eye_tracker.get_cursor_position(1080, 1920)
                if eye_pos:
                    self.fusion.add_command(
                        'eye',
                        'gaze',
                        0.9,
                        {'x': eye_pos[0], 'y': eye_pos[1]}
                    )
                
                # === ACTUALIZAR CONTEXTO ===
                
                if android_frame is not None:
                    # Detectar app actual
                    self._update_context(android_frame)
                    
                    # Agregar acciones recientes al contexto
                    if len(self.fusion.command_queue) > 0:
                        recent_action = self.fusion.command_queue[-1]
                        self.core.context.recent_actions.append(
                            f"{recent_action.source}_{recent_action.action}"
                        )
                
                # === FUSIÓN Y EJECUCIÓN ===
                
                action = self.fusion.process_commands()
                if action:
                    self.fusion.execute_action(action)
                
                # === SUGERENCIAS PROACTIVAS ===
                
                if self.proactive_mode:
                    current_time = time.time()
                    if current_time - self.last_proactive_check > 30:  # Cada 30s
                        suggestion = self.core.proactive_suggestion(android_frame)
                        if suggestion:
                            self.voice.speak(suggestion)
                        
                        self.last_proactive_check = current_time
                
                # === DETECCIÓN DE RUTINAS ===
                
                if len(self.core.context.recent_actions) >= 5:
                    time_window = self.core._get_time_of_day()
                    actions = list(self.core.context.recent_actions)[-5:]
                    self.core.detect_routine(actions, time_window)
                
                # === VISUALIZACIÓN ===
                
                display = self._create_total_visualization(
                    webcam_frame, android_frame, 
                    hand_info, face_info, eye_pos
                )
                
                cv2.imshow('Asistente Total', display)
                
                # === FPS & STATS ===
                
                fps_counter += 1
                if time.time() - fps_time > 1.0:
                    fps = fps_counter / (time.time() - fps_time)
                    stats = self.cache.get_statistics()
                    
                    print(f"\r[📊] FPS: {fps:.1f} | Cache: {stats['hit_rate']:.0f}% | "
                          f"Comandos: {len(self.fusion.command_queue)} | "
                          f"Memoria: {len(self.core.short_term_memory)}", end='')
                    
                    fps_counter = 0
                    fps_time = time.time()
                
                # Salir
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):  # Toggle proactive
                    self.proactive_mode = not self.proactive_mode
                    status = "activado" if self.proactive_mode else "desactivado"
                    self.voice.speak(f"Modo proactivo {status}")
        
        except KeyboardInterrupt:
            print("\n\n[!] Detenido por usuario")
        
        finally:
            self._cleanup()
    
    def _main_loop_gestures(self):
        """Loop para modo solo gestos"""
        
        print("\n[👋] Modo gestos activo - Presiona Q para salir\n")
        
        try:
            while self.running:
                ret, webcam_frame = self.webcam.read()
                if not ret:
                    continue
                
                webcam_frame = cv2.flip(webcam_frame, 1)
                android_frame = self.screen.get_frame()
                
                # Procesar gestos
                hand_info = self.hand_controller.process_frame(webcam_frame.copy())
                face_info = self.face_controller.process_frame(webcam_frame.copy())
                eye_pos = self.eye_tracker.get_cursor_position(1080, 1920)
                
                # Agregar comandos
                if hand_info['gesture'] != HandGesture.NONE:
                    self.fusion.add_command('hand', hand_info['gesture'].name.lower(), 
                                          hand_info['confidence'], hand_info)
                
                if face_info['expression'] != FacialExpression.NEUTRAL:
                    self.fusion.add_command('face', face_info['expression'].name.lower(),
                                          face_info['confidence'], face_info)
                
                if eye_pos:
                    self.fusion.add_command('eye', 'gaze', 0.9, 
                                          {'x': eye_pos[0], 'y': eye_pos[1]})
                
                # Ejecutar
                action = self.fusion.process_commands()
                if action:
                    self.fusion.execute_action(action)
                
                # Visualizar
                display = self._create_total_visualization(
                    webcam_frame, android_frame,
                    hand_info, face_info, eye_pos
                )
                
                cv2.imshow('Control por Gestos', display)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()
    
    # === HANDLERS DE INPUTS ===
    
    def _handle_voice_input(self, text: str):
        """Handler para input de voz"""
        print(f"\n[🎤] Usuario dice: '{text}'")
        
        # Verificar si es activación
        wake_words = ['hola', 'hey', 'oye']
        if any(wake in text.lower() for wake in wake_words):
            if self.core.personality['name'].lower() in text.lower():
                self.voice.speak("Dime")
                return
        
        # Procesar como comando
        android_frame = self.screen.get_frame()
        result = self.conversation.process_user_input(text, android_frame)
        
        # Si fue exitoso, agregar a memoria
        if result.get('success'):
            self.core.context.recent_actions.append(f"voice_{text[:20]}")
    
    def _handle_audio_gesture(self, gesture: AudioGesture):
        """Handler para gestos de audio"""
        print(f"[🔊] Audio: {gesture.name}")
        
        self.fusion.add_command(
            'audio',
            gesture.name.lower(),
            0.85,
            {'gesture': gesture}
        )
    
    # === HANDLERS DE ACCIONES MULTIMODALES ===
    
    def _handle_multimodal_click(self, action: dict):
        """Handler para clicks multimodales"""
        x = action.get('x', 540)
        y = action.get('y', 960)
        method = action.get('method', 'unknown')
        source = action.get('source', 'unknown')
        
        print(f"[🖱️] Click ({x}, {y}) - Fuente: {source} - Método: {method}")
        
        # Feedback según método
        feedback_map = {
            'gaze_snap': "Click donde miras",
            'pinch_wink': "Seleccionado",
            'hand_pinch': "Agarrado",
        }
        
        feedback = feedback_map.get(method, "Click")
        self.voice.speak(feedback)
        
        # Ejecutar
        self.control.click(x, y, 1080, 1920)
        time.sleep(0.3)
    
    def _handle_multimodal_swipe(self, action: dict):
        """Handler para swipes"""
        direction = action.get('direction', 'right')
        
        print(f"[👆] Swipe {direction}")
        
        W, H = 1080, 1920
        swipes = {
            'left': (800, 960, 280, 960),
            'right': (280, 960, 800, 960),
            'up': (540, 1600, 540, 400),
            'down': (540, 400, 540, 1600)
        }
        
        if direction in swipes:
            x1, y1, x2, y2 = swipes[direction]
            self.control.swipe(x1, y1, x2, y2, duration=0.3)
    
    def _handle_multimodal_scroll(self, action: dict):
        """Handler para scroll"""
        direction = action.get('direction', 'down')
        self.control._scroll(direction)
    
    def _handle_multimodal_zoom(self, action: dict):
        """Handler para zoom"""
        direction = action.get('direction', 'in')
        
        center_x, center_y = 540, 960
        
        if direction == 'in':
            self.control.swipe(center_x-100, center_y, center_x-200, center_y, 0.3)
            time.sleep(0.05)
            self.control.swipe(center_x+100, center_y, center_x+200, center_y, 0.3)
        else:
            self.control.swipe(center_x-200, center_y, center_x-100, center_y, 0.3)
            time.sleep(0.05)
            self.control.swipe(center_x+200, center_y, center_x+100, center_y, 0.3)
    
    def _handle_multimodal_system(self, action: dict):
        """Handler para acciones del sistema"""
        sys_action = action.get('action')
        
        print(f"[⚙️] Sistema: {sys_action}")
        
        # Mapear a capacidades
        action_map = {
            'back': lambda: self.control._press_back(),
            'home': lambda: self.control._press_home(),
            'like': lambda: self.capabilities.like_current_post(),
            'screenshot': lambda: self.capabilities.take_screenshot(),
            'share': lambda: self.capabilities.share_current_screen(),
        }
        
        handler = action_map.get(sys_action)
        if handler:
            handler()
    
    def _handle_voice_command(self, action: dict):
        """Handler para comandos de voz complejos"""
        command = action.get('command', '')
        
        # Usar conversación manager
        android_frame = self.screen.get_frame()
        self.conversation.process_user_input(command, android_frame)
    
    # === UTILIDADES ===
    
    def _update_context(self, frame):
        """Actualiza contexto basado en pantalla"""
        # Usar cache para no analizar constantemente
        cached = self.cache.get_screen_analysis(frame, 'context')
        
        if cached:
            self.core.context.current_app = cached.get('app')
            self.core.context.current_activity = cached.get('activity')
        else:
            # Análisis rápido con Gemini
            try:
                analysis = self.vision.detect_all_interactive_elements(frame)
                context = analysis.get('screen_context', '')
                
                # Inferir app
                app = self._infer_app_from_context(context)
                self.core.context.current_app = app
                
                # Inferir actividad
                activity = self._infer_activity_from_context(context)
                self.core.context.current_activity = activity
                
                # Guardar en cache
                self.cache.store_screen_analysis(frame, {
                    'app': app,
                    'activity': activity
                }, 'context')
                
            except Exception as e:
                print(f"[!] Error actualizando contexto: {e}")
    
    def _infer_app_from_context(self, context: str) -> str:
        """Infiere app desde contexto"""
        context_lower = context.lower()
        
        app_keywords = {
            'whatsapp': 'whatsapp',
            'youtube': 'youtube',
            'instagram': 'instagram',
            'facebook': 'facebook',
            'twitter': 'twitter',
            'chrome': 'chrome',
            'gmail': 'gmail',
            'maps': 'maps',
            'spotify': 'spotify',
        }
        
        for keyword, app_name in app_keywords.items():
            if keyword in context_lower:
                return app_name
        
        return 'unknown'
    
    def _infer_activity_from_context(self, context: str) -> str:
        """Infiere actividad desde contexto"""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['mensaje', 'chat', 'conversación']):
            return 'messaging'
        elif any(word in context_lower for word in ['video', 'reproduciendo', 'playing']):
            return 'watching'
        elif any(word in context_lower for word in ['buscar', 'search', 'navegando']):
            return 'browsing'
        elif any(word in context_lower for word in ['juego', 'game', 'score']):
            return 'gaming'
        elif any(word in context_lower for word in ['configuración', 'settings']):
            return 'settings'
        else:
            return 'browsing'
    
    def _create_total_visualization(self, webcam, android, hand_info, face_info, eye_pos):
        """Crea visualización completa del dashboard"""
        
        # Redimensionar frames
        webcam_display = cv2.resize(webcam, (320, 240))
        
        if android is not None:
            android_display = cv2.resize(android, (270, 480))
        else:
            android_display = np.zeros((480, 270, 3), dtype=np.uint8)
        
        # Canvas principal
        canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # === LAYOUT ===
        
        # Webcam (arriba izquierda)
        canvas[10:250, 10:330] = webcam_display
        
        # Android (centro)
        canvas[120:600, 505:775] = android_display
        
        # === PANEL DE INFO (derecha) ===
        
        info_x = 800
        y = 30
        
        # Título
        cv2.putText(canvas, self.core.personality['name'].upper(), (info_x, y),
                   cv2.FONT_HERSHEY_BOLD, 1.0, (0, 255, 255), 2)
        y += 50
        
        # Estado del asistente
        state = self.conversation.state.value if hasattr(self, 'conversation') else 'idle'
        cv2.putText(canvas, f"Estado: {state}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y += 30
        
        # Contexto actual
        app = self.core.context.current_app or 'N/A'
        activity = self.core.context.current_activity or 'idle'
        cv2.putText(canvas, f"App: {app}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y += 25
        cv2.putText(canvas, f"Actividad: {activity}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y += 40
        
        # === INPUTS ===
        
        cv2.putText(canvas, "INPUTS:", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
        y += 30
        
        # Manos
        hand_gesture = hand_info['gesture'].name if hand_info else 'NONE'
        hand_color = (0, 255, 0) if hand_gesture != 'NONE' else (100, 100, 100)
        cv2.putText(canvas, f"Hand: {hand_gesture}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, hand_color, 1)
        y += 25
        
        # Cara
        face_expr = face_info['expression'].name if face_info else 'NEUTRAL'
        face_color = (255, 255, 0) if face_expr != 'NEUTRAL' else (100, 100, 100)
        cv2.putText(canvas, f"Face: {face_expr}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 1)
        y += 25
        
        # Mirada
        if eye_pos:
            cv2.putText(canvas, f"Gaze: ({eye_pos[0]}, {eye_pos[1]})", (info_x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
        else:
            cv2.putText(canvas, "Gaze: No detectado", (info_x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        y += 25
        
        # Audio
        audio_gesture = self.audio_controller.detected_gesture.name
        audio_color = (0, 200, 255) if audio_gesture != 'NONE' else (100, 100, 100)
        cv2.putText(canvas, f"Audio: {audio_gesture}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, audio_color, 1)
        y += 40
        
        # === STATS ===
        
        cv2.putText(canvas, "STATS:", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)
        y += 30
        
        stats = self.cache.get_statistics()
        cv2.putText(canvas, f"Cache: {stats['hit_rate']:.0f}%", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y += 20
        
        cv2.putText(canvas, f"API Saved: {stats['api_calls_saved']}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y += 20
        
        memory_count = len(self.core.short_term_memory)
        cv2.putText(canvas, f"Memoria: {memory_count}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y += 20
        
        pref_count = len(self.core.preferences)
        cv2.putText(canvas, f"Preferencias: {pref_count}", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y += 30
        
        # === COMANDOS RECIENTES ===
        
        cv2.putText(canvas, "COMANDOS:", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 100), 2)
        y += 25
        
        for cmd in list(self.fusion.command_queue)[-8:]:
            text = f"{cmd.source}: {cmd.action[:18]}"
            age = time.time() - cmd.timestamp
            alpha = max(50, 255 - int(age * 50))
            color = (alpha, alpha, alpha)
            
            cv2.putText(canvas, text, (info_x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
            y += 18
        
        # === ACCIONES RECIENTES ===
        
        y = 550
        cv2.putText(canvas, "ACCIONES:", (info_x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 200), 2)
        y += 25
        
        recent = list(self.core.context.recent_actions)[-6:]
        for action in recent:
            cv2.putText(canvas, action[:25], (info_x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
            y += 18
        
        # === INSTRUCCIONES (abajo) ===
        
        instructions = [
            "Q: Salir  |  P: Toggle Proactivo",
            "Di 'Hola " + self.core.personality['name'] + "' para activar voz",
        ]
        
        y_inst = 680
        for inst in instructions:
            cv2.putText(canvas, inst, (10, y_inst),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            y_inst += 25
        
        return canvas
    
    def _full_calibration(self):
        """Calibración completa"""
        print("\n[📐] CALIBRACIÓN COMPLETA")
        
        self.voice.speak("Iniciando calibración. Sigue las instrucciones")
        
        # 1. Eye tracking
        print("\n1/3: Calibración de mirada")
        self.voice.speak("Calibración de mirada. Mira los puntos que aparezcan")
        self.eye_tracker.start()
        self.eye_tracker.calibrate(points=9)
        
        # 2. Gestos de mano
        print("\n2/3: Prueba de gestos")
        self.voice.speak("Ahora prueba estos gestos: mano abierta, puño, pellizco, pulgar arriba")
        input("Presiona Enter cuando hayas practicado...")
        
        # 3. Audio
        print("\n3/3: Calibración de audio")
        self.voice.speak("Calibración de audio. Haz un chasquido cuando te lo indique")
        self.audio_controller.calibrate()
        
        self.voice.speak("Calibración completa. Sistema listo")
        print("\n[✓] Calibración completada")
    
    def _ask_yes_no(self, question: str) -> bool:
        """Pregunta sí/no"""
        response = input(f"{question} (s/n): ").lower()
        return response in ['s', 'si', 'sí', 'y', 'yes']
    
    def _cleanup(self):
        """Limpieza al cerrar"""
        print("\n\n[🧹] Cerrando asistente...")
        
        self.running = False
        
        # Detener componentes
        if hasattr(self, 'eye_tracker'):
            self.eye_tracker.stop()
        
        if hasattr(self, 'audio_controller'):
            self.audio_controller.stop()
        
        if hasattr(self, 'webcam'):
            self.webcam.release()
        
        cv2.destroyAllWindows()
        
        # Guardar memoria
        if hasattr(self, 'core'):
            self.core._save_memory()
        
        # Despedida
        if hasattr(self, 'voice'):
            self.voice.speak("Hasta luego. Fue un placer ayudarte")
        
        # Mostrar estadísticas finales
        print("\n" + "="*70)
        print("📊 ESTADÍSTICAS FINALES")
        print("="*70)
        
        if hasattr(self, 'cache'):
            stats = self.cache.get_statistics()
            print(f"  Cache hit rate: {stats['hit_rate']:.1f}%")
            print(f"  API calls ahorradas: {stats['api_calls_saved']}")
        
        if hasattr(self, 'core'):
            print(f"  Recuerdos guardados: {len(self.core.long_term_memory)}")
            print(f"  Preferencias aprendidas: {len(self.core.preferences)}")
            print(f"  Rutinas detectadas: {len(self.core.routines)}")
        
        print("\n[✓] Sistema cerrado correctamente")
        print("Gracias por usar el Asistente Total\n")


def main():
    """Entry point"""
    
    # ASCII Art
    print("""
    
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║       █████╗ ███████╗██╗███████╗████████╗███████╗        ║
    ║      ██╔══██╗██╔════╝██║██╔════╝╚══██╔══╝██╔════╝        ║
    ║      ███████║███████╗██║███████╗   ██║   █████╗          ║
    ║      ██╔══██║╚════██║██║╚════██║   ██║   ██╔══╝          ║
    ║      ██║  ██║███████║██║███████║   ██║   ███████╗        ║
    ║      ╚═╝  ╚═╝╚══════╝╚═╝╚══════╝   ╚═╝   ╚══════╝        ║
    ║                                                           ║
    ║              ANDROID TOTAL v5.0                          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    
    """)
    
    # Cargar configuración
    try:
        with open('config.json') as f:
            config = json.load(f)
    except Exception as e:
        print(f"[!] Error cargando config.json: {e}")
        print("Creando configuración por defecto...")
        
        config = {
            'api_services': {
                'openrouter': {
                    'api_key': input("Ingresa tu API key de OpenRouter: "),
                    'base_url': 'https://openrouter.ai/api/v1',
                    'model': 'google/gemini-2.0-flash-exp:free'
                }
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
    
    # Crear e iniciar asistente
    try:
        assistant = TotalAssistant(config)
        assistant.start()
    except Exception as e:
        print(f"\n[!] Error fatal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()