import os
import datetime as dt

def write_error(code:int=0,error:str="NULL" ,message:str="NULL"):

    os.makedirs("logs", exist_ok=True)
    
    with open("logs/errors.log", "a", encoding="utf-8") as file:
        file.write(f"{dt.datetime.now()}|{code}|{error}|{message}\n")
