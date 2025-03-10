import sqlite3
from uuid import uuid4
from flask import g, session, redirect, url_for
from functools import wraps
from hashlib import sha256
from secrets import token_urlsafe
from views.api.utils import write_error
import re

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("instance/users.db")
    return db

class Auth:
    def __init__(self, request) -> None:
        self.request = request
    
    @property
    def con(self):
        return get_db()
    
    def authenticate(self,f):
        @wraps(f)
        def inner(*args,**kwargs):
            email:str = self.request.form.get("email")
            pwd:str = self.request.form.get("pwd")
            user = tuple(self.cur.execute(f"SELECT id, pwd from users where email = '{email}'"))
            print(user)
            try:
                user = user[0]
                user_id, user_pwd = user[0], user[1]
                if user_pwd == sha256(pwd.encode()).hexdigest():
                    session["id"] = user_id
                    session["token"] = token_urlsafe()
                    try:
                        self.cur.execute(f'''UPDATE users SET token='{session.get("token")}' WHERE id ='{user_id}';''')
                        self.con.commit()
                    except Exception as e:
                        write_error(200, e, f"Couldn't udpate token user_id: {user_id}")
                    return redirect(url_for("admin.t_stats"))
            except IndexError as e:
                print(e)
                pass
            return f(*args, **kwargs)
        return inner
    
    def authorize(self, f):
        @wraps(f)
        def inner(*args, **kwargs):
            user_id = session.get("id")
            user = tuple(self.cur.execute(f"SELECT token from users where id = '{user_id}'"))
            try:
                user = user[0]
                user_token = user[0]
                if user_token == session.get("token"):
                    return f(*args, **kwargs)
            except:
                return redirect(url_for("api.r_home"))
            
        return inner
    
    @property
    def cur(self):
        return self.con.cursor()
    
    def create(self):
        self.cur.execute('''CREATE VIRTUAL TABLE users USING FTS5(
                        id,
                        email,
                        pwd,
                        token
                        );''')
        self.con.commit()

    def enter(self, query:str, length:int=None, date:str=None, dataset:str=None, time:float=None,is_from_web:bool=False ,error:bool=None, update:bool=False):
        query = re.sub("\'XX\d{1,} OR .{1,}", "ALL_IDS LIMIT 1000;", query)
        if update:
            last_id = tuple(self.cur.execute("SELECT id FROM queries ORDER BY date DESC LIMIT 1;"))[0][0]
            query_str = f'''
                        UPDATE queries SET length = ?, date=?, dataset=?, time=?, is_from_web=?, error=0 WHERE id = '{last_id}';
                        '''
            try:
                self.cur.execute(query_str, (length, date, dataset, time, True if is_from_web else False))
                self.con.commit()
            except Exception as e:
                write_error(211, e, f"Couldn't save query on update: {query_str}")
        else:
            query_str = f'''
                    INSERT INTO queries VALUES(
                    '{uuid4().hex}',
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                    )
                    '''
            try:
                self.cur.execute(query_str, (query, length, date, dataset, time,is_from_web ,error))
                self.con.commit()
            except Exception as e:
                write_error(210, e, f"Couldn't save query on creation: {query_str}")

    @property
    def users(self):
        return tuple(self.cur.execute("SELECT id, email, pwd from USERS;"))



