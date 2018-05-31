#! /usr/bin/python
#encoding=utf-8
__author__ = 'hui.yin@uniswdc.com'

import sys
import traceback
import time
import re
import threading
import subprocess
import ConfigParser
from snack import *
#from set_hostname_ssh_parms import load_c15000_config
#from set-vizion-deploy-parms import generate_vizion_json

class ExtProgressWindow:

    def __init__(self, screen, title, text):
        self.screen = screen
        self.g = GridForm(self.screen, title, 1, 2)
        self.s = Scale(70, 100)
        self.t = Textbox(70, 5, text)
        self.g.add(self.t, 0, 0)
        self.g.add(self.s, 0, 1)

    def show(self):
        self.g.draw()
        self.screen.refresh()

    def update(self, progress, text):
        self.s.set(progress)
        self.t.setText(text)
        self.g.draw()
        self.screen.refresh()

    def close(self):
        time.sleep(1)
        self.screen.popWindow()

class Install_progress:

    def __init__(self):
        self.config_file = DEPLOY_CONFIG_FILE
        self.config_read = ConfigParser.RawConfigParser()
        self.config_read.read(self.config_file)
        self.sections = self.config_read.sections()
        self.lastest_section = self.sections[-1]

    def get_progress_value(self):
        progress_value = self.config_read.get(
            self.lastest_section,
            'deploy_percentage'
        )
        return int(progress_value[:-1])

    def get_current_job_name(self):
        current_job = None
        progress_value = self.get_progress_value()
        if progress_value != 100:
            current_job = self.config_read.get(
                self.lastest_section,
                'next_deploy_phase'
            )
        return current_job

    def get_deploy_info(self):
        info = []
        for section in self.sections:
            name = self.config_read.get(section, 'deploy_type')
            ret = self.config_read.get(section, 'deploy_result')
            info.append("{}: {}".format(name, ret))

        current_job = self.get_current_job_name()
        if current_job:
            info.append("{}: {}".format(current_job, 'running'))

        return info

def ExtListboxChoiceWindow(screen, title, text, items,
                buttons = ('Ok', 'Cancel'),
                width = 40, scroll = 0, height = -1,
                default = None, help = None):

    if (height == -1): height = len(items)

    bb = ButtonBar(screen, buttons, compact=1)
    t = TextboxReflowed(width, text)
    l = Listbox(height, scroll = scroll, returnExit = 1)
    count = 0
    for item in items:
        if (type(item) == types.TupleType):
            (text, key) = item
        else:
            text = item
            key = count

        if (default == count):
            default = key
        elif (default == item):
            default = key

        l.append(text, key)
        count = count + 1

    if (default != None):
        l.setCurrent (default)

    g = GridFormHelp(screen, title, help, 1, 3)
    g.add(t, 0, 0)
    g.add(l, 0, 1, padding = (0, 1, 0, 1))
    g.add(bb, 0, 2, growx = 1)

    rc = g.runOnce()

    return (rc, bb.buttonPressed(rc), l.current())

def ExtAlert(screen, title, msg, width=70):
    return ExtButtonChoiceWindow(screen, title, msg, ["Ok"], width)

def ExtButtonChoiceWindow(screen, title, text,
                buttons = [ 'Ok', 'Cancel' ],
                width = 40, x = None, y = None, help = None):

    bb = ButtonBar(screen, buttons, compact=1)
    t = TextboxReflowed(width, text, maxHeight = screen.height - 12)

    g = GridFormHelp(screen, title, help, 1, 2)
    g.add(t, 0, 0, padding = (0, 0, 0, 1))
    g.add(bb, 0, 1, growx = 1)
    return bb.buttonPressed(g.runOnce(x, y))

def ExtEntryWindow(screen, title, text, prompts,
            allowCancel = 1, width = 40, entryWidth = 20,
            buttons = [ 'Ok', 'Cancel' ], help = None):

    bb = ButtonBar(screen, buttons, compact=1);
    t = TextboxReflowed(width, text)

    count = 0
    for n in prompts:
        count = count + 1

    sg = Grid(2, count)

    count = 0
    entryList = []
    for n in prompts:
        if (type(n) == types.TupleType):
            (n, e) = n
            if (type(e) in types.StringTypes):
                e = Entry(entryWidth, e)
        else:
            e = Entry(entryWidth)

        sg.setField(Label(n), 0, count, padding = (0, 0, 1, 0), anchorLeft = 1)
        sg.setField(e, 1, count, anchorLeft = 1)
        count = count + 1
        entryList.append(e)

    g = GridFormHelp(screen, title, help, 1, 3)

    g.add(t, 0, 0, padding = (0, 0, 0, 1))
    g.add(sg, 0, 1, padding = (0, 0, 0, 1))
    g.add(bb, 0, 2, growx = 1)

    result = g.runOnce()

    entryValues = []
    count = 0
    for n in prompts:
        entryValues.append(entryList[count].value())
        count = count + 1

    return (result, bb.buttonPressed(result), tuple(entryValues))

def ExtButtonChoiceWindow(screen, title, text,
                buttons = [ 'Ok', 'Cancel' ],
                width = 40, x = None, y = None, help = None):

    bb = ButtonBar(screen, buttons, compact=1)
    t = TextboxReflowed(width, text, maxHeight = screen.height - 12)

    g = GridFormHelp(screen, title, help, 1, 2)
    g.add(t, 0, 0, padding = (0, 0, 0, 1))
    g.add(bb, 0, 1, growx = 1)
    return bb.buttonPressed(g.runOnce(x, y))

def validate_ip_format(ip):
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        button = ExtAlert(
            screen,
            "Error: IP Format",
            "IP format error, please write correct IP!",
        )
        return False

def validate_ip_duplicate(ip, config_type):
    result = True
    ips = get_ips(config_type)
    if ip in ips:
        button = ExtAlert(
            screen,
            "Error: IP Duplicate",
            "{} already exists, please write another IP!".format(ip),
        )
        result = False
    return result

def validate_not_empty(host):
    result = True
    for item in host:
        if not item:
            result = False
            break
    if not result:
        button = ExtAlert(
            screen,
            "Error: Content Empty",
            "Exist empty info, please supply for each host info!",
        )
    return result

def validate_extra_config():
    for host in Vizion_hosts:

def get_format_data(data, config_type):
    if config_type == "basic":
        seq = [
            'IP Address',
            'Hostname',
            'Password'
        ]
    elif config_type == "extra":
        seq = [
            'IP Address',
            'Hostname',
            'Password',
            'Devices'
        ]
    elif config_type == "extra_global":
        seq = [
            'Ntpserver',
            'IP Range'
        ]

    format_data = []
    for s in seq:
        format_data.append((s + ":", data[s]))
    return format_data

def get_C15000_format_config():
    key_map = {
        'IP Address': 'ipaddr',
        'Hostname': 'hostname',
        'Password': 'password'
    }
    data = {'ssh': {}}
    for host in C15000_hosts:
        data['ssh'][host['IP Address']] = {}
        for k, v in host.items():
            data['ssh'][host['IP Address']][key_map[k]] = v

    return data

def get_Vizion_format_config():
    key_map = {
        'IP Address': 'ipaddr',
        'Hostname': 'hostname',
        'Password': 'password',
        'Ntpserver': 'ntpserver',
        'IP Range': 'ip_range'
    }
    data = []
    for host in Vizion_hosts:
        item = {}
        for k, v in Extra_global_settings.items():
            item[key_map[k]] = v
        for k, v in host.items():
            if k == "Devices":
                devices = v.split(',')
                for device in devices:
                    key = 'device' + str(devices.index(device) + 1)
                    item[key] = device
            else:
                item[key_map[k]] = v
        data.append(item)

    return data

def start_deploy():
    load_c15000_config(
        deploy_type="console", get_C15000_format_config()
    )

    generate_vizion_json(
        deploy_type="console", get_Vizion_format_config()
    )

    do_shell("bash {}".format(DEPLOY_SCRIPT_FILE))

def do_shell(cmd):
    p = subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True
    )
    output, err = p.communicate()
    while p.poll() is None:
        try:
            proc = psutil.Process(p.pid)
            for c in proc.children(recursive=True):
                c.kill()
            proc.kill()
        except psutil.NoSuchProcess:
            pass
    if p.returncode == 1:
        sys.exit(0)
    return output


def get_ips(config_type):
    if config_type == "basic":
        hosts = C15000_hosts
    elif config_type == "extra":
        hosts = Vizion_hosts
    ips = [host['IP Address'] for host in hosts]
    return ips

def C15000_window(current, data=None):
    buttons = [ 'Save', 'Cancel', 'Exit']
    if not data:
        data = ['IP Address:', 'Hostname:', 'Password:']
        if current != 'add':
            data = get_format_data(C15000_hosts[current], 'basic')
            buttons.insert(1, 'Delete')

    host = ExtEntryWindow(
        screen,
        'C15000 Config',
        'C15000 Config',
        data,
        width = 40,
        entryWidth = 40,
        buttons = buttons
    )

    if host[1] == "exit":
        return
    elif host[1] == "save":
        new_host = {
            'IP Address': host[2][0],
            'Hostname': host[2][1],
            'Password': host[2][2]
        }
        if not validate_ip_format(host[2][0]):
            return C15000_window(
                current, get_format_data(new_host, 'basic')
            )

        if not validate_not_empty(host[2]):
            return C15000_window(
                current, get_format_data(new_host, 'basic')
            )

        if current == "add":
            if not validate_ip_duplicate(host[2][0], 'basic'):
                return C15000_window(
                    current, get_format_data(new_host, 'basic')
                )
            C15000_hosts.append(new_host)
        else:
            C15000_hosts[current] = new_host
    elif host[1] == "delete":
        button = ExtButtonChoiceWindow(
            screen,
            'Delete host',
            'Are you sure to delete current host?'
        )
        if button == "ok":
            del(C15000_hosts[current])
        else:
            C15000_window(current)
    C15000_hosts_list()

def Vizion_window(current, data=None):
    buttons = [ 'Save', 'Cancel', "Exit"]
    if not data:
        data = [
            'IP Address:',
            'Hostname:',
            'Password:',
            'Devices:'
        ]
        if current != 'add':
            data = get_format_data(Vizion_hosts[current], 'extra')
            buttons.insert(1, 'Delete')
    host = ExtEntryWindow(
        screen,
        'Vizion Config',
        'Vizion Config',
        data,
        width = 40,
        entryWidth = 40,
        buttons = buttons
    )

    if host[1] == "exit":
        return
    elif host[1] == "save":
        new_host = {
            'IP Address': host[2][0],
            'Hostname': host[2][1],
            'Password': host[2][2],
            'Devices': host[2][3],
        }
        if not validate_ip_format(host[2][0]):
            return Vizion_window(
                current, get_format_data(new_host, 'extra')
            )

        if not validate_not_empty(host[2]):
            return Vizion_window(
                current, get_format_data(new_host, 'extra')
            )

        if current == "add":
            if not validate_ip_duplicate(host[2][0], 'extra'):
                return Vizion_window(
                    current, get_format_data(new_host, 'extra')
                )
            Vizion_hosts.append(new_host)
        else:
            Vizion_hosts[current] = new_host
    elif host[1] == "delete":
        button = ExtButtonChoiceWindow(
            screen,
            'Delete host',
            'Are you sure to delete current host?'
        )
        if button == "ok":
            del(Vizion_hosts[current])
        else:
            Vizion_window(current)
    Vizion_hosts_list()

def Progress_window():
    #a = threading.Thread(target = start_deploy)
    #a.start()
    progress = ExtProgressWindow(
        screen,
        "CG20 Deploy",
        "Start deploy CG20 ..."
    )
    progress.show()
    last_progress_value = ""
    while True:
        install_info = Install_progress()
        progress_value = install_info.get_progress_value()
        detail_info = install_info.get_deploy_info()
        if progress_value != last_progress_value:
            progress.update(
                progress_value, "\n".join(detail_info) + "\n\n"
            )
        last_progress_value = progress_value
        state = ""
        for phase in detail_info:
            state = phase.split(':')[1].strip()
            if state == "failed":
                break
        if progress_value == "100" or state == "failed":
            break
    progress.close()
    Deploy_result_window(detail_info)

def Deploy_result_window(info):
    button = ExtAlert(
        screen,
        'Deploy Result',
        "\n".join(info)
    )
    if button == "ok":
        return

def Import_C15000_settings():
    info_level = 'Info'
    success = []
    fail = []
    ips = get_ips('extra')
    for host in C15000_hosts:
        if host['IP Address'] in ips:
            fail.append(host['IP Address'])
        else:
            success.append(host['IP Address'])
            host['Devices'] = ''
            Vizion_hosts.append(host)

    info = "Import successfully:{}".format(
        "\n\t" + "\n\t".join(success))
    if fail:
        info_level = "Warning"
        info += "\n\nImport failed: Already exists!{}".format(
            "\n\t" + "\n\t".join(fail))

    button = ExtAlert(
        screen,
        '{}: Import Basic Settings'.format(info_level),
        info
    )
    if button == "ok":
        Vizion_hosts_list()

def Global_settings_window():
    data = get_format_data(Extra_global_settings, 'extra_global')
    ret, button, settings = ExtEntryWindow(
        screen,
        'Extra Global Settings',
        'Extar global settings, such as ntpserver, ip range etc',
        data,
        width = 80,
        entryWidth = 80,
        buttons = [ 'Save', 'Cancel', 'Exit']
    )

    if button == "exit":
        return
    if button == "save":
        Extra_global_settings['Ntpserver'] = settings[0]
        Extra_global_settings['IP Range'] = settings[1]
    Vizion_hosts_list()

def C15000_hosts_list():
    ips = [('Add new host', 'add')]
    for host in C15000_hosts:
        ips.append((host['IP Address'], C15000_hosts.index(host)))

    ret, button, lb = ExtListboxChoiceWindow(
        screen,
        'Basic Config',
        "Basic hosts list",
        ips,
        buttons=("prev", "next", "exit"),
        width=50,
        height=5,
    )

    if button == "exit":
        return
    elif button == "next":
        Vizion_hosts_list()
    elif lb is not None:
        C15000_window(lb)

def Vizion_hosts_list():
    ips = [('Add new host', 'add')]
    for host in Vizion_hosts:
        ips.append((host['IP Address'], Vizion_hosts.index(host)))

    ret, button, lb = ExtListboxChoiceWindow(
        screen,
        'Extra Config',
        "Extra config hosts",
        ips,
        buttons=("prev", "next", "import", "global settings", "exit"),
        width=50,
        height=5,
    )

    if button == "exit":
        return
    elif button == "prev":
        C15000_hosts_list()
    elif button == "next":
        button = ExtButtonChoiceWindow(
            screen,
            'Start Install',
            'Are you sure to start install?'
        )
        if button == "ok":
            Progress_window()
        elif button == "cancel":
            Vizion_hosts_list()
    elif button == "import":
        Import_C15000_settings()
    elif button == "global settings":
        Global_settings_window()
    elif lb is not None:
        Vizion_window(lb)

def main():
    try:
        C15000_hosts_list()
    except:
        print traceback.format_exc()
    finally:
        screen.finish()
        return ''

def log(content):
    with open("tt.log", 'a+') as f:
        f.write(str(content) + "\n")

DEPLOY_CONFIG_FILE = "config.ini"
DEPLOY_SCRIPT_FILE = "/home/cg20/install.sh"
#DEPLOY_CONFIG_FILE = "/opt/cg20_deploy_config.ini"
C15000_hosts = []
Vizion_hosts = []
Extra_global_settings = {
    'Ntpserver': '',
    'IP Range': ''
}
screen = SnackScreen()
main()
