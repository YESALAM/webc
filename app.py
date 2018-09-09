import tornado.web
from tornado.ioloop import IOLoop
from terminado import TermSocket, UniqueTermManager
import terminado
import os,sys
import signal

NO_SUCH_PROCESS_ERRNO = 3

pid = str(os.getpid())
pidfile = "./xterm.pid"
file(pidfile, 'w').write(pid)

def _cast_unicode(s):
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return s

class CommandTermManager(UniqueTermManager):

    def clearCmd(self):
        self.shell_command[:] = []

    def addCmd(self,cmd):
        print(cmd)        
        
        if type(cmd) == list:
            self.shell_command.extend(cmd)
        else:
            self.shell_command.append(cmd)
        print(self.shell_command)

    def get_terminal(self,shell_command, url_component=None):
        if self.max_terminals and len(self.ptys_by_fd) >= self.max_terminals:
            raise terminado.management.MaxTerminalsReached(self.max_terminals)

        term = self.new_terminal()
        self.start_reading(term)
        return term

    def client_disconnected(self, websocket):
        """Send terminal SIGHUP when client disconnects."""
        self.log.info("Websocket closed, sending SIGHUP to terminal.")
        if websocket.terminal:
            if os.name == 'nt':
                websocket.terminal.kill()
                # Immediately call the pty reader to process
                # the eof and free up space
                self.pty_read(websocket.terminal.ptyproc.fd)
                return
            try:
                websocket.terminal.killpg(signal.SIGHUP)
            except OSError as e:
                if e.errno != NO_SUCH_PROCESS_ERRNO:
                    raise 


class SingleTermSocket(TermSocket):

    def open(self,url_component=None):
        """Websocket connection opened.
        
        Call our terminal manager to get a terminal, and connect to it as a
        client.
        """
        # Jupyter has a mixin to ping websockets and keep connections through
        # proxies alive. Call super() to allow that to set up:
        # super(TermSocket, self).open(url_component)
        
        self._logger.info("TermSocket.open: %s", url_component)

        url_component = _cast_unicode(url_component)
        self.term_name = url_component or 'tty'
        file = self.get_query_argument("file")
        print(file)
        self.term_manager.clearCmd()
        self.term_manager.addCmd("./cmd")
        self.term_manager.addCmd("gcc -w /tmp/"+file+".c -o /tmp/"+file+" -lm ")
        self.term_manager.addCmd(" /tmp/"+file)
        self.terminal = self.term_manager.get_terminal(url_component)
        for s in self.terminal.read_buffer:
            self.on_pty_read(s)
        self.terminal.clients.append(self)

        self.send_json_message(["setup", {}])
        self._logger.info("TermSocket.open: Opened %s", self.term_name)

if __name__ == '__main__':
    shell_command=["firejail","--quiet","--seccomp=rmdir,exit","--nosound","--caps.drop=all","--name=code-playground","--rlimit-fsize=5000000","--rlimit-nofile=50","--private=/tmp","--net=none","--blacklist=/usr/bin/man","--blacklist=/bin/ps","--blacklist=/usr/bin/passwd","./try"]
    term_manager = CommandTermManager(shell_command=["./cmd"])
    handlers = [
                 (r"/websocket/(.*)", SingleTermSocket,{'term_manager':term_manager}),
                 (r"/()", tornado.web.StaticFileHandler, {'path':'./C.html'}),
                 (r"/(.*)", tornado.web.StaticFileHandler, {'path':'./.'})
               ]
    app = tornado.web.Application(handlers)
    app.listen(8079)
    try:
        IOLoop.current().start()
    finally:
        term_manager.shutdown()
        os.unlink(pidfile)
