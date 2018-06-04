import worker
import zmq_sock_utils

class WorkerStub:
    def __init__ (self, casu_number, socket):
        self.casu_number = casu_number
        self.socket = socket
        self.in_use = False

    def key (self):
        return 'casu-%03d' % (self.casu_number)

    def start_domset (self):
        """
        Initialize the DOMSET controller.
        """
        print ("Sending start DOMSET command to worker responsible for casu #%d..." % (self.casu_number))
        answer = zmq_sock_utils.send_recv (self.socket, [worker.START])
        print ("Worker responded with: %s" % (str (answer)))

    def terminate_session (self):
        """
        Terminate the session with the worker, which causes the worker process to finish.
        """
        print ("Sending terminate command to worker responsible for casu #%d..." % (self.casu_number))
        answer = zmq_sock_utils.send_recv (self.socket, [worker.TERMINATE])
        print ("Worker responded with: %s" % (str (answer)))

    def __repr__ (self):
        return '(%d %s %s)' % (self.casu_number, self.socket.__repr__ (), self.in_use.__repr__ ())

def connect_workers (list_worker_settings):
    '''
    Connect to workers and return a dictionary with each casu number associated with a worker stub.
    '''
    return {
        ws.casu_number : WorkerStub (ws.casu_number, ws.connect_to_worker ())
        for ws in list_worker_settings
    }

