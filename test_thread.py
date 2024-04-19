import threading
import unittest
import client
import constants
import select
import time
import socket
import os
import os.path
import logging
import sys

DATADIR = 'testdata'
TIMEOUT = 3  # Una cantidad razonable de segundos para esperar respuestas


class TestBase(unittest.TestCase):

    # Entorno de testing ...
    def setUp(self):
        print("\nIn method %s:" % self._testMethodName)
        os.system('rm -rf %s' % DATADIR)
        os.mkdir(DATADIR)

    def tearDown(self):
        os.system('rm -rf %s' % DATADIR)
        if hasattr(self, 'client'):
            if self.client.connected:
                # Deshabilitar el logging al desconectar
                # Dado que en algunos casos de prueba forzamos a que
                # nos desconecten de mala manera
                logging.getLogger().setLevel('CRITICAL')
                try:
                    self.client.close()
                except socket.error:
                    pass  # Seguramente ya se desconecto del otro lado
                logging.getLogger().setLevel('WARNING')
            del self.client
        if hasattr(self, 'output_file'):
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
            del self.output_file

    # Funciones auxiliares:
    def new_client(self):
        assert not hasattr(self, 'client')
        try:
            self.client = client.Client()
        except socket.error:
            self.fail("No se pudo establecer conexión al server")
        return self.client


class TestMultithreading(TestBase):
    
    def test_multiple_clients(self):
        # Función que cada hilo ejecutará
        def client_thread():
            c = self.new_client()
            c.send('get_file_listing\r\n')
            status, message = c.read_response_line(TIMEOUT)
            self.assertEqual(status, constants.CODE_OK,
                             "El servidor no respondió correctamente a la solicitud de lista de archivos")
            c.close()

        # Crear y ejecutar múltiples hilos de cliente
        num_clients = 5
        threads = []
        for _ in range(num_clients):
            t = threading.Thread(target=client_thread)
            threads.append(t)
            t.start()

        # Esperar a que todos los hilos terminen
        for t in threads:
            t.join()
            
            

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMultithreading))
    return suite


def main():
    import optparse
    global DATADIR
    parser = optparse.OptionParser()
    parser.set_usage("%prog [opciones] [clases de tests]")
    parser.add_option('-d', '--datadir',
                      help="Directorio donde genera los datos; "
                      "CUIDADO: CORRER LOS TESTS *BORRA* LOS DATOS EN ESTE DIRECTORIO",
                      default=DATADIR)
    options, args = parser.parse_args()
    DATADIR = options.datadir
    # Correr tests
    unittest.main(argv=sys.argv[0:1] + args)


if __name__ == '__main__':
    main()