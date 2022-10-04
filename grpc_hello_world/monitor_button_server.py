#!/usr/bin/env python
import grpc
from concurrent import futures
from monitor_button_pb2 import ButtonActions, ButtonEvent, ButtonPressCount
import monitor_button_pb2_grpc

class MonitorButtonService(
                monitor_button_pb2_grpc.ButtonMonitoringServicer):
    counter = 0
    lastTime = 0.
    lastState = None
    shortestCountableInterval = 0.15
    def HandleButtonEvent(self, request, context):
        thisTime = request.timeOccurred
        if request.action == ButtonActions.PRESS:
            ledState = True
        else:
            ledState = False

        # first time - depending on where in bounce, could be high or low
        if self.lastState is None:
            if ledState:
                self.lastTime = thisTime
                self.counter += 1
                print(self.counter)
        elif ledState != self.lastState:
            if thisTime > self.lastTime + self.shortestCountableInterval:
                self.lastTime = thisTime
                if ledState:
                    self.counter += 1
                    print(self.counter)
        self.lastState = ledState
        return ButtonPressCount(count=self.counter)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    monitor_button_pb2_grpc.add_ButtonMonitoringServicer_to_server(
        MonitorButtonService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
