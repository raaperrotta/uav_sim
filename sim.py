#sim.py

from model import *
import numpy as n
import scipy.stats as s
from scipy.optimize import curve_fit

def run_sim(distance, num_uavs, num_cwis):

    env = Environment()

    env.ships.append(Ship(env, pos=n.array([0.,0.])))

    env.gen_uavs(num_uavs, distance)

    env.radars.append(Radar(env, period=2., ranges=[60., 20.], p_detect=n.array([0.2, 0.8]), ship=env.ships[0]))

    for ii in range(num_cwis):
        env.add_weapon('CWIS', env.ships[0])

    env.add_weapon('MGS', env.ships[0])
    env.add_weapon('5-inch Gun', env.ships[0])

    env.run(until=env.end_sim)
    results = []
    for ship in env.ships:
        results.append(ship.health)
    return n.mean(results)


# The iterator that calls each iteration and handles the results
def run_batch(num_runs, distance, num_uavs, num_cwis):
    result = 0
    for ii in xrange(num_runs):
        result += run_sim(distance, num_uavs, num_cwis)
        print ii, result

    return float(result)/float(num_runs)


run_batch(10, 1.8e4, 12, 2)


"""
def binom_interval(success, total, confint=0.95):
    quantile = (1 - confint) / 2.
    lower = s.beta.ppf(quantile, success, total - success + 1)
    upper = s.beta.ppf(1 - quantile, success + 1, total - success)
    return (lower, upper)


script execution

num_runs = 1
num_params = 3
X = n.zeros([num_runs*num_params, num_params])
Y = n.zeros([num_runs*num_params, 1])

ii = 0

for distance in n.linspace(20000,30000,num_runs):
    X[ii] = [distance, 12, 2]
    Y[ii] = batch_run(*X[ii])
    ii += 1

for num_uavs in n.linspace(1,31,num_runs):
    X[ii] = [25000, num_uavs, 2]
    Y[ii] = batch_run(*X[ii])
    ii += 1

for num_cwis in n.linspace(1,5,num_runs):
    X[ii] = [25000, 12, num_cwis]
    Y[ii] = batch_run(*X[ii])
    ii += 1

def my_model(x, p):
    x = n.matrix(x)
    x = n.sqrt(x.transpose()*x)
    l = len(p)/2
    print p[:l]
    print p[-l:]

p0 = n.ones(num_params)

my_model(None, p0.tolist())

popt, pcov = curve_fit(my_model, X, Y, p0)
"""
