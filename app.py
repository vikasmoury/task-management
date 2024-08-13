from flask import Flask, request, jsonify, abort
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
# from uuid import uuid4
import MySQLdb

app = Flask(__name__)

# Configuration for MySQL
app.config['MYSQL_USER'] = 'root'  # MySQL username
app.config['MYSQL_PASSWORD'] = 'Vikas20@'  # MySQL password
app.config['MYSQL_DB'] = 'task_db'  # Database name
app.config['MYSQL_HOST'] = 'localhost'  # Database host
app.config['JWT_SECRET_KEY'] = 'Vikas123'
print("Connecting to MySQL with user:", app.config['MYSQL_USER'])
jwt = JWTManager(app)
mysql = MySQL(app)

# Helper function to generate a new UUID
# def generate_id():
#     return str(uuid4())
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')  # Ensure to hash passwords in a real app

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    conn = mysql.connection
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except MySQLdb.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        cursor.close()

@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user and user[1] == password:  # Password verification should use hashed passwords
        user_id = user[0]
        access_token = create_access_token(identity=user_id)
        
        # Fetch user details
        cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        user_details = cursor.fetchone()
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user_details[0],
                'username': user_details[1]
            }
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

# Create Task
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.json
    # task_id = generate_id()
    id = data.get('id')
    title = data.get('title')
    description = data.get('description')
    due_date = data.get('due_date')

    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (id, title, description, due_date) VALUES (%s, %s, %s, %s)", 
                   (id, title, description, due_date))
    conn.commit()
    cursor.close()

    return jsonify({'id':id, 'title': title, 'description': description, 'due_date': due_date}), 201

# Read Task - List all tasks
@app.route('/tasks', methods=['GET'])
def get_tasks():
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    cursor.close()

    task_list = [{'id': row[0], 'title': row[1], 'description': row[2], 'due_date': row[3]} for row in tasks]
    return jsonify(task_list), 200

# # Read Task - Get a specific task
@app.route('/tasks/<id>', methods=['GET'])
def get_task(id):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
    task = cursor.fetchone()
    cursor.close()

    if task:
        return jsonify({'id': task[0], 'title': task[1], 'description': task[2], 'due_date': task[3]}), 200
    else:
        abort(404)

# # Update Task
@app.route('/tasks/<id>', methods=['PUT'])
def update_task(id):
    data = request.json
    title = data.get('title')
    description = data.get('description')
    due_date = data.get('due_date')

    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET title = %s, description = %s, due_date = %s WHERE id = %s",
                   (title, description, due_date, id))
    conn.commit()
    cursor.close()

    return jsonify({'id': id, 'title': title, 'description': description, 'due_date': due_date}), 200

# # Delete Task
@app.route('/tasks/<id>', methods=['DELETE'])
def delete_task(id):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    conn.commit()
    cursor.close()

    return jsonify({'message': 'Task deleted'}), 200

# # Add Member to Task
# @app.route('/tasks/<int:task_id>/users', methods=['POST'])
# def add_user(task_id):
#     data = request.json
#     user_id = data.get('user_id')

#     conn = mysql.connection
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO task_user (task_id, user_id) VALUES (%s, %s)", (task_id, user_id))
#     conn.commit()
#     cursor.close()

#     return jsonify({'task_id': task_id, 'user_id': user_id}), 200
@app.route('/tasks/<int:task_id>/users', methods=['POST'])
def add_user(task_id):
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    conn = mysql.connection
    cursor = conn.cursor()

    try:
        # Check if the user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE id = %s", (user_id,))
        if cursor.fetchone()[0] == 0:
            return jsonify({'error': 'User does not exist'}), 400

        # Check if the task exists (optional)
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE id = %s", (task_id,))
        if cursor.fetchone()[0] == 0:
            return jsonify({'error': 'Task does not exist'}), 400

        # Check if the user is already added to the task (optional)
        cursor.execute("SELECT COUNT(*) FROM task_user WHERE task_id = %s AND user_id = %s", (task_id, user_id))
        if cursor.fetchone()[0] > 0:
            return jsonify({'error': 'User is already added to this task'}), 400

        cursor.execute("INSERT INTO task_user (task_id, user_id) VALUES (%s, %s)", (task_id, user_id))
        conn.commit()
        
        return jsonify({'task_id': task_id, 'user_id': user_id}), 200

    except MySQLdb.IntegrityError as e:
        conn.rollback()
        app.logger.error(f"IntegrityError occurred: {e}")
        if "FOREIGN KEY constraint fails" in str(e):
            return jsonify({'error': 'Foreign key constraint fails: check if user and task exist'}), 400
        return jsonify({'error': 'IntegrityError occurred'}), 500

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error occurred: {e}")
        return jsonify({'error': 'An error occurred while adding the user to the task'}), 500

    finally:
        cursor.close()

# # Remove Member from TaskS
@app.route('/tasks/<task_id>/users/<user_id>', methods=['DELETE'])
def remove_member(task_id, user_id):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("DELETE FROM task_users WHERE task_id = %s AND member_id = %s", (task_id, user_id))
    conn.commit()
    cursor.close()

    return jsonify({'task_id': task_id, 'member_id': user_id}), 200

# # View users of a Task
@app.route('/tasks/<task_id>/users', methods=['GET'])
def view_users(task_id):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.name
        FROM users m
        JOIN task_users tm ON m.id = tm.member_id
        WHERE tm.task_id = %s
    """, (task_id,))
    users = cursor.fetchall()
    cursor.close()

    member_list = [{'id': row[0], 'name': row[1]} for row in users]
    return jsonify(member_list), 200

# # Create Member (For example purposes)
# @app.route('/users', methods=['POST'])
# def create_member():
#     data = request.json
#     member_id = generate_id()
#     name = data.get('name')

#     conn = mysql.connection
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO users (id, name) VALUES (%s, %s)", (member_id, name))
#     conn.commit()
#     cursor.close()

#     return jsonify({'id': member_id, 'name': name}), 201

if __name__ == '__main__':
    app.run(debug=True)
