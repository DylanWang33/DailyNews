# git 同步

import subprocess

def run(cmd):

    subprocess.run(cmd)

def push():

    run(["git","add","."])
    run(["git","commit","-m","auto news"])
    run(["git","push"])