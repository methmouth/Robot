import json
import time
from datetime import datetime
from collections import deque
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import pickle
import os

@dataclass
class Memory:
    """Memoria del asistente"""
    timestamp: float
    type: str  # 'command', 'context', 'preference', 'routine'
    content: Dict[str, Any]
    importance: int  # 1-10

@dataclass
class UserPreference:
    """Preferencia del usuario"""
    key: str
    value: Any
    learned_from: str  # 'explicit' o 'implicit'
    confidence: float
    last_updated: float

@dataclass
class ContextState:
    """Estado contextual actual"""
    current_app: Optional[str]
    current_activity: str  # 'browsing', 'messaging', 'gaming', etc.
    time_of_day: str  # 'morning', 'afternoon', 'evening', 'night'
    location_type: Optional[str]  # 'home', 'work', 'commute', etc.
    user_mood: Optional[str]  # inferido de gestos/voz
    recent_actions: List[str]

class AssistantCore:
    """
    Núcleo cognitivo del asistente
    Maneja: Memoria, Contexto, Aprendizaje, Toma de decisiones
    """
    
    def __init__(self, vision_api, voice_manager):
        self.vision = vision_api
        self.voice = voice_manager
        
        # Memoria
        self.short_term_memory = deque(maxlen=100)  # Últimas 100 interacciones
        self.long_term_memory = []  # Persistente
        self.working_memory = {}  # Contexto actual de la tarea
        
        # Preferencias del usuario
        self.preferences = {}
        
        # Estado contextual
        self.context = ContextState(
            current_app=None,
            current_activity='idle',
            time_of_day=self._get_time_of_day(),
            location_type=None,
            user_mood=None,
            recent_actions=deque(maxlen=20)
        )
        
        # Rutinas aprendidas
        self.routines = {}  # {'morning_routine': [...], 'before_sleep': [...]}
        
        # Personalidad del asistente
        self.personality = {
            'name': 'Atlas',  # Nombre personalizable
            'tone': 'friendly',  # friendly, professional, casual, humorous
            'verbosity': 'medium',  # brief, medium, detailed
            'proactive': True,  # Sugerir acciones sin pedir
        }
        
        # Carga de memoria persistente
        self._load_memory()
        
        print(f"[🧠] {self.personality['name']} inicializado")
    
    def understand_intent(self, user_input: str, frame=None) -> Dict:
        """
        Entiende la intención del usuario con contexto completo
        """
        # Construir contexto enriquecido
        context_info = self._build_rich_context(frame)
        
        # Prompt avanzado para Gemini
        prompt = f"""Eres {self.personality['name']}, un asistente personal altamente inteligente.

CONTEXTO ACTUAL:
- App actual: {context_info['current_app']}
- Actividad: {context_info['activity']}
- Hora: {context_info['time']}
- Usuario suele: {context_info['user_patterns']}
- Última acción: {context_info['last_action']}

PREFERENCIAS DEL USUARIO:
{json.dumps(self._get_relevant_preferences(), indent=2)}

COMANDO DEL USUARIO: "{user_input}"

Analiza el comando y responde en JSON:
{{
  "intent": "categoría de intención",
  "action": "acción específica a realizar",
  "parameters": {{"key": "value"}},
  "requires_confirmation": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "por qué interpretaste así",
  "suggested_response": "qué decirle al usuario",
  "follow_up_suggestions": ["sugerencia 1", "sugerencia 2"],
  "screen_analysis_needed": true/false,
  "execution_steps": [
    {{"action": "...", "params": {{...}}}},
  ],
  "context_updates": {{"key": "value"}},
  "learn_from_this": true/false
}}

INTENTS POSIBLES:
- app_control: abrir/cerrar apps
- communication: mensajes, llamadas, emails
- information: búsquedas, consultas
- entertainment: música, videos, juegos
- productivity: notas, calendario, recordatorios
- settings: cambiar configuraciones
- navigation: ir a lugares
- personal: cosas personales del usuario
- meta: comandos sobre el asistente mismo
- ambiguous: necesita más info

Sé conversacional, natural y proactivo. Si detectas que el usuario está haciendo algo repetitivo, sugiérelo como rutina.
"""

        try:
            response = self.vision.vision.api_call_with_context(
                prompt, 
                frame if context_info['screen_analysis_needed'] else None
            )
            
            intent_data = json.loads(response)
            
            # Guardar en memoria
            self._store_interaction(user_input, intent_data)
            
            # Aprender si es necesario
            if intent_data.get('learn_from_this'):
                self._learn_from_interaction(user_input, intent_data)
            
            return intent_data
            
        except Exception as e:
            print(f"[!] Error entendiendo intent: {e}")
            return self._fallback_intent(user_input)
    
    def execute_intent(self, intent_data: Dict, control_system) -> Dict:
        """
        Ejecuta la intención entendida
        """
        action = intent_data.get('action')
        params = intent_data.get('parameters', {})
        steps = intent_data.get('execution_steps', [])
        
        print(f"\n[🎯] Ejecutando: {action}")
        print(f"[💭] Razonamiento: {intent_data.get('reasoning')}")
        
        # Responder al usuario
        response = intent_data.get('suggested_response')
        if response:
            self.voice.speak(response)
        
        # Confirmar si es necesario
        if intent_data.get('requires_confirmation'):
            confirmation = self._ask_confirmation(intent_data)
            if not confirmation:
                self.voice.speak("Entendido, cancelado")
                return {'success': False, 'reason': 'user_cancelled'}
        
        # Ejecutar pasos
        results = []
        for step in steps:
            result = self._execute_step(step, control_system)
            results.append(result)
            
            if not result.get('success'):
                self.voice.speak(f"Hubo un problema: {result.get('error')}")
                return {'success': False, 'results': results}
            
            # Pausa entre acciones para naturalidad
            time.sleep(0.5)
        
        # Actualizar contexto
        if 'context_updates' in intent_data:
            self._update_context(intent_data['context_updates'])
        
        # Sugerencias de seguimiento
        if intent_data.get('follow_up_suggestions'):
            self._suggest_follow_ups(intent_data['follow_up_suggestions'])
        
        return {'success': True, 'results': results}
    
    def learn_preference(self, key: str, value: Any, source: str = 'implicit'):
        """Aprende una preferencia del usuario"""
        confidence = 1.0 if source == 'explicit' else 0.7
        
        if key in self.preferences:
            # Actualizar confianza
            old_pref = self.preferences[key]
            if old_pref.value == value:
                confidence = min(1.0, old_pref.confidence + 0.1)
        
        self.preferences[key] = UserPreference(
            key=key,
            value=value,
            learned_from=source,
            confidence=confidence,
            last_updated=time.time()
        )
        
        print(f"[📚] Aprendido: {key} = {value} (confianza: {confidence:.0%})")
        self._save_memory()
    
    def detect_routine(self, actions: List[str], time_window: str) -> Optional[str]:
        """
        Detecta si una secuencia de acciones es una rutina
        """
        # Buscar patrones repetidos
        action_signature = '->'.join(actions)
        
        # Si ya existe una rutina similar
        for routine_name, routine_data in self.routines.items():
            if routine_data['time_window'] == time_window:
                similarity = self._calculate_similarity(
                    actions, 
                    routine_data['actions']
                )
                
                if similarity > 0.8:
                    # Incrementar confianza
                    routine_data['occurrences'] += 1
                    routine_data['confidence'] = min(
                        1.0, 
                        routine_data['confidence'] + 0.1
                    )
                    
                    # Sugerir automatización
                    if routine_data['occurrences'] >= 3 and not routine_data.get('automated'):
                        self._suggest_automation(routine_name, routine_data)
                    
                    return routine_name
        
        # Nueva rutina potencial
        if len(actions) >= 3:  # Mínimo 3 acciones
            routine_name = f"routine_{time_window}_{len(self.routines)}"
            self.routines[routine_name] = {
                'actions': actions,
                'time_window': time_window,
                'occurrences': 1,
                'confidence': 0.3,
                'automated': False
            }
            print(f"[🔄] Rutina potencial detectada: {routine_name}")
        
        return None
    
    def proactive_suggestion(self, frame=None) -> Optional[str]:
        """
        Genera sugerencias proactivas basadas en contexto
        """
        if not self.personality['proactive']:
            return None
        
        # Analizar contexto actual
        current_time = datetime.now().hour
        
        # Rutinas de tiempo
        if 7 <= current_time < 9:  # Mañana
            if 'morning_routine' in self.routines:
                if self.routines['morning_routine'].get('automated'):
                    return None  # Ya se ejecutó
                return "¿Quieres que ejecute tu rutina de la mañana?"
        
        # Basado en historial
        if len(self.context.recent_actions) > 5:
            pattern = self._detect_pattern(list(self.context.recent_actions))
            if pattern:
                return f"Noto que sueles {pattern}. ¿Te ayudo?"
        
        # Basado en app actual y análisis de pantalla
        if frame is not None and self.context.current_app:
            suggestion = self._context_aware_suggestion(frame)
            if suggestion:
                return suggestion
        
        return None
    
    def _build_rich_context(self, frame) -> Dict:
        """Construye contexto enriquecido"""
        return {
            'current_app': self.context.current_app or 'desconocida',
            'activity': self.context.current_activity,
            'time': self._get_time_of_day(),
            'user_patterns': self._summarize_patterns(),
            'last_action': list(self.context.recent_actions)[-1] if self.context.recent_actions else 'ninguna',
            'screen_analysis_needed': frame is not None
        }
    
    def _get_relevant_preferences(self) -> Dict:
        """Obtiene preferencias relevantes al contexto"""
        relevant = {}
        for key, pref in self.preferences.items():
            if pref.confidence > 0.6:  # Solo preferencias confiables
                relevant[key] = pref.value
        return relevant
    
    def _execute_step(self, step: Dict, control_system) -> Dict:
        """Ejecuta un paso individual"""
        action_type = step.get('action')
        params = step.get('params', {})
        
        try:
            if action_type == 'open_app':
                control_system.control._open_app(params['package'])
                
            elif action_type == 'click':
                x, y = params.get('x'), params.get('y')
                if x and y:
                    control_system.control.click(x, y, 1080, 1920)
                else:
                    # Buscar elemento
                    frame = control_system.screen.get_frame()
                    element = control_system.vision.find_element(
                        frame, 
                        params.get('description')
                    )
                    if element.get('found'):
                        control_system.control.click(
                            element['x'], element['y'], 1080, 1920
                        )
            
            elif action_type == 'type':
                control_system.control._type_text(params['text'])
            
            elif action_type == 'wait':
                time.sleep(params.get('seconds', 1))
            
            elif action_type == 'scroll':
                control_system.control._scroll(params.get('direction', 'down'))
            
            elif action_type == 'search':
                self._perform_search(params['query'], control_system)
            
            elif action_type == 'navigate':
                self._navigate_to(params['destination'], control_system)
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _store_interaction(self, user_input: str, intent_data: Dict):
        """Guarda interacción en memoria"""
        memory = Memory(
            timestamp=time.time(),
            type='command',
            content={
                'user_input': user_input,
                'intent': intent_data
            },
            importance=self._calculate_importance(intent_data)
        )
        
        self.short_term_memory.append(memory)
        
        # Promover a memoria de largo plazo si es importante
        if memory.importance >= 7:
            self.long_term_memory.append(memory)
            self._save_memory()
    
    def _learn_from_interaction(self, user_input: str, intent_data: Dict):
        """Aprende de la interacción"""
        # Extraer preferencias implícitas
        params = intent_data.get('parameters', {})
        
        # Ejemplo: si siempre usa Chrome para buscar
        if intent_data.get('action') == 'search':
            if 'browser' in params:
                self.learn_preference('preferred_browser', params['browser'], 'implicit')
        
        # Patrones de tiempo
        hour = datetime.now().hour
        action = intent_data.get('action')
        
        time_pattern_key = f"action_time_{action}"
        if time_pattern_key not in self.preferences:
            self.preferences[time_pattern_key] = UserPreference(
                key=time_pattern_key,
                value=[hour],
                learned_from='implicit',
                confidence=0.3,
                last_updated=time.time()
            )
        else:
            # Agregar hora a patrón
            times = self.preferences[time_pattern_key].value
            times.append(hour)
            # Mantener solo últimas 10
            self.preferences[time_pattern_key].value = times[-10:]
    
    def _get_time_of_day(self) -> str:
        """Determina momento del día"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        elif 18 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def _summarize_patterns(self) -> str:
        """Resume patrones del usuario"""
        patterns = []
        
        # Apps más usadas
        if 'favorite_apps' in self.preferences:
            apps = self.preferences['favorite_apps'].value
            patterns.append(f"usar {', '.join(apps[:3])}")
        
        # Horarios
        time_of_day = self._get_time_of_day()
        patterns.append(f"estar activo en {time_of_day}")
        
        return '; '.join(patterns) if patterns else 'aún aprendiendo'
    
    def _calculate_importance(self, intent_data: Dict) -> int:
        """Calcula importancia de una interacción (1-10)"""
        importance = 5  # Base
        
        # Comandos explícitos son más importantes
        if intent_data.get('requires_confirmation'):
            importance += 2
        
        # Alta confianza = importante
        if intent_data.get('confidence', 0) > 0.9:
            importance += 1
        
        # Ciertos intents son críticos
        critical_intents = ['personal', 'settings', 'communication']
        if intent_data.get('intent') in critical_intents:
            importance += 2
        
        return min(10, importance)
    
    def _save_memory(self):
        """Guarda memoria persistente"""
        data = {
            'long_term_memory': [asdict(m) for m in self.long_term_memory],
            'preferences': {k: asdict(v) for k, v in self.preferences.items()},
            'routines': self.routines,
            'personality': self.personality
        }
        
        with open('assistant_memory.pkl', 'wb') as f:
            pickle.dump(data, f)
    
    def _load_memory(self):
        """Carga memoria persistente"""
        if os.path.exists('assistant_memory.pkl'):
            try:
                with open('assistant_memory.pkl', 'rb') as f:
                    data = pickle.load(f)
                
                self.long_term_memory = [Memory(**m) for m in data.get('long_term_memory', [])]
                self.preferences = {k: UserPreference(**v) for k, v in data.get('preferences', {}).items()}
                self.routines = data.get('routines', {})
                self.personality.update(data.get('personality', {}))
                
                print(f"[💾] Memoria cargada: {len(self.long_term_memory)} recuerdos")
            except:
                print("[!] No se pudo cargar memoria")
    
    def _fallback_intent(self, user_input: str) -> Dict:
        """Intent de respaldo cuando falla el análisis"""
        return {
            'intent': 'ambiguous',
            'action': 'clarify',
            'confidence': 0.3,
            'suggested_response': f"No estoy seguro de entender '{user_input}'. ¿Puedes ser más específico?",
            'execution_steps': []
        }
    
    def _ask_confirmation(self, intent_data: Dict) -> bool:
        """Pide confirmación al usuario"""
        action = intent_data.get('action')
        self.voice.speak(f"¿Confirmas que quieres {action}? Di sí o no")
        
        # Esperar respuesta
        response = self.voice.listen_once()
        if response:
            return any(word in response.lower() for word in ['sí', 'si', 'yes', 'confirmo', 'ok'])
        
        return False
    
    def _suggest_follow_ups(self, suggestions: List[str]):
        """Sugiere acciones de seguimiento"""
        if len(suggestions) > 0:
            suggestion = suggestions[0]
            # Sugerir después de un delay
            time.sleep(2)
            self.voice.speak(f"Por cierto, también podrías {suggestion}")
    
    def _context_aware_suggestion(self, frame) -> Optional[str]:
        """Sugerencia basada en lo que ve en pantalla"""
        # Analizar pantalla
        analysis = self.vision.detect_all_interactive_elements(frame)
        context = analysis.get('screen_context', '')
        
        # Sugerencias contextuales
        if 'mensaje' in context.lower() and 'sin leer' in context.lower():
            return "Tienes mensajes sin leer. ¿Los reviso?"
        
        if 'notificación' in context.lower():
            return "Hay notificaciones pendientes"
        
        return None
    
    def _detect_pattern(self, actions: List[str]) -> Optional[str]:
        """Detecta patrón en acciones recientes"""
        # Simple pattern matching
        if actions.count('scroll_down') >= 3:
            return "hacer mucho scroll. ¿Buscas algo específico?"
        
        return None
    
    def _calculate_similarity(self, actions1: List[str], actions2: List[str]) -> float:
        """Calcula similitud entre dos secuencias de acciones"""
        # Implementación simple de Jaccard similarity
        set1 = set(actions1)
        set2 = set(actions2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
   