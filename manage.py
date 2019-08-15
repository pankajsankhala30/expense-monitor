from flask import Flask, render_template, request, url_for, redirect, flash, session, g
from dbconnect import connection
from functools import wraps
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from MySQLdb import escape_string as thwart
from flask_mail import Mail, Message
import datetime
import gc
from wtforms.fields.html5 import EmailField

app = Flask(__name__)
app.secret_key = "super secret key"

@app.route('/')
def homepage():
	if session.get('logged_in') == True:
		return redirect(url_for('dashboard'))
	else:
		# return render_template("main.html")
		return redirect(url_for('login_page'))

@app.route('/Terms/')
def terms():
	return render_template("terms.html")

@app.route('/About/')
def about():
	return render_template("about.html")

@app.route('/Contact/', methods=["GET","POST"])
def contact():
	try:
		c,conn = connection()		
		error = None
		if request.method == "POST":
			q_text = request.form['que']
			q_text = q_text.replace('\r', ';').replace('\n', ';')
			c.execute("INSERT INTO queries (uid, username, query) VALUES (%s, %s, %s)",(session.get('uid'),session.get('username'),q_text))
			conn.commit()
			c.close()
			conn.close()
			flash("Your query has been submitted successfully")
			return redirect(url_for('dashboard'))
		gc.collect()
		return render_template("contact.html")
	except Exception as e:
		return(str(e))

@app.route('/DarkMode/')
def dark_mode():
	session['mode'] = 'dark'
	return redirect(url_for('dashboard'))

@app.route('/LightMode/')
def light_mode():
	session['mode'] = 'light'
	return redirect(url_for('dashboard'))

@app.errorhandler(404)
def page_not_found(e):
	try:
		gc.collect()
		rule = request.path
		if "feed" in rule or "favicon" in rule or "wp-content" in rule or "wp-login" in rule or "wp-login" in rule or "wp-admin" in rule or "xmlrpc" in rule or "tag" in rule or "wp-include" in rule or "style" in rule or "apple-touch" in rule or "genericons" in rule or "topics" in rule or "category" in rule or "index" in rule or "include" in rule or "trackback" in rule or "download" in rule or "viewtopic" in rule or "browserconfig" in rule:
			pass
		else:
			pass
		return render_template('404.html'), 404
	except Exception as e:
		return(str(e))

# login required decorator
def login_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('You need to login first.')
			return redirect(url_for('login_page'))
	return wrap

# logout required decorator
def logout_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			flash('Your already logged in.')
			return redirect(url_for('dashboard'))
		else:
			return f(*args, **kwargs)
	return wrap

@app.route('/dashboard/', methods=["GET","POST"])
@login_required
def dashboard():

	try:
		c,conn = connection()		
		error = None

		c.execute("SELECT cash, bank, paytm, amazon, owe_in, owe_out FROM users WHERE username = (%s)", (thwart(session.get('username')),))
		wallets = c.fetchone()

		c.execute("SELECT date, amount, name, oid FROM passbook_owe WHERE uid = (%s) ORDER BY date DESC", (session.get('uid'),))
		passbook_o = c.fetchall()

		if session.get('passbook_limit') :
			c.execute("SELECT date, amount, val, mode, activity, total, pid FROM passbook WHERE uid = (%s) ORDER BY pid DESC LIMIT %s", (session.get('uid'),session.get('passbook_limit')))
			passbook = c.fetchall()
			session['passbook_limit'] = ''
		else:
			c.execute("SELECT date, amount, val, mode, activity, total, pid FROM passbook WHERE uid = (%s) ORDER BY pid DESC LIMIT 10", (session.get('uid'),))
			passbook = c.fetchall()

		# c.execute("SELECT date, amount, val, mode, activity, total, pid FROM passbook WHERE uid = (%s) ORDER BY pid DESC LIMIT 10", (session.get('uid'),))
		# passbook = c.fetchall()

		# print(Date_all[0][0].strftime("%d-%m-%y"), type(Date_all[0][0].strftime("%d-%m-%y")))
		def Date_valid(Date_all):

			start = datetime.datetime.now()
			z_dates = []
			z_dates.append(start.strftime('%d-%m-%y'))
			for i in range(29): 
				start -= datetime.timedelta(days=1)
				z_dates.append(start.strftime('%d-%m-%y'))

			Date_list = []
			count_d = 1
			for i in range(len(Date_all)):
				if count_d > 30:
					del Date_all[i-1:]
					del Date_list[-1]
					break
				Date_all[i][0] = Date_all[i][0].strftime("%d-%m-%y")
				Date_list.append(Date_all[i][0])
				if len(Date_list) >= 2:
					if Date_list[-1] != Date_list[-2]:
						count_d+=1
			Set_date = list(set(Date_list))
			Set_date = sorted(Set_date, key=lambda x: datetime.datetime.strptime(x, '%d-%m-%y'))
			Set_date.reverse()
			Set_amu = []
			for i in range(len(Set_date)):
				day_sum = 0
				for e in range(len(Date_all)):
					if Date_all[e][0] == Set_date[i]:
						day_sum += Date_all[e][1]
				Set_amu.append(day_sum)

			for i in range(len(z_dates)):
				if i >= len(Set_date) :
					Set_date.insert(i, z_dates[i])
					Set_amu.insert(i, 0)
				else:
					if z_dates[i] != Set_date[i]:
						Set_date.insert(i, z_dates[i])
						Set_amu.insert(i, 0)

			Max_amu = max(Set_amu[0:30])
			len_list = len(Set_date[0:30])

			return Set_date[0:30] , Set_amu[0:30] , Max_amu , len_list 

		c.execute("SELECT date, amount FROM passbook WHERE uid = (%s) AND mode != 'Person' AND activity != 'Updated' AND val = 1 ORDER BY pid DESC ", (session.get('uid'),))
		Date_all_a = c.fetchall()
		if len(Date_all_a) != 0:
			Date_all_a = [list(i) for i in Date_all_a]
			Set_date_a , Set_amu_a , Max_amu_a , len_list_a = Date_valid(Date_all_a)
		else : Set_date_a , Set_amu_a , Max_amu_a , len_list_a = 0, 0, 0, 0

		c.execute("SELECT date, amount FROM passbook WHERE uid = (%s) AND mode = 'Cash' AND activity != 'Updated' AND val = 1 ORDER BY pid DESC ", (session.get('uid'),))
		Date_all_c = c.fetchall()
		if len(Date_all_c) != 0:
			Date_all_c = [list(i) for i in Date_all_c]
			Set_date_c , Set_amu_c , Max_amu_c , len_list_c = Date_valid(Date_all_c)
		else : Set_date_c , Set_amu_c , Max_amu_c , len_list_c = 0, 0, 0, 0

		c.execute("SELECT date, amount FROM passbook WHERE uid = (%s) AND mode = 'Bank' AND activity != 'Updated' AND val = 1 ORDER BY pid DESC ", (session.get('uid'),))
		Date_all_b = c.fetchall()
		if len(Date_all_b) != 0:
			Date_all_b = [list(i) for i in Date_all_b]
			Set_date_b , Set_amu_b , Max_amu_b , len_list_b = Date_valid(Date_all_b)
		else : Set_date_b , Set_amu_b , Max_amu_b , len_list_b = 0, 0, 0, 0

		c.execute("SELECT date, amount FROM passbook WHERE uid = (%s) AND mode = 'Paytm' AND activity != 'Updated' AND val = 1 ORDER BY pid DESC ", (session.get('uid'),))
		Date_all_p = c.fetchall()
		if len(Date_all_p) != 0:
			Date_all_p = [list(i) for i in Date_all_p]
			Set_date_p , Set_amu_p , Max_amu_p , len_list_p = Date_valid(Date_all_p)
		else : Set_date_p , Set_amu_p , Max_amu_p , len_list_p = 0, 0, 0, 0

		if request.method == "POST":
			def val_validator(input_amount):
				if input_amount[0] == '-':
					value = 1
					amount_val = input_amount[1:]
				elif input_amount[0] == '+':
					value = 0
					amount_val = input_amount[1:]
				else:
					value = 0
					amount_val = input_amount
				return value, amount_val

			wallets_dic = {'cash': 0, 'bank': 1, 'paytm': 2, 'amazon': 3}

			if 'bills' in request.form:
				_, amount_val = val_validator(request.form['bills'])
				wallet_type = request.form.get('comp_select')
				comments = request.form['bills_dis']
				value = 1
				cmd_users = 'UPDATE users SET ' + wallet_type + '=' + wallet_type + ' - %s WHERE username = %s'
				c.execute(cmd_users, (amount_val, thwart(session.get('username'))))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, wallet_type.capitalize(), comments.capitalize(), wallets[wallets_dic[wallet_type]]))
			elif 'cash' in request.form:
				value, amount_val = val_validator(request.form['cash'])
				c.execute("""UPDATE users SET cash = cash + %s WHERE username = %s""",(request.form['cash'], thwart(session.get('username'))))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, 'Cash', 'Updated', wallets[0]))
			elif 'bank' in request.form:
				value, amount_val = val_validator(request.form['bank'])
				c.execute("""UPDATE users SET bank = bank + %s WHERE username = %s""",(request.form['bank'], thwart(session.get('username'))))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, 'Bank', 'Updated', wallets[1]))
			elif 'paytm' in request.form:
				value, amount_val = val_validator(request.form['paytm'])
				c.execute("""UPDATE users SET paytm = paytm + %s WHERE username = %s""",(request.form['paytm'], thwart(session.get('username'))))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, 'Paytm', 'Updated', wallets[2]))
			elif 'amazon' in request.form:
				value, amount_val = val_validator(request.form['amazon'])
				c.execute("""UPDATE users SET amazon = amazon + %s WHERE username = %s""",(request.form['amazon'], thwart(session.get('username'))))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, 'Amazon', 'Updated', wallets[3]))
			elif 'filter' in request.form:
				value = int(request.form['filter'])
				if value < 0 : value = 10
				session['passbook_limit'] = value
			elif 'passbook_del' in request.form:
				del_row = int(request.form['passbook_del'])
				c.execute("DELETE FROM passbook WHERE pid = '%s'", (del_row,))
			elif 'owe_in' in request.form:
				_, amount_val = val_validator(request.form['owe_in_amount'])
				person_name = request.form['owe_in_person']
				wallet_type = request.form.get('comp_select_in')
				value = 1
				ver_in = c.execute("SELECT * FROM passbook_owe WHERE name = %s AND uid = %s", (person_name.capitalize(), session.get('uid')))
				if int(ver_in) >0 :
					c.execute("UPDATE passbook_owe SET amount = amount + %s WHERE name = %s AND uid = %s", (amount_val, person_name.capitalize(), session.get('uid')))
				else :
					c.execute("INSERT INTO passbook_owe (uid, amount, name) VALUES (%s, %s, %s)", (session.get('uid'), amount_val, person_name.capitalize()))
				c.execute("SELECT amount FROM passbook_owe WHERE uid = %s", (session.get('uid'),))
				am_list = c.fetchall()
				owe_out_val = 0
				owe_in_val = 0
				for i in am_list:
					if i[0] < 0 : owe_out_val = owe_out_val + float(abs(i[0]))
					if i[0] > 0 : owe_in_val = owe_in_val + i[0]
					else: pass
				c.execute("""UPDATE users SET owe_out = %s, owe_in = %s WHERE username = %s""",(owe_out_val, owe_in_val, thwart(session.get('username'))))
				if wallet_type != 'old':
					cmd_users = 'UPDATE users SET ' + wallet_type + '=' + wallet_type + ' - %s WHERE username = %s'
					c.execute(cmd_users, (amount_val, thwart(session.get('username'))))
				else: pass
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, 'Person', person_name.capitalize(), wallets[4]))
			elif 'owe_out' in request.form:
				_, amount_val = val_validator(request.form['owe_out_amount'])
				person_name = request.form['owe_out_person']
				wallet_type = request.form.get('comp_select_out')
				value = 0
				ver_out = c.execute("SELECT * FROM passbook_owe WHERE name = %s AND uid = %s", (person_name.capitalize(), session.get('uid')))
				if int(ver_out) >0 :
					c.execute("UPDATE passbook_owe SET amount = amount - %s WHERE name = %s AND uid = %s", (amount_val, person_name.capitalize(), session.get('uid')))
				else :
					c.execute("INSERT INTO passbook_owe (uid, amount, name) VALUES (%s, -%s, %s)", (session.get('uid'), amount_val, person_name.capitalize()))
				c.execute("SELECT amount FROM passbook_owe WHERE uid = %s", (session.get('uid'),))
				am_list = c.fetchall()
				owe_out_val = 0
				owe_in_val = 0
				for i in am_list:
					if i[0] < 0 : owe_out_val = owe_out_val + float(abs(i[0]))
					if i[0] > 0 : owe_in_val = owe_in_val + i[0]
					else: pass
				c.execute("""UPDATE users SET owe_out = %s, owe_in = %s WHERE username = %s""",(owe_out_val, owe_in_val, thwart(session.get('username'))))
				if wallet_type != 'old':
					cmd_users = 'UPDATE users SET ' + wallet_type + '=' + wallet_type + ' + %s WHERE username = %s'
					c.execute(cmd_users, (amount_val, thwart(session.get('username'))))
				else: pass
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), amount_val, value, 'Person', person_name.capitalize(), wallets[5]))
			elif 'owe_in_del' in request.form:
				del_am = request.form['owe_in_del']
				wallet_type = request.form.get('comp_select_in_del')
				c.execute("SELECT amount, name FROM passbook_owe WHERE oid = %s", (del_am,))
				an_tup = c.fetchall()
				am_to_del = float(an_tup[0][0])
				person_name = an_tup[0][1]
				value = 0
				c.execute("""UPDATE passbook_owe SET amount = 0 WHERE oid = %s""",(del_am,))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), am_to_del, value, 'Person', person_name.capitalize(), wallets[4]))
				c.execute("UPDATE users SET owe_in = owe_in - %s WHERE username = %s", (am_to_del, thwart(session.get('username'))))
				if wallet_type != 'old':
					cmd_users = 'UPDATE users SET ' + wallet_type + '=' + wallet_type + ' + %s WHERE username = %s'
					c.execute(cmd_users, (am_to_del, thwart(session.get('username'))))
				else: pass
			elif 'owe_out_del' in request.form:
				del_am = request.form['owe_out_del']
				wallet_type = request.form.get('comp_select_out_del')
				c.execute("SELECT amount, name FROM passbook_owe WHERE oid = %s", (del_am,))
				an_tup = c.fetchall()
				am_to_del = float(str(an_tup[0][0])[1:])
				person_name = an_tup[0][1]
				value = 1
				c.execute("""UPDATE passbook_owe SET amount = 0 WHERE oid = %s""",(del_am,))
				c.execute("INSERT INTO passbook (uid, amount, val, mode, activity, total) VALUES (%s, %s, %s, %s, %s, %s)",(session.get('uid'), am_to_del, value, 'Person', person_name.capitalize(), wallets[5]))
				c.execute("UPDATE users SET owe_out = owe_out - %s WHERE username = %s", (am_to_del, thwart(session.get('username'))))
				if wallet_type != 'old':
					cmd_users = 'UPDATE users SET ' + wallet_type + '=' + wallet_type + ' - %s WHERE username = %s'
					c.execute(cmd_users, (am_to_del, thwart(session.get('username'))))
				else: pass
			else:
				pass
			conn.commit()
			c.close()
			conn.close()
			return redirect(url_for('dashboard'))

		gc.collect()
		return render_template("dashboard.html", wallets = wallets, passbook = passbook, passbook_o = passbook_o, Set_date_a = Set_date_a, Set_amu_a = Set_amu_a, Max_amu_a = Max_amu_a, len_list_a = len_list_a, Set_date_c = Set_date_c, Set_amu_c = Set_amu_c, Max_amu_c = Max_amu_c, len_list_c = len_list_c, Set_date_b = Set_date_b, Set_amu_b = Set_amu_b, Max_amu_b = Max_amu_b, len_list_b = len_list_b, Set_date_p = Set_date_p, Set_amu_p = Set_amu_p, Max_amu_p = Max_amu_p, len_list_p = len_list_p)
	except Exception as e:
		return(str(e))

@app.route('/logout/')
@login_required
def logout():
	session.pop('logged_in', None)
	session.clear()
	flash('You have been logged out.')
	gc.collect()
	return redirect(url_for('homepage'))

@app.route('/user/<name_user>/', methods=["GET","POST"])
@login_required
def user(name_user):
	if session.get('username') == name_user:
		c, conn = connection()
		c.execute("SELECT username , full_name, sex, img, email, phone, cash, bank, paytm, amazon, owe_in, owe_out FROM users WHERE username = (%s)", (thwart(session.get('username')),))
		info = c.fetchone()

		if request.method == "POST":
			if 'name' in request.form:
				fname = request.form['name'].title()
				c.execute("UPDATE users SET full_name = %s WHERE username = %s", (fname, thwart(session.get('username'))))
			if 'number' in request.form:
				numb = request.form['number']
				if len(numb) ==10 : 
					c.execute("UPDATE users SET phone = %s WHERE username = %s", (numb, thwart(session.get('username'))))
				else :
					flash('Enter a valid phone number!')
			if 'sex' in request.form:
				gen = request.form.get('comp_select')
				c.execute("UPDATE users SET sex = %s WHERE username = %s", (gen, thwart(session.get('username'))))
			conn.commit()
			c.close()
			conn.close()
			return redirect('/user/'+session.get('username'))
		else:
			pass

		conn.commit()
		c.close()
		conn.close()
		return render_template("user.html", info=info)
		gc.collect()
	else:
		return render_template("404.html")

@app.route('/user/switch/')
@login_required
def switch():
	session.pop('logged_in', None)
	session.clear()
	flash('You have been logged out.')
	gc.collect()
	return redirect(url_for('login_page'))

@app.route('/login/', methods=["GET","POST"])
@logout_required
def login_page():
	error = ''
	try:
		c, conn = connection()
		if request.method == "POST":

			data = c.execute("SELECT uid, username, password, sex FROM users WHERE username = (%s)",
							 (thwart(request.form['username']),))
			
			data_all = c.fetchone()
			data_uid = data_all[0]
			data_sex = data_all[3]
			data = data_all[2]

			if sha256_crypt.verify(request.form['password'], data):
				session['logged_in'] = True
				session['username'] = request.form['username']
				session['uid'] = data_uid
				session['sex'] = data_sex

				flash("You are now logged in")
				return redirect(url_for("dashboard"))

			else:
				error = "Invalid credentials, try again."

		gc.collect()

		return render_template("login.html", error=error)

	except Exception as e:
		flash(e)
		error = "Invalid credentials, try again!"
		return render_template("login.html", error = error)

class RegistrationForm(Form):
	username = TextField('Username', [validators.Length(min=4, max=20)])
	# email = TextField('Email Address', [validators.Length(min=6, max=50)])
	email = EmailField('Email address', [validators.DataRequired(), validators.Email()])
	password = PasswordField('Password', [validators.Required(), validators.EqualTo('confirm', message='Passwords must match')])
	confirm = PasswordField('Repeat Password')
	accept_tos = BooleanField('I accept the <a href="/Terms" target="blank">Terms of Service</a>', [validators.Required()])

@app.route('/user/change-password/', methods=['GET', 'POST'])
@login_required
def change_password():
	try:
		c,conn = connection()
		
		error = None
		if request.method == 'POST':

			data = c.execute("SELECT uid, username, password FROM users WHERE username = (%s)",
					(thwart(session.get('username')),))
			data = c.fetchone()[2]


			if sha256_crypt.verify(request.form['password'], data):
				# flash('Authentication Successful.')
				if len(request.form['npassword']) > 0:
					#flash("You wanted to change password")

					if request.form.get('npassword') == request.form.get('rpassword'):
						try:
							# flash("new passwords matched")
							print("hello")
							password = sha256_crypt.encrypt((str(request.form['npassword'])))
							
							c,conn = connection()
							
							data = c.execute("UPDATE users SET password = %s where username = %s",
							(thwart(password), thwart(session.get('username'))))

							conn.commit()
							c.close()
							conn.close()
							flash("Password changed")
						except Exception as e:
							return(str(e))
					else:
						flash("Passwords do not match!")

				return redirect(url_for('dashboard'))

			else:
				flash('Invalid credentials. Try again')
				error = 'Invalid credentials. Try again'
		gc.collect()          
		return render_template('change_pass.html', error=error)
	except Exception as e:
		return(str(e))

@app.route('/register/', methods=['GET', 'POST'])
@logout_required
def register():

	try:
		form = RegistrationForm(request.form)
		if request.method == 'POST' and form.validate():
			#flash("register attempted")

			username = form.username.data
			email = form.email.data

			password = sha256_crypt.encrypt((str(form.password.data)))
			c,conn = connection()

			x = c.execute("SELECT * FROM users WHERE username = (%s)",
				(thwart(username),))
			y = c.execute("SELECT * FROM users WHERE email = (%s)",
				(thwart(email),))

			if int(x) > 0:
				flash("That username is already taken, please choose another")
				return render_template('register.html', form=form)
			elif int(y) > 0:
				flash("This email is already in use")
				return render_template('register.html', form=form)
			else:
				c.execute("INSERT INTO users (username, password, email, cash, bank, paytm, amazon, owe_in, owe_out) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
					(thwart(username), thwart(password), thwart(email), 0, 0, 0, 0, 0, 0))
				conn.commit()
				flash('Thanks for registering')
				c.close()
				conn.close()
				gc.collect()
				return redirect(url_for('login_page'))
		gc.collect()
		return render_template('register.html', form=form)
	except Exception as e:
		return(str(e))

@app.template_filter('INR')
def currency(val):
	return "{:,.2f}".format(val)
@app.template_filter('INR_s')
def currency(val):
	return "{:,.2f}".format(val)
@app.template_filter('INR_f')
def currency(val):
	return "{:,}".format(val)
@app.template_filter('INR_only')
def currency(val):
	return "{:,}/-".format(val)
@app.template_filter('INR_only_f')
def currency(val):
	return "{:,}".format(val)
@app.template_filter('ABS')
def abs(val):
	return str(val)[1:]
@app.template_filter('CAP')
def cap(val):
	return val.capitalize()
@app.template_filter('timestamp_f')
def ts(val):
	return val.strftime("%d %b %y, %I:%M %p")
@app.template_filter('datetime')
def dt(val):
	val_n = datetime.datetime.strptime(val, '%d-%m-%y')
	return val_n.strftime("%d %b %y")

if __name__ == "__main__":
	# app.run(debug=True,host='0.0.0.0')
	app.run()
