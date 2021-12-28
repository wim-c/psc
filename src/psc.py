import enum


class Event:
    def __str__(self):
        return f'event {self.name()}'

    def name(self):
        return type(self).__name__


class Reply:
    def __str__(self):
        return f'reply {self.name()}'

    def name(self):
        return type(self).__name__


class StateDict:
    event_annotation_key = 'event'

    define_enter_key = 'enter'
    define_exit_key = 'exit'
    define_handle_key = 'handle'

    entry_handlers_key = '_entry_handlers'
    exit_handlers_key = '_exit_handlers'
    event_handlers_key = '_event_handlers'

    def __init__(self):
        super().__init__()
        self.entry_handlers = {}
        self.exit_handlers = {}
        self.event_handlers = {}

        self.dict = {
            self.entry_handlers_key: self.entry_handlers,
            self.exit_handlers_key: self.exit_handlers,
            self.event_handlers_key: self.event_handlers
        }

    def __setitem__(self, key, value):
        if key == self.define_enter_key:
            self.add_handler(self.entry_handlers, value)
        elif key == self.define_exit_key:
            self.add_handler(self.exit_handlers, value)
        elif key == self.define_handle_key:
            self.add_handler(self.event_handlers, value)
        else:
            self.dict[key] = value

    def __getitem__(self, key):
        return self.dict[key]

    def add_handler(self, handlers, handler):
        event_type = handler.__annotations__.get(self.event_annotation_key)
        if event_type in handlers:
            handlers[event_type].append(handler)
        else:
            handlers[event_type] = [handler]


class StateMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, *, is_state_type=True):
        return StateDict() if is_state_type else super().__prepare__(name, bases)

    def __new__(cls, name, bases, classdict, *, is_state_type=True):
        if not is_state_type:
            return super().__new__(cls, name, bases, classdict)
        new_cls = super().__new__(cls, name, bases, classdict.dict)
        new_cls._prepare_state_type()
        return new_cls


class HandleResult(enum.Enum):
    UNKNOWN = 0
    UNHANDLED = 1
    HANDLED = 2


class StateConstructor:
    def __init__(self, state_chart):
        self.state_chart = state_chart
        self.instances = {}

    def get_instance(self, state_type):
        if (instance := self.instances.get(state_type)) is None:
            instance = state_type(self)
            self.instances[state_type] = instance
        return instance


class AbstractState:
    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def _prepare_state_type(cls):
        pass

    def __init__(self, constructor):
        super().__init__()
        self._state_chart = constructor.state_chart

    def __str__(self):
        self._write_to(parts := [])
        return ''.join(parts)

    def _write_to(self, parts):
        parts.append(self.name())

    def reply(self, event):
        self._state_chart._reply(event)

    def transit(self, state_type):
        self._state_chart._transit(state_type)

    def _invoke_event_handlers(self, handlers, event):
        result = HandleResult.HANDLED
        for handler in handlers:
            if handler(self, event) == False:
                result = HandleResult.UNHANDLED
        return result

    def _invoke_default_handlers(self, handlers):
        result = HandleResult.HANDLED
        for handler in handlers:
            if handler(self) == False:
                result = HandleResult.UNHANDLED
        return result

    def _dispatch_event(self, handlers, event):
        result = HandleResult.UNKNOWN
        if event is not None and (selected := handlers.get(type(event))) is not None:
            result = self._invoke_event_handlers(selected, event)
        if result != HandleResult.HANDLED and (selected := handlers.get(None)) is not None:
            result = self._invoke_default_handlers(selected)
        return result

    def _enter(self, event):
        self._dispatch_event(self._entry_handlers, event)

    def _exit(self, event):
        self._dispatch_event(self._exit_handlers, event)

    def _handle(self, event):
        return self._dispatch_event(self._event_handlers, event)


class ConcreteState(AbstractState):
    def __init__(self, constructor):
        super().__init__(constructor)
        self._linked_joint_states = None

    @classmethod
    def _add_targets_to(cls, target_states):
        target_states.append(cls)

    @classmethod
    def _has_state_type(cls, state_type):
        return state_type is cls

    @classmethod
    def _index_states(cls, target_index, index):
        target_index[cls] = index

    def _link_joint_state(self, state):
        if self._linked_joint_states is None:
            self._linked_joint_states = [state]
        else:
            self._linked_joint_states.append(state)

    def _enter(self, event):
        super()._enter(event)

        if (joint_states := self._linked_joint_states) is not None:
            for state in joint_states:
                state._enter_guard_state(event)

    def _exit(self, event):
        if (joint_states := self._linked_joint_states) is not None:
            for state in joint_states:
                state._exit_guard_state(event)

        super()._exit(event)

    def _initiate(self, event):
        pass

    def _exit_for_state(self, state_type, event):
        # Always exit this state first for any state transition.
        return True

    def _enter_for_state(self, state_type, event):
        return True


class SimpleState(ConcreteState, metaclass=StateMeta, is_state_type=False):
    pass


class ParentState(ConcreteState):
    @classmethod
    def _prepare_state_type(cls):
        target_index = {}
        for index, state_type in enumerate(cls.states):
            state_type._index_states(target_index, index)
        cls._target_index = target_index

    @classmethod
    def _index_states(cls, target_index, index):
        super()._index_states(target_index, index)
        for state_type in cls.states:
            state_type._index_states(target_index, index)

    @classmethod
    def _has_state_type(cls, state_type):
        return super()._has_state_type(state_type) or state_type in cls._target_index

    def __init__(self, constructor):
        super().__init__(constructor)
        self._states = [constructor.get_instance(s) for s in self.states]


class CompositeState(ParentState, metaclass=StateMeta, is_state_type=False):
    def __init__(self, constructor):
        super().__init__(constructor)
        self._current_state = None

    def _write_to(self, parts):
        super()._write_to(parts)
        if (current_state := self._current_state) is not None:
            parts.append('.')
            current_state._write_to(parts)

    def _exit(self, event):
        if (current_state := self._current_state) is not None:
            self._current_state = None
            current_state._exit(event)
        super()._exit(event)

    def _handle(self, event):
        result = HandleResult.UNKNOWN
        if (current_state := self._current_state) is not None:
            result = current_state._handle(event)
        if result != HandleResult.HANDLED:
            result = super()._handle(event)
        return result

    def _initiate(self, event):
        super()._initiate(event)
        if (current_state := self._current_state) is None:
            current_state = self._states[0]
            current_state._enter(event)
            self._current_state = current_state
        current_state._initiate(event)

    def _exit_for_state(self, state_type, event):
        if (target_state := self._get_target_state(state_type)) is None:
            return True
        elif (current_state := self._current_state) is None:
            return False
        elif target_state is not current_state or current_state._exit_for_state(state_type, event):
            current_state._exit(event)
            self._current_state = None
        return False

    def _enter_for_state(self, state_type, event):
        if state_type is type(self):
            return True
        elif (target_state := self._get_target_state(state_type)) is None or \
                ((current_state := self._current_state) is not None and current_state is not target_state):
            return False
        elif current_state is None:
            current_state = target_state
            current_state._enter(event)
            self._current_state = current_state
        return current_state._enter_for_state(state_type, event)

    def _get_target_state(self, state_type):
        if (target_index := self._target_index.get(state_type)) is None:
            return None
        else:
            return self._states[target_index]


class ParallelState(ParentState, metaclass=StateMeta, is_state_type=False):
    joint_states = None

    def __init__(self, constructor):
        super().__init__(constructor)
        self._active_states = [None for s in self.states]
        if (joint_states := self.joint_states) is None:
            self._joint_states = None
        else:
            self._joint_states = [constructor.get_instance(s) for s in joint_states]

    def _write_to(self, parts):
        super()._write_to(parts)
        has_active_states = False
        for state in self._get_active_states():
            if has_active_states:
                parts.append(', ')
            else:
                parts.append('[')
                has_active_states = True
            state._write_to(parts)
        if has_active_states:
            parts.append(']')

    def _exit(self, event):
        for index, state in enumerate(self._active_states):
            if state is not None:
                self._active_states[index] = None
                state._exit(event)

        super()._exit(event)

    def _handle(self, event):
        result = HandleResult.UNKNOWN

        for state in self._get_active_states():
            state_result = state._handle(event)
            if state_result == HandleResult.UNHANDLED:
                result = state_result
            elif state_result == HandleResult.HANDLED and result == HandleResult.UNKNOWN:
                result = state_result

        if result != HandleResult.HANDLED:
            result = super()._handle(event)

        return result

    def _initiate(self, event):
        super()._initiate(event)

        for index, state in enumerate(self._active_states):
            if state is None:
                state = self._states[index]
                state._enter(event)
                self._active_states[index] = state
            state._initiate(event)

    def _exit_for_state(self, state_type, event):
        target_index = self._target_index.get(state_type)
        if target_index is None:
            return True
        elif (state := self._active_states[target_index]) is not None and state._exit_for_state(state_type, event):
            self._active_states[target_index] = None
            state._exit(event)
        return False

    def _enter_for_state(self, state_type, event):
        if state_type is type(self):
            return True
        elif (target_index := self._target_index.get(state_type)) is None:
            return False
        elif (state := self._active_states[target_index]) is None:
            state = self._states[target_index]
            state._enter(event)
            self._active_states[target_index] = state
        return state._enter_for_state(state_type, event)

    def _get_active_states(self):
        for state in self._active_states:
            if state is not None:
                yield state

        if (joint_states := self._joint_states) is not None:
            for state in joint_states:
                if state._is_active():
                    yield state


class JointState(AbstractState, metaclass=StateMeta, is_state_type=False):
    @classmethod
    def _prepare_state_type(cls):
        guard_states = []
        for state_type in cls.guards:
            state_type._add_targets_to(guard_states)
        cls._guards = list(set(guard_states))

    @classmethod
    def _add_targets_to(cls, target_states):
        target_states.extend(cls._guards)

    def __init__(self, constructor):
        super().__init__(constructor)
        self._inactive_guards = len(self._guards)
        for state_type in self._guards:
            constructor.get_instance(state_type)._link_joint_state(self)

    def _enter_guard_state(self, event):
        self._inactive_guards -= 1
        if self._inactive_guards == 0:
            self._enter(event)
            
    def _exit_guard_state(self, event):
        if self._inactive_guards == 0:
            self._exit(event)
        self._inactive_guards += 1

    def _is_active(self):
        return self._inactive_guards == 0


class StateChartDict:
    reply_annotation_key = 'reply'
    define_reply_key = 'reply'
    reply_handlers_key = '_reply_handlers'

    def __init__(self):
        super().__init__()
        self.reply_handlers = {}
        self.dict = {
            self.reply_handlers_key: self.reply_handlers
        }

    def __setitem__(self, key, value):
        if key == self.define_reply_key:
            self.add_handler(self.reply_handlers, value)
        else:
            self.dict[key] = value

    def __getitem__(self, key):
        return self.dict[key]

    def add_handler(self, handlers, handler):
        event_type = handler.__annotations__[self.reply_annotation_key]
        if event_type in handlers:
            handlers[event_type].append(handler)
        else:
            handlers[event_type] = [handler]


class StateChartMeta(type):
    @classmethod
    def __prepare__(cls, name, bases, *, is_state_chart_type=True):
        return StateChartDict() if is_state_chart_type else super().__prepare__(name, bases)

    def __new__(cls, name, bases, classdict, *, is_state_chart_type=True):
        d = classdict.dict if is_state_chart_type else classdict
        return super().__new__(cls, name, bases, d)


class StateChart(metaclass=StateChartMeta, is_state_chart_type=False):
    def __init__(self, *, name=None):
        super().__init__()
        self._state = None
        self._current_event = None
        self._event_queue = []
        self._reply_queue = None
        self._transit_queue = []
        self.name = name

    def _dispatch_reply(self, reply):
        if (handlers := self._reply_handlers.get(type(reply))) is None:
            self.report_unprocessed_reply(reply)
        else:
            for handler in handlers:
                handler(self, reply)

    def _reply(self, reply):
        if (reply_queue := self._reply_queue) is None:
            self._dispatch_reply(reply)
        else:
            reply_queue.append(reply)

    def _transit(self, state_type):
        if self.state._has_state_type(state_type):
            self._transit_queue.append(state_type)
        else:
            self.report_transition_error(state_type)

    def initiate(self):
        if (state := self._state) is None:
            constructor = StateConstructor(self)
            state = constructor.get_instance(self.state)
            state._enter(None)
            self._state = state
        state._initiate(None)

        while len(self._transit_queue) > 0:
            self._handle_transitions(None)

        self.report_initiated()

    def terminate(self):
        if (state := self._state) is not None:
            state._exit(None)
            self._state = None

        self.report_terminated()

    def process(self, event):
        event_queue = self._event_queue
        if self._current_event is not None:
            event_queue.append(event)
        else:
            self._dispatch_event(event)
            while len(event_queue) > 0:
                event = event_queue.pop(0)
                self._dispatch_event(event)

    def decorate_message(self, msg):
        parts = []
        if (name := self.name) is not None:
            parts.append(f'In {name}: ')
        if (event := self._current_event) is not None:
            parts.append(f'While processing {event}: ')
        parts.append(msg)
        if (state := self._state) is not None:
            parts.append(' in state ')
            state._write_to(parts)
        return ''.join(parts)

    def log(self, msg):
        print(msg)

    def report_error(self, msg_factory):
        self.log(self.decorate_message(msg_factory()))

    def report_info(self, msg_factory):
        self.log(self.decorate_message(msg_factory()))

    def get_unprocessed_event_msg(self):
        return 'Unprocessed event'

    def get_unprocessed_reply_msg(self, reply):
        return f'Unprocessed {reply}'

    def get_transition_error_msg(self, state_type):
        return f'Transition error for {state_type.name()}'

    def get_not_initiated_msg(self):
        return 'State chart not initiated'

    def get_initiated_msg(self):
        return 'State chart initiated'

    def get_terminated_msg(self):
        return 'State chart terminated'

    def get_transitions_msg(self, states):
        states_list = ', '.join(state.name() for state in states)
        return f'transition to [{states_list}]'

    def get_event_procesed_msg(self, event):
        return f'Processed {event}'

    def report_unprocessed_event(self):
        self.report_error(self.get_unprocessed_event_msg)

    def report_unprocessed_reply(self, reply):
        self.report_error(lambda: self.get_unprocessed_reply_msg(reply))

    def report_transition_error(self, state_type):
        self.report_error(lambda: self.get_transition_error_msg(state_type))

    def report_not_initiated(self):
        self.report_error(self.get_not_initiated_msg)

    def report_initiated(self):
        self.report_info(self.get_initiated_msg)

    def report_terminated(self):
        self.report_info(self.get_terminated_msg)

    def report_transitions(self, states):
        self.report_info(lambda: self.get_transitions_msg(states))

    def report_event_procesed(self, event):
        self.report_info(lambda: self.get_event_procesed_msg(event))

    def _dispatch_event(self, event):
        if (state := self._state) is None:
            self.report_not_initiated()
            return

        # Make current event available and ensure that recursive process
        # requests get queued.
        self._current_event = event

        # Queue any replies until after all exit handlers have been called.
        self._reply_queue = (reply_queue := [])

        # Handle the current event.  This can lead to any number of queued
        # replies and transitions (state transitions).
        if state._handle(event) != HandleResult.HANDLED:
            self.report_unprocessed_event()

        # Replies will not be queued anyore from this point onward but executed
        # immediately.
        self._reply_queue = None

        # Handle all scheduled transitions.  Execute scheduled reply handlers
        # between handling all exit handlers and handling all entry
        # handlers.
        self._handle_transitions(reply_queue)

        # Repeatedly handle possible further transitions.  No (queued) replies
        # need to be executed anymore.
        while len(self._transit_queue) > 0:
            self._handle_transitions(None)

        # The event has been handled (if possible) and the reply and transit
        # queues have been reset.  Allow the processing of a next event. 
        self._current_event = None

        self.report_event_procesed(event)

    def _handle_transitions(self, reply_queue):
        state = self._state
        event = self._current_event

        # Only process the current amount of transition request.  More
        # transition requests may be queued while processing, but these will
        # only be processed in the next call to this method.
        target_count = len(transit_queue := self._transit_queue)

        if target_count > 0:
            self.report_transitions(transit_queue)

        # Exit all states as required by the set of all scheduled transitions.
        for target_index in range(target_count):
            target_type = transit_queue[target_index]
            if state._exit_for_state(target_type, event):
                state._exit(event)

                # A transition to the top state is allowed.  Set state to None
                # here to indicate that the top state has to be entered again
                # below.  No more exits can be performed now.
                state = None
                break

        # Execute scheduled replies.
        if reply_queue is not None:
            for reply in reply_queue:
                self._dispatch_reply(reply)

        # Enter the top state again if it is not active anymore.
        if state is None:
            state = self._state
            state._enter(event)

        # Enter all states as required by the set of all scheduled transitions.
        for target_index in range(target_count):
            target_type = transit_queue[target_index]
            if not state._enter_for_state(target_type, event):
                self.report_transition_error(target_type)

        # Remove all handled transitions from the transition queue.  Note that
        # more transitions may remain if exit-, reply-, and entry handlers
        # requested these.
        del transit_queue[:target_count]
