#!/usr/bin/env python
import grpc
from concurrent import futures
from monitor_keypress_pb2 import KeysPressed, Empty
import monitor_keypress_pb2_grpc

class MonitorKeyboardService(
            monitor_keypress_pb2_grpc.KeyboardMonitoringServicer):
    def HandleButtonEvent(self, request, context):
        print(request.KeysPressed)
        return Empty


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    monitor_keyboard_pb2_grpc.add_KeyboardMonitoringServicer_to_server(
        MonitorKeyboardService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
