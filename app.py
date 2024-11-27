from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__, static_folder="static", template_folder="templates")

# MySQL Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  
    'database': 'hotel_ASE'
}

# Helper function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/rooms")
def view_rooms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms")
    rooms = cursor.fetchall()
    conn.close()
    return render_template("rooms.html", rooms=rooms)

@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    if request.method == "POST":
        name = request.form["name"]
        room_id = request.form["room_id"]
        guests = request.form["guests"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reservations (name, room_id, guests, start_date, end_date) 
            VALUES (%s, %s, %s, %s, %s)
        """, (name, room_id, guests, start_date, end_date))
        conn.commit()
        conn.close()
        return redirect(url_for("view_reservations"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms")
    rooms = cursor.fetchall()
    conn.close()
    return render_template("reservation.html", rooms=rooms)

@app.route("/reservations")
def view_reservations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.name, rm.type, r.guests, r.start_date, r.end_date 
        FROM reservations r
        JOIN rooms rm ON r.room_id = rm.id
    """)
    reservations = cursor.fetchall()
    conn.close()
    return render_template("reservations.html", reservations=reservations)

@app.route("/edit_reservation/<int:reservation_id>", methods=["GET", "POST"])
def edit_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        room_id = request.form["room_id"]
        guests = request.form["guests"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        cursor.execute("""
            UPDATE reservations 
            SET name = %s, room_id = %s, guests = %s, start_date = %s, end_date = %s 
            WHERE id = %s
        """, (name, room_id, guests, start_date, end_date, reservation_id))
        conn.commit()
        conn.close()
        return redirect(url_for("view_reservations"))
    cursor.execute("SELECT * FROM reservations WHERE id = %s", (reservation_id,))
    reservation = cursor.fetchone()
    cursor.execute("SELECT * FROM rooms")
    rooms = cursor.fetchall()
    conn.close()
    return render_template("edit_reservation.html", reservation=reservation, rooms=rooms)

@app.route("/cancel_reservation/<int:reservation_id>")
def cancel_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reservations WHERE id = %s", (reservation_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_reservations"))

# Health check route to verify if Flask app is running properly
@app.route("/health")
def health_check():
    try:
        # Check if the database connection is successful
        conn = get_db_connection()
        conn.close()
        return "Flask is running and database connection is successful!", 200
    except Exception as e:
        return f"Flask is running, but database connection failed: {str(e)}", 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
