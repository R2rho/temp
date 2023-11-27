import sys, os
import threading
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from abc import ABCMeta, abstractmethod
from http import HTTPStatus
import asyncio
import orjson
import traceback
import websockets
import os

from core.Executor import Executor
from server.router import Router
from server.routes import *

class Server(metaclass=ABCMeta):
    name='Server'
    description='Abstract baseclass for various server types'

    @abstractmethod
    def __init__(self, host:str = '127.0.0.1',port:int=8000, logging:bool=False, allowed_clients:list[str] | None=None) -> None:
        if allowed_clients is None : allowed_clients = []
        self.host = host
        self.port = port
        self.logging = logging
        self.allowed_clients = ['localhost',host]
        self.allowed_clients.extend([ac for ac in allowed_clients if ac not in self.allowed_clients])

        self.router = Router()
        
    @abstractmethod
    async def firewall(self, path, request_headers):
        '''
            A very basic firewall
        '''
        requesting_ip = request_headers['Host'].split(':')[0]
        if self.logging: print(f'requesting ip: {requesting_ip}')
        if requesting_ip not in self.allowed_clients:
            return (HTTPStatus.UNAUTHORIZED, [], b'')
        
    async def handler(self,websocket):
        '''
            Initial handler for all websocket messages
        '''
        try:
            output_queue = asyncio.Queue(10)
            consumer_task = asyncio.create_task(self.consumer_handler(websocket,output_queue))
            producer_task = asyncio.create_task(self.producer_handler(websocket,output_queue))
            #Consumer and producer tasks are create to handle the websocket
            #Then returns when the websocket is closed
            done, pending = await asyncio.wait(
                [consumer_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=50000
            )
        except websockets.ConnectionClosed:
            if self.logging:
                print('Connection closed by client')
        finally:
            for task in pending:
                if task == producer_task:
                    await asyncio.wait_for(output_queue.join(), timeout=14500)
                task.cancel()
        if self.logging:
            print(f'Closing connection with {websocket.host}')

    async def consumer_handler(self, websocket, output_queue):
        ''''
            Decodes json messages and passes them to the API
            pre-processing of requests can be implemented here
        '''
        try:
            while True:
                async for message in websocket:
                    asyncio.create_task(self.API(orjson.loads(message),websocket,output_queue))
                if websocket.closed:
                    return
        except Exception:
            if self.logging: print(traceback.format_exc())

    async def producer_handler(self, websocket, output_queue):
        '''
            Waits for the available messages in the output_queue added by consumer
            Passes the message to the API and sends back to requestor

            Assumes API does not return empty strings
        '''
        while True:
            try:
                message = await output_queue.get()
                if not message: 
                    message = (HTTPStatus.BAD_REQUEST, [], b'')
                else:
                    try:
                        message = orjson.dumps(message,option=orjson.OPT_SERIALIZE_NUMPY).decode()
                    except:
                        message = {'error': ' Unable to serialize response JSON'}
                    finally:
                        await websocket.send(message)
            except Exception:
                if self.logging:
                    print(traceback.format_exc())

    def run_server(self):
        '''
            Starts the websocket server listening on specified port and address
        '''
        asyncio.run(self._run_server())
        return True

    async def _run_server(self):
        MAX_REQUEST_SIZE = int(1000000*1000*10) #bytes*Mb*Gb ==> 10Gb
        WRITE_LIMIT      = int(1000000*1000*0.25) #250Mb write limit
        READ_LIMIT       = int(1000000*1000*0.25) #250Mb read limit
        PING_TIMEOUT     = None
        CLOSE_TIMEOUT    = 14400 #seconds -> 4 hr for really long toolpath generation times
        try:
            async with websockets.serve(
                ws_handler=self.handler, 
                host=self.host, 
                port=self.port,
                process_request=self.firewall,
                max_size=MAX_REQUEST_SIZE,
                write_limit=WRITE_LIMIT,
                read_limit=READ_LIMIT,
                ping_timeout=PING_TIMEOUT,
                close_timeout=CLOSE_TIMEOUT
            ) as server:
                if self.logging:
                    socket_data = server.sockets[0].getsockname()
                    message = {'server':str(socket_data[0]), 'port':str(socket_data[1]), 'PID':str(os.getpid())}
                    print(orjson.dumps(message).decode(),flush=True)
                    print(server)
                    #waits for the socket server to return -- only happens when server is shutdown
                    await asyncio.Future()
        except Exception:
            if self.logging:
                print('Unable to start websocket server')
                print(traceback.format_ex())

@abstractmethod
async def API(self,message, websocket,output_queue):
    if message['actions'] == 'search':
        self.ret_message = {'action':'result', 'value':'OK', 'status':'ok'}



class AppServer(Server):
    name = 'App Server'
    description = 'A websocket server to handle all incoming requests for the application state and processes'

    def __init__(self, host: str = '127.0.0.1', port: int = 8000, logging: bool = False, allowed_clients: list[str] | None = None) -> None:
        super().__init__(host=host, port=port, logging=logging, allowed_clients=allowed_clients)    
        self.executor = Executor()

    async def firewall(self, path, request_headers):
        return await super().firewall(path, request_headers)
        
    async def API(self,message,websocket,output_queue):
        '''
            Handles all API endpoints
            requests follow: 
            {
                'action': '<method string>',
                'value' : '<dict or string with data>',
                'uuid'  : '<uuid for request>'
            }
        '''
        

        try:
            response = {'action':message['action'],'value':'', 'uuid':message['uuid'], 'status':'ok'}
            if message['action'] == 'ping': response['value'] = 'OK'

            else:
                response = self.router.route_request(message)

        except (KeyError, TypeError):
            response['status'] = 'error'
            response['value'] = {'error':f'Bad Request - Malformed parameter: {e.args[0]}\n\n',
                                 'traceback':traceback.format_exc()
                                 }
        except Exception as e:
            response['status'] = 'error'
            response['value'] = {'error' : 'An unknown error occured',
                                 'traceback': traceback.format_exc()
                                 }
        await output_queue.put(response)

        
if __name__ == '__main__':
    import server.http_server as http_server
    # Start the HTTP server in a separate thread
    http_server_thread = threading.Thread(target=http_server.run, args=(8001,))
    http_server_thread.start()
    
    server = AppServer(
        host='127.0.0.1',
        port=8000,
        allowed_clients=['127.0.0.1'],
        logging=True
    )
    server.run_server()

   
    
    