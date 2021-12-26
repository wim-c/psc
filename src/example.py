import scm


class EvRequestOn(scm.Event): pass
class EvRequestOff(scm.Event): pass


class EvTurnedOn(scm.Event): pass
class EvTurnedOff(scm.Event): pass


class ReplyOnRequested(scm.Reply): pass
class ReplyOffRequested(scm.Reply): pass

class ReplyTurnOn(scm.Reply): pass
class ReplyTurnOff(scm.Reply): pass


class OnRequest(scm.SimpleState):
    def enter(self):
        print('OnRequest.enter')

    def enter(self, event:EvRequestOn):
        print('OnRequest.enter by EvRequestOn')

    def exit(self):
        print('OnRequest.exit')

    def handle(self, event:EvRequestOff):
        self.goto(OffRequest)
        self.reply(ReplyOffRequested())


class OffRequest(scm.SimpleState):
    def enter(self):
        print('OffRequest.enter')

    def enter(self, event:EvRequestOff):
        print('OffRequest.enter by EvRequestOff')

    def exit(self):
        print('OffRequest.exit')

    def handle(self, event:EvRequestOn):
        self.goto(OnRequest)
        self.reply(ReplyOnRequested())


class RequestState(scm.CompositeState):
    states = [OnRequest, OffRequest]

    def enter(self):
        print('RequestState.enter')

    def exit(self):
        print('RequestState.exit')


class On(scm.SimpleState):
    def enter(self):
        print('On.enter')

    def exit(self):
        print('On.exit')


class GoingOff(scm.SimpleState):
    def enter(self):
        print('GoingOff.enter')
        self.reply(ReplyTurnOff())

    def exit(self):
        print('GoingOff.exit')

    def handle(self, event:EvTurnedOff):
        self.goto(Off)


class GoingOn(scm.SimpleState):
    def enter(self):
        print('GoingOn.enter')
        self.reply(ReplyTurnOn())

    def exit(self):
        print('GoingOn.exit')

    def handle(self, event:EvTurnedOn):
        self.goto(On)


class Off(scm.SimpleState):
    def enter(self):
        print('Off.enter')

    def exit(self):
        print('Off.exit')


class EngineState(scm.CompositeState):
    states = [Off, GoingOn, GoingOff, On]

    def enter(self):
        print('EngineState.enter')

    def exit(self):
        print('EngineState.exit')


class TurnOn(scm.JointState):
    states = [OnRequest, Off]

    def enter(self):
        print('TurnOn.enter')
        self.goto(GoingOn)

    def exit(self):
        print('TurnOn.exit')


class TurnOff(scm.JointState):
    states = [OffRequest, On]

    def enter(self):
        print('TurnOff.enter')
        self.goto(GoingOff)

    def exit(self):
        print('TurnOff.exit')


class TopState(scm.ParallelState):
    states = [RequestState, EngineState]
    joint_states = [TurnOn, TurnOff]

    def enter(self):
        print('TopState.enter')

    def exit(self):
        print('TopState.exit')


class ExampleStateChart(scm.StateChart):
    state = TopState

    def reply(self, reply:ReplyOnRequested):
        print('Example.reply:ReplyOnRequested')

    def reply(self, reply:ReplyOffRequested):
        print('Example.reply:ReplyOffRequested')

    def reply(self, reply:ReplyTurnOn):
        print('Example.reply:ReplyTurnOn')

    def reply(self, reply:ReplyTurnOff):
        print('Example.reply:ReplyTurnOff')
