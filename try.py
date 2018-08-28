import terminado
import tornado
import os
from tornado.ioloop import IOLoop

class WebmuxTermManager(terminado.SingleTermManager):
    def get_terminal(self, port_number):
        self.shell_command = ["bash"]
        term = self.new_terminal()
        self.start_reading(term)
        return term

class TerminalPageHandler(tornado.web.RequestHandler):
    def get_host(self, port_number):
        pass

    def get(self, port_number):
        return self.render("term.html", static=self.static_url, ws_url_path="/_websocket/"+port_number, hostname=self.get_host(port_number))

if __name__ == "__main__":

    TEMPLATE_DIR = "./"
    STATIC_DIR = "./"
    term_manager = WebmuxTermManager(shell_command=('bash'))
    handlers = [
        (r"/_websocket/(\w+)", terminado.TermSocket, {'term_manager': term_manager}),
        (r"/shell/([\d]+)/?", TerminalPageHandler),
        (r"/webmux_static/(.*)", tornado.web.StaticFileHandler, {'path':os.path.join(TEMPLATE_DIR,"webmux_static")}),
    ]
    application = tornado.web.Application(handlers, static_path=STATIC_DIR,template_path=TEMPLATE_DIR,term_manager=term_manager,debug=True)
    application.listen(8888)


    try:
        IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info("\nShuttiing down")
    finally:
        term_manager.shutdown()
        IOLoop.current().close()