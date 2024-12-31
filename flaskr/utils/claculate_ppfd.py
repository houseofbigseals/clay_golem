from scipy.optimize import curve_fit
import numpy as np
import sqlite3

def read_and_filter_data(db_path, start_datetime, end_datetime):
    pass

def approximation_with_r2(func, x, y):
    popt, pcov = curve_fit(f=func, xdata=x, ydata=y)
    print("popt using scipy: {}".format(popt))
    print("pcov using scipy: {}".format(pcov))
    # perr = np.sqrt(np.diag(pcov))
    # print("perr using scipy: {}".format(perr))

    # to compute R2
    # https://stackoverflow.com/questions/19189362/getting-the-r-squared-value-using-curve-fit

    residuals = y - func(x, *popt)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)
    print("r_squared using custom code: {}".format(r_squared))
    return popt, r_squared

def full_linear_approximation(file_, start_datetime, end_datetime):
    """
    Method to get data from csv and calculate F.
    :param file_: path to csv file with data in format 04/26/24,11:30:44,440
    :param start_datetime: string in format '%m/%d/%y,%H:%M:%S'   - like '04/26/24,09:07:00'
    :param end_datetime: string in format '%m/%d/%y,%H:%M:%S'
    :param func: func for approximation in scipy curve_fit
    :return: F, lpopt, r_squared, x_datetime, y, y_lopt
    """
    def lin_func(tt, a, b):
        return a * tt + b
    filtered_data = read_and_filter_data(file_, start_datetime, end_datetime)
    y = np.array(filtered_data['Value'], dtype=int)
    x_datetime = filtered_data.index.values  # scipy cannot work with datetime as args
    x_timestamp = np.array([pd.Timestamp(t).timestamp() for t in x_datetime])  # scipy can work with timestamps
    lpopt, r_squared = approximation_with_r2(lin_func, x_timestamp, y)
    F = -lpopt[0]
    y_lopt = lin_func(x_timestamp, *lpopt)
    # x - time data
    # y - raw co2 data
    # y_lopt  approx co2 data
    return F, lpopt, r_squared, x_datetime, y, y_lopt