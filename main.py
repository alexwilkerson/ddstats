import os
import sys
import math
import requests
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response, url_for
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_
from flask_bower import Bower
from flask_cors import CORS
from byte_converters import to_int_16, to_int_32, to_uint_64
from time_ago import time_ago

# latest release
current_version = "0.3.1"
# lowest release number that is valid
valid_version = "0.1.9"

death_types = ["FALLEN", "SWARMED", "IMPALED", "GORED", "INFESTED", "OPENED", "PURGED",
               "DESECRATED", "SACRIFICED", "EVISCERATED", "ANNIHILATED", "INTOXICATED",
               "ENVENMONATED", "INCARNATED", "DISCARNATED", "BARBED"]

app = Flask(__name__)
app.url_map.strict_slashes = False
Bower(app)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') \
    or 'sqlite:////Users/alex/code/ddstats/app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

# jinja filters
app.jinja_env.filters['time_ago'] = time_ago

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


class Spawnset(db.Model):
    survival_hash = db.Column(db.String(32), primary_key=True, nullable=False)
    spawnset_name = db.Column(db.String(), nullable=False)


@app.route('/about')
def about_page():
    return render_template('about.html')


@app.route('/users')
def users_page():
    users = User.query.order_by(User.rank).all()
    live_users = get_live_users()
    # users = db.session.query(Game.player_id).distinct().all()
    # users_list = []
    # for user in users:
    #     r = requests.get('http://ddstats.com/api/get_scores?user={}'.format(user.player_id))
    #     user_data = r.json()
    #     users_list.append(user_data["player_name"])

    # print(users_list)
    return render_template('users.html', users=users, live_users=live_users)


@app.route('/games/', defaults={'page_num': 1})
@app.route('/games/<int:page_num>')
def games_page(page_num):
    games = Game.query.join(User, Game.player_id == User.id).\
            order_by(Game.id.desc()).\
            add_columns(Game.id, Game.player_id,
                        Game.game_time, Game.homing_daggers,
                        Game.gems,
                        Game.enemies_alive,
                        Game.enemies_killed,
                        Game.death_type,
                        Game.daggers_fired,
                        Game.daggers_hit,
                        Game.time_stamp,
                        Game.replay_player_id,
                        User.username).paginate(per_page=10,
                                                page=page_num,
                                                error_out=True)
    # this is probably not needed
    if games is None:
        return('No games found.')

    live_users = get_live_users()
    return render_template('games.html', games=games, death_types=death_types, live_users=live_users)


@app.route('/user/<int:user_id>', defaults={'page_num': 1})
@app.route('/user/<int:user_id>/<int:page_num>')
def user_page(user_id, page_num):
    games = Game.query.filter(((Game.player_id==user_id) & (Game.replay_player_id==0)) | (Game.replay_player_id==user_id)).order_by(Game.id.desc()).paginate(per_page=10, page=page_num, error_out=True)
    if games is None:
        return('No user found with that ID')

    existing_player = User.query.filter_by(id=user_id).first()
    if existing_player is not None:
        r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(user_id))
        user_data = r.json()
        existing_player.username=user_data['player_name']
        existing_player.rank=user_data['rank']
        existing_player.game_time=user_data['time']
        existing_player.death_type=user_data['death_type']
        existing_player.gems=user_data['gems']
        existing_player.daggers_fired=user_data['shots_fired']
        existing_player.daggers_hit=user_data['shots_hit']
        existing_player.enemies_killed=user_data['kills']
        existing_player.accuracy=user_data['accuracy']
        existing_player.time_total=user_data['time_total']
        existing_player.deaths_total=user_data['deaths_total']
        existing_player.gems_total=user_data['gems_total']
        existing_player.enemies_killed_total=user_data['kills_total']
        existing_player.daggers_fired_total=user_data['shots_fired_total']
        existing_player.daggers_hit_total=user_data['shots_hit_total']
        existing_player.accuracy_total=user_data['accuracy_total']
        db.session.commit()

    return render_template('user.html', user_data=user_data, user_id=user_id, games=games, death_types=death_types)


@app.route('/game_log/<game_number>')
def game_log(game_number):
    r = requests.get('http://ddstats.com/api/game/{}'.format(game_number))
    game_data = r.json()
    player_id = game_data["player_id"]
    submitter_id = 0
    submitter_name = ""
    if game_data["replay_player_id"] is not 0:
        submitter_id = player_id
        player_id = game_data["replay_player_id"]
        r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(submitter_id))
        submitter_data = r.json()
        submitter_name = submitter_data["player_name"]
    r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(player_id))
    user_data = r.json()
    if "player_name" not in user_data:
        user_data["player_name"] = "UNKNOWN"

    if game_data["daggers_fired"] is 0:
        accuracy = 0.0
    else:
        accuracy = round(game_data["daggers_hit"] / game_data["daggers_fired"] * 100, 2)

    # used to fix rounding error on game_time
    dd_high_score_str = str(user_data["time"])
    dd_high_score = float(dd_high_score_str[:dd_high_score_str.find('.')+4])
    game_time_str = str(game_data["game_time"])
    game_time = float(game_time_str[:game_time_str.find('.')+4])
    current_high_score = dd_high_score == game_time
    # game_time_list = game_time_list[:-1]
    # game_time_list.append(round(game_data["game_time"], 4))
    live_users = get_live_users()
    spawnset = db.session.query(Spawnset.spawnset_name).filter(Spawnset.survival_hash==game_data["survival_hash"]).first()
    if spawnset is None:
        spawnset_name = "UNKNOWN"
    else:
        spawnset_name = spawnset.spawnset_name

    return render_template('game_log.html',
                           live_users=live_users,
                           player_name=user_data["player_name"],
                           current_high_score=current_high_score,
                           dd_high_score=user_data["time"],
                           player_id=player_id,
                           game_number=game_number,
                           game_time=float("{0:.4f}".format(game_data["game_time"])),
                           # game_time="{}".format(game_data["game_time"]),
                           death_type=game_data["death_type"],
                           gems="{:,}".format(game_data["gems"]),
                           homing_daggers="{:,}".format(game_data["homing_daggers"]),
                           homing_daggers_max=game_data["homing_daggers_max"],
                           homing_daggers_max_time=game_data["homing_daggers_max_time"],
                           accuracy=accuracy,
                           enemies_alive="{:,}".format(game_data["enemies_alive"]),
                           enemies_alive_max=game_data["enemies_alive_max"],
                           enemies_alive_max_time=game_data["enemies_alive_max_time"],
                           daggers_hit="{:,}".format(game_data["daggers_hit"]),
                           daggers_fired="{:,}".format(game_data["daggers_fired"]),
                           enemies_killed="{:,}".format(game_data["enemies_killed"]),
                           # game_time_list=game_time_list,
                           # gems_list=gems_list,
                           # homing_daggers_list=homing_daggers_list,
                           # max_homing=max(homing_daggers_list),
                           # max_homing_time=homing_daggers_list.index(max(homing_daggers_list)),
                           # accuracy_list=accuracy_list,
                           # enemies_killed_list=enemies_killed_list,
                           # enemies_alive_list=enemies_alive_list,
                           level_two_time=game_data["level_two_time"],
                           level_three_time=game_data["level_three_time"],
                           level_four_time=game_data["level_four_time"],
                           time_stamp=time_ago(game_data["time_stamp"]),
                           submitter_id=submitter_id,
                           submitter_name=submitter_name,
                           spawnset_name=spawnset_name)


@app.route('/api/dataset/<game_number>')
def highchart_dataset(game_number):
    r = requests.get('http://ddstats.com/api/game/{}/all'.format(game_number))
    data = r.json()
    r = requests.get('http://ddstats.com/api/game/{}'.format(game_number))
    game_data = r.json()
    if "message" in data:
        return data["message"]
    game_time_list = []
    gems_list = []
    homing_daggers_list = []
    accuracy_list = []
    enemies_killed_list = []
    enemies_alive_list = []
    for row in data["state_list"]:
        game_time_list.append(math.floor(row["game_time"]))
        gems_list.append(row["gems"])
        homing_daggers_list.append(row["homing_daggers"])
        if row["daggers_fired"] is 0:
            accuracy_list.append(0)
        else:
            accuracy_list.append(round((row["daggers_hit"]/row["daggers_fired"])*100, 2))
        enemies_killed_list.append(row["enemies_killed"])
        enemies_alive_list.append(row["enemies_alive"])
    r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(game_data["player_id"]))
    user_data = r.json()

    if game_data["daggers_fired"] is 0:
        accuracy = 0.0
    else:
        accuracy = round(game_data["daggers_hit"] / game_data["daggers_fired"] * 100, 2)

    game_time_list = game_time_list[:-1]
    game_time_list.append(round(game_data["game_time"], 4))

    datasets = []
    if (sum(gems_list) is not 0):
        datasets.append({'name': 'Gems',
                         'data': gems_list,
                         'unit': 'gems',
                         'type': 'area',
                         'valueDecimals': 0})
    if (sum(homing_daggers_list) is not 0):
        datasets.append({'name': 'Homing Daggers',
                         'data': homing_daggers_list,
                         'unit': 'homing daggers',
                         'type': 'area',
                         'valueDecimals': 0})
    if (sum(accuracy_list) is not 0.0):
        datasets.append({'name': 'Accuracy',
                         'data': accuracy_list,
                         'unit': '%',
                         'type': 'area',
                         'valueDecimals': 1})
    if (sum(enemies_alive_list) is not 0):
        datasets.append({'name': 'Enemies Alive',
                         'data': enemies_alive_list,
                         'unit': 'enemies alive',
                         'type': 'area',
                         'valueDecimals': 0})
    if (sum(enemies_killed_list) is not 0):
        datasets.append({'name': 'Enemies Killed',
                         'data': enemies_killed_list,
                         'unit': 'enemies killed',
                         'type': 'area',
                         'valueDecimals': 0})

    dataset = {'xData': game_time_list,
               'datasets': datasets}
    return jsonify(dataset)


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


@app.route('/releases')
def releases():
    with open('releases.json') as f:
        data = json.load(f)
        return render_template('releases.html', releases=data)


@app.route('/classic_homing_log/<int:game_number>.txt', methods=['GET'])
def get_classic_homing(game_number):
    r = requests.get('https://ddstats.com/api/game/{}'.format(game_number))
    data = r.json()
    text =  "*** CLASSIC HOMING LOG ***\n\n"
    text += "Time: {}\t\tDeath: {}\n".format(round(data["game_time"], 4), data["death_type"])
    if data["daggers_fired"] is 0:
        accuracy = 0.0
    else:
        accuracy = round(data["daggers_hit"] / data["daggers_fired"] * 100, 2)
    text += "Gems: {}\t\tAccuracy: {}%\n".format(data["gems"], accuracy)
    text += "Homing Daggers: {}\tDaggers Hit: {}\n".format(data["homing_daggers"],
                                                             data["daggers_hit"])
    text += "Enemies Alive: {}\tDaggers Fired: {}\n".format(data["enemies_alive"],
                                                              data["daggers_fired"])
    text += "Enemies Killed: {}\t{}\n\n".format(data["enemies_killed"],
                                                  data["time_stamp"])

    r = requests.get('https://ddstats.com/api/game/{}/homing_daggers'.format(game_number))
    data = r.json()
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
    # query = db.session.query(Game, Spawnset).join(Spawnset).filter_by(id=game_id)
    game = query.first()

    if game is None:
        return jsonify({'message': 'Game not found.'})
    else:
        if game.death_type is -1:
            death_type = "RESTART"
        else:
            death_type = death_types[game.death_type]
        return jsonify({"game_id": game.id, "player_id": game.player_id,
                        "game_time": game.game_time,
                        "death_type": death_type,
                        "gems": game.gems, "homing_daggers": game.homing_daggers,
                        "homing_daggers_max": game.homing_daggers_max,
                        "homing_daggers_max_time": game.homing_daggers_max_time,
                        "daggers_hit": game.daggers_hit,
                        "daggers_fired": game.daggers_fired,
                        "enemies_alive": game.enemies_alive,
                        "enemies_alive_max": game.enemies_alive_max,
                        "enemies_alive_max_time": game.enemies_alive_max_time,
                        "enemies_killed": game.enemies_killed,
                        "level_two_time": game.level_two_time,
                        "level_three_time": game.level_three_time,
                        "level_four_time": game.level_four_time,
                        "time_stamp": game.time_stamp,
                        "replay_player_id": game.replay_player_id,
                        "survival_hash": game.survival_hash,
                        "version": game.version})


@app.route('/api/game/<game_number>/all', methods=['GET'])
def get_all_game_states(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    state_list = [row.serialize for row in query.all()]
    states = {"state_list": state_list}

    if len(state_list) is 0:
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

    if data['playerID'] == -1:
        return jsonify({'message': 'Some kind of error occurred.'}), 400

    r = requests.get('http://ddstats.com/api/refresh_user_by_id/{}'.format(data['playerID']))
    user_data = r.json()

    if 'playerName' in data:
        existing_player = User.query.filter_by(id=data['playerID']).first()
        if existing_player is None:
            r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(data['playerID']))
            user_data = r.json()
            new_player = User(id=data['playerID'], username=data['playerName'],
                              rank=user_data['rank'],
                              game_time=user_data['time'],
                              death_type=user_data['death_type'],
                              gems=user_data['gems'],
                              daggers_fired=user_data['shots_fired'],
                              daggers_hit=user_data['shots_hit'],
                              enemies_killed=user_data['kills'],
                              accuracy=user_data['accuracy'],
                              time_total=user_data['time_total'],
                              deaths_total=user_data['deaths_total'],
                              gems_total=user_data['gems_total'],
                              enemies_killed_total=user_data['kills_total'],
                              daggers_fired_total=user_data['shots_fired_total'],
                              daggers_hit_total=user_data['shots_hit_total'],
                              accuracy_total=user_data['accuracy_total'])
            db.session.add(new_player)
        else:
            existing_player.username = data['playerName']
        db.session.commit()

    # version and data added in same release, so this replaces the default if they
    # are using an older version
    if 'version' not in data:
        # v3 survival hash
        submit_version = ""
    else:
        submit_version = data["version"]

    if data["replayPlayerID"] > 0:
        existing = db.session.query(Game.id).filter(and_(
                                                 # remove this to disable multiple users rec
                                                 # same game...for now it is fine.
                                                 Game.player_id == data["playerID"],
                                                 # Game.replay_player_id == data["replayPlayerID"],
                                                 Game.game_time == data["inGameTimer"],
                                                 Game.death_type == data["deathType"],
                                                 Game.gems == data["gems"],
                                                 Game.homing_daggers == data["homingDaggers"],
                                                 Game.daggers_fired == data["daggersFired"],
                                                 Game.daggers_hit == data["daggersHit"],
                                                 Game.enemies_alive == data["enemiesAlive"],
                                                 Game.enemies_killed == data["enemiesKilled"],
                                                 Game.version == data["version"]
                                                )).filter(or_(Game.replay_player_id == 0,
                                                              Game.replay_player_id == data["replayPlayerID"])).first()
        if existing is not None:
            return jsonify({'message': 'Replay already recorded.', 'game_id': existing.id})

    if 'survivalHash' not in data:
        survival_hash = '5ff43e37d0f85e068caab5457305754e'
    else:
        survival_hash = data["survivalHash"]

    new_game = Game(player_id=data['playerID'], granularity=data['granularity'],
                    game_time=data['inGameTimer'], death_type=data['deathType'],
                    gems=data['gems'], homing_daggers=data['homingDaggers'],
                    daggers_fired=data['daggersFired'], daggers_hit=data['daggersHit'],
                    enemies_alive=data['enemiesAlive'], enemies_killed=data['enemiesKilled'],
                    replay_player_id=data["replayPlayerID"], version=submit_version,
                    survival_hash=survival_hash)

    # if levelTwoTime is set, then we know the rest of these var are set also
    if 'levelTwoTime' in data:
        new_game.level_two_time = data["levelTwoTime"]
        new_game.level_three_time = data["levelThreeTime"]
        new_game.level_four_time = data["levelFourTime"]
        new_game.homing_daggers_max_time = data["homingDaggersMaxTime"]
        new_game.enemies_alive_max_time = data["enemiesAliveMaxTime"]
        new_game.homing_daggers_max = data["homingDaggersMax"]
        new_game.enemies_alive_max = data["enemiesAliveMax"]

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

    motd = ""
    with open('motd.json') as f:
        data = json.load(f)
        motd = data["motd"]

    update_available = True
    valid = False

    data = request.get_json()

    sv = data["version"].split('.')
    scv = current_version.split('.')
    svv = valid_version.split('.')

    if (int(sv[0]) > int(scv[0])):
        update_available = False
    elif (int(sv[0]) == int(scv[0])) and (int(sv[1]) > int(scv[1])):
        update_available = False
    elif (int(sv[1]) == int(scv[1])) and (int(sv[2]) >= int(scv[2])):
        update_available = False

    if (int(sv[0]) > int(svv[0])):
        valid = True
    elif (int(sv[0]) == int(svv[0])) and (int(sv[1]) > int(svv[1])):
        valid = True
    elif (int(sv[1]) == int(svv[1])) and (int(sv[2]) >= int(svv[2])):
        valid = True

    return jsonify({'motd': motd,
                    'valid_version': valid,
                    'update_available': update_available})


@app.route('/')
def index():
    return render_template('index.html')
    # content = get_file('dagger.txt')
    # return Response(content, mimetype="text/plain")


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

def get_live_users():
    query = db.session.query(Live.player_id.label("player_id"))
    return [row.player_id for row in query.all()]


@app.template_filter('get_username')
def get_username(user_id):
    q = User.query.filter_by(id=user_id).first()
    if q:
        return q.username
    r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(user_id))
    user_data = r.json()
    if "player_name" not in user_data:
        return "UNKNOWN"
    return user_data["player_name"]


@app.template_filter()
def numberFormat(value, digits=0):
    if isinstance(value, int):
        return format(int(value), ',d')
    elif isinstance(value, float):
        return format(float(value), ',.' + str(digits) + 'f')


########################################################
#         devil dagger's backend api conversion        #
########################################################

class Leaderboard(object):
    leaderboard_data = ""

    deaths_global = 0
    kills_global = 0
    time_global = 0
    gems_global = 0
    shots_hit_global = 0
    shots_fired_global = 0
    players = 0
    entries = []

    def __init__(self, offset, user=None):
        if user is None:
            self.update(offset)

    def update(self, offset=None):
        if offset is None:
            offset = '0'

        post_values = dict(user='0', level='survival', offset=offset)

        req = requests.post("http://dd.hasmodai.com/backend16/get_scores.php", post_values)
        self.leaderboard_data = req.content

        self.deaths_global      = to_uint_64(self.leaderboard_data, 11)
        self.kills_global       = to_uint_64(self.leaderboard_data, 19)
        self.time_global        = to_uint_64(self.leaderboard_data, 35) / 10000
        self.gems_global        = to_uint_64(self.leaderboard_data, 43)
        self.shots_hit_global   = to_uint_64(self.leaderboard_data, 51)
        self.shots_fired_global = to_uint_64(self.leaderboard_data, 27)
        self.players            = to_int_32(self.leaderboard_data, 75)

        entry_count = to_int_16(self.leaderboard_data, 59)
        rank_iterator = 0
        byte_pos = 83
        self.entries = []
        while(rank_iterator < entry_count):
            entry = Entry()
            username_length = to_int_16(self.leaderboard_data, byte_pos)
            username_bytes = bytearray(username_length)
            byte_pos += 2
            for i in range(byte_pos, byte_pos + username_length):
                username_bytes[i-byte_pos] = self.leaderboard_data[i]

            byte_pos += username_length

            entry.username = username_bytes.decode("utf-8")
            entry.rank = to_int_32(self.leaderboard_data, byte_pos)
            entry.userid = to_int_32(self.leaderboard_data, byte_pos + 4)
            entry.time = to_int_32(self.leaderboard_data, byte_pos + 12) / 10000
            entry.kills = to_int_32(self.leaderboard_data, byte_pos + 16)
            entry.gems = to_int_32(self.leaderboard_data, byte_pos + 28)
            entry.shots_hit = to_int_32(self.leaderboard_data, byte_pos + 24)
            entry.shots_fired = to_int_32(self.leaderboard_data, byte_pos + 20)
            if entry.shots_fired == 0:
                entry.shots_fired = 1
            entry.death_type = death_types[to_int_16(self.leaderboard_data, byte_pos + 32)]
            entry.time_total = to_uint_64(self.leaderboard_data, byte_pos + 60) / 10000
            entry.kills_total = to_uint_64(self.leaderboard_data, byte_pos + 44)
            entry.gems_total = to_uint_64(self.leaderboard_data, byte_pos + 68)
            entry.deaths_total = to_uint_64(self.leaderboard_data, byte_pos + 36)
            entry.shots_hit_total = to_uint_64(self.leaderboard_data, byte_pos + 76)
            entry.shots_fired_total = to_uint_64(self.leaderboard_data, byte_pos + 52)
            if entry.shots_fired_total == 0:
                entry.shots_fired_total = 1

            byte_pos += 88

            self.entries.append(entry)

            rank_iterator += 1

    def get_user(self, user):
        post_values = dict(user=user, level='survival', offset='0')

        req = requests.post("http://dd.hasmodai.com/backend16/get_scores.php", post_values)
        self.leaderboard_data = req.content

        # if (user < 1 or user > to_int_32(self.leaderboard_data, 75)):
        # if (user < 1 or user > 200000):
        if (user < 1):
            return None

        byte_pos = 83

        entry = Entry()

        while(byte_pos < len(self.leaderboard_data)):
            username_length = to_int_16(self.leaderboard_data, byte_pos)
            if (user != to_int_32(self.leaderboard_data, byte_pos + 6 + username_length)):
                byte_pos += 90 + username_length
            else:
                username_length = to_int_16(self.leaderboard_data, byte_pos)
                username_bytes = bytearray(username_length)
                byte_pos += 2
                for i in range(byte_pos, byte_pos + username_length):
                    username_bytes[i-byte_pos] = self.leaderboard_data[i]

                byte_pos += username_length

                entry.username = username_bytes.decode("utf-8")
                entry.rank = to_int_32(self.leaderboard_data, byte_pos)
                entry.userid = to_int_32(self.leaderboard_data, byte_pos + 4)
                entry.time = to_int_32(self.leaderboard_data, byte_pos + 12) / 10000
                entry.kills = to_int_32(self.leaderboard_data, byte_pos + 16)
                entry.gems = to_int_32(self.leaderboard_data, byte_pos + 28)
                entry.shots_hit = to_int_32(self.leaderboard_data, byte_pos + 24)
                entry.shots_fired = to_int_32(self.leaderboard_data, byte_pos + 20)
                if entry.shots_fired == 0:
                    entry.shots_fired = 1
                entry.death_type = death_types[to_int_16(self.leaderboard_data, byte_pos + 32)]
                entry.time_total = to_uint_64(self.leaderboard_data, byte_pos + 60) / 10000
                entry.kills_total = to_uint_64(self.leaderboard_data, byte_pos + 44)
                entry.gems_total = to_uint_64(self.leaderboard_data, byte_pos + 68)
                entry.deaths_total = to_uint_64(self.leaderboard_data, byte_pos + 36)
                entry.shots_hit_total = to_uint_64(self.leaderboard_data, byte_pos + 76)
                entry.shots_fired_total = to_uint_64(self.leaderboard_data, byte_pos + 52)
                if entry.shots_fired_total == 0:
                    entry.shots_fired_total = 1
                return entry


class Entry(object):
    username = ""
    userid = 0
    rank = 0
    time = 0
    kills = 0
    gems = 0
    shots_hit = 0
    shots_fired = 0
    death_type = ""
    time_total = 0
    kills_total = 0
    gems_total = 0
    deaths_total = 0
    shots_hit_total = 0
    shots_fired_total = 0

    def __eq__(self, other):
        try:
            return (self.rank, self.time, self.kills) == (other.rank, other.time,
                                                          other.kills)
        except AttributeError:
            return NotImplemented


@app.route('/api/get_user_by_id/<int:uid>')
def get_user_by_id(uid):
        post_values = dict(uid=uid)

        req = requests.post("http://dd.hasmodai.com/backend16/get_user_by_id_public.php", post_values)
        data = req.content
        if (uid < 1) or (uid is None):
            return jsonify({'message': 'Invalid user ID.'})

        byte_pos = 19

        username_length = to_int_16(data, byte_pos)
        username_bytes = bytearray(username_length)
        byte_pos += 2
        for i in range(byte_pos, byte_pos + username_length):
            username_bytes[i-byte_pos] = data[i]

        byte_pos += username_length

        username = username_bytes.decode("utf-8")
        rank = to_int_32(data, byte_pos)
        userid = to_uint_64(data, byte_pos + 4)
        time = to_int_32(data, byte_pos + 12) / 10000
        kills = to_int_32(data, byte_pos + 16)
        gems = to_int_32(data, byte_pos + 28)
        shots_hit = to_int_32(data, byte_pos + 24)
        shots_fired = to_int_32(data, byte_pos + 20)
        if shots_fired > 0:
            accuracy = float("{0:.2f}".format((shots_hit/shots_fired)*100))
        else:
            accuracy = "0.00"
        death_type = death_types[to_int_16(data, byte_pos + 32)]
        time_total = to_uint_64(data, byte_pos + 60) / 10000
        kills_total = to_uint_64(data, byte_pos + 44)
        gems_total = to_uint_64(data, byte_pos + 68)
        deaths_total = to_uint_64(data, byte_pos + 36)
        shots_hit_total = to_uint_64(data, byte_pos + 76)
        shots_fired_total = to_uint_64(data, byte_pos + 52)
        if shots_fired_total > 0:
            accuracy_total = float("{0:.2f}".format((shots_hit_total/shots_fired_total)*100))
        else:
            accuracy_total = "0.00"

        return jsonify({'player_name': username,
                        'rank': rank,
                        'player_id': userid,
                        'time': time,
                        'kills': kills,
                        'gems': gems,
                        'shots_hit': shots_hit,
                        'shots_fired': shots_fired,
                        'accuracy': accuracy,
                        'death_type': death_type,
                        'time_total': time_total,
                        'kills_total': kills_total,
                        'gems_total': gems_total,
                        'deaths_total': deaths_total,
                        'shots_hit_total': shots_hit_total,
                        'shots_fired_total': shots_fired_total,
                        'accuracy_total': accuracy_total})

        
@app.route('/api/refresh_user_by_id/<int:uid>')
def refresh_user_by_id(uid):
    existing_player = User.query.filter_by(id=uid).first()
    if existing_player is None:
        return jsonify({'message': 'Not a valid ddstats user.'})
    else:
        r = requests.get('http://ddstats.com/api/get_user_by_id/{}'.format(uid))
        user_data = r.json()
        existing_player.username = user_data['player_name']
        existing_player.rank = user_data['rank']
        existing_player.game_time = user_data['time']
        existing_player.death_type = user_data['death_type']
        existing_player.gems = user_data['gems']
        existing_player.daggers_fired = user_data['shots_fired']
        existing_player.daggers_hit = user_data['shots_hit']
        existing_player.enemies_killed = user_data['kills']
        existing_player.accuracy = user_data['accuracy']
        existing_player.time_total = user_data['time_total']
        existing_player.deaths_total = user_data['deaths_total']
        existing_player.gems_total = user_data['gems_total']
        existing_player.enemies_killed_total = user_data['kills_total']
        existing_player.daggers_fired_total = user_data['shots_fired_total']
        existing_player.daggers_hit_total = user_data['shots_hit_total']
        existing_player.accuracy_total = user_data['accuracy_total']
        db.session.commit()
        return jsonify({'message': 'Success'})


@app.route('/api/get_scores', methods=['GET'])
def get_scores():
    offset = request.args.get('offset', default='0', type=int)
    user = request.args.get('user', default=None, type=int)
    leaderboard = Leaderboard(offset, user)
    if user is None:
        entry_list = []
        for entry in leaderboard.entries:
            entry_list.append({"player_name": entry.username,
                               "player_id": entry.userid,
                               "rank": entry.rank,
                               "game_time": entry.time,
                               "gems": entry.gems,
                               "daggers_hit": entry.shots_hit,
                               "daggers_fired": entry.shots_fired,
                               "enemies_killed": entry.kills,
                               "death_type": entry.death_type,
                               "total_game_time": entry.time_total,
                               "total_gems": entry.gems_total,
                               "total_daggers_hit": entry.shots_hit_total,
                               "total_daggers_fired": entry.shots_fired_total,
                               "total_enemies_killed": entry.kills_total,
                               "total_deaths": entry.deaths_total})

        leaderboard_json = {"global_player_count": leaderboard.players,
                            "global_time": leaderboard.time_global,
                            "global_gems": leaderboard.gems_global,
                            "global_daggers_hit": leaderboard.shots_hit_global,
                            "global_daggers_fired": leaderboard.shots_fired_global,
                            "global_enemies_killed": leaderboard.kills_global,
                            "global_deaths": leaderboard.deaths_global,
                            "entry_list": entry_list}
    else:
        entry = leaderboard.get_user(user)
        if entry is not None:
            leaderboard_json = {"player_name": entry.username,
                                "player_id": entry.userid,
                                "rank": entry.rank,
                                "game_time": entry.time,
                                "gems": entry.gems,
                                "daggers_hit": entry.shots_hit,
                                "daggers_fired": entry.shots_fired,
                                "enemies_killed": entry.kills,
                                "death_type": entry.death_type,
                                "total_game_time": entry.time_total,
                                "total_gems": entry.gems_total,
                                "total_daggers_hit": entry.shots_hit_total,
                                "total_daggers_fired": entry.shots_fired_total,
                                "total_enemies_killed": entry.kills_total,
                                "total_deaths": entry.deaths_total}
        else:
            leaderboard_json = {"message": "Invalid user ID."}

    return jsonify(leaderboard_json)

########################################################
#     end of devil dagger's backend api conversion     #
########################################################


# socketio stuff

@app.route('/socketio_test')
def show_socketio_test():
    return render_template('socketio_test.html')


# these two functions append the timestamp to static files so the flush
# correctly when updated.
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path, endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5666, debug=True)
