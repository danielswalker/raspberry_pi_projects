#!/usr/bin/env python
import grpc
from concurrent import futures
from send_keypresses_pb2 import KeysPressed, Empty
import send_keypresses_pb2_grpc

class KeySenderService(
            send_keypresses_pb2_grpc.KeySenderServicer):
    def HandleKeyEvent(self, request, context):
        print(request.keys)
        return Empty()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    send_keypresses_pb2_grpc.add_KeySenderServicer_to_server(
        KeySenderService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
