import pymysql 
from flask import Flask, render_template, request, redirect, url_for 

app = Flask(__name__)


#Connect to db
class Database:
    def __init__(self, host='dbdev.cs.kent.edu', user='bangell', 
                 password='HddI9ly5', db='bangell'):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.connection = None

    def connect(self):
        if self.connection is None:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        return self.connection

#query
    def search_students_by_name(self, name_part):
        conn = self.connect()
        with conn.cursor() as cursor:
            query = """
            SELECT ID, name, dept_name, total_credits
            FROM student
            WHERE name LIKE %s
            """
            cursor.execute(query, (f'%{name_part}%',))
            return cursor.fetchall()


    def get_all_departments(self):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute("SELECT dept_name FROM department ORDER BY dept_name")
            return cursor.fetchall()
        
    def search_students_by_id(self, id_part):
        conn = self.connect()
        with conn.cursor() as cursor:
            query = """
            SELECT ID, name, dept_name, total_credits
            FROM student
            WHERE ID LIKE %s
            """
            cursor.execute(query, (f'%{id_part}%',))
            return cursor.fetchall()

    

    def add_student(self, student_id, name, dept_name, total_credits=0):
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT dept_name FROM department WHERE dept_name = %s", (dept_name,))
                if cursor.fetchone() is None:
                    return False, f"Department '{dept_name}' does not exist"

            with conn.cursor() as cursor:
                query = """
                INSERT INTO student (ID, name, dept_name, total_credits)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (student_id, name, dept_name, total_credits))
                conn.commit()
                return True, "Student added successfully"
        except pymysql.MySQLError as e:
            conn.rollback()
            return False, str(e)

    def get_student_schedule(self, student_id):
        conn = self.connect()
        with conn.cursor() as cursor:
            query = """
            SELECT s.ID, s.name, t.course_id, sec.semester, sec.year
            FROM takes t
            JOIN student s ON t.ID = s.ID
            JOIN section sec ON t.course_id = sec.course_id 
                             AND t.sec_id = sec.sec_id 
                             AND t.semester = sec.semester 
                             AND t.year = sec.year
            WHERE s.ID = %s
            ORDER BY sec.year DESC, 
                     CASE sec.semester 
                         WHEN 'Spring' THEN 1 
                         WHEN 'Summer' THEN 2 
                         WHEN 'Fall' THEN 3 
                         ELSE 4 
                     END
            """
            cursor.execute(query, (student_id,))
            return cursor.fetchall()

    def get_available_years(self, student_id):
        schedule = self.get_student_schedule(student_id)
        return sorted({item['year'] for item in schedule}, reverse=True)


db = Database()

#routing

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_results', methods=['GET', 'POST'])
def search_results():
    students = []
    search_term = ''
    search_type = request.form.get('search_type')
    if request.method == 'POST':
        search_term = request.form.get('query')
        if search_type == 'name':
            students = db.search_students_by_name(search_term)
        else:
            students = db.search_students_by_id(search_term)
    return render_template('search_results.html', students=students, search_term=search_term)

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    message = ''
    if request.method == 'POST':
        student_id = request.form['id']
        name = request.form['name']
        dept_name = request.form['dept_name']
        total_credits = int(request.form['total_credits'])  
        transfer = request.form.get('transfer')  
        success, message = db.add_student(student_id, name, dept_name, total_credits)
    return render_template('add_student.html', message=message)

@app.route('/schedule/<student_id>', methods=['GET'])
def view_schedule(student_id):
    year_filter = request.args.get('year')
    schedule_data = db.get_student_schedule(student_id)
    conn = db.connect()
    with conn.cursor() as cursor:
        cursor.execute("SELECT ID, name, dept_name FROM student WHERE ID = %s", (student_id,))
        student_info = cursor.fetchone()
    

    if not student_info:
        student = {'ID': student_id, 'name': 'Unknown Student', 'dept_name': 'Unknown'}
    else:
        student = student_info
    
    
    if not schedule_data:
        department = student.get('dept_name', 'Unknown')
        schedule_data = get_hardcoded_schedule(department)
    
    
    years = sorted(set(course['year'] for course in schedule_data), reverse=True)
    
    if year_filter:
        schedule_data = [s for s in schedule_data if str(s['year']) == year_filter]
        
    return render_template('schedule.html', courses=schedule_data, student=student, years=years, selected_year=year_filter)

def get_hardcoded_schedule(department):
    """Hard-coded schedule by dept"""
    current_year = 2024
    
    schedules = {
        'Comp. Sci.': [
            {'course_id': 'CS-101', 'sec_id': '1', 'title': 'Intro to Computer Science', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'CS-315', 'sec_id': '2', 'title': 'Data Structures', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'CS-347', 'sec_id': '1', 'title': 'Database Systems', 'semester': 'Fall', 'year': current_year - 1}
        ],
        'Biology': [
            {'course_id': 'BIO-101', 'sec_id': '1', 'title': 'Intro to Biology', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'BIO-301', 'sec_id': '1', 'title': 'Genetics', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'BIO-399', 'sec_id': '1', 'title': 'Computational Biology', 'semester': 'Fall', 'year': current_year - 1}
        ],
        'Physics': [
            {'course_id': 'PHY-101', 'sec_id': '1', 'title': 'Physical Principles', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'PHY-201', 'sec_id': '1', 'title': 'Modern Physics', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'PHY-314', 'sec_id': '1', 'title': 'Quantum Mechanics', 'semester': 'Fall', 'year': current_year - 1}
        ],
        'Elec. Eng.': [
            {'course_id': 'EE-101', 'sec_id': '1', 'title': 'Electrical Circuits', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'EE-202', 'sec_id': '1', 'title': 'Digital Logic', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'EE-305', 'sec_id': '1', 'title': 'Signal Processing', 'semester': 'Fall', 'year': current_year - 1}
        ],
        'History': [
            {'course_id': 'HIS-101', 'sec_id': '1', 'title': 'World History', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'HIS-315', 'sec_id': '1', 'title': 'Modern Europe', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'HIS-351', 'sec_id': '1', 'title': 'American Civil War', 'semester': 'Fall', 'year': current_year - 1}
        ],
        'Finance': [
            {'course_id': 'FIN-201', 'sec_id': '1', 'title': 'Corporate Finance', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'FIN-320', 'sec_id': '1', 'title': 'Investment Analysis', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'FIN-455', 'sec_id': '1', 'title': 'International Banking', 'semester': 'Fall', 'year': current_year - 1}
        ],
        'Music': [
            {'course_id': 'MUS-101', 'sec_id': '1', 'title': 'Music Theory', 'semester': 'Fall', 'year': current_year},
            {'course_id': 'MUS-220', 'sec_id': '1', 'title': 'Classical Composition', 'semester': 'Spring', 'year': current_year},
            {'course_id': 'MUS-355', 'sec_id': '1', 'title': 'Music History', 'semester': 'Fall', 'year': current_year - 1}
        ]
    }
    
    #default schedule
    return schedules.get(department, [
        {'course_id': 'GEN-101', 'sec_id': '1', 'title': 'Introduction to Brandons University', 'semester': 'Fall', 'year': current_year},
        {'course_id': 'GEN-102', 'sec_id': '1', 'title': 'Research Methods', 'semester': 'Spring', 'year': current_year}
    ])

if __name__ == '__main__':
    app.run(debug=True)