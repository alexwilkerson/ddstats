import os
import math
import requests
from datetime import datetime
from flask import Flask, request, jsonify, Response, url_for
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bower import Bower

app = Flask(__name__)
Bower(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') \
    or 'sqlite:////Users/alex/code/ddstats/app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

db = SQLAlchemy(app)


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


@app.route('/game_log/<game_number>')
def game_log(game_number):
    r = requests.get('http://ddstats.com/api/game/{}/all'.format(game_number))
    data = r.json()
    gems_list = []
    homing_daggers_list = []
    accuracy_list = []
    enemies_killed_list = []
    enemies_alive_list = []
    for row in data["state_list"]:
        gems_list.append(row["gems"])
        homing_daggers_list.append(row["homing_daggers"])
        if row["daggers_fired"] is 0:
            accuracy_list.append(0)
        else:
            accuracy_list.append(round((row["daggers_hit"]/row["daggers_fired"])*100, 2))
        enemies_killed_list.append(row["enemies_killed"])
        enemies_alive_list.append(row["enemies_alive"])
    return render_template('game_log.html',
                           gems_list=gems_list,
                           homing_daggers_list=homing_daggers_list,
                           accuracy_list=accuracy_list,
                           enemies_killed_list=enemies_killed_list,
                           enemies_alive_list=enemies_alive_list)


@app.route('/homing_log/<game_number>/')
def homing_log(game_number):
    r = requests.get('http://ddstats.com/api/game/{}/homing_daggers'.format(game_number))
    data = r.json()
    homing_daggers_list = []
    for row in data["homing_daggers_list"]:
        homing_daggers_list.append(row["homing_daggers"])
    return render_template('homing_log.html', homing_daggers_list=homing_daggers_list)


@app.route('/highcharts_test/')
def highcharts_test():
    return render_template('highcharts_test.html')


@app.route('/chartist_test/')
def chartist_test():
    return render_template('chartist_test.html')


@app.route('/classic_homing_log/<game_number>', methods=['GET'])
def get_classic_homing(game_number):
    r = requests.get('http://uncorrected.com:5666/api/game/{}/homing_daggers'.format(game_number))
    data = r.json()
    text = ""
    last = 0
    for row in data["homing_daggers_list"]:
        if int(row["game_time"]) >= 10 and int(row["game_time"]) % 10 is 0:
            text += str(int(row["game_time"])-10) + "s:\t" +\
                    str(row["homing_daggers"]) + "\t|" +\
                    ("~" * math.ceil(row["homing_daggers"]/10)) + "\n"
            last = int(row["game_time"])
    text += str(last) + "s:\t" + str(data["homing_daggers_list"][-1]["homing_daggers"]) +\
        "\t|" + ("~" * math.ceil(data["homing_daggers_list"][-1]["homing_daggers"]/10))
    return Response(text, mimetype='text/plain')


@app.route('/api/user', methods=['GET'])
def get_all_users():

    query = db.session.query(Game.player_id.distinct().label("player_id"))
    user_list = [row.player_id for row in query.all()]
    users = {"user_list": user_list}

    if len(users) is 0:
        return jsonify({'message': 'No users found.'})
    else:
        return jsonify(users)


@app.route('/api/user/<user_id>', methods=['GET'])
def get_all_games_by_user(user_id):

    query = db.session.query(Game).filter_by(player_id=user_id)
    game_id_list = [row.id for row in query.all()]
    game_ids = {"player_id": user_id, "game_id_list": game_id_list}

    if len(game_ids) == 0:
        return jsonify({'message': 'No games found.'})
    else:
        return jsonify(game_ids)


@app.route('/api/game/<game_id>', methods=['GET'])
def get_game_stats(game_id):

    query = db.session.query(Game).filter_by(id=game_id)
    game = query.first()

    if game is None:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify({"game_id": game.id, "player_id": game.player_id,
                        "game_time": game.game_time,
                        "gems": game.gems, "homing_daggers": game.homing_daggers,
                        "daggers_hit": game.daggers_hit,
                        "daggers_fired": game.daggers_fired,
                        "enemies_alive": game.enemies_alive,
                        "enemies_killed": game.enemies_killed})


@app.route('/api/game/<game_number>/all', methods=['GET'])
def get_all_game_states(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    state_list = [row.serialize for row in query.all()]
    states = {"state_list": state_list}

    if states is None:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(states)


@app.route('/api/game/<game_number>/game_time', methods=['GET'])
def get_game_time(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    game_time_list = [row.game_time for row in query.all()]
    game_time = {"game_time_list": game_time_list}

    if len(game_time) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(game_time)


@app.route('/api/game', methods=['GET'])
def get_all_games():

    query = db.session.query(Game.id.label("id"))
    games = [row.id for row in query.all()]
    game_id_list = {"game_id_list": games}

    if len(games) is 0:
        return jsonify({'message': 'No games found.'})
    else:
        return jsonify(game_id_list)


@app.route('/api/game/<game_number>/gems', methods=['GET'])
def get_game_gems(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    gems_list = []
    for row in query.all():
        gems_list.append({"game_time": round(row.game_time, 4),
                          "gems": row.gems})

    gems = {"gems_list": gems_list}

    if len(gems_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(gems)


@app.route('/api/game/<game_number>/homing_daggers', methods=['GET'])
def get_game_homing_daggers(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    homing_daggers_list = []
    for row in query.all():
        homing_daggers_list.append({"game_time": round(row.game_time, 4),
                                    "homing_daggers": row.homing_daggers})

    homing_daggers = {"homing_daggers_list": homing_daggers_list}

    if len(homing_daggers_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(homing_daggers)


@app.route('/api/game/<game_number>/daggers_hit', methods=['GET'])
def get_game_daggers_hit(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    daggers_hit_list = []
    for row in query.all():
        daggers_hit_list.append({"game_time": round(row.game_time, 4),
                                 "daggers_hit": row.daggers_hit})

    daggers_hit = {"daggers_hit_list": daggers_hit_list}

    if len(daggers_hit_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(daggers_hit)


@app.route('/api/game/<game_number>/daggers_fired', methods=['GET'])
def get_game_daggers_fired(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    daggers_fired_list = []
    for row in query.all():
        daggers_fired_list.append({"game_time": round(row.game_time, 4),
                                   "daggers_fired": row.daggers_fired})

    daggers_fired = {"daggers_fired_list": daggers_fired_list}

    if len(daggers_fired_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(daggers_fired)


@app.route('/api/game/<game_number>/enemies_killed', methods=['GET'])
def get_game_enemies_killed(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    enemies_killed_list = []
    for row in query.all():
        enemies_killed_list.append({"game_time": round(row.game_time, 4),
                                    "enemies_killed": row.enemies_killed})

    enemies_killed = {"enemies_killed_list": enemies_killed_list}

    if len(enemies_killed_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(enemies_killed)


@app.route('/api/game/<game_number>/enemies_alive', methods=['GET'])
def get_game_enemies_alive(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    enemies_alive_list = []
    for row in query.all():
        enemies_alive_list.append({"game_time": round(row.game_time, 4),
                                   "enemies_alive": row.enemies_alive})

    enemies_alive = {"enemies_alive_list": enemies_alive_list}

    if len(enemies_alive_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(enemies_alive)


@app.route('/api/submit_game', methods=['POST'])
def create_game():
    data = request.get_json()

    new_game = Game(player_id=data['playerID'], granularity=data['granularity'],
                    game_time=data['inGameTimer'], death_type=data['deathType'],
                    gems=data['gems'], homing_daggers=data['homingDaggers'],
                    daggers_fired=data['daggersFired'], daggers_hit=data['daggersHit'],
                    enemies_alive=data['enemiesAlive'], enemies_killed=data['enemiesKilled'])
    db.session.add(new_game)
    db.session.commit()
    db.session.refresh(new_game)

    for i in range(len(data["inGameTimerVector"])):
        new_state = State(game_id=new_game.id,
                          game_time=data["inGameTimerVector"][i],
                          gems=data["gemsVector"][i],
                          homing_daggers=data["homingDaggersVector"][i],
                          daggers_hit=data["daggersHitVector"][i],
                          daggers_fired=data["daggersFiredVector"][i],
                          enemies_alive=data["enemiesAliveVector"][i],
                          enemies_killed=data["enemiesKilledVector"][i])
        db.session.add(new_state)
    db.session.commit()

    return jsonify({'message': 'Game submitted.', 'game_id': new_game.id})


@app.route('/api/get_motd', methods=['POST'])
def get_motd():
    # data = request.get_json()

    return jsonify({'motd': 'Hi, thanks for using this.'})


@app.route('/')
def index():
    content = get_file('dagger.txt')
    return Response(content, mimetype="text/plain")


def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return str(exc)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5666)
