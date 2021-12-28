import psc


class EvRequestOn(psc.Event): pass
class EvRequestOff(psc.Event): pass


class EvTurnedOn(psc.Event): pass
class EvTurnedOff(psc.Event): pass


class ReplyOnRequested(psc.Reply): pass
class ReplyOffRequested(psc.Reply): pass

class ReplyTurnOn(psc.Reply): pass
class ReplyTurnOff(psc.Reply): pass


class OnRequest(psc.SimpleState):
    def enter(self):
        print('OnRequest.enter')

    def enter(self, event:EvRequestOn):
        print('OnRequest.enter by EvRequestOn')

    def exit(self):
        print('OnRequest.exit')

    def handle(self, event:EvRequestOff):
        self.transit(OffRequest)
        self.reply(ReplyOffRequested())


class OffRequest(psc.SimpleState):
    def enter(self):
        print('OffRequest.enter')

    def enter(self, event:EvRequestOff):
        print('OffRequest.enter by EvRequestOff')

    def exit(self):
        print('OffRequest.exit')

    def handle(self, event:EvRequestOn):
        self.transit(OnRequest)
        self.reply(ReplyOnRequested())


class RequestState(psc.CompositeState):
    states = [OnRequest, OffRequest]

    def enter(self):
        print('RequestState.enter')

    def exit(self):
        print('RequestState.exit')


class On(psc.SimpleState):
    def enter(self):
        print('On.enter')

    def exit(self):
        print('On.exit')


class GoingOff(psc.SimpleState):
    def enter(self):
        print('GoingOff.enter')
        self.reply(ReplyTurnOff())

    def exit(self):
        print('GoingOff.exit')

    def handle(self, event:EvTurnedOff):
        self.transit(Off)


class GoingOn(psc.SimpleState):
    def enter(self):
        print('GoingOn.enter')
        self.reply(ReplyTurnOn())

    def exit(self):
        print('GoingOn.exit')

    def handle(self, event:EvTurnedOn):
        self.transit(On)


class Off(psc.SimpleState):
    def enter(self):
        print('Off.enter')

    def exit(self):
        print('Off.exit')


class EngineState(psc.CompositeState):
    states = [Off, GoingOn, GoingOff, On]

    def enter(self):
        print('EngineState.enter')

    def exit(self):
        print('EngineState.exit')


class TurnOn(psc.JointState):
    guards = [OnRequest, Off]

    def enter(self):
        print('TurnOn.enter')
        self.transit(GoingOn)

    def exit(self):
        print('TurnOn.exit')


class TurnOff(psc.JointState):
    guards = [OffRequest, On]

    def enter(self):
        print('TurnOff.enter')
        self.transit(GoingOff)

    def exit(self):
        print('TurnOff.exit')


class TopState(psc.ParallelState):
    states = [RequestState, EngineState]
    joint_states = [TurnOn, TurnOff]

    def enter(self):
        print('TopState.enter')

    def exit(self):
        print('TopState.exit')


class ExampleStateChart(psc.StateChart):
    state = TopState

    def reply(self, reply:ReplyOnRequested):
        print('Example.reply:ReplyOnRequested')

    def reply(self, reply:ReplyOffRequested):
        print('Example.reply:ReplyOffRequested')

    def reply(self, reply:ReplyTurnOn):
        print('Example.reply:ReplyTurnOn')

    def reply(self, reply:ReplyTurnOff):
        print('Example.reply:ReplyTurnOff')
