from socketio_main import app
import sqlite3


# clears out the live table
conn = sqlite3.connect('app.db')
c = conn.cursor()
c.execute('delete from live')
conn.commit()
conn.close()


if __name__ == "__main__":
    app.run()
