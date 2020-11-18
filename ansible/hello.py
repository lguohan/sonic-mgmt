#!/usr/bin/env python3

import re
import sys
import subprocess
from flask import Flask, request
from markupsafe import escape
app = Flask(__name__)

def run_cmd(cmdline):
#    with open(cmd_debug_fname, 'a') as fp:
#        fp.write("CMD: %s\n" % cmdline)

    cmd = cmdline.split(' ')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    ret_code = process.returncode

    if ret_code != 0:
        raise Exception("ret_code=%d, error message=%s. cmd=%s" % (ret_code, stderr, cmdline))

# with open(cmd_debug_fname, 'a') as fp:
#        fp.write("OUTPUT: \n%s" % stdout.decode('utf-8'))

    return stdout.decode('utf-8')

def get_mux_cable_active_side(tbname, portindex):
    cmdline = "ovs-ofctl dump-flows --names mbr-{}-{}".format(tbname, portindex)
    out = run_cmd(cmdline)

    sides = None
    activeside = None
    nicport = None
    activeside_index = "-1"

    for l in out.split('\n'):
        m = re.search("in_port=\"(muxy-.*)\" actions=output:\"(.*)\",output:\"(.*)\"", l)
        if m:
            nicport = m.group(1)
            sides = sorted([m.group(2), m.group(3)])
        else:
            m = re.search("in_port=\"(.*)\" actions=output:\"muxy-".format(tbname), l)
            if m:
                activeside = m.group(1)

    if sides is not None and activeside is not None:
        activeside_index = str(sides.index(activeside))

    return (activeside_index, sides, nicport)

def set_mux_cable_active_side(tbname, portindex, activeside):

    (current_activeside, sides, nicport) = get_mux_cable_active_side(tbname, portindex)

    if current_activeside and current_activeside != activeside:
        run_cmd("ovs-ofctl del-flows --names mbr-{}-{} in_port=\"{}\"".format(tbname, portindex, sides[int(current_activeside)]))

    run_cmd("ovs-ofctl add-flow --names mbr-{}-{} in_port=\"{}\",actions=output:\"{}\"".format(tbname, portindex, sides[int(activeside)], nicport))

@app.route('/')
def hello_world():
    return 'Hello, World!'

# Setup a command route to listen for prefix advertisements
@app.route('/muxycable/side/<tbname>/<portindex>/<dutname>')
def mux_cable_get_side(tbname, dutname, portname):
    return '{}:{}'.format(tbname, dutname)

@app.route('/muxycable/activeside/<tbname>/<portindex>', methods = ['GET', 'POST'])
def mux_cable_active_side(tbname, portindex):
    if request.method == 'GET':

        (activeside, _, _) = get_mux_cable_active_side(tbname, portindex)

        return "{}\n".format(activeside)

    elif request.method == 'POST':

        activeside = request.form['side']
        if activeside not in ["0", "1"]:
            return "NOT OK\n"

        set_mux_cable_active_side(tbname, portindex, activeside)

        return "OK\n"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=sys.argv[1])
