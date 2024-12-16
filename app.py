from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash
from datetime import date

app = Flask(__name__, static_folder="static", template_folder="templates")

# Set a secret key for session management
app.secret_key = 'your_secret_key'

# MySQL Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Use environment variables in production for security
    'database': 'hotel_ASE'
}

# Helper function to get a database connection
def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None




@app.route("/")
def home():
    return render_template("index.html")




@app.route("/rooms")
def view_rooms():
    conn = get_db_connection()
    if not conn:
        return "Database connection error", 500
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms")
    rooms = cursor.fetchall()
    conn.close()
    return render_template("rooms.html", rooms=rooms)






@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    if not session.get("user_id"):
        return redirect(url_for("signin"))

    conn = get_db_connection()
    if not conn:
        return "Database connection error", 500
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        room_id = request.form["room_id"]
        guests = request.form["guests"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        # Check if start_date is a past date
        if start_date < date.today().strftime('%Y-%m-%d'):
            flash("Start date cannot be in the past!")
            return redirect(url_for("reserve"))

        # Validate input
        if int(guests) <= 0 or start_date >= end_date:
            flash("Invalid reservation details, please try again!")
            return redirect(url_for("reserve"))

        # Check for room availability during the requested period
        cursor.execute("""
            SELECT * FROM reservations 
            WHERE room_id = %s 
              AND (start_date < %s AND end_date > %s)
        """, (room_id, end_date, start_date))
        overlapping_reservations = cursor.fetchall()

        if overlapping_reservations:
            flash("Room is already reserved for the selected dates. Please choose a different room or date range.")
            return redirect(url_for("reserve"))

        # If available, insert the reservation
        cursor.execute("""
            INSERT INTO reservations (name, room_id, guests, start_date, end_date, user_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, room_id, guests, start_date, end_date, session["user_id"]))
        conn.commit()
        conn.close()
        flash("Reservation successful!")
        return redirect(url_for("view_reservations"))

    # Fetch all rooms
    cursor.execute("SELECT id, type, price FROM rooms")
    rooms = cursor.fetchall()
    conn.close()

    # Pass the current date to the template
    current_date = date.today().strftime('%Y-%m-%d')
    return render_template("reservation.html", rooms=rooms, current_date=current_date)







@app.route("/reservations")
def view_reservations():
    if not session.get("user_id"):
        return redirect(url_for("signin"))

    conn = get_db_connection()
    if not conn:
        return "Database connection error", 500
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.name, rm.type, r.guests, r.start_date, r.end_date 
        FROM reservations r
        JOIN rooms rm ON r.room_id = rm.id
        WHERE r.user_id = %s
    """, (session["user_id"],))
    reservations = cursor.fetchall()
    conn.close()
    return render_template("reservations.html", reservations=reservations)




@app.route("/edit_reservation/<int:reservation_id>", methods=["GET", "POST"])
def edit_reservation(reservation_id):
    conn = get_db_connection()
    if not conn:
        return "Database connection error", 500
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        room_id = request.form["room_id"]
        guests = request.form["guests"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        if int(guests) <= 0 or start_date >= end_date:
            flash("Invalid reservation details, please try again!")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        # Check for overlapping reservations for the new room
        cursor.execute("""
            SELECT * FROM reservations 
            WHERE room_id = %s 
              AND id != %s
              AND (start_date < %s AND end_date > %s)
        """, (room_id, reservation_id, end_date, start_date))
        overlapping_reservations = cursor.fetchall()

        if overlapping_reservations:
            flash("Room is already reserved for the selected dates. Please choose a different room or date range.")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        # Update the reservation details
        cursor.execute("""
            UPDATE reservations 
            SET name = %s, room_id = %s, guests = %s, start_date = %s, end_date = %s 
            WHERE id = %s
        """, (name, room_id, guests, start_date, end_date, reservation_id))

        conn.commit()
        conn.close()
        flash("Reservation updated successfully!")
        return redirect(url_for("view_reservations"))

    # Fetch the current reservation details
    cursor.execute("SELECT * FROM reservations WHERE id = %s", (reservation_id,))
    reservation = cursor.fetchone()

    # Fetch all rooms
    cursor.execute("SELECT id, type, price FROM rooms")
    rooms = cursor.fetchall()
    conn.close()

    return render_template("edit_reservation.html", reservation=reservation, rooms=rooms)





@app.route("/cancel_reservation/<int:reservation_id>")
def cancel_reservation(reservation_id):
    conn = get_db_connection()
    if not conn:
        return "Database connection error", 500
    cursor = conn.cursor()

    # Check if the reservation exists before attempting to delete it
    cursor.execute("SELECT room_id FROM reservations WHERE id = %s", (reservation_id,))
    reservation = cursor.fetchone()

    if not reservation:
        conn.close()
        flash("Reservation not found.")
        return redirect(url_for("view_reservations"))

    # Delete the reservation
    cursor.execute("DELETE FROM reservations WHERE id = %s", (reservation_id,))
    conn.commit()
    conn.close()

    flash("Reservation canceled successfully!")
    return redirect(url_for("view_reservations"))





@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone_number = request.form["phone_number"]
        nationality = request.form["nationality"]
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        security_question = request.form["security_question"]
        security_answer = request.form["security_answer"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users 
                (first_name, last_name, email, phone_number, nationality, username, password, security_question, security_answer)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (first_name, last_name, email, phone_number, nationality, username, password, security_question, security_answer))
            conn.commit()
            return redirect(url_for("signin"))
        except mysql.connector.Error as e:
            return f"Error: {str(e)}"
        finally:
            conn.close()

    return render_template("signup.html")




@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        identifier = request.form["identifier"]
        password = request.form["password"]

        # Check for admin login
        if identifier == "Admin" and password == "123":
            session["username"] = "Admin"  # Set session for admin
            return redirect(url_for("admin_dashboard"))

        # Regular user login
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM users 
            WHERE email = %s OR username = %s
        """, (identifier, identifier))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("view_reservations"))
        return render_template("wrong_password.html")

    return render_template("signin.html")





@app.route("/admin")
def admin_dashboard():
    # Check if user is authenticated as Admin
    if "username" not in session or session["username"] != "Admin":
        return redirect(url_for("signin"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id AS reservation_id, r.name AS booking_name, r.room_id, 
               r.start_date, r.end_date, u.username, u.email, r.user_id
        FROM reservations r
        JOIN users u ON r.user_id = u.id
    """)
    bookings = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", bookings=bookings)






@app.route("/admin/user/<int:user_id>")
def view_user_details(user_id):
    # Check if user is authenticated as Admin
    if "username" not in session or session["username"] != "Admin":
        return redirect(url_for("signin"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM users WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template("user_details.html", user=user)





@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        identifier = request.form["identifier"]
        security_question = request.form["security_question"]
        security_answer = request.form["security_answer"]
        new_password = generate_password_hash(request.form["new_password"])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if user exists with the provided security question and answer
        cursor.execute("""
            SELECT * FROM users 
            WHERE (email = %s OR username = %s) AND security_question = %s AND security_answer = %s
        """, (identifier, identifier, security_question, security_answer))

        user = cursor.fetchone()
        if user:
            # Update the user's password
            cursor.execute("""
                UPDATE users 
                SET password = %s 
                WHERE id = %s
            """, (new_password, user["id"]))
            conn.commit()
            conn.close()
            return redirect(url_for("signin"))
        else:
            conn.close()
            return "Invalid security question or answer, please try again."

    return render_template("forgot_password.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("signin"))



if __name__ == "__main__":
    app.run(port=5000, debug=True)
