from scipy.optimize import curve_fit
import numpy as np
#import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from scipy.interpolate import Rbf
from mpl_toolkits.mplot3d import Axes3D
import pickle

def read_and_filter_data(db_path, start_datetime, end_datetime):
    pass

# def approximation_with_r2(func, x, y):
#     popt, pcov = curve_fit(f=func, xdata=x, ydata=y)
#     print("popt using scipy: {}".format(popt))
#     print("pcov using scipy: {}".format(pcov))
#     # perr = np.sqrt(np.diag(pcov))
#     # print("perr using scipy: {}".format(perr))
#
#     # to compute R2
#     # https://stackoverflow.com/questions/19189362/getting-the-r-squared-value-using-curve-fit
#
#     residuals = y - func(x, *popt)
#     ss_res = np.sum(residuals ** 2)
#     ss_tot = np.sum((y - np.mean(y)) ** 2)
#     r_squared = 1 - (ss_res / ss_tot)
#     print("r_squared using custom code: {}".format(r_squared))
#     return popt, r_squared

# def full_linear_approximation(file_, start_datetime, end_datetime):
#     """
#     Method to get data from csv and calculate F.
#     :param file_: path to csv file with data in format 04/26/24,11:30:44,440
#     :param start_datetime: string in format '%m/%d/%y,%H:%M:%S'   - like '04/26/24,09:07:00'
#     :param end_datetime: string in format '%m/%d/%y,%H:%M:%S'
#     :param func: func for approximation in scipy curve_fit
#     :return: F, lpopt, r_squared, x_datetime, y, y_lopt
#     """
#     def lin_func(tt, a, b):
#         return a * tt + b
#     filtered_data = read_and_filter_data(file_, start_datetime, end_datetime)
#     y = np.array(filtered_data['Value'], dtype=int)
#     x_datetime = filtered_data.index.values  # scipy cannot work with datetime as args
#     x_timestamp = np.array([pd.Timestamp(t).timestamp() for t in x_datetime])  # scipy can work with timestamps
#     lpopt, r_squared = approximation_with_r2(lin_func, x_timestamp, y)
#     F = -lpopt[0]
#     y_lopt = lin_func(x_timestamp, *lpopt)
#     # x - time data
#     # y - raw co2 data
#     # y_lopt  approx co2 data
#     return F, lpopt, r_squared, x_datetime, y, y_lopt


def r2_score(y_true, y_pred):
    """
        y_true : array-like
        Actual (observed) values.
        y_pred : array-like
        Predicted values.
        Returns
        -------
        float
        R-squared value
    """
    ss_res = np.sum((y_true - y_pred) ** 2)  # residual sum of squares
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)  # total sum of squares
    return 1 - (ss_res / ss_tot)


import numpy as np


def rmsd(y_true, y_pred):
    """
    Calculate the Root Mean Squared Deviation (RMSD),
    also known as Root Mean Squared Error (RMSE).

    Parameters
    ----------
    y_true : array-like
        Actual (observed) values.
    y_pred : array-like
        Predicted values.

    Returns
    -------
    float
        The RMSD (RMSE) value.
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.sqrt(np.mean((y_true - y_pred) ** 2))


def mae(y_true, y_pred):
    """
    Calculate the Mean Absolute Error (MAE).

    Parameters
    ----------
    y_true : array-like
        Actual (observed) values.
    y_pred : array-like
        Predicted values.

    Returns
    -------
    float
        The MAE value.
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.mean(np.abs(y_true - y_pred))

def poly2d(X, a, b, c, d, e, f):
    """
    2D polynomial surface of degree 2:
    z = a + b*x + c*y + d*x^2 + e*x*y + f*y^2
    X - is vector with red, white pwm duty
    result is ppfd on that duty level
    """
    x, y = X
    return a + b*x + c*y + d*(x**2) + e*(x*y) + f*(y**2)

ppfd_exp_fit_params = [6.11918934, 5.72541582, 5.49188308, 0.00870387, -0.01768939, 0.0090811]

def get_poly_exp_ppfd(red_duty, white_duty):
    return poly2d((red_duty, white_duty), *ppfd_exp_fit_params)

def get_rbf_exp_ppfd(red_duty, white_duty):
    with open("rbf_exp_ppfd_model.pkl", "rb") as f:
        rbf_loaded = pickle.load(f)
        return rbf_loaded(red_duty, white_duty)

def ppfd_curve_fit(data_path="/opt/clay/clay_golem/instance/experiment_data.db"):
    """
    Complex function to get approximation of
    """
    # 1. Connect to the SQLite database
    db_path = data_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 2. Retrieve the relevant data
    cursor.execute("SELECT red_duty, white_duty, ppfd FROM measurements WHERE stand='exp' and point=25")
    rows = cursor.fetchall()
    conn.close()
    print(np.shape(rows))

    # 3. Convert to NumPy arrays
    # rows is a list of tuples: [(red_duty1, white_duty1, ppfd1), (red_duty2, white_duty2, ppfd2), ...]
    reds, whites, ppfd = zip(*rows)  # Unpack into separate iterables
    reds = np.array(reds, dtype=float)
    whites = np.array(whites, dtype=float)
    ppfd = np.array(ppfd, dtype=float)
    print(np.shape(reds))

    # 4. Fit the data using curve_fit
    #    'xdata' will be a tuple: (reds, whites)
    #    'ydata' is the ppfd array
    popt, pcov = curve_fit(f=poly2d, xdata=(reds, whites), ydata=ppfd)
    # x, y, z are 1D arrays of your data
    rbf_model = Rbf(reds, whites, ppfd, function='multiquadric')  # or 'linear', 'cubic', etc.
    # popt now contains the best-fit parameters [a, b, c, d, e, f]
    print("Fitted parameters (a, b, c, d, e, f) =", popt)
    with open("rbf_exp_ppfd_model.pkl", "wb") as f:
        pickle.dump(rbf_model, f)

    # 4. We want to produce a "surface" of ppfd over the grid of (red_duty, white_duty).
    #    If your data is arranged in a full grid (e.g., 0,20,40,60,80,100 for both red and white),
    #    we can do the following:

    # Find unique levels of red_duty and white_duty and sort them
    unique_reds = np.unique(reds)
    unique_whites = np.unique(whites)
    print(unique_reds, unique_whites)

    # Create a meshgrid from these unique values
    #   xx, yy will be 2D arrays, shape = (len(unique_whites), len(unique_reds))
    xx, yy = np.meshgrid(unique_reds, unique_whites)
    # print (xx, yy)

    # Also
    # Flatten xx, yy so we can plug them into poly2d
    xx_flat = xx.ravel()
    yy_flat = yy.ravel()

    # Initialize zz (for the ppfd surface) with zeros (or NaNs)
    zz = np.zeros_like(xx, dtype=float)

    # Predict z-values (the surface) using the fitted parameters
    zz_fit_flat = poly2d((xx_flat, yy_flat), *popt)
    z_rbf_pred = rbf_model(xx_flat, yy_flat)
    # print(zz_fit_flat)
    # print(ppfd)

    print(get_poly_exp_ppfd(0, 0))
    print(get_poly_exp_ppfd(100, 0))
    print(get_poly_exp_ppfd(0, 100))
    print(get_poly_exp_ppfd(40, 40))

    print(rbf_model(0, 0))
    print(rbf_model(100, 0))
    print(rbf_model(0, 100))
    print(rbf_model(40, 40))


    # lets calculate R^2 for fitted data
    r2 = r2_score(ppfd, zz_fit_flat)
    rmsd_ = rmsd(ppfd, zz_fit_flat)
    mae_ = mae(ppfd, zz_fit_flat)
    print(f"R^2 = {r2}, RMSD = {rmsd_}, MAE= {mae_}")
    r2 = r2_score(ppfd, z_rbf_pred)
    rmsd_ = rmsd(ppfd, z_rbf_pred)
    mae_ = mae(ppfd, z_rbf_pred)
    print(f"R^2 = {r2}, RMSD = {rmsd_}, MAE= {mae_}")

    # zz_fit = zz_fit_flat.reshape(xx.shape)  # reshape back to 2D
    zz_fit = z_rbf_pred.reshape(xx.shape)

    # Fill zz by matching (red_duty, white_duty) pairs in the fetched data
    for i, red_val in enumerate(unique_reds):
        for j, white_val in enumerate(unique_whites):
            # mask where red_duty == red_val and white_duty == white_val
            mask = (reds == red_val) & (whites == white_val)
            # print(mask)
            # print(ppfd[mask])
            # Store the ppfd value in the surface array (assuming there's exactly one match)
            if np.any(mask):
                zz[j, i] = ppfd[mask][0]

    print(zz)

    # 5. Plot using Matplotlib's 3D Surface Plot
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection='3d')

    # (A) Scatter plot of the real data
    ax.scatter(reds, whites, ppfd, color='r', label='Data')

    # (B) Surface plot of the fitted polynomial
    surf = ax.plot_surface(xx, yy, zz_fit, alpha=0.5, cmap='viridis')
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label="Fitted PPFD")
    ax.set_xlabel("Red Duty")
    ax.set_ylabel("White Duty")
    ax.set_zlabel("PPFD")
    ax.set_title("RBF fit: PPFD vs. (Red Duty, White Duty)")
    ax.legend()

    # # Create the surface
    # surf = ax.plot_surface(xx, yy, zz, cmap='viridis', edgecolor='none', alpha=0.8)
    # ax.set_xlabel("Red Duty")
    # ax.set_ylabel("White Duty")
    # ax.set_zlabel("PPFD")
    #
    # # Optional: add a colorbar for the surface
    # fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label="PPFD")
    #
    # plt.title("PPFD as a function of Red Duty and White Duty")

    plt.tight_layout()
    plt.show()
    # fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    #
    # # Make data.
    # X = np.arange(-5, 5, 0.25)
    # Y = np.arange(-5, 5, 0.25)
    # print(np.shape(X))
    # print(np.shape(Y))
    # X, Y = np.meshgrid(X, Y)
    # R = np.sqrt(X ** 2 + Y ** 2)
    # Z = np.sin(R)
    # print(np.shape(X))
    # print(np.shape(Y))
    # print(np.shape(R))
    # print(np.shape(Z))
    #
    # # Plot the surface.
    # surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm,
    #                        linewidth=0, antialiased=False)
    #
    # # Customize the z axis.
    # ax.set_zlim(-1.01, 1.01)
    # ax.zaxis.set_major_locator(LinearLocator(10))
    # # A StrMethodFormatter is used automatically
    # ax.zaxis.set_major_formatter('{x:.02f}')
    #
    # # Add a color bar which maps values to colors.
    # fig.colorbar(surf, shrink=0.5, aspect=5)
    #
    # plt.show()

if __name__ == "__main__":

    # ppfd_curve_fit()

    print(get_poly_exp_ppfd(0, 0))
    print(get_poly_exp_ppfd(100, 0))
    print(get_poly_exp_ppfd(0, 100))
    print(get_poly_exp_ppfd(40, 40))

    print(get_rbf_exp_ppfd(0, 0))
    print(get_rbf_exp_ppfd(100, 0))
    print(get_rbf_exp_ppfd(0, 100))
    print(get_rbf_exp_ppfd(40, 40))


