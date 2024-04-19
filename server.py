#!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import socket
import sys
import threading
import os
import connection
from constants import *


class Server(object):
    """
    El servidor, que crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """

    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print("Serving %s on %s:%s." % (directory, addr, port))

        if not os.path.isdir(directory):
            os.mkdir(directory)

        self.server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.bind((addr,port))
        self.dir = directory
        self.server_socket.listen(MAX_CONNECTIONS)
        self.threadLimiter = threading.BoundedSemaphore(MAX_CONNECTIONS)

        print("Server ready. Waiting connections...")

    def handle(self, connection):
        """
        Atiende una conexión. Recibe un objeto Connection y se encarga
        de manejarla.
        """  
        #c.send(b"Esperando tu turno...\n")
        self.threadLimiter.acquire()
        def handler():
            #c.send(b"Aceptado\n")
            print("Cliente aceptado")
            try:
                
                connection.handle()
            finally:
                print("Cliente desconectado\n")
                self.threadLimiter.release()
        t = threading.Thread(target=handler)
        t.start()

    def serve(self):
        """
        Loop principal del servidor. Acepta clientes y los envia al handler
        """
        while True:
            active_connections = threading.active_count() - 1 # Contar las conexiones activas
            print(f"[ACTIVE CONNECTIONS] {active_connections}")
            client,addr = self.server_socket.accept()
            #if self.clients >= MAX_CONNECTIONS:
            #    client.close()
            #    self.clients -= 1
            connection_c = connection.Connection(client,self.dir)
            self.handle(connection_c)
            
def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help="Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help="Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help="Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)

    server = Server(options.address, port, options.datadir)
    server.serve()


if __name__ == '__main__':
    main()
