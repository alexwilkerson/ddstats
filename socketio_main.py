import sys
import os
from datetime import datetime
from flask import Flask, request, jsonify, Response, url_for
from flask import render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from flask_bower import Bower
from flask_cors import CORS
from time_ago import time_ago

app = Flask(__name__)
app.url_map.strict_slashes = False
Bower(app)
CORS(app)

socketio = SocketIO(app, async_mode='gevent_uwsgi')


########################################################
#                    socketio stuff                    #
########################################################

@socketio.on('connect', namespace='/test')
def test_connect():
    print('This standard output', file=sys.stdout)
    emit('my response', {'data': 'Connected'}, broadcast=True)

@socketio.on('my event', namespace='/admin')
def add_to_live():
    print("working", file=sys.stdout)
    # print(player_id, file=sys.stdout)

@socketio.on('message')
def handle_message(message):
    print('received message: ' + message, file=sys.stdout)

########################################################
#                  end socketio stuff                  #
########################################################


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=7666, debug=True)
