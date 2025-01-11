import pickle

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

def get_exp_duty_by_ppfd(ppfd_red, ppfd_white):
    pass


if __name__ == "__main__":
    print(get_rbf_exp_ppfd(100, 100))