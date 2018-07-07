import sys
import time
import os
from datetime import datetime
from flask import Flask, request, jsonify, Response, url_for
from flask import render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
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
    rank = db.Column(db.Integer, nullable=False)
    game_time = db.Column(db.Float, nullable=False)
    death_type = db.Column(db.Integer, nullable=False)
    gems = db.Column(db.Integer, nullable=False)
    daggers_fired = db.Column(db.Integer, nullable=False)
    daggers_hit = db.Column(db.Integer, nullable=False)
    enemies_killed = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    time_total = db.Column(db.Float, nullable=False)
    deaths_total = db.Column(db.Integer, nullable=False)
    gems_total = db.Column(db.Integer, nullable=False)
    enemies_killed_total = db.Column(db.Integer, nullable=False)
    daggers_fired_total = db.Column(db.Integer, nullable=False)
    daggers_hit_total = db.Column(db.Integer, nullable=False)
    accuracy_total = db.Column(db.Float, nullable=False)


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


user_list = []


@socketio.on('aaa')
def received_aaa():
    print('aaa receieved', file=sys.stdout)
    emit('on_aaa_response')


@socketio.on('connect', namespace='/ddstats-bot')
def ddstats_bot_connect():
    print('Bot connected.', file=sys.stdout)
    time.sleep(2)
    emit('test_connection', 'connected')


@socketio.on('connect', namespace='/test')
def test_connect():
    print('This standard output', file=sys.stdout)
    emit('my response', {'data': 'Connected'}, broadcast=True)
    emit('welcome', broadcast=True)


@socketio.on('disconnect', namespace='/user_page')
def user_page_disconnect():
    global user_list
    user = next((u for u in user_list if u['sid'] == request.sid), None)
    user_list = [u for u in user_list if u['sid'] != request.sid]
    if user is not None:
        player_id = user['player_id']
        users_in_room = [u for u in user_list if u['player_id'] == player_id]
        user_count = len(users_in_room)
        emit('update_user_count', user_count, room=player_id)

        # player = db.session.query(Live).filter_by(player_id=player_id).first()
        # if player is not None:
            # emit('update_user_count', user_count, name_space='/stats', room=player.sid)
        # print(str(len(users_in_room)) + ' user(s) in room ' + str(player_id), file=sys.stdout)


# @socketio.on('my event', namespace='/admin')
# def add_to_live():
    # print(player_id, file=sys.stdout)


@socketio.on('join', namespace='/user_page')
def user_page_join(player_id):
    global user_list
    join_room(player_id)
    user_list.append({'sid': request.sid, 'player_id': player_id})
    # print(player_id + ': someone joined the room.', file=sys.stdout)
    users_in_room = [u for u in user_list if u['player_id'] == player_id]
    user_count = len(users_in_room)
    emit('update_user_count', user_count, room=player_id)

    # player = db.session.query(Live).filter_by(player_id=player_id).first()
    # if player is not None:
        # emit('update_user_count', user_count, name_space='/stats', room=player.sid)


@socketio.on('login')
def login(player_id):
    player = Live(player_id=int(player_id), sid=request.sid)
    db.session.add(player)
    db.session.flush()
    db.session.commit()
    emit('user_login', player_id, broadcast=True, namespace='/ddstats-bot')
    # users_in_room = [u for u in user_list if u['player_id'] == player_id]
    # user_count = len(users_in_room)
    # emit('update_user_count', user_count, name_space='/stats', room=request.sid)
    # emit('test_send', {'data': 'test'}, broadcast=True, namespace='/leaderbot')


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
         level_four, is_replay, death_type), room=str(player_id),
         namespace='/user_page', include_self=False, broadcast=True)


@socketio.on('game_submitted', namespace='/stats')
def game_submitted(game_id):
    print(game_id, file=sys.stdout)
    game = db.session.query(Game).filter_by(id=game_id).first()
    if game:
        emit('game_received', (game.id, game.game_time, game.death_type, game.gems,
                               game.homing_daggers,
                               game.enemies_alive, game.enemies_killed,
                               game.daggers_hit, game.daggers_fired),
                               namespace='/user_page', room=str(game.player_id), broadcast=True)


@socketio.on('get_status', namespace='/stats')
def get_status(player_id):
    sid = db.session.query(Live.sid).filter_by(player_id=player_id).first()
    if sid is not None:
        emit('get_status', room=sid)
    else:
        emit('status', (-3)) 


########################################################
#                  end socketio stuff                  #
########################################################


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=7666, debug=True)
