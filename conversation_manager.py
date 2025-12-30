import time
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class ConversationState(Enum):
    """Estados de la conversación"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    CLARIFYING = "clarifying"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    MULTI_TURN = "multi_turn"

@dataclass
class ConversationTurn:
    """Un turno de conversación"""
    speaker: str  # 'user' o 'assistant'
    message: str
    timestamp: float
    intent: Optional[str] = None
    metadata: Optional[dict] = None

class ConversationManager:
    """
    Gestiona conversaciones naturales multi-turno
    Mantiene contexto y maneja diálogos complejos
    """
    
    def __init__(self, assistant_core, voice_manager):
        self.core = assistant_core
        self.voice = voice_manager
        
        # Estado de conversación
        self.state = ConversationState.IDLE
        self.conversation_history = []
        self.current_topic = None
        self.pending_clarification = None
        self.multi_turn_context = {}
        
        # Callbacks
        self.on_state_change: Optional[Callable] = None
        
        print("[💬] Conversation Manager inicializado")
    
    def start_conversation(self):
        """Inicia una conversación"""
        self._change_state(ConversationState.LISTENING)
        
        greeting = self._generate_greeting()
        self.say(greeting)
        
        self._add_turn('assistant', greeting)
    
    def process_user_input(self, user_input: str, frame=None) -> dict:
        """
        Procesa input del usuario con contexto conversacional
        """
        print(f"\n[👤] Usuario: {user_input}")
        self._add_turn('user', user_input)
        
        self._change_state(ConversationState.PROCESSING)
        
        # Manejar según estado
        if self.state == ConversationState.CLARIFYING:
            return self._handle_clarification(user_input)
        
        elif self.state == ConversationState.WAITING_CONFIRMATION:
            return self._handle_confirmation(user_input)
        
        elif self.state == ConversationState.MULTI_TURN:
            return self._handle_multi_turn(user_input, frame)
        
        else:
            return self._handle_new_command(user_input, frame)
    
    def say(self, message: str, emotion: str = 'neutral'):
        """Asistente habla con emoción"""
        print(f"[🤖] {self.core.personality['name']}: {message}")
        
        # Ajustar tono según emoción
        if emotion == 'excited':
            message = f"¡{message}!"
        elif emotion == 'apologetic':
            message = f"Lo siento, {message}"
        elif emotion == 'curious':
            message = f"{message}?"
        
        self.voice.speak(message)
        self._add_turn('assistant', message)
    
    def ask(self, question: str, options: List[str] = None) -> str:
        """Hace una pregunta y espera respuesta"""
        if options:
            options_str = ', '.join(options[:-1]) + f" o {options[-1]}"
            full_question = f"{question} Puedes decir {options_str}"
        else:
            full_question = question
        
        self.say(full_question, emotion='curious')
        
        # Esperar respuesta
        self._change_state(ConversationState.LISTENING)
        response = self.voice.listen_once()
        
        if response:
            self._add_turn('user', response)
            return response
        
        return ""
    
    def clarify(self, ambiguous_intent: dict) -> dict:
        """Pide aclaración cuando hay ambigüedad"""
        self._change_state(ConversationState.CLARIFYING)
        self.pending_clarification = ambiguous_intent
        
        # Generar pregunta de aclaración
        clarification = self._generate_clarification_question(ambiguous_intent)
        self.say(clarification)
        
        # Esperar respuesta del usuario
        response = self.voice.listen_once()
        if response:
            return self.process_user_input(response)
        
        return {'success': False, 'reason': 'no_response'}
    
    def confirm(self, action_description: str) -> bool:
        """Pide confirmación de una acción"""
        self._change_state(ConversationState.WAITING_CONFIRMATION)
        
        confirmation_msg = f"Voy a {action_description}. ¿Está bien?"
        self.say(confirmation_msg)
        
        response = self.voice.listen_once()
        if response:
            self._add_turn('user', response)
            confirmed = self._parse_confirmation(response)
            
            if confirmed:
                self.say("Perfecto", emotion='neutral')
            else:
                self.say("Entendido, no lo haré", emotion='neutral')
            
            self._change_state(ConversationState.IDLE)
            return confirmed
        
        return False
    
    def _handle_new_command(self, user_input: str, frame) -> dict:
        """Maneja un comando nuevo"""
        
        # Entender con contexto conversacional
        intent = self.core.understand_intent(user_input, frame)
        
        # Verificar si necesita aclaración
        if intent['confidence'] < 0.6 or intent['intent'] == 'ambiguous':
            return self.clarify(intent)
        
        # Verificar si es comando multi-turno
        if self._is_multi_turn_command(intent):
            return self._start_multi_turn(intent, frame)
        
        # Responder al usuario
        response = intent.get('suggested_response')
        if response:
            self.say(response)
        
        # Ejecutar
        self._change_state(ConversationState.EXECUTING)
        result = self.core.execute_intent(intent, self._get_control_system())
        
        # Feedback
        if result['success']:
            self.say("Listo", emotion='neutral')
        else:
            self.say(f"Hubo un problema: {result.get('reason')}", emotion='apologetic')
        
        self._change_state(ConversationState.IDLE)
        return result
    
    def _handle_clarification(self, user_input: str) -> dict:
        """Maneja respuesta a solicitud de aclaración"""
        
        if not self.pending_clarification:
            return {'success': False}
        
        # Usar la respuesta para refinar el intent
        refined_intent = self._refine_intent_with_clarification(
            self.pending_clarification,
            user_input
        )
        
        self.pending_clarification = None
        self._change_state(ConversationState.IDLE)
        
        # Procesar intent refinado
        return self._handle_new_command(
            refined_intent.get('refined_input', user_input),
            None
        )
    
    def _handle_confirmation(self, user_input: str) -> dict:
        """Maneja respuesta a confirmación"""
        confirmed = self._parse_confirmation(user_input)
        
        if confirmed:
            self.say("De acuerdo")
            # Continuar con la acción pendiente
        else:
            self.say("Entendido, cancelado")
        
        self._change_state(ConversationState.IDLE)
        return {'confirmed': confirmed}
    
    def _handle_multi_turn(self, user_input: str, frame) -> dict:
        """Maneja conversación multi-turno"""
        
        context = self.multi_turn_context
        step = context.get('current_step', 0)
        steps = context.get('steps', [])
        
        if step >= len(steps):
            # Conversación completada
            self.say("Perfecto, tengo todo lo que necesito")
            self._change_state(ConversationState.EXECUTING)
            
            # Ejecutar con toda la información recopilada
            result = self._execute_multi_turn_command(context)
            
            self.multi_turn_context = {}
            self._change_state(ConversationState.IDLE)
            return result
        
        # Procesar respuesta del paso actual
        current_step = steps[step]
        context['data'][current_step['key']] = user_input
        
        # Avanzar al siguiente paso
        context['current_step'] = step + 1
        
        if context['current_step'] < len(steps):
            next_step = steps[context['current_step']]
            self.ask(next_step['question'])
        
        return {'success': True, 'in_progress': True}
    
    def _start_multi_turn(self, intent: dict, frame) -> dict:
        """Inicia conversación multi-turno"""
        self._change_state(ConversationState.MULTI_TURN)
        
        # Determinar qué información necesitamos
        steps = self._plan_multi_turn_steps(intent)
        
        self.multi_turn_context = {
            'intent': intent,
            'steps': steps,
            'current_step': 0,
            'data': {},
            'frame': frame
        }
        
        # Hacer primera pregunta
        first_step = steps[0]
        self.ask(first_step['question'])
        
        return {'success': True, 'in_progress': True}
    
    def _is_multi_turn_command(self, intent: dict) -> bool:
        """Verifica si el comando requiere múltiples turnos"""
        
        # Comandos que típicamente necesitan más info
        multi_turn_intents = [
            'send_message',  # Necesita: contacto, mensaje
            'create_event',  # Necesita: título, fecha, hora
            'set_reminder',  # Necesita: qué, cuándo
            'search_and_action',  # Necesita: qué buscar, qué hacer
        ]
        
        action = intent.get('action')
        params = intent.get('parameters', {})
        
        # Si falta información crítica
        if action in multi_turn_intents:
            required = self._get_required_params(action)
            missing = [p for p in required if p not in params]
            
            if missing:
                return True
        
        return False
    
    def _plan_multi_turn_steps(self, intent: dict) -> List[dict]:
        """Planifica los pasos de una conversación multi-turno"""
        action = intent.get('action')
        params = intent.get('parameters', {})
        
        steps = []
        
        if action == 'send_message':
            if 'contact' not in params:
                steps.append({
                    'key': 'contact',
                    'question': '¿A quién le quieres enviar el mensaje?'
                })
            if 'message' not in params:
                steps.append({
                    'key': 'message',
                    'question': '¿Qué mensaje quieres enviar?'
                })
            if 'app' not in params:
                steps.append({
                    'key': 'app',
                    'question': '¿Por WhatsApp o SMS?'
                })
        
        elif action == 'create_event':
            if 'title' not in params:
                steps.append({
                    'key': 'title',
                    'question': '¿Cuál es el título del evento?'
                })
            if 'date' not in params:
                steps.append({
                    'key': 'date',
                    'question': '¿Para qué día?'
                })
            if 'time' not in params:
                steps.append({
                    'key': 'time',
                    'question': '¿A qué hora?'
                })
        
        elif action == 'set_reminder':
            if 'task' not in params:
                steps.append({
                    'key': 'task',
                    'question': '¿Qué te tengo que recordar?'
                })
            if 'when' not in params:
                steps.append({
                    'key': 'when',
                    'question': '¿Cuándo te lo recuerdo?'
                })
        
        return steps
    
    def _execute_multi_turn_command(self, context: dict) -> dict:
        """Ejecuta comando después de recopilar toda la info"""
        
        intent = context['intent']
        data = context['data']
        
        # Actualizar parámetros con los datos recopilados
        intent['parameters'].update(data)
        
        # Ejecutar
        return self.core.execute_intent(intent, self._get_control_system())
    
    def _generate_greeting(self) -> str:
        """Genera saludo personalizado"""
        hour = time.localtime().tm_hour
        name = self.core.personality['name']
        
        if 5 <= hour < 12:
            greeting = f"Buenos días. Soy {name}"
        elif 12 <= hour < 18:
            greeting = f"Buenas tardes. Soy {name}"
        else:
            greeting = f"Buenas noches. Soy {name}"
        
        # Agregar contexto si hay
        if self.core.routines:
            greeting += ". ¿En qué te ayudo hoy?"
        else:
            greeting += ", tu asistente personal. ¿Qué necesitas?"
        
        return greeting
    
    def _generate_clarification_question(self, intent: dict) -> str:
        """Genera pregunta de aclaración inteligente"""
        
        possible_meanings = intent.get('possible_meanings', [])
        
        if possible_meanings:
            options = ', '.join(possible_meanings[:-1]) + f" o {possible_meanings[-1]}"
            return f"No estoy seguro si quieres {options}. ¿Cuál es?"
        
        return "No entendí bien. ¿Puedes explicar de otra forma?"
    
    def _refine_intent_with_clarification(self, original_intent: dict, clarification: str) -> dict:
        """Refina intent con la aclaración del usuario"""
        
        # Combinar input original con aclaración
        original_input = original_intent.get('original_input', '')
        refined_input = f"{original_input}. Específicamente: {clarification}"
        
        return {
            'refined_input': refined_input,
            'context': original_intent
        }
    
    def _parse_confirmation(self, response: str) -> bool:
        """Parsea respuesta de confirmación"""
        response_lower = response.lower()
        
        affirmative = ['sí', 'si', 'yes', 'ok', 'dale', 'confirmo', 'adelante', 'hazlo', 'claro']
        negative = ['no', 'nope', 'cancela', 'mejor no', 'espera', 'detente']
        
        if any(word in response_lower for word in affirmative):
            return True
        if any(word in response_lower for word in negative):
            return False
        
        # Si es ambiguo, pedir aclaración
        self.say("No estoy seguro. ¿Es un sí o un no?")
        retry = self.voice.listen_once()
        if retry:
            return self._parse_confirmation(retry)
        
        return False
    
    def _get_required_params(self, action: str) -> List[str]:
        """Obtiene parámetros requeridos para una acción"""
        requirements = {
            'send_message': ['contact', 'message', 'app'],
            'create_event': ['title', 'date', 'time'],
            'set_reminder': ['task', 'when'],
            'make_call': ['contact'],
            'navigate_to': ['destination'],
        }
        
        return requirements.get(action, [])
    
    def _add_turn(self, speaker: str, message: str, intent: str = None):
        """Agrega turno a historial"""
        turn = ConversationTurn(
            speaker=speaker,
            message=message,
            timestamp=time.time(),
            intent=intent
        )
        
        self.conversation_history.append(turn)
        
        # Mantener solo últimos 50 turnos en memoria
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def _change_state(self, new_state: ConversationState):
        """Cambia estado de conversación"""
        old_state = self.state
        self.state = new_state
        
        print(f"[🔄] Estado: {old_state.value} → {new_state.value}")
        
        if self.on_state_change:
            self.on_state_change(old_state, new_state)
    
    def _get_control_system(self):
        """Obtiene referencia al sistema de control"""
        # Esto se inyectará desde el main
        return getattr(self, '_control_system', None)
    
    def inject_control_system(self, control_system):
        """Inyecta sistema de control"""
        self._control_system = control_system