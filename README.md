# PSC
A parallel state chart library for Python 3.

## Introduction
This is a library to model state charts in Python 3.  It support many
well-known concepts such as composite and parallel states, entry- and exit
handlers, hierarchical event handling, etc.  It also extends this familiar
behavior with some new concepts, particularly in the area of parallel states,
that make state charts much more expressive and powerful.  The name PSC,
parallel state charts, reflects this focus on parallel state modeling.

Before diving into the details, let's explore some examples of extended
concepts.  In PSC it is allowed to handle events in multiple regions (parallel
substates) of a parallel state simultaneously.  In this case an event will
trigger all such handlers.  Other libraries often allow an event to be handled
only in a single parallel region and might even have undefined behavior if
handlers for the same event appear in multiple parallel regions.

In PSC a single event can lead to atomic state transitions in multiple parallel
regions.  These transitions may be triggered by separate handlers in parallel
regions.  It is also perfectly fine for a single handler to trigger multiple
state transitions, as long as all target states can be active at the same time.
(So either they must be nested states, or, rather more useful, appear in
separate regions of a parallel state.)

Finally, PSC support so-callad joint states.  A joint state is a pseudo state
that is active when and only when a specified set of other states (called its
guard states) are all active.  Joint states are very convenient to specify
behavior that depends on the state of multiple regions of a parallel state.  A
frequently occurring pattern is to tie a request to an actual state.  For
exampla "if the switch is in the ON position and the motor is off then start
the motor".  Here a switch state is coupled to a motor state to trigger
specific activation behavior.

## A state chart usage pattern
The PSC library strongly advocates a strict separation between actual state
behavior and the client code specific actions that are required when certain
transitions or other state chart events occur.  States in a PSC state chart are
defined by deriving from specific base state classes (see the section about
state types).  State behavior is defined by adding specific methods to state
classes.  While it is possible to write any code you want in such state methods
_this is strongly discouraged_.

State methods should only contain code to check event guard conditions, to
request state transitions, and to send replies to the client code.  All further
specific code should be implemented outside of the state chart or any of its
states and instead be wired to replies that the state chart can send.  See the
sections about sending replies and the `StateChart` class for more details.

So the setup of code that uses a PSC state chart should look as follows:

```
   ,---------------.   events   ,---------------.
   |               |----------->|               |
   |  Client code  |            |  State chart  | 
   |               |<-----------|               |
   `---------------'   replies  `---------------'
```

## Defining state behavior
All state behavior in PCS is defined by specific methods in a state class that
derives from one of the four state types in PCS.  See section State types for
more information on all four state types.  In this section we'll use a simple
state as example:

```python
import psc


class ExampleState(psc.SimpleState):
    # State behavior is specified by methods.  See the subsections below
    # for the supported methods and their effects.
```

### Entry handlers
An entry handler is defined by a method with the name `enter`.  An entry
handler can specify a specific event type to indicate that it only triggers if
the current event (i.e. the event that is being processed by the state chart)
has this type.  Note that _any number_ of `enter`  methods may occur.  All these methods will trigger as specified.

```python
    def enter(self):
        # This is a generic entry handler.  It will trigger when this state
        # becomes active (unless all specific event type entry handlers already
        # handled it).

    def enter(self, event:StartEvent):
        # This is an event type specific entry handler.  It triggers only when
        # the current event has type StartEvent.  Note that the argument must
        # be named 'event'.  If (and only if) some event type specific handler
        # returns False then all generic entry handlers will also trigger.
```

### Exit handlers
Exit handlers are defined by one or more methods with the name `exit` and
trigger when a state becomes inactive.  Exit handlers may specify a specific
event type to trigger only when the current event has that type.

```python
    def exit(self):
        # This is a generic exit handler.  It will trigger when this state
        # becomes inactive (unless all specific event type exit handlers
        # already handled it).

    def exit(self, event:StartEvent):
        # This is an event type specific exit handler.  It triggers only when
        # the current event has type StartEvent.  Note that the argument must
        # be named 'event'.  If (and only if) some event type specific handler
        # returns False then all generic exit handlers will also trigger.
```

### Event handlers
Event handlers are defined by one or more methods with the name `handle` and
specify a typed `event` argument.  An event handler of an active state triggers
when the current event (i.e. the event that is being processed by the state
chart) has the specified type unless all active nested states already handled
the event.  An event handler can return `False` to indicate that the event was
not handled.

```python
    def handle(self, event:SomeEvent):
        # Handle event of type SomeEVent.

    def handle(self, event:AnotherEvent):
        # Handle event of type AnotherEvent.
```

An event handler can implement a  _guard_ by checking a condition on the event
and returning `False` when the condition is not met:

```python
    def handle(self, event:SomeEvent):
        # Only handle events with priority at least 2.
        if event.priority < 2:
            # Event is not handled.
            return False
        # Handle event here.
```

A nested state can force its parent state to handle an event by simply
returning `False` unconditionally.  This will forward the event to the parent
state, even if some other handler actually did handle the event.  Remember that
an event is forwarded unless _all_ event handlers handled it.

```python
    def handle(self, event:SomeEvent):
        # Handle event of type SomeEvent.

    def handle(self, event:SomeEvent):
        # Force that an event of type SomeEvent is considered to be not handled
        # in this state and will therefore be forwarded to a parent state (if
        # any).  Note that this will happen even though the event handler above
        # handles the event.
        return False
```

## Implementing state behavior
The previous sections explain how to define handlers for specific events.  Such
handlers must have a way to implement specific behavior.  All PSC state types
offer the methods described in the following sections.  A handler can call any
of these methods any number of times (remember that PSC allows multiple atomic
state transitions), even if the handler returns `False` and so does not handle
the event (including entry and exit events).

### State transitions
A handler can request a transition to another state by calling its `transit`
method with its target state type.  Note that it is allowed to request multiple
state stransitions (by making multiple) calls as long as all states can be
active at the same time.  State transitions are not effectuated immediately.
Instead, all requested transitions will be performed only after all (event)
handlers have been triggered as specified.

```python
    def handle(event:SwitchOnEvent):
        # Transition to the StateOn state.
        self.transit(StateOn)
```

All state transitions in PSC are so-called _outer transitions_: If a transition
to an already active state is requested then that state will be exited first
and then entered again (triggering possible exit- and entry handlers).  If
multiple transitions are requested then the PSC library takes care to perform
the minimal number of required state exit and entry actions to activate all
target states.  In particular, any exit- and entry handler is triggered at most
once during a transition, regardless of the number of target states.  Also,
exit handlers are always triggered _before_ any entry handler.

Requesting a state transition to a joint state is equivalent to requesting
simultaneous state transitions to all its guard states.  See the section about
joint states for more information.

### Sending replies
A reply is the counterpart of an event: Client code sends events to a PSC state
chart which in turn processes these events and sends replies back to client
code.  Any handler can send a reply by calling its state's `reply` method,
passing a reply instance to send to the client.  See the section about the
`StateChart` class for more information about how client code can receive
replies from a PSC state chart.

Replies are sent at different moments, depending on the handler that sends the
reply.  Replies sent from an entry- or exit handler are sent immediately.
Replies sent from an event handler are first collected until all event handlers
have been triggered.  Then, if no state transitions are requested, all replies
are sent.  If one or more state transitions are requested as a result of
processing the event then all replies are sent right after all exit handlers
have triggered and before any entry handler is triggered.

```python
    def enter(self):
        # Send a reply to client code immediately.
        self.reply(EnterReply())

    def handle(self, event:SwitchOn):
        # Send a reply to client code and transition to StateOn.  The reply is
        # sent during the state transition after all exit handlers have
        # triggered and before any entry handler is triggered.  In this case
        # this means that the ExitReply from the exit handler below is sent
        # before the SwitchedOnReply.
        self.reply(SwitchedOnReply())
        self.transit(StateOn)
    
    def exit(self):
        # Send a reply to client code immediately.
        self.reply(ExitReply())
```

## Event and reply types
Any type can be used as either event type or reply type in PSC.  Nevertheless,
PSC defines the base types `Event` and `Reply` from which you can derive your
own event and reply types.  This has several advantages: It explicitly
expresses that certain types are intended to be events (sent to state chart) or
replies (sent from a state chart) and both base classes provide basic `__str__`
method implementations that are convenient when logging events or replies.

```python
import psc


class MyEvent(psc.Event):
    # Add optional event constructor and fields here.


class MyReply(psc.Reply):
    # Add optional reply constructor and fields here.
```

## State types
PCS supports four different types of states: simple states, composite states,
parallel states, and joint states.  Each of these is described in the following sections.

### The `SimpleState` class
A simple state is a leaf state: it can have no child states.  A simple state is defined by deriving from the `SimpleState class`.

```python
import psc


class MySimpleState(pcs.SimpleState):
    # State behavior methods are defined here.
```

### The `CompositeState` class
A composite state can have nested states (also called child states).  Exactly
one nested state of an active composite state will be active at any time.  A
nested state can be a simple state, composite state, or parallel state.
Usually a composite state will have at least two nested states, although this
is not required.

A composite state is defined by deriving from the
`CompositeState` class and must define a class variable called `states` that
lists the state types of its nested states.  The first entry in this `states`
list is considered to be the initial nested state type: if a transition is made
to a composite state, then that initial state is activated upon entry.

```python
import psc


class MyCompositeState(psc.CompositeState):
    # The list of nested state types.  The first type in this list is
    # considered to be the type of the initial nested state.
    states = [NestedA, NestedB]

    # State behavior methods are defined here.
```

### The `ParallelState` class
A parallel state can have nested states (also called regions or child states).
All nested states of an active parallel state are active at the same time.  A
nested state can be a simple state, composite state, or parallel state.
Usually a parallel state will have at least two nested states and all nested
states are composite states, although this is not required.

A parallel state can also contain zero or more joint states.  These joint
states are not considered to be nested states and any number of these joint
states can be active at any time.  A joint state is active precisely when all
of its guard states are active.  See the section about joint states for
details.

A parallel state is defined by deriving from the `ParallelState` class.  It
must define a class variable called `states` that lists the state types of its
nested states and it may define a class variable called `joint_states` that
lists its contained joint state types.

```python
import psc


class MyParallelState(psc.ParallelState):
    # The list of nested state types.  All nested states will be active when
    # this parallel state is itself active.
    states = [NestedA, NestedB]

    # An optional list of joint state types.  Any of these contained joint
    # states will be active precisely when all their guard states are active.
    joint_states = [JointA, JointB, JointC]

    # State behavior methods are defined here.
```

### The `JointState` class
A joint state can specify any number of guard states (usually more than two,
although this is not required).  All guard states of a joint state must be able
to be active at the same time and a joint state may not be a guard state of
itself (either directly or indirectly).  This usually means that guard states
are nested states in different regions of a parallel state.  Other than these
restrictions, any state may appear as a guard state in any number of joint
states.  A guard state is not a nested state of a joint state and can be active
while the joint state itself is not active.

A joint state is active precisely when all its guard states are active.  In
that case all entry handlers of guard states trigger before any entry handler
of the joint state triggers.  If a joint state becomes inactive (because at
least one of its guard states becomes inactive) then its exit handlers trigger
before any exit handler of guard states.

A transition to a joint state is equivalent to simultaneous transitions to all
of its guard states.  In this case the joint states becomes active because all
its guard states become active.

A joint state is defined by deriving from the `JointState` class.  It must
define a class variable called `states` that lists the state types of its guard
states.

```python
import psc


class MyJointState(psc.JointState):
    # The list of guard state types.
    states = [GuardA, GuardB]

    # State behavior methods are defined here.
```

## The StateChart class
