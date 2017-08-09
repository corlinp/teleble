import json, markdown
import tornado
from tornado import escape, ioloop, web, websocket, template


class GetUpdateUserHandler(tornado.web.RequestHandler):
    def get(self, user_id):
        data = user_data_handler.get_user(user_id)
        if data is None:
            self.send_error(404)
            return
        self.write(json.dumps(data))

    def post(self, user_id):
        data = tornado.escape.json_decode(self.request.body)
        user_id = user_data_handler.store_user(data, user_id=user_id)
        self.write({'user_id': user_id})


def make_app():
    return tornado.web.Application([
        #(r"/", MainHandler),
        (r'/users', PostUserHandler),
        (r'/users/([A-Za-z0-9]+)', GetUpdateUserHandler),
        (r'/pools/create', PostUserPoolsHandler),
        (r'/pools/active/([A-Za-z0-9]+)', GetActiveUserPoolsHandler),
        (r'/pools/archive/([A-Za-z0-9]+)', GetArchiveUserPoolsHandler),
        (r'/doc(s?)', DocHandler),
        (r'/pools/ws', EchoWebSocket),
    ])


if __name__ == "__main__":
    user_pool_handler.start_pool_timer()
    app = make_app()
    app.listen(80)
    tornado.ioloop.IOLoop.current().start()