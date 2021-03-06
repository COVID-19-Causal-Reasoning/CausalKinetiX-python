"""
utility class and functions related to B-spline for Python implementation.

Example
-------
data1 = np.array([0,1,2,3,4,5,6,7,8,9,10])
data2 = np.random.rand(15)*10;data2.sort()
xx = np.array([i/100 for i in range(1001)])
BB = get_BSbasis(data1)
# plot b-spline basis
for PP in BB:
    plt.plot(xx,PP(xx))

# plot heatmap of basis matrix
basis_mat = get_basis_matrix(data2, BB)
plt.imshow(basis_mat, cmap=plt.cm.Greys, interpolation='nearest')

# plot heatmap of derivative matrix
deriv_mat = get_deriv_matrix(data2, BB)
plt.imshow(deriv_mat, cmap=plt.cm.Greys, interpolation='nearest')

# plot heatmap of penalty matrix
pen_mat = get_penalty_matrix(BB)
plt.imshow(pen_mat, cmap=plt.cm.Greys, interpolation='nearest')
"""

import numpy as np
import scipy.interpolate


class PP_Cubic:
    """
    description
    -----------
    Cubic Piecewise polynomial object.
    (Cubic stand for 3rd order (e.g. x^3 + 8*x^2 + 3*x + 9) and 4 consequent intervals)
    """
    def __init__(self, idx, knots, coefs):
        assert(len(knots) == 5)
        assert(type(knots) == np.ndarray)
        assert(coefs.shape == (4, 4)) #coefs
        assert((knots[:-1] > knots[1:]).sum() == 0) # check if sorted
        self.idx = idx
        self.knots = knots
        self.coefs = coefs #[piece_id, term_order]

    def __call__(self, vec):
        """
        get basis matrix for given data points(vec).
        """
        assert(type(vec) == np.ndarray)

        def eval_PP(x):
            if not (self.knots[0] <= x and x <= self.knots[4]):
                return 0
            elif (self.knots[0] <= x and x <= self.knots[1]):
                return sum(self.coefs[0, k]*(x-self.knots[0])**(3-k) for k in range(4))
            elif (self.knots[1] <= x and x <= self.knots[2]):
                return sum(self.coefs[1, k]*(x-self.knots[1])**(3-k) for k in range(4))
            else:
                idx = min(3, (self.knots <= x).sum() - 1)
                return sum(self.coefs[idx, k]*(x-self.knots[idx])**(3-k) for k in range(4))
        return np.vectorize(eval_PP, otypes=[np.float])(vec)

    # define method for penalty term
    # e.g. differenciate both basis twice and multiply and integrate over the domain of the data 
    def __mod__(PP1, PP2):
        # for broadcasting, override mod operator (%).
        """
        get the piecewise polynomial which is a product of derivatives of given piecewise polynomials.
        used for calculating pernalty matrix.
        """
        if np.abs(PP1.idx - PP2.idx) > 3:
            return 0.

        def conv(A, B):
            # for utility
            # multiplication of polinomials are equivalent to convolution of the coefficient vector
            return np.array([np.convolve(a, b) for (a, b) in zip(A, B)])

        PP1 = PP1.differentiate().differentiate()
        PP2 = PP2.differentiate().differentiate()

        if PP1.idx < PP2.idx:
            prod_coefs = np.zeros([4, 4])
            prod_coefs[PP2.idx-PP1.idx:, 1:] = conv(PP1.coefs[PP2.idx-PP1.idx:, 2:], PP2.coefs[:PP1.idx-PP2.idx, 2:])
            # "[,2:]"...second derivative is polynomial of degree 1 (order 2).
            # So coefficients of the higher degrees can be ignored.
        elif PP1.idx == PP2.idx:
            prod_coefs = np.zeros([4, 4])
            prod_coefs[:, 1:] = conv(PP1.coefs[:, 2:], PP2.coefs[:, 2:])
            # "[,2:]"...second derivative is polynomial of degree 1 (order 2).
            # So coefficients of the higher degrees can be ignored.
        elif PP1.idx > PP2.idx:
            prod_coefs = np.zeros([4, 4])
            prod_coefs[:PP2.idx-PP1.idx, 1:] = conv(PP1.coefs[:PP2.idx-PP1.idx, 2:], PP2.coefs[PP1.idx-PP2.idx:, 2:])
            # "[,2:]"...second derivative is polynomial of degree 1 (order 2).
            # So coefficients of the higher degrees can be ignored.
        else:
            raise(Exception(""))

        total = 0
        for i in range(4):
            total -= np.poly1d(prod_coefs[i, :]).integ()(0)
            total += np.poly1d(prod_coefs[i, :]).integ()(PP1.knots[i+1]-PP1.knots[i])
        return total

    def differentiate(self):
        out_coefs = np.zeros([4, 4])
        for i in range(4):
            tmp_coef = np.poly1d(self.coefs[i, :]).deriv().coefficients
            out_coefs[i, 4-len(tmp_coef):] = tmp_coef
        return PP_Cubic(self.idx, self.knots, out_coefs)


def get_BSbasis(data):
    """
    parameter
    ---------
    data : 1d-array.

    return
    ------
    basis : array of PP_Cubic object.

    description
    -----------
    construct bspline object from the given data points.
    one PP_Cubic object represents one B-spline basis.
    len(data) + 2 basises are needed for B-spline interpolation
    """
    assert(type(data) == np.ndarray)
    data_padded = np.concatenate([[data[0]]*3, data, [data[-1]]*3])
    basis = np.zeros([len(data)-2+4], dtype=np.object)
    for i in range(len(data)-2+4):
        Bbasis = scipy.interpolate.BSpline.basis_element(data_padded[i:i+5])
        Bbasis = scipy.interpolate.PPoly.from_spline(Bbasis)
        coefs_shifted = Bbasis.c.T[3:7]
        basis[i] = PP_Cubic(idx=i, knots=data_padded[i:i+5], coefs=Bbasis.c.T[3:7])
    return basis


def get_basis_matrix(data, BSbasis):
    return np.array([basis(data) for basis in BSbasis]).T


def get_deriv_matrix(data, BSbasis):
    BSderiv = np.zeros_like(BSbasis)
    for i in range(len(BSbasis)):
        BSderiv[i] = BSbasis[i].differentiate()
    return np.array([deriv(data) for deriv in BSderiv]).T


def get_penalty_matrix(BSbasis):
    BSbasis = np.reshape(BSbasis, [len(BSbasis), 1])
    return (BSbasis % BSbasis.T).astype(np.float64)
