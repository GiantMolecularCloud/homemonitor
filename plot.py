"""
Periodically generate statistics plots
To be displayed on the homeserver statistics page
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator
from datetime import datetime,timedelta

# force grid to background for all plots
plt.rcParams['axes.axisbelow'] = True


#############################################################################
# homemonitor plots
#############################################################################

class homemonitor_plot:
    """
    A class to plot some statistics.
    """

    def __init__(self):
        """
        Initialize plot information
        """

        self.data      = None
        self.templim   = None
        self.co2lim    = None
        self.plotdir   = 'static'
        self.logname   = 'home'         # hard coded for now
        self.figwidth  = 6              # inches
        self.fontsize  = 10
        self.day_plot  = None
        self.hist_plot = None


#############################################################################
    def load_data(self):
        """
        Load dataset and determine plot ranges
        """
        print("Starting loading data")

        # load data
        self.data = np.genfromtxt(os.path.join('logs',self.logname+'.csv'), delimiter=',', skip_header=1, dtype=('U19','<i8','<f8'), names=('date','co2','temp'))

        #calculate limits for plotting
        self.templim = (np.nanmin(self.data['temp']), np.nanmax(self.data['temp']))
        self.templim = (self.templim[0]-0.05*(self.templim[1]-self.templim[0]), self.templim[1]+0.05*(self.templim[1]-self.templim[0]))
        self.co2lim  = (np.nanmin(self.data['co2']), np.nanmax(self.data['co2']))
        self.co2lim  = (self.co2lim[0]-0.05*(self.co2lim[1]-self.co2lim[0]), self.co2lim[1]+0.05*(self.co2lim[1]-self.co2lim[0]))
        print("Finished loading data")

#############################################################################
    def plot_day(self):
        print("Starting plot: 24h")

        # set up figure
        fig = plt.figure(figsize=(self.figwidth,0.75*self.figwidth))
        gs  = GridSpec(2,1)
        gs.update(left=0.1, right=0.95, top=0.9, bottom=0.1, hspace=0.05, wspace=0.0)
        ax_t = plt.subplot(gs[0, 0:])
        ax_co = plt.subplot(gs[1, 0:], sharex=ax_t)

        # plot 2D histograms over time as hexbin
        ax_t.hexbin([int(h)+int(m)/60.+int(s)/3600 for h,m,s in [x[11:19].split(':') for x in self.data['date']]],
                    self.data['temp'], gridsize=100, cmap='Reds', mincnt=1, extent=(0,24,self.templim[0],self.templim[1]), norm=colors.PowerNorm(gamma=0.5))
        ax_co.hexbin([int(h)+int(m)/60.+int(s)/3600 for h,m,s in [x[11:19].split(':') for x in self.data['date']]],
                     self.data['co2'], gridsize=100, cmap='Blues', mincnt=1, extent=(0,24,self.co2lim[0],self.co2lim[1]), norm=colors.PowerNorm(gamma=0.5))

        # format figure, labels, ticks
        ax_t.set_title("Last updated "+datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fontsize=self.fontsize)
        ax_t.grid(True)
        ax_co.grid(True)
        ax_t.xaxis.tick_top()
        ax_t.xaxis.set_label_position('top')
        ax_t.set_xlabel(r"Hour of the day", fontsize=self.fontsize)
        ax_co.set_xlabel(r"Hour of the day", fontsize=self.fontsize)
        ax_t.set_ylabel(r"temperature [$^\circ$C]", fontsize=self.fontsize)
        ax_co.set_ylabel(r"CO2 concentration [ppm]", fontsize=self.fontsize)
        ax_t.tick_params(axis='both', which='major', labelsize=self.fontsize)
        ax_co.tick_params(axis='both', which='major', labelsize=self.fontsize)
        ax_t.set_xscale('linear')
        ax_t.set_yscale('linear')
        ax_co.set_yscale('linear')
        ax_t.set_xlim(-0.5,24.5)
        ax_t.set_ylim(self.templim)
        ax_co.set_ylim(self.co2lim)
        ax_t.xaxis.set_major_locator(MultipleLocator(1))
        ax_t.yaxis.set_major_locator(MultipleLocator(2.5))
        ax_co.yaxis.set_major_locator(MultipleLocator(500))
        fig.savefig(os.path.join(self.plotdir,self.logname+'.24h.svg'), bbox_inches='tight')

        # store figure for later use
        self.day_plot = fig

        print("Finished plot: 24h")

#############################################################################

    # CO2 vs. temperature
    def plot_hist(self):
        print("Starting plot: histogram")

        # set up figure and its panels
        fig = plt.figure(figsize=(self.figwidth,self.figwidth))
        gs = GridSpec(4,4)
        gs.update(left=0.1, right=1., top=1., bottom=0.1, hspace=0.0, wspace=0.0)
        ax_t = plt.subplot(gs[0, :-1])
        ax_tco = plt.subplot(gs[1:, :-1], sharex=ax_t)
        ax_co = plt.subplot(gs[1:, -1], sharey=ax_tco)
        ax_t.spines['left'].set_visible(False)
        ax_t.spines['right'].set_visible(False)
        ax_t.spines['top'].set_visible(False)
        ax_co.spines['right'].set_visible(False)
        ax_co.spines['top'].set_visible(False)
        ax_co.spines['bottom'].set_visible(False)
        ax_t.tick_params(axis='both', which='both', bottom=True, top=False, left=False, right=False, labelbottom=False, labeltop=False, labelleft=False, labelright=False)
        ax_co.tick_params(axis='both', which='both', bottom=False, top=False, left=True, right=False, labelbottom=False, labeltop=False, labelleft=False, labelright=False)

        # plot 2D histogram as hexbin
        ax_tco.hexbin(self.data['temp'], self.data['co2'], gridsize=50, cmap='Blues', mincnt=1, norm =colors.PowerNorm(gamma=0.5))

        # plot marginalizations
        hist_temp1 = ax_t.hist(self.data['temp'], bins=50, histtype='stepfilled', color='black', label='all time')
        hist_co21 = ax_co.hist(self.data['co2'],  bins=50, histtype='stepfilled', color='black', label='all time', orientation='horizontal')

        # get date of last week and last month
        today = datetime.now()
        last_week  = today - timedelta(days=7)
        last_week  = last_week.strftime('%Y-%m-%d %H:%M:%S')
        last_month = today - timedelta(days=30)
        last_month = last_month.strftime('%Y-%m-%d %H:%M:%S')
        last_3month = today - timedelta(days=90)
        last_3month = last_3month.strftime('%Y-%m-%d %H:%M:%S')

        # get data index of last week and last month
        self.idx_3month = 0
        self.idx_month  = 0
        self.idx_week   = 0
        for i in np.arange(len(self.data)-1,0,-1):
            if ( self.data['date'][i] > last_week ):
                self.idx_week = i
            if ( self.data['date'][i] > last_month ):
                self.idx_month = i
            if ( self.data['date'][i] > last_3month ):
                self.idx_3month = i
            else:
                break

        # plot historic marginalizations
        ax_t.hist(self.data['temp'][self.idx_3month:-1], bins=hist_temp1[1], histtype='stepfilled', color='midnightblue', label='last 3 months')
        ax_co.hist(self.data['co2'][self.idx_3month:-1], bins=hist_co21[1],  histtype='stepfilled', color='midnightblue', orientation='horizontal', label='last 3 months')
        ax_t.hist(self.data['temp'][self.idx_month:-1], bins=hist_temp1[1], histtype='stepfilled', color='dodgerblue', label='last month')
        ax_co.hist(self.data['co2'][self.idx_month:-1], bins=hist_co21[1],  histtype='stepfilled', color='dodgerblue', orientation='horizontal', label='last month')
        ax_t.hist(self.data['temp'][self.idx_week:-1], bins=hist_temp1[1], histtype='stepfilled', color='aqua', label='last week' )
        ax_co.hist(self.data['co2'][self.idx_week:-1], bins=hist_co21[1],  histtype='stepfilled', color='aqua', orientation='horizontal', label='last week')

        # finish figure
        ax_t.set_title("Last updated "+datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fontsize=self.fontsize)
        ax_tco.grid(True)
        ax_t.xaxis.grid(True)
        ax_co.yaxis.grid(True)
        ax_tco.set_xlabel(r"temperature [$^\circ$C]", fontsize=self.fontsize)
        ax_tco.set_ylabel(r"CO concentration [ppm]", fontsize=self.fontsize)
        ax_tco.tick_params(axis='both', which='major', labelsize=self.fontsize)
        ax_tco.set_xscale('linear')
        ax_tco.set_yscale('linear')
        ax_tco.set_xlim(self.templim)
        ax_tco.set_ylim(self.co2lim)
        ax_t.legend(loc='lower left', numpoints=1, bbox_to_anchor=(1.0,0.0,0.33,1.0), ncol=1, mode="expand", borderaxespad=0., fontsize=self.fontsize, frameon=False)
        fig.savefig(os.path.join(self.plotdir,self.logname+'.hist.svg'), bbox_inches='tight')

        # store figure for later use
        self.hist_plot = fig

        print("Finished plot: histogram")


#############################################################################
# Generate plots
#############################################################################

def generate_plots():
    """
    Generate the plots and save them to be displayed by the server
    """

    hmp = homemonitor_plot()
    hmp.load_data()
    hmp.plot_day()
    hmp.plot_hist()


#############################################################################
#############################################################################

# frequency analysis
####################

# plt.clf()
# f, Pxx = signal.periodogram(self.data['temp'], 1.)
# plt.loglog(f, Pxx)
# plt.xlabel('frequency [Hz]')
# plt.ylabel('signal')
# plt.xlim(1e-6,1e-2)
# plt.ylim(1e-1,1e7)
#
#
#
#
# plt.clf()
# f, Pxx = signal.periodogram(self.data['co2'], 1.)
# plt.loglog(f, Pxx)
# plt.xlabel('frequency [Hz]')
# plt.ylabel('signal')
# plt.xlim(1e-6,1e-2)
# plt.ylim(1e1,1e10)
#
#
# def smooth(x, box_pts):
#     box = np.ones(box_pts)/box_pts
#     x_smooth = np.convolve(x, box, mode='same')
#     return x_smooth
#
# plt.clf()
# f, Pxx = signal.periodogram(smooth(self.data['temp'],100), 1.)
# plt.loglog(f, Pxx)
# plt.xlabel('frequency [Hz]')
# plt.ylabel('signal')
# plt.xlim(1e-6,1e-1)
# plt.ylim(1e-4,1e7)
