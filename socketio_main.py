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

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') \
    or 'sqlite:////Users/alex/code/ddstats/app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

socketio = SocketIO(app, async_mode='gevent_uwsgi')


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    player_id = db.Column(db.Integer, nullable=False)
    granularity = db.Column(db.Integer, nullable=False)
    game_time = db.Column(db.Float, nullable=False)
    death_type = db.Column(db.Integer, nullable=False)
    gems = db.Column(db.Integer, nullable=False)
    homing_daggers = db.Column(db.Integer, nullable=False)
    daggers_fired = db.Column(db.Integer, nullable=False)
    daggers_hit = db.Column(db.Integer, nullable=False)
    enemies_alive = db.Column(db.Integer, nullable=False)
    enemies_killed = db.Column(db.Integer, nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    replay_player_id = db.Column(db.Integer, default=0, nullable=False)
    survival_hash = db.Column(db.String(32))
    version = db.Column(db.String(16))
    level_two_time = db.Column(db.Float, default=0.0, nullable=False)
    level_three_time = db.Column(db.Float, default=0.0, nullable=False)
    level_four_time = db.Column(db.Float, default=0.0, nullable=False)
    homing_daggers_max_time = db.Column(db.Float, default=0.0, nullable=False)
    enemies_alive_max_time = db.Column(db.Float, default=0.0, nullable=False)
    homing_daggers_max = db.Column(db.Integer, default=0, nullable=False)
    enemies_alive_max = db.Column(db.Integer, default=0, nullable=False)


class State(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    game_time = db.Column(db.Float, nullable=False)
    gems = db.Column(db.Integer, nullable=False)
    homing_daggers = db.Column(db.Integer, nullable=False)
    daggers_hit = db.Column(db.Integer, nullable=False)
    daggers_fired = db.Column(db.Integer, nullable=False)
    enemies_alive = db.Column(db.Integer, nullable=False)
    enemies_killed = db.Column(db.Integer, nullable=False)

    @property
    def serialize(self):
        return {
                'game_time': self.game_time,
                'gems': self.gems,
                'homing_daggers': self.homing_daggers,
                'daggers_hit': self.daggers_hit,
                'daggers_fired': self.daggers_fired,
                'enemies_alive': self.enemies_alive,
                'enemies_killed': self.enemies_killed
               }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    username = db.Column(db.String(128), index=True, nullable=False)


class Live(db.Model):
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    sid = db.Column(db.String(32))


@app.before_first_request
def clear_live_table():
    db.session.query(Live).delete()
    db.session.commit()


########################################################
#                    socketio stuff                    #
########################################################

@socketio.on('connect', namespace='/test')
def test_connect():
    print('This standard output', file=sys.stdout)
    emit('my response', {'data': 'Connected'}, broadcast=True)


# @socketio.on('my event', namespace='/admin')
# def add_to_live():
    # print(player_id, file=sys.stdout)


@socketio.on('login')
def login(player_id):
    player = Live(player_id=int(player_id), sid=request.sid)
    db.session.add(player)
    db.session.flush()
    db.session.commit()


@socketio.on('disconnect')
def handle_disconnect():
    exists = db.session.query(Live.player_id).filter_by(sid=request.sid).scalar() is not None
    if exists:
        Live.query.filter_by(sid=request.sid).delete()
        db.session.commit()


@socketio.on('message')
def handle_message(message):
    print('received message: ' + message, file=sys.stdout)


@socketio.on('submit', namespace='/stats')
def receive_stats(player_id, game_time, gems, homing_daggers,
                  enemies_alive, enemies_killed, daggers_hit,
                  daggers_fired, level_two, level_three, level_four,
                  is_replay, death_type):
    emit('receive', (game_time, gems, homing_daggers, enemies_alive,
         enemies_killed, daggers_hit, daggers_fired, level_two, level_three,
         level_four, is_replay, death_type), namespace='/'+str(player_id),
         include_self=False, broadcast=True)


########################################################
#                  end socketio stuff                  #
########################################################


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=7666, debug=True)
