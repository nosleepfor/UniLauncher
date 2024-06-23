import webview
import minecraft_launcher_lib as mll
import eel
import threading
import os
import signal
import requests
import psutil
import json
import webbrowser
import uuid
import subprocess
import showinfm
import pymsgbox
from cryptography.fernet import Fernet

version = 1

opts = mll.utils.generate_test_options()
opts['launcherName'] = 'UniLauncher'
opts['jvmArguments'] = ['-Xms128M']


vversions = None

def server():
    eel.init('content')
    eel.start('index.html', port=8000, mode=False)

@eel.expose
def show_mcdir():
    showinfm.show_in_file_manager(mll.utils.get_minecraft_directory())

@eel.expose
def login(username):
    webview.active_window().evaluate_js('location.href="main_page.html"')
    conf = get_config()
    conf['username']=username
    set_config(conf)

@eel.expose
def elylogin(username, passw):
    #enc b'1_KoFoqHvTfdTGBY7Fkgnlmf8lKAdNd6jh8QVuT44PE='
    webview.active_window().evaluate_js('location.href="main_page.html"')
    conf = get_config()
    f = Fernet(b'1_KoFoqHvTfdTGBY7Fkgnlmf8lKAdNd6jh8QVuT44PE=')
    conf['username']=username
    conf['elyby']['password']=f.encrypt(passw.encode('utf-8')).decode()
    set_config(conf)

@eel.expose
def get_config():
    return json.load(open('config.json'))

@eel.expose
def set_config(config: dict):
    json.dump(config, open('config.json', 'w'))

c = get_config()
if not c['mem']:
    c['mem'] = int(round(psutil.virtual_memory().total/(1073741824))/2)
    set_config(c)

@eel.expose
def webbrowser_open(url):
    webbrowser.open(url)

@eel.expose
def versions():
    global vversions

    
    if vversions == None:
        fabr = mll.fabric.get_stable_minecraft_versions()
        vers = []
        for v in mll.utils.get_available_versions(mll.utils.get_minecraft_directory()):
            vers.append(['vanilla', v['id']])
            f = mll.forge.find_forge_version(v['id'])
            if f:
                vers.append(['forge', f])
            if v['id'] in fabr:
                vers.append(['fabric', fabr[fabr.index(v['id'])]])
           

        vversions= vers
        return vers
    else:
        return vversions

@eel.expose
def is_installed(ver):
    type, ver = ver.split(':')
    sver = ver
    if type == 'forge':
        ver = f'{ver.split("-")[0]}-forge-{ver.split("-")[1]}'
        print(ver)
        if not ver in [id['id'] for id in mll.utils.get_installed_versions(mll.utils.get_minecraft_directory())]:
            ver = sver.split('-')[0]+'-forge'+sver.split('-')[0]+'-'+sver.split('-')[1]
            print(ver)
            return ver in [id['id'] for id in mll.utils.get_installed_versions(mll.utils.get_minecraft_directory())]
    if type == 'fabric':
        f=find_fabric(ver)
        if f != False:
            return True
        return False
    
    return ver in [id['id'] for id in mll.utils.get_installed_versions(mll.utils.get_minecraft_directory())]
print(mll.utils.get_installed_versions(mll.utils.get_minecraft_directory()))

@eel.expose
def max_mem():
    return int(round(psutil.virtual_memory().total/(1073741824)))

@eel.expose
def new_bg():
    result = window.create_file_dialog(
        webview.OPEN_DIALOG, allow_multiple=False, file_types= ('Image Files (*.jpg;*.png)',)
    )
    print(result)
    open('content/bg.jpg', 'wb').write(open(result[0], 'rb').read())
    eel.reload()

def find_fabric(mc_ver: str):
    fbr = [vs['id'] for vs in mll.utils.get_installed_versions(mll.utils.get_minecraft_directory())]
    for v in fbr:
        pts = v.split('-')
        if len(pts) > 2:
            if pts[0]+'-'+pts[1] == 'fabric-loader':
                if pts[-1] == mc_ver:
                    return fbr[fbr.index(v)]
    return False

@eel.expose
def install(verr):
    type, ver = verr.split(':')
    print(type,ver)
    if is_installed(verr):
        play(verr)
        return
    eel.start_progress()
    def set_progress(p):
        eel.set_progress(f'{p}/{m}')
    def set_max(mx):
        global m
        m = mx
    def set_status(s):
        eel.set_progress(s)
    callback = {'setProgress': set_progress, 'setMax': set_max, 'setStatus': set_status}
    if type == 'vanilla':
        mll.install.install_minecraft_version(ver,mll.utils.get_minecraft_directory(), callback=callback)
    if type == 'forge':
        mll.forge.install_forge_version(ver, mll.utils.get_minecraft_directory(), callback)
    if type == 'fabric':
        mll.fabric.install_fabric(ver, mll.utils.get_minecraft_directory(), callback=callback)
    print(type)
    eel.end_progress()

def play(ver):
    type, ver = ver.split(':')
    sver = ver
    if type == 'forge':
        ver = f'{ver.split("-")[0]}-forge-{ver.split("-")[1]}'
        if not ver in [id['id'] for id in mll.utils.get_installed_versions(mll.utils.get_minecraft_directory())]:
            ver = sver.split('-')[0]+'-forge'+sver.split('-')[0]+'-'+sver.split('-')[1]
    if type == 'fabric':
        ver = find_fabric(ver)
    
    conf = get_config()
    print(conf)
    opts['username'] = conf['username']
    
    if (conf['customskinloader']) and (conf['elyby']['password'] != ''):
        username, userid, token = ely_auth(conf['username'], conf['elyby']['password'])
        print('UniLauncher: Skinsystem using mod CustomSkinLoader')
        if token != None:
                
            opts['uuid'] = userid
            opts['token']= token
    
    if (conf['ely_by_patch']) and (conf['elyby']['password'] != ''):
        opts['jvmArguments'].append(f'-javaagent:{os.path.abspath("authlib-injector-1.2.5.jar")}=ely.by')
        
        username, userid, token = ely_auth(conf['username'], conf['elyby']['password'])
        print('UniLauncher: Skinsystem using authlib')
        if token != None:
            
            opts['uuid'] = userid
            opts['token']= token

    if conf['custom_resolution']['enabled']:
        opts['customResolution'] = conf['custom_resolution']['enabled']
        opts['resolutionHeight'] = str(conf['custom_resolution']['y'])
        opts['resolutionWidth'] = str(conf['custom_resolution']['x'])

    opts['jvmArguments'].append(f'-Xmx{conf["mem"]}G')
    webview.active_window().hide()
    subprocess.call(mll.command.get_minecraft_command(ver, mll.utils.get_minecraft_directory(), opts))
    webview.active_window().show()

def ely_auth(username, password):
    try:
        f = Fernet(b'1_KoFoqHvTfdTGBY7Fkgnlmf8lKAdNd6jh8QVuT44PE=')
        print(f.decrypt(password.encode()).decode())
        user_auth = requests.post('https://authserver.ely.by/auth/authenticate', data={
            'username': username,
            'password': f.decrypt(password.encode()).decode(),
            'clientToken': str(uuid.uuid4()),
            'requestUser': True
        }).json()
        return user_auth['user']['username'], user_auth['user']['id'], user_auth['accessToken']
    except:
        pymsgbox.alert('Аутентификация через ely.by не прошла', 'Ошибка авторизации')
        return None, None, None


if __name__ == "__main__":
    # latest = int(requests.get('https://raw.githubusercontent.com/nosleepfor/nosleepfor.github.io/main/current.txt').text)
    # if latest == version:
    #     pass
    # elif version < latest:
    #     print('You need an update!')
    # elif version > latest:
    #     print('Youre living in a future')

    threading.Thread(target=server).start()

    if get_config()['username']==None:
        url = 'http://localhost:8000/'
        

    else:
        url = 'http://localhost:8000/main_page.html'

    window = webview.create_window('UniLauncher', url, width=1200, height=800, resizable=False)

    def exit():
        os.kill(os.getpid(), signal.SIGKILL)
    window.events.closed += exit

    webview.start(debug=True)