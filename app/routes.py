from flask import render_template, url_for, flash, redirect, request, Markup
from flask.ext.login import login_required, login_user, logout_user, current_user
from app import app, db

# - Marketing Moduel Imports -- Move these to blueprint.
# Marketing Module imports - dependencies.
import requests
from collections import Counter
from bs4 import BeautifulSoup
import operator
import re
import nltk
# Marketing Module imports - from w/in app.
from .stop_words import stops

from .models import User, Messages, Result, AppNotifications
from .forms import LoginForm, RegisterForm, UserAddForm, UserUpdateForm, UserDeleteForm, CustomerAddForm, CustomerUpdateForm, PersonnelAddForm, PersonnelUpdateForm
from .modals import user_add_modal, user_update_modal, customer_add_modal, customer_update_modal, personnel_add_modal, personnel_update_modal
from .services.telephony.contacts import CompanyContacts
from .services.telephony.sms import sms_response, sms_check_in_data
from .services.telephony.calls import call_response, call_check_in_data
from .includes import add_user, update_user, delete_user, check_permissions_to_update_user, check_permissions_to_assign_user_role, check_permissions_to_delete_user


##############
# - Variables


##############
# - Decorators


##############
# - Root Path
@app.route('/')
def root_path():
    if current_user.is_authenticated():
        return redirect(url_for('index'))
    else:
        return redirect(url_for('welcome'))


@app.route('/welcome')
def welcome():
    logged_in = current_user.is_authenticated()
    user = current_user
    login_form = LoginForm(request.form)
    register_form = RegisterForm(request.form)

    return render_template('core_modules/welcome/index.html',
                           module_name="Just-a-Dash Control Panel",
                           page_name="Welcome",
                           icon="fa fa-star-o",
                           module_abbreviation="Home",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           register_form=register_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/index')
@login_required
def index():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('core_modules/dashboard/index.html',
                           module_name="Just-a-Dash Control Panel",
                           page_name="Dashboard",
                           icon="fa fa-dashboard",
                           module_abbreviation="Home",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/home')
@login_required
def home():
    return redirect(url_for('root_path'))


@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('root_path'))


################
# - Core Modules
@app.route('/account-settings')
@login_required
def account_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('core_modules/account_settings/index.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="Account Settings",
                           module_name="Account Settings",
                           page_name="Account Settings Home",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/config')
@app.route('/app-config')
@app.route('/app-settings')
@login_required
def app_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('core_modules/app_settings/index.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="App Settings",
                           module_name="App Settings",
                           page_name="App Settings Home",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/user-management', methods=['GET', 'POST'])
@login_required
def user_management():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    modals = {'UserAddModal': user_add_modal, 'UserUpdateModal': user_update_modal}

    # To do: Need to fix this so that my forms are able to create fields dynamically based on database values.
    # The code below doesn't seem to break app, but does not seem to have an effect.
    add_form = UserAddForm(request.form)
    update_form = UserUpdateForm(request.form)
    delete_form = UserDeleteForm(request.form)
    # db_populate_object = namedtuple('literal', 'name age')(**{'name': 'John Smith', 'age': 23})
    # add_form.append_field("test", SelectField('test'))(obj=db_populate_object)

    forms = {'User-Add-Form': add_form,
             'User-Update-Form': update_form,
             'User-Delete-Form': delete_form}

    if request.method == 'POST':

        if request.form['form_submit']:

            if request.form['form_submit'] == 'User-Add-Form':
                if add_form.validate_on_submit():
                    # NEED TO CHECK AUTHORITY TO ASSIGN
                    add_user(add_form)
                else:
                    flash('Attempted to add record, but form submission failed validation. Please ensure that all of the non-blank fields submitted pass validation.','danger')

            elif request.form['form_submit'] == 'User-Delete-Form':
                superiority = check_permissions_to_delete_user(delete_form, current_user)
                if superiority == False:
                    flash('Failed to delete user. Your administrative role must to be higher than another\'s in order to delete.','danger')
                elif superiority == True:
                    if delete_form.validate_on_submit():
                        delete_user(update_form)
                    else:
                        flash('Attempted to delete record, but an unexpected error occurred. Please contact the application administrator', 'danger')
                else:
                    flash('One or more errors occurred while attempting to determine user permissions. Please contact the application administrator.', 'danger')

            elif request.form['form_submit'] == 'User-Update-Form':
                # may need to change the following line, as it might deny all.
                authority = check_permissions_to_assign_user_role(update_form, current_user)
                if authority == True:
                    role_superiorities = check_permissions_to_update_user(update_form, current_user)
                    if update_form.validate_on_submit():
                        update_user(update_form, role_superiorities)
                    else:
                        flash('Attempted to update record, but form submission failed validation. Please ensure that all of the non-blank fields submitted pass validation.', 'danger')
            else:
                flash('An error occurred while processing the submitted form. Please correct the errors in your form submission. If you feel this message is in error, please contact the application administrator.', 'danger')
        else:
            flash('Error. Data appears to have been posted to the server, but could not determine type of form submission. Please contact the application administrator.', 'danger')

        return redirect((url_for('user_management')))

    return render_template('core_modules/app_settings/user_management.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="App Settings",
                           module_name="App Settings",
                           page_name="User Management",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           users=db.session.query(User),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in,
                           modals=modals,
                           forms=forms)


@app.route('/logout')
def logout():
    logged_in = current_user.is_authenticated()
    logout_user()
    flash(u'Logged out. Thank you, come again!', 'success')
    return redirect(url_for('welcome'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    logged_in = current_user.is_authenticated()
    errors = []
    login_form = LoginForm(request.form)
    register_form = RegisterForm()

    if request.method == 'POST':
        if login_form.validate_on_submit():
            user = User.query.filter_by(username=request.form['username']).first()
            # - This one is for bcrypt. Right now I'm using PBKDF2 a la Werkeug Security.
            # if user is not None and bcrypt.check_password_hash(user.password, request.form['password']):
            if user is not None and user.check_password(request.form['password']):
                login_user(user)
                flash(u'Logged in. Welcome back!', 'success')
                return redirect(url_for('index'))
            else:
                errors.append('Login failed. Please check that your credentials are correct, and try again.')
                user = User.query.filter_by(username=request.form['username']).first()
                for error in errors:
                    flash(error, 'danger')
        else:
            flash('Login failed. Please make sure to to fill out all fields before submitting.', 'danger')
    return render_template('core_modules/login/index.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="Home",
                           module_name="Just-a-Dash Control Panel",
                           page_name="Login",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           register_form=register_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/register', methods=['GET', 'POST'])
def register():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    register_form = RegisterForm()
    if request.method == 'POST':
        if register_form.validate_on_submit():
            new_user = User(
                username=register_form.username.data,
                email=register_form.email.data,
                password=register_form.password.data,
                admin_role='None',
                oms_role='None',
                crm_role='None',
                hrm_role='None',
                ams_role='None',
                mms_role='None')
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Registration complete! You have been logged in.', 'success')
            flash(Markup('<strong>Info! -</strong> '), 'info')
            return redirect(url_for('index'))
        else:
            flash('Registration failed, please try again.', 'warning')
            flash('When registering, ensure the following conditions are all met. (1) Username is between 3-25 '
                  'characters, (2) E-mail is between 6-40 characters, (3) Password is beteen 6-25 characters, '
                  '(4) Password and confirm password are matching.', 'info')

    return render_template('core_modules/register/index.html',
                           icon="fa fa-pencil-square-o",
                           module_abbreviation="Registration",
                           module_name="Registration",
                           page_name="New Submission",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           register_form=register_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/profile')
@login_required
def profile():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)

    return render_template('core_modules/profile/index.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="Profile",
                           module_name="Profile",
                           page_name="Profile Home",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           profile_form=UserUpdateForm(request.form),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/notifications')
@login_required
def notifications():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('core_modules/profile/notifications.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="Profile",
                           module_name="Profile",
                           page_name="Notifications",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/tasks')
@login_required
def tasks():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('core_modules/profile/tasks.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="Profile",
                           module_name="Profile",
                           page_name="Tasks",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


############
# - Modules - OMS
@app.route('/operations')
@login_required
def operations(*args):
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    try:
        check_in_type = args[0]
    except:
        check_in_type = None

    if check_in_type == "sms_check_in":
        check_in_entries = sms_check_in_data()
    elif check_in_type == "call_check_in":
        check_in_entries = call_check_in_data()
    elif check_in_type == None:
        check_in_entries = call_check_in_data()
    else:
        check_in_entries = {".": {"timestamp": ".", "first_name": ".", "last_name": ".", "phone_number": "."}}

    return render_template('modules/operations/index.html',
                           icon="fa fa-fort-awesome",
                           module_abbreviation="OMS",
                           module_name="Operations Management",
                           page_name="OMS Home",
                           check_in_entries=check_in_entries,
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/checkin')
@app.route('/check-in')
@app.route('/callin')
@app.route('/call-in')
@login_required
def call_check_in():
    return operations("call_check_in")


@app.route('/textin')
@app.route('/text-in')
@app.route('/text-checkin')
@app.route('/sms-checkin')
@login_required
def sms_check_in():
    return operations("sms_check_in")


# - Services
@app.route('/sms')
@app.route('/sms_send')
@app.route('/sms_receive')
def sms():
    return sms_response()


@app.route('/call', methods=['GET', 'POST'])
@app.route('/calls', methods=['GET', 'POST'])
@app.route('/call_send', methods=['GET', 'POST'])
@app.route('/call_receive', methods=['GET', 'POST'])
def call():
    return call_response()


@app.route('/oms-settings')
@login_required
def oms_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('modules/operations/settings.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="OMS",
                           module_name="Operations Management",
                           page_name="OMS Settings",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           profile_form=UserUpdateForm(request.form),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


############
# - Modules - CRM
@app.route('/crm', methods=['GET', 'POST'])
@login_required
def crm():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    modals = {'CustomerAddModal': customer_add_modal, 'CustomerUpdateModal': customer_update_modal}
    forms = {'Customer-Add-Form': CustomerAddForm(request.form),
             'Customer-Update-Form': CustomerUpdateForm(request.form)}

    try:
        customers = CompanyContacts.get_customer_contacts()
    except:
        customers = {"-": {"timestamp": "-", "first_name": "-", "last_name": "-", "phone_number": "-"}}

    return render_template('modules/crm/index.html',
                           icon="ion-person-stalker",
                           module_abbreviation="CRM",
                           module_name="Customer Relationship Management",
                           page_name="CRM Home",
                           form_title="Customer",
                           customer_data=customers,
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in,
                           modals=modals,
                           forms=forms)


@app.route('/crm-settings')
@login_required
def crm_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('modules/crm/settings.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="CRM",
                           module_name="Customer Relationship Management",
                           page_name="CRM Settings",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           profile_form=UserUpdateForm(request.form),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


############
# - Modules - HRM
@app.route('/hr', methods=['GET', 'POST'])
@app.route('/hrm', methods=['GET', 'POST'])
@login_required
def hrm():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    modals = {'PersonnelAddModal': personnel_add_modal, 'PersonnelUpdateModal': personnel_update_modal}
    forms = {'Personnel-Add-Form': PersonnelAddForm(request.form),
             'Personnel-Update-Form': PersonnelUpdateForm(request.form)}

    try:
        personnel = CompanyContacts.get_contacts()
    except:
        personnel = CompanyContacts.get_contacts()
        # personnel = {"-": {"timestamp": "-", "first_name": "-", "last_name": "-", "phone_number": "-"}}

    return render_template('modules/hrm/index.html',
                                icon="fa fa-users",
                                module_abbreviation="HRM",
                                module_name="Human Resource Management",
                                page_name="HRM Home",
                                form_title="Personnel",
                                personnel_data=personnel,
                                messages=db.session.query(Messages),
                                app_notifications=db.session.query(AppNotifications),
                                login_form=login_form,
                                current_user=current_user,
                                logged_in=logged_in,
                                modals=modals,
                                forms=forms)


@app.route('/hrm-settings')
@login_required
def hrm_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('modules/hrm/settings.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="HRM",
                           module_name="Human Resources Management",
                           page_name="HRM Settings",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           profile_form=UserUpdateForm(request.form),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


############
# - Modules - AMS
@app.route('/bms')
@app.route('/billing')
@app.route('/ams')
@app.route('/accounting')
@login_required
def accounting():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('modules/accounting/index.html',
                           icon="fa fa-bar-chart",
                           module_abbreviation="AMS",
                           module_name="Accounting Management",
                           page_name="AMS Home",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/ams-settings')
@login_required
def ams_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('modules/accounting/settings.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="AMS",
                           module_name="Accounting Management",
                           page_name="AMS Settings",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           profile_form=UserUpdateForm(request.form),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


############
# - Modules - MMS
@app.route('/mms', methods=['GET', 'POST'])
@app.route('/marketing', methods=['GET', 'POST'])
@login_required
def marketing():
    logged_in = current_user.is_authenticated()
    errors = []
    results = {}
    login_form = LoginForm(request.form)
    if request.method == "POST":
        try:
            url = request.form['url']
            # See if URL submitted contains 'http://' prepended.
            if url.find("http://") == 0:
                # r = requests.get(url).text.encode("utf-8")
                # r = requests.get(url).text
                r = requests.get(url)
                # print(r)
            else:
                url = "http://" + url
                r = requests.get(url)
        except:
            errors.append('Unable to get URL. Please make sure it\'s valid and try again.')
            return render_template('modules/marketing/index.html',
                                   icon="fa fa-line-chart",
                                   module_abbreviation="MMS",
                                   module_name="Marketing Management",
                                   page_name="MMS Home",
                                   errors=errors,
                                   messages=db.session.query(Messages),
                                   app_notifications=db.session.query(AppNotifications),
                                   login_form=login_form,
                                   current_user=current_user,
                                   logged_in=logged_in)

        if r:
            # text processing
            raw = BeautifulSoup(r.text).get_text()
            nltk.data.path.append('./nltk_data/')  # set the path
            tokens = nltk.word_tokenize(raw)
            text = nltk.Text(tokens)

            # remove punctuation, count raw words
            nonPunct = re.compile('.*[A-Za-z].*')
            raw_words = [w for w in text if nonPunct.match(w)]
            raw_word_count = Counter(raw_words)

            # stop words
            no_stop_words = [w for w in raw_words if w.lower() not in stops]
            no_stop_words_count = Counter(no_stop_words)

            # save the results
            results = sorted(
                no_stop_words_count.items(),
                key=operator.itemgetter(1),
                reverse=True
            )[0:10]

            try:
                result = Result(
                    url=url,
                    result_all=raw_word_count,
                    result_no_stop_words=no_stop_words_count)
                db.session.add(result)
                db.session.commit()
            except:
                errors.append("Unable to add item to database.")

    return render_template('modules/marketing/index.html',
                           icon="fa fa-line-chart",
                           module_abbreviation="MMS",
                           module_name="Marketing Management",
                           page_name="MMS Home",
                           errors=errors,
                           results=results,
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


@app.route('/mms-settings')
@login_required
def mms_settings():
    logged_in = current_user.is_authenticated()
    login_form = LoginForm(request.form)
    return render_template('modules/marketing/settings.html',
                           icon="fa fa-dashboard",
                           module_abbreviation="MMS",
                           module_name="Marketing Management",
                           page_name="MMS Settings",
                           messages=db.session.query(Messages),
                           app_notifications=db.session.query(AppNotifications),
                           profile_form=UserUpdateForm(request.form),
                           login_form=login_form,
                           current_user=current_user,
                           logged_in=logged_in)


if __name__ == "__main__":
    print("## Running Just-a-Dash routes.py directly. ##")
