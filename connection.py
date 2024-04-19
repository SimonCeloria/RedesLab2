# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
import os
from constants import *
from base64 import b64encode


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket, directory):
        """
        Inicializa una nueva conexión con un socket ya aceptado.
        """
        self.s_connection = socket
        self.dir = directory
        self.status = CODE_OK
        self.connected = True
        self.actual_command =[]
        self.buffer = ""
        self.body_response = ""

    def close(self):
        try:
            if(self.connected==True):
                self.s_connection.close()
                self.connected= False
        except socket.error as e:
            print(f"error cerrando socket: {e}")

    def build_body_response(self, body_append):
        self.body_response += body_append

    def quit(self, is_multiple):
        """
        Cierra la conexión.
        """
        self.status = CODE_OK
        print("Cerrando conexión...")
        if not is_multiple:
            self.send_response('')
        else:
            response = str(self.status) + ' '+ error_messages[self.status]+EOL
            self.build_body_response(response)
        self.close()

    def get_file_listing(self,is_multiple):
        file_list = os.listdir(path=self.dir)
        body_msg = ""
        for file in file_list:
            body_msg += file + EOL
        
        if not is_multiple:
            self.send_response(body_msg)
        else:
            response = str(self.status) + ' '+ error_messages[self.status]+EOL
            response += body_msg + EOL
            self.build_body_response(response)


    def is_valid_file(self, filename):
        is_valid = True
        if len(filename) > MAX_FILENAME or not isinstance(filename, str) or len(filename) == 0:
            is_valid = False
        elif not all(c.isalnum() or c in '-._' for c in filename):
            is_valid = False
        return is_valid
    
    def send_error_response(self, is_multiple):
        if not is_multiple:
            self.send_response('')
        else:
            response = (str(self.status) + ' '+ error_messages[self.status]+EOL).encode('ascii')
            self.build_body_response(response)

    def get_metadata(self, request, is_multiple):
        file = request[1]
        file_list = os.listdir(path=self.dir)
        
        
        
        # Valido el nombre del archivo
        if not self.is_valid_file(file):
            self.status = FILE_NOT_FOUND
            self.send_error_response(is_multiple)
            return
        
        if file not in file_list:
            self.status = FILE_NOT_FOUND
            self.send_error_response(is_multiple)
            return

        path = f'{self.dir}/{file}'
        metadata = str(os.path.getsize(path))
        if not is_multiple:
            self.send_response(metadata)
        else:
            response = str(self.status) + ' '+ error_messages[self.status]+EOL
            response+= metadata+EOL
            self.build_body_response(response)

    def get_slice(self, request, is_multiple):
        file = request[1]
        try:
            offset = int(request[2])
            size = int(request[3])
        except ValueError:
            self.status = INVALID_ARGUMENTS
            self.send_error_response(is_multiple)
            return
        
        file_list = os.listdir(path=self.dir)
        if file not in file_list:
            self.status = FILE_NOT_FOUND
            self.send_error_response(is_multiple)
            return
        path = f'{self.dir}/{file}'
        tam = os.path.getsize(path)

        if offset > tam:
            self.status = BAD_OFFSET
            self.send_error_response(is_multiple)
            return
        
        fd = os.open(path, os.O_RDONLY)

        try:
            os.lseek(fd, offset, os.SEEK_SET)
            bytes_readed = os.read(fd, size)
            bytes_readed = b64encode(bytes_readed)
            if not is_multiple:
                self.send_response(bytes_readed)
            else:
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                response += bytes_readed + EOL.encode('ascii')
                self.build_body_response(response)

        except Exception as e:
            print(e)
            self.status = INTERNAL_ERROR
            if not is_multiple:
                self.send_response('')
            else: 
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                self.build_body_response(response)
                self.s_connection.send(self.body_response.encode("ascii"))
            print("Cerrando conexión...")
            self.close()
        finally:
            os.close(fd)

    def send_response(self, body):
        if body != '':
            response = (str(self.status) + ' '+ error_messages[self.status]+EOL).encode('ascii') 
            response += body if type(body)== bytes else body.encode('ascii')
            response += EOL.encode('ascii')
        else:
            response = str(self.status) + ' '+ error_messages[self.status]+EOL
            response = response.encode('ascii')
        try:
            self.s_connection.send(response)
        except Exception as e:
            print(f"exception sending response: {e}")

    def validate_request(self, is_multiple):
        if b'\n' in self.actual_command:
            self.status = BAD_EOL
            if not is_multiple:
                self.send_response('')
            else:
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                self.build_body_response(response)
                self.s_connection.send(self.body_response.encode("ascii"))
            print("cerrando conexion")
            self.close()

        self.actual_command = self.actual_command.decode("ascii")
        self.actual_command = self.actual_command.split()
        

        if(self.actual_command[0] not in VALID_COMMANDS):
            print(error_messages[INVALID_COMMAND], str(INVALID_COMMAND)+ '\r\n')
            self.status = INVALID_COMMAND
            if not is_multiple:
                self.send_response('')
            else:
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                self.build_body_response(response)
            return
        
        if(self.actual_command[0] in ['quit', 'get_file_listing'] and len(self.actual_command)>1):
            print(error_messages[INVALID_ARGUMENTS], str(INVALID_ARGUMENTS) + '\r\n')
            self.status = INVALID_ARGUMENTS
            if not is_multiple:
                self.send_response('')
            else:
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                self.build_body_response(response)
            return
        elif(self.actual_command[0] == 'get_metadata' and len(self.actual_command)!= 2):
            print(error_messages[INVALID_ARGUMENTS], str(INVALID_ARGUMENTS) + '\r\n')
            self.status = INVALID_ARGUMENTS
            if not is_multiple:
                self.send_response('')
            else:
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                self.build_body_response(response)
            return
        elif(self.actual_command[0] == 'get_slice' and len(self.actual_command)!= 4):
            print(error_messages[INVALID_ARGUMENTS], str(INVALID_ARGUMENTS) + '\r\n')
            self.status = INVALID_ARGUMENTS
            if not is_multiple:
                self.send_response('')
            else:
                response = str(self.status) + ' '+ error_messages[self.status]+EOL
                self.build_body_response(response)
            return
        else:
            self.status = CODE_OK





    def read_line(self, buffer):
        """
        Lee un mensaje completo de la conexión.
        """
        while not b'\r\n' in buffer and self.connected:
            try:
                buffer += self.s_connection.recv(BUFFER_SIZE)
            except socket.error:
                print("socketerrorr")
                self.status =BAD_EOL
                print("El cliente se desconectó inesperadamente...")
                self.close()
                return []
            except UnicodeError :
                print("unicoderrorr")
                self.status = INTERNAL_ERROR
                self.send_response('')
                print("Cerrando conexión...")
                self.close()
                return []
            if buffer == b'':
                print("socketerrorr")
                self.status =BAD_EOL
                print("El cliente se desconectó inesperadamente...")
                self.close()
                return []
        buffer = buffer.split(b'\r\n')
        buffer = [buf for buf in buffer if buf !=b'']      #elimino los elementos vacíos que me quedaron del split
        return buffer




    def execute(self, request, is_multiple):
        """
        Redirecciona el pedido del cliente al método correspondiente.
        """
        # FALTA: Redirigir el pedido al método correspondiente.
        command = request[0]
        if command == 'quit':
            self.quit(is_multiple)
        elif command == 'get_slice':
            self.get_slice(request, is_multiple)
        elif command == 'get_metadata':
            self.get_metadata(request, is_multiple)
        elif command == 'get_file_listing':
            self.get_file_listing(is_multiple)
        
        

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        if not os.path.exists(self.dir):
            self.status = INTERNAL_ERROR
            self.close()

        while self.connected:
            buffer = b""
            buffer = self.read_line(buffer)
            self.buffer = buffer           
            if len(self.buffer) >1:
                for command in self.buffer:
                    self.actual_command = command
                    self.validate_request(True)
                    if self.status == CODE_OK and self.connected:
                        self.execute(self.actual_command, True)
                
                if self.status == CODE_OK and self.connected:
                    self.s_connection.send(self.body_response.encode('ascii'))
                self.status = CODE_OK
                self.body_response = ""
                #ejecuta muchos comandos juntos
            elif len(self.buffer) == 0:
                continue
            else:
                try:
                    self.actual_command = self.buffer[0]
                    self.validate_request(False)
                    if self.status == CODE_OK and self.connected:
                        self.execute(self.actual_command, False)
                    self.status = CODE_OK
                except Exception as e:
                    print(f"error exception:    {e}")
                    self.status = INTERNAL_ERROR
                    self.send_response('')
                    print("Cerrando conexión exception ...")
                    self.close()
                
        self.close()