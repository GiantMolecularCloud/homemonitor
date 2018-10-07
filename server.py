""" Flask server for HomeMonitor
    Adapted from CO2meter: https://github.com/vfilimonov/co2meter.git
"""
import optparse
import logging
import threading
import time
import glob
import os
import socket
import signal
import json

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import flask
from flask import request, render_template, jsonify
import pandas as pd

import co2meter as co2

_DEFAULT_PORT = '8008'
_DEFAULT_INTERVAL = 30  # seconds
_DEFAULT_NAME = 'home'
_INIT_TIME = 30  # time to initialize and calibrate device
_URL = 'https://github.com/vfilimonov/co2meter'

_COLORS = {'r': '#E81F2E', 'y': '#FAAF4C', 'g': '#7FB03F'}
_IMG_G = '1324881/36358454-d707e2f4-150e-11e8-9bd1-b479e232f28f'
_IMG_Y = '1324881/36358456-d8b513ba-150e-11e8-91eb-ade37733b19e'
_IMG_R = '1324881/36358457-da3e3e8c-150e-11e8-85af-855571275d88'
_RANGE_MID = [800, 1200]

_name = _DEFAULT_NAME

###############################################################################
mon = None

###############################################################################
app = flask.Flask(__name__)
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True


###############################################################################
@app.route('/')
def home():
    # Read CO2 and temp values
    if mon is None:
        status = '<h1 align="center" style="color:%s;">Device is not connected</h1>' % _COLORS['r']
    else:
        status = ''
    try:
        vals = list(mon._last_data)
        vals[-1] = '%.1f' % vals[-1]
    except:
        data = read_logs()
        vals = data.split('\n')[-2].split(',')
        if status == '':
            status = '<h1 align="center" style="color:%s;">Device is not ready</h1>' % _COLORS['r']
    # Select image and color
    if int(vals[1]) >= _RANGE_MID[1]:
        color = _COLORS['r']
        img = _IMG_R
    elif int(vals[1]) < _RANGE_MID[0]:
        color = _COLORS['g']
        img = _IMG_G
    else:
        color = _COLORS['y']
        img = _IMG_Y
    co2 = '<font color="%s">%s ppm</font>' % (color, vals[1])
    # Return template
    return render_template('index.html', image=img, timestamp=vals[0],
                           co2=vals[1], color=color, temp=vals[2], url=_URL,
                           status=status)


#############################################################################
@app.route('/log', defaults={'logname': None})
@app.route('/log/<string:logname>')
def log(logname):
    data = read_logs(name=logname)
    return '<h1>Full log</h1>' + wrap_table(data)


@app.route('/log.csv', defaults={'logname': None})
@app.route('/log/<string:logname>.csv')
def log_csv(logname):
    data = read_logs(name=logname)
    return wrap_csv(data, logname)


@app.route('/log.json', defaults={'logname': None})
@app.route('/log/<string:logname>.json')
def log_json(logname):
    data = read_logs(name=logname)
    return wrap_json(data)


#############################################################################
@app.route('/rename')
def get_shape_positions():
    args = request.args
    logging.info('rename', args.to_dict())
    new_name = args.get('name', default=None, type=str)
    if new_name is None:
        return 'Error: new log name is not specified!'
    global _name
    _name = new_name
    return 'Log name has changed to "%s"' % _name


#############################################################################
@app.route('/kill')
def shutdown():
    server_stop()
    global _monitoring
    _monitoring = False
    return 'Server shutting down...'


#############################################################################
# Dashboard on plotly.js
#############################################################################
def prepare_data(name=None, span='24H'):
    data = read_logs(name)
    data = pd.read_csv(StringIO(data), parse_dates=[0]).set_index('timestamp')
    if span != 'FULL':
        data = data.last(span)

    if span == '24H':
        data = data.resample('60s').mean()
    elif span == '7D':
        data = data.resample('600s').mean()
    elif span == '30D':
        data = data.resample('1H').mean()
    elif span == 'FULL':
        if len(data) > 3000:  # Resample only long series
            data = data.resample('1H').mean()
    data = data.round({'co2': 0, 'temp': 1})
    return data

def rect(y0, y1, color):
    return {'type': 'rect', 'layer': 'below',
            'xref': 'paper', 'x0': 0, 'x1': 1,
            'yref': 'y', 'y0': y0, 'y1': y1,
            'fillcolor': color, 'opacity': 0.2, 'line': {'width': 0}}


def caption(title, x, y):
    return {'xref': 'paper', 'yref': 'paper', 'x': x, 'y': y, 'text': title,
            'showarrow': False, 'font': {'size': 16},
            'xanchor': 'center', 'yanchor': 'bottom'}


#############################################################################
@app.route("/chart/", strict_slashes=False)
@app.route("/chart/<name>", strict_slashes=False)
@app.route("/chart/<name>/<freq>", strict_slashes=False)
def chart_co2_temp(name=None, freq='24H'):
    data = prepare_data(name, freq)

    co2_min = min(350, data['co2'].min() - 50)
    co2_max = max(2000, data['co2'].max() + 50)
    t_min = data['temp'].min()-2
    t_max = data['temp'].max()+2

    rect_green = rect(co2_min, _RANGE_MID[0], _COLORS['g'])
    rect_yellow = rect(_RANGE_MID[0], _RANGE_MID[1], _COLORS['y'])
    rect_red = rect(_RANGE_MID[1], co2_max, _COLORS['r'])

    # Check if mobile
    try:
        agent = request.headers.get('User-Agent')
        phones = ['iphone', 'android', 'blackberry', 'fennec', 'iemobile']
        staticPlot = any(phone in agent.lower() for phone in phones)
    except RuntimeError:
        staticPlot = False

    # Make figure
    index = data.index.format()
    co2 = list(pd.np.where(data.co2.isnull(), None, data.co2))
    temp = list(pd.np.where(data.temp.isnull(), None, data.temp))

    d_co2 = {'mode': 'lines+markers', 'type': 'scatter',
             'name': 'CO2 concentration',
             'xaxis': 'x1', 'yaxis': 'y1',
             'x': index, 'y': co2}
    d_temp = {'mode': 'lines+markers', 'type': 'scatter',
              'name': 'Temperature',
              'xaxis': 'x1', 'yaxis': 'y2',
              'x': index, 'y': temp}
    ann_co2min = {'x': str(data['co2'].idxmin()),
                  'y': data['co2'].min(),
                  'xref': 'x1',
                  'yref': 'y1',
                  'text': str(data['co2'].min()),
                  'hovertext': 'minimum\nCO2: '+str(data['co2'].min())+'\ndate: '+str(data['co2'].idxmin()),
                  'showarrow': True,
                  'arrowhead': 1,
                  'ax': 0,
                  'ay': -25
                 }
    ann_co2max = {'x': str(data['co2'].idxmax()),
                  'y': data['co2'].max(),
                  'xref': 'x1',
                  'yref': 'y1',
                  'text': str(data['co2'].max()),
                  'hovertext': 'maximum\nCO2: '+str(data['co2'].max())+'\ndate: '+str(data['co2'].idxmax()),
                  'showarrow': True,
                  'arrowhead': 1,
                  'ax': 0,
                  'ay': -25
                 }
    ann_tempmin = {'x': str(data['temp'].idxmin()),
                   'y': data['temp'].min(),
                   'xref': 'x1',
                   'yref': 'y2',
                   'text': str(data['temp'].min()),
                   'hovertext': 'minimum\ntemperature: '+str(data['temp'].min())+'\ndate: '+str(data['temp'].idxmin()),
                   'showarrow': True,
                   'arrowhead': 1,
                   'ax': 0,
                   'ay': -25
                 }
    ann_tempmax = {'x': str(data['temp'].idxmax()),
                   'y': data['temp'].max(),
                   'xref': 'x1',
                   'yref': 'y2',
                   'text': str(data['temp'].max()),
                   'hovertext': 'maximum\ntemperature: '+str(data['temp'].max())+'\ndate: '+str(data['temp'].idxmax()),
                   'showarrow': True,
                   'arrowhead': 1,
                   'ax': 0,
                   'ay': -25
                 }

    config = {'displayModeBar': False, 'staticPlot': staticPlot}
    layout = {'margin': {'l': 30, 'r': 10, 'b': 30, 't': 30},
              'showlegend': False,
              'shapes': [rect_green, rect_yellow, rect_red],
              'xaxis1': {'domain': [0, 1], 'anchor': 'y2'},
              'yaxis1': {'domain': [0.55, 1], 'anchor': 'free', 'position': 0,
                         'range': [co2_min, co2_max]},
              'yaxis2': {'domain': [0, 0.45], 'anchor': 'x1',
                         'range': [t_min, t_max]},
              'annotations': [caption('CO2 concentration', 0.5, 1),
                              caption('Temperature', 0.5, 0.45),
                              ann_co2min, ann_co2max,
                              ann_tempmin, ann_tempmax]
              }
    fig = {'data': [d_co2, d_temp], 'layout': layout, 'config': config}
    return jsonify(fig)


#############################################################################
@app.route("/dashboard")
def dashboard_plotly():
    # Get list of files
    files = glob.glob('logs/*.csv')
    files = [os.path.splitext(os.path.basename(_))[0] for _ in files]
    # And find selected for jinja template
    files = [(_, _ == _name) for _ in files]
    return render_template('dashboard.html', files=files)


#############################################################################
# Monitoring routines
#############################################################################
def read_logs(name=None):
    """ read log files """
    if name is None:
        name = _name
    with open(os.path.join('logs', name + '.csv'), 'r') as f:
        data = f.read()
    return data


#############################################################################
def write_to_log(vals):
    """ file name for a current log """
    # Create file if does not exist
    fname = os.path.join('logs', _name + '.csv')
    if not os.path.exists('logs'):
        os.makedirs('logs')
    if not os.path.isfile(fname):
        with open(fname, 'a') as f:
            f.write('timestamp,co2,temp\n')
    # Append to file
    with open(fname, 'a') as f:
        f.write('%s,%d,%.1f\n' % vals)


def read_co2_data():
    """ A small hack to read co2 data from monitor in order to account for case
        when monitor is not initialized yet
    """
    global mon
    if mon is None:
        # Try to initialize
        try:
            mon = co2.CO2monitor()
            # Sleep. If we read from device before it is calibrated, we'll
            # get wrong values
            time.sleep(_INIT_TIME)
        except OSError:
            return None
    try:
        return mon.read_data_raw(max_requests=1000)
    except OSError:
        # We kill the link and will require to initialize monitor again next time
        mon = None
        return None


def monitoring_CO2(interval):
    """ Tread for monitoring / logging """
    while _monitoring:
        # Request concentration and temperature
        vals = read_co2_data()
        if vals is None:
            logging.info('[%s] monitor is not connected' % co2.now())
        else:
            # Write to log and sleep
            logging.info('[%s] %d ppm, %.1f deg C' % tuple(vals))
            write_to_log(vals)
        # Sleep for the next call
        time.sleep(interval)


#############################################################################
def start_monitor(interval=_DEFAULT_INTERVAL):
    """ Start CO2 monitoring in a thread """
    logging.basicConfig(level=logging.INFO)

    global _monitoring
    _monitoring = True
    t = threading.Thread(target=monitoring_CO2, args=(interval,))
    t.start()
    return t


#############################################################################
# Server routines
#############################################################################
def my_ip():
    """ Get my local IP address """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))  # Google Public DNS
        return s.getsockname()[0]


#############################################################################
def start_server():
    """ Runs Flask instance using command line arguments """
    # Based on http://flask.pocoo.org/snippets/133/

    host = my_ip()
    parser = optparse.OptionParser()
    parser.add_option("-H", "--host",
                      help="Hostname of the Flask app [default %s]" % host,
                      default=host)
    parser.add_option("-P", "--port",
                      help="Port for the Flask app [default %s]" % _DEFAULT_PORT,
                      default=_DEFAULT_PORT)
    parser.add_option("-I", "--interval",
                      help="Interval in seconds for CO2meter requests [default %d]" % _DEFAULT_INTERVAL,
                      default=_DEFAULT_INTERVAL)
    parser.add_option("-N", "--name",
                      help="Name for the log file [default %s]" % _DEFAULT_NAME,
                      default=_DEFAULT_NAME)
    parser.add_option("-m", "--nomonitoring",
                      help="No live monitoring (only flask server)",
                      action="store_true", dest="no_monitoring")
    parser.add_option("-s", "--noserver",
                      help="No server (only monitoring to file)",
                      action="store_true", dest="no_server")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug",
                      help=optparse.SUPPRESS_HELP)
    options, _ = parser.parse_args()

    if options.debug and not options.no_monitoring:
        parser.error("--debug option could be used only with --no_monitoring")
    global _name
    _name = options.name

    # Start monitoring
    if not options.no_monitoring:
        start_monitor(interval=int(options.interval))

    # Start server
    if not options.no_server:
        app.run(debug=options.debug, host=options.host, port=int(options.port))


def stop_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


###############################################################################
def wrap_csv(data, fname='output'):
    """ Make CSV response downloadable """
    if fname is None:
        fname = 'log'
    si = StringIO(data)
    output = flask.make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=%s.csv" % fname
    output.headers["Content-type"] = "text/csv"
    return output


def wrap_json(data):
    """ Convert CSV to JSON and make it downloadable """
    entries = [_.split(',') for _ in data.split('\n') if _ != '']
    js = [{k: v for k, v in zip(['timestamp', 'co2', 'temp'], x)}
          for x in entries[1:]]
    return jsonify(js)


def wrap_table(data):
    """ Return HTML for table """
    res = ('<table><thead><tr><th>Timestamp</th><th>CO2 concentration</th>'
           '<th>Temperature</th></tr></thead><tbody>')
    for line in data.split('\n')[1:]:
        res += '<tr>' + ''.join(['<td>%s</td>' % d for d in line.split(',')]) + '</tr>'
    res += '</tbody></table>'
    return res


###############################################################################
if __name__ == '__main__':
    # start_server() will take care of start_monitor()
    start_server()
