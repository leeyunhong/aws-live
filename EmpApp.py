from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *
from datetime import datetime

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('AddEmp.html')


@app.route("/about", methods=['GET','POST'])
def about():
    return render_template('AboutUs.html', about=about)

@app.route("/getemp", methods=['GET','POST'])
def GetEmp():
    return render_template('GetEmp.html', GetEmp=GetEmp)

def show_image(bucket):
    s3_client = boto3.client('s3')
    public_urls = []
    
    #check whether the emp_id inside the image_url
    emp_id = request.form['emp_id']

    try:
        for item in s3_client.list_objects(Bucket=bucket)['Contents']:
            presigned_url = s3_client.generate_presigned_url('get_object', Params = {'Bucket': bucket, 'Key': item['Key']}, ExpiresIn = 100)
            if emp_id in presigned_url:
               public_urls.append(presigned_url)
    except Exception as e:
        pass
    # print("[INFO] : The contents inside show_image = ", public_urls)
    return public_urls

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

# @app.route("/getemp", methods=['POST'])
# def GetEmp():
#     cursor = db_conn.cursor()
#     cursor.execute('SELECT * FROM employee')
#     data = cursor.fetchall()
#     cursor.close()
#     print(data[0])
#     return render_template('GetEmp.html', data=data)

@app.route("/fetchdata", methods=['GET','POST'])
def fetchdata():
    if request.method == 'POST':
            emp_id = request.form['emp_id']
            cursor = db_conn.cursor()
            fetch_emp_sql = "SELECT * FROM employee WHERE emp_id = %s"
            cursor.execute(fetch_emp_sql,(emp_id))
            emp= cursor.fetchall()

            (id,fname,lname,priSkill,location) = emp[0]

            att_emp_sql = "SELECT attendance.date, attendance.time, attendance.att_values FROM attendance INNER JOIN employee ON attendance.emp_id = employee.emp_id WHERE employee.emp_id = %s"
            mycursor = db_conn.cursor()
            mycursor.execute(att_emp_sql, (emp_id))
            att_result= mycursor.fetchall()

            return render_template('GetEmpOutput.html', id=id,fname=fname,lname=lname,priSkill=priSkill,location=location,att_result=att_result)
    else:
        return render_template('AddEmp.html', fetchdata=fetchdata)

@app.route('/delete-emp', methods=['GET','POST'])
def DeleteEmp():
    emp_id= request.form['emp_id']

    mycursor = db_conn.cursor()
    del_emp_sql = "DELETE FROM employee WHERE emp_id = %s"
    mycursor.execute(del_emp_sql, (emp_id))
    db_conn.commit()
    try:
        return render_template('SuccessDelete.html')
    except Exception as e:
        return render_template('UnsuccessDelete.html')


@app.route("/editemp", methods=['GET','POST'])
def EditEmp():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        pri_skill = request.form['pri_skill']
        location = request.form['location']
        emp_id = request.form['emp_id']    

        update_sql = "UPDATE employee SET first_name = %s, last_name = %s, pri_skill = %s, location = %s WHERE emp_id = %s"
        cursor = db_conn.cursor()       

        changefield = (first_name, last_name, pri_skill, location, emp_id)
        try:
            cursor.execute(update_sql, (changefield))
            db_conn.commit()
            emp_name = "" + first_name + " " + last_name

        finally:
            cursor.close()

        return render_template('SuccessUpdate.html', name=emp_name,id=emp_id)
    else:
        return render_template('GetEmp.html', AddEmp=AddEmp)

@app.route('/attendance-emp', methods=['GET','POST'])
def AttendanceEmp():
    if request.method == 'POST':

        now = datetime.now()
        dt_string = now.strftime("%d%m%Y%H%M%S")
        d_string = now.strftime("%d/%m/%Y")
        t_string = now.strftime("%H:%M:%S")

        attendance_id = request.form['attendance_id'] + dt_string
        date = request.form['date'] + d_string
        time = request.form['time'] + t_string
        attendance = request.form.getlist('attendance')
        emp_id = request.form['emp_id']
        
        attendance = ','.join(attendance)
        att_values = (attendance)

        try:

            insert_att_sql = 'INSERT INTO attendance VALUES (%s,%s,%s,%s,%s)'
            cursor = db_conn.cursor()

            cursor.execute(insert_att_sql, (attendance_id,date,time,att_values,emp_id))
            db_conn.commit()

            return render_template('SuccessTakeAttendance.html', Id = attendance_id )
        except Exception as e:
                return str(e)

        finally:
            cursor.close()

# @app.route("/deleteemp", methods=['POST'])
# def DeleteEmp():
#     cursor = db_conn.cursor()
#     cursor.execute('DELETE FROM employee WHERE emp_id = {0}',format(emp_id))
#     db_conn.commit()
#     print(data[0])
#     return render_template('GetEmp.html')

# @app.route("/updateemp", methods=['POST'])
# def UpdateEmp(emp_id):
#     cursor = db_conn.cursor()
#     if request.methods =='POST':
#         first_name = request.form['first_name']
#         last_name = request.form['last_name']
#         pri_skill = request.form['pri_skill']
#         location = request.form['location']

#         cursor.execute("""UPDATE employee SET first_name=%s, last_name=%s, pri_skill=%s,location=%s WHERE emp_id = %s""",(first_name,last_name,pri_skill,location))
#         conn.commit()
#         return render_template('GetEmp.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
