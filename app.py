from flask import Flask
from flask import request
from flask import json
import sqlite3

app = Flask(__name__)
sqlite_file = 'db.db'


@app.route('/backend_score_submission', methods=['POST'])
def backend_score_submission():
    if request.headers['Content-Type'] == 'application/json':
        parsed_json = request.json

        conn, c = connect(sqlite_file)

        game_id = insert_game(c, parsed_json)
        insert_states(c, parsed_json, game_id)

        conn.commit()
        conn.close()

        print("game " + str(game_id) + " submitted.")

        return "JSON Message: " + json.dumps(request.json)
    else:
        return ":( i am not a happy person and i need therapy."


@app.route('/ddstats/<int:player_id>')
def show_player_games(player_id):
    conn, c = connect(sqlite_file)
    sql = "SELECT id FROM games WHERE playerID=?"
    c.execute(sql, (player_id,))

    rows = c.fetchall()

    if len(rows) is 0:
        html = "no user found"
    else:
        html = ""
        for row in rows:
            game_id = str(row[0])
            html += "<a href='{}/{}'>{}</a><br>".format(player_id, game_id, game_id)

    conn.close()
    return html


@app.route('/ddstats/<int:player_id>/<int:game_id>')
def show_game(player_id, game_id):
    conn, c = connect(sqlite_file)
    sql = "SELECT * FROM games WHERE playerID=? AND id=?"
    c.execute(sql, (player_id, game_id))

    html = ""
    if c.fetchone() is None:
        html = "game not found."
    else:
        sql = "SELECT * FROM states WHERE game_id=?"
        c.execute(sql, (game_id,))
        rows = c.fetchall()
        for row in rows:
            gems = row[3]
            html += str(gems) + "<br>"

    conn.close()
    return html


@app.route('/')
def api_root():
    return 'dongle'


def connect(sqlite_file):
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    return conn, c


def insert_game(c, parsed_json):
    sql = ''' INSERT INTO games(playerID, granularity, game_time, death_type,
                                gems, homing_daggers, daggers_fired, daggers_hit,
                                enemies_alive, enemies_killed) VALUES(?,?,?,?,?,?,?,?,?,?) '''
    game = (parsed_json["playerID"], parsed_json["granularity"], parsed_json["inGameTimer"],
            parsed_json["deathType"], parsed_json["gems"], parsed_json["homingDaggers"],
            parsed_json["daggersFired"], parsed_json["daggersHit"], parsed_json["enemiesAlive"],
            parsed_json["enemiesKilled"])
    c.execute(sql, game)
    return c.lastrowid


def insert_states(c, parsed_json, game_id):
    sql = ''' INSERT INTO states(game_id, state_number, game_time, gems,
                                 homing_daggers, daggers_hit, daggers_fired,
                                 enemies_alive, enemies_killed) VALUES(?,?,?,?,?,?,?,?,?) '''
    for i in range(len(parsed_json["inGameTimerVector"])):
        state = (game_id, i, parsed_json["inGameTimerVector"][i],
                 parsed_json["gemsVector"][i], parsed_json["homingDaggersVector"][i],
                 parsed_json["daggersHitVector"][i], parsed_json["daggersFiredVector"][i],
                 parsed_json["enemiesAliveVector"][i], parsed_json["enemiesKilledVector"][i])
        c.execute(sql, state)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5666)
