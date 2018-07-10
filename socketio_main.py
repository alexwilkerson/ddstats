import sys
import time
import os
from datetime import datetime
from flask import Flask, request, jsonify, Response, url_for
from flask import render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, and_
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


engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])


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


threshold = 1000
user_list = []
player_dict = {}


@socketio.on('connect', namespace='/ddstats-bot')
def ddstats_bot_connect():
    print('Bot connected.', file=sys.stdout)


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
    global player_dict
    player = Live(player_id=int(player_id), sid=request.sid)
    db.session.add(player)
    db.session.flush()
    db.session.commit()
    emit('user_login', player_id, broadcast=True, namespace='/ddstats-bot')
    if player_id is not -1:
        name = db.session.query(User.username).filter_by(id=player_id).scalar()
        player_dict[str(player_id)] = {}
        player_dict[str(player_id)]["name"] = name
        player_dict[str(player_id)]["game_time"] = 0.0
        player_dict[str(player_id)]["death_type"] = -2 # in menu
        player_dict[str(player_id)]["is_replay"] = False
    # users_in_room = [u for u in user_list if u['player_id'] == player_id]
    # user_count = len(users_in_room)
    # emit('update_user_count', user_count, name_space='/stats', room=request.sid)
    # emit('test_send', {'data': 'test'}, broadcast=True, namespace='/leaderbot')


@socketio.on('disconnect')
def handle_disconnect():
    player_id = db.session.query(Live.player_id).filter_by(sid=request.sid).scalar()
    if player_id is not None:
        if str(player_id) in player_dict:
            del player_dict[str(player_id)]
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
    if player_id is -1:
        return
    global player_dict
    global threshold
    user = db.session.query(User).filter_by(id=player_id).first()
    if str(player_id) in player_dict:
        if player_dict[str(player_id)]['game_time'] < threshold and game_time >= threshold:
            emit('threshold_alert', (user.username, player_id, threshold), namespace='/ddstats-bot', broadcast=True)
    # get user stats, compare to previous and current time
    player_best = db.session.query(User.game_time).filter_by(id=player_id).first()
    if player_best is not None:
        player_best = player_best[0]
        if str(player_id) in player_dict:
            if player_dict[str(player_id)]['game_time'] < player_best and game_time >= player_best:
                emit('player_best', (user.username, player_id, player_best, game_time), namespace='/ddstats-bot', broadcast=True)
    # finally, set game time
    if str(player_id) not in player_dict:
        player_dict[str(player_id)] = {}
    player_dict[str(player_id)]['game_time'] = game_time
    player_dict[str(player_id)]['death_type'] = death_type
    player_dict[str(player_id)]['is_replay'] = is_replay
    emit('receive', (game_time, gems, homing_daggers, enemies_alive,
         enemies_killed, daggers_hit, daggers_fired, level_two, level_three,
         level_four, is_replay, death_type), room=str(player_id),
         namespace='/user_page', include_self=False, broadcast=True)


@socketio.on('game_submitted', namespace='/stats')
def game_submitted(game_id):
    global threshold
    print(game_id, file=sys.stdout)
    game = db.session.query(Game).filter_by(id=game_id).first()
    if game:
        emit('game_received', (game.id, game.game_time, game.death_type, game.gems,
                               game.homing_daggers,
                               game.enemies_alive, game.enemies_killed,
                               game.daggers_hit, game.daggers_fired),
                               namespace='/user_page', room=str(game.player_id), broadcast=True)
        user = db.session.query(User).filter_by(id=game.player_id).first()
        if user is not None:
            if game.game_time >= threshold:
                emit('threshold_submit', (user.username, game.game_time, game.death_type, game_id), namespace='/ddstats-bot', broadcast=True)
            if game.game_time >= user.game_time:
                emit('player_best_submit', (user.username, game.game_time, game.death_type, user.game_time, game_id), namespace='/ddstats-bot', broadcast=True)


@socketio.on('get_status', namespace='/stats')
def get_status(player_id):
    sid = db.session.query(Live.sid).filter_by(player_id=player_id).first()
    if sid is not None:
        emit('get_status', room=sid)
    else:
        emit('status', (-3)) 


###############
# ddstats-bot #
###############

@socketio.on('get_live_users', namespace='/ddstats-bot')
def get_live_users(channel_id):
    with engine.connect() as conn:
        users = conn.execute('select user.username from user inner join live on live.player_id = user.id').fetchall()
        user_list = []
        for user in users:
            user_list.append(user[0])
        if len(users) is 0:
            user_list.append('No users are live.')
        # emit('live_users', (user_list, channel_id))
        emit('live_users', (player_dict, channel_id))


########################################################
#                  end socketio stuff                  #
########################################################


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=7666, debug=True)
