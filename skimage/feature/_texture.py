"""
Methods to characterize image textures.
"""

import math
import numpy as np
from scipy import ndimage

from ._greycomatrix import _glcm_loop


def greycomatrix(image, distances, angles, levels=256, symmetric=False,
                 normed=False):
    """Calculate the grey-level co-occurrence matrix.

    A grey level co-occurence matrix is a histogram of co-occuring
    greyscale values at a given offset over an image.

    Parameters
    ----------
    image : array_like of uint8
        Integer typed input image. The image will be cast to uint8, so
        the maximum value must be less than 256.
    distances : array_like
        List of pixel pair distance offsets.
    angles : array_like
        List of pixel pair angles in radians.
    levels : int, optional
        The input image should contain integers in [0, levels-1],
        where levels indicate the number of grey-levels counted
        (typically 256 for an 8-bit image). The maximum value is
        256.
    symmetric : bool, optional
        If True, the output matrix `P[:, :, d, theta]` is symmetric. This
        is accomplished by ignoring the order of value pairs, so both
        (i, j) and (j, i) are accumulated when (i, j) is encountered
        for a given offset. The default is False.
    normed : bool, optional
        If True, normalize each matrix `P[:, :, d, theta]` by dividing
        by the total number of accumulated co-occurrences for the given
        offset. The elements of the resulting matrix sum to 1. The
        default is False.

    Returns
    -------
    P : 4-D ndarray
        The grey-level co-occurrence histogram. The value
        `P[i,j,d,theta]` is the number of times that grey-level `j`
        occurs at a distance `d` and at an angle `theta` from
        grey-level `i`. If `normed` is `False`, the output is of
        type uint32, otherwise it is float64.

    References
    ----------
    .. [1] The GLCM Tutorial Home Page,
           http://www.fp.ucalgary.ca/mhallbey/tutorial.htm
    .. [2] Pattern Recognition Engineering, Morton Nadler & Eric P.
           Smith
    .. [3] Wikipedia, http://en.wikipedia.org/wiki/Co-occurrence_matrix


    Examples
    --------
    Compute 2 GLCMs: One for a 1-pixel offset to the right, and one
    for a 1-pixel offset upwards.

    >>> image = np.array([[0, 0, 1, 1],
    ...                   [0, 0, 1, 1],
    ...                   [0, 2, 2, 2],
    ...                   [2, 2, 3, 3]], dtype=np.uint8)
    >>> result = greycomatrix(image, [1], [0, np.pi/2], levels=4)
    >>> result[:, :, 0, 0]
    array([[2, 2, 1, 0],
           [0, 2, 0, 0],
           [0, 0, 3, 1],
           [0, 0, 0, 1]], dtype=uint32)
    >>> result[:, :, 0, 1]
    array([[3, 0, 2, 0],
           [0, 2, 2, 0],
           [0, 0, 1, 2],
           [0, 0, 0, 0]], dtype=uint32)

    """

    assert levels <= 256
    image = np.ascontiguousarray(image)
    assert image.ndim == 2
    assert image.min() >= 0
    assert image.max() < levels
    image = image.astype(np.uint8)
    distances = np.ascontiguousarray(distances, dtype=np.float64)
    angles = np.ascontiguousarray(angles, dtype=np.float64)
    assert distances.ndim == 1
    assert angles.ndim == 1

    P = np.zeros((levels, levels, len(distances), len(angles)),
                 dtype=np.uint32, order='C')

    # count co-occurences
    _glcm_loop(image, distances, angles, levels, P)

    # make each GLMC symmetric
    if symmetric:
        Pt = np.transpose(P, (1, 0, 2, 3))
        P = P + Pt

    # normalize each GLMC
    if normed:
        P = P.astype(np.float64)
        glcm_sums = np.apply_over_axes(np.sum, P, axes=(0, 1))
        glcm_sums[glcm_sums == 0] = 1
        P /= glcm_sums

    return P


def greycoprops(P, prop='contrast'):
    """Calculate texture properties of a GLCM.

    Compute a feature of a grey level co-occurrence matrix to serve as
    a compact summary of the matrix. The properties are computed as
    follows:

    - 'contrast': :math:`\\sum_{i,j=0}^{levels-1} P_{i,j}(i-j)^2`
    - 'dissimilarity': :math:`\\sum_{i,j=0}^{levels-1}P_{i,j}|i-j|`
    - 'homogeneity': :math:`\\sum_{i,j=0}^{levels-1}\\frac{P_{i,j}}{1+(i-j)^2}`
    - 'ASM': :math:`\\sum_{i,j=0}^{levels-1} P_{i,j}^2`
    - 'energy': :math:`\\sqrt{ASM}`
    - 'correlation':
        .. math:: \\sum_{i,j=0}^{levels-1} P_{i,j}\\left[\\frac{(i-\\mu_i) \\
                  (j-\\mu_j)}{\\sqrt{(\\sigma_i^2)(\\sigma_j^2)}}\\right]


    Parameters
    ----------
    P : ndarray
        Input array. `P` is the grey-level co-occurrence histogram
        for which to compute the specified property. The value
        `P[i,j,d,theta]` is the number of times that grey-level j
        occurs at a distance d and at an angle theta from
        grey-level i.

    prop : {'contrast', 'dissimilarity', 'homogeneity', 'energy', \
            'correlation', 'ASM'}, optional
        The property of the GLCM to compute. The default is 'contrast'.

    Returns
    -------
    results : 2-D ndarray
        2-dimensional array. `results[d, a]` is the property 'prop' for
        the d'th distance and the a'th angle.

    References
    ----------
    .. [1] The GLCM Tutorial Home Page,
           http://www.fp.ucalgary.ca/mhallbey/tutorial.htm

    Examples
    --------
    Compute the contrast for GLCMs with distances [1, 2] and angles
    [0 degrees, 90 degrees]

    >>> image = np.array([[0, 0, 1, 1],
    ...                   [0, 0, 1, 1],
    ...                   [0, 2, 2, 2],
    ...                   [2, 2, 3, 3]], dtype=np.uint8)
    >>> g = greycomatrix(image, [1, 2], [0, np.pi/2], levels=4,
    ...                  normed=True, symmetric=True)
    >>> contrast = greycoprops(g, 'contrast')
    >>> contrast
    array([[ 0.58333333,  1.        ],
           [ 1.25      ,  2.75      ]])

    """

    assert P.ndim == 4
    (num_level, num_level2, num_dist, num_angle) = P.shape
    assert num_level == num_level2
    assert num_dist > 0
    assert num_angle > 0

    # create weights for specified property
    I, J = np.ogrid[0:num_level, 0:num_level]
    if prop == 'contrast':
        weights = (I - J) ** 2
    elif prop == 'dissimilarity':
        weights = np.abs(I - J)
    elif prop == 'homogeneity':
        weights = 1. / (1. + (I - J) ** 2)
    elif prop in ['ASM', 'energy', 'correlation']:
        pass
    else:
        raise ValueError('%s is an invalid property' % (prop))

    # compute property for each GLCM
    if prop == 'energy':
        asm = np.apply_over_axes(np.sum, (P ** 2), axes=(0, 1))[0, 0]
        results = np.sqrt(asm)
    elif prop == 'ASM':
        results = np.apply_over_axes(np.sum, (P ** 2), axes=(0, 1))[0, 0]
    elif prop == 'correlation':
        results = np.zeros((num_dist, num_angle), dtype=np.float64)
        I = np.array(range(num_level)).reshape((num_level, 1, 1, 1))
        J = np.array(range(num_level)).reshape((1, num_level, 1, 1))
        diff_i = I - np.apply_over_axes(np.sum, (I * P), axes=(0, 1))[0, 0]
        diff_j = J - np.apply_over_axes(np.sum, (J * P), axes=(0, 1))[0, 0]

        std_i = np.sqrt(np.apply_over_axes(np.sum, (P * (diff_i) ** 2),
                                           axes=(0, 1))[0, 0])
        std_j = np.sqrt(np.apply_over_axes(np.sum, (P * (diff_j) ** 2),
                                           axes=(0, 1))[0, 0])
        cov = np.apply_over_axes(np.sum, (P * (diff_i * diff_j)),
                                 axes=(0, 1))[0, 0]

        # handle the special case of standard deviations near zero
        mask_0 = std_i < 1e-15
        mask_0[std_j < 1e-15] = True
        results[mask_0] = 1

        # handle the standard case
        mask_1 = mask_0 == False
        results[mask_1] = cov[mask_1] / (std_i[mask_1] * std_j[mask_1])
    elif prop in ['contrast', 'dissimilarity', 'homogeneity']:
        weights = weights.reshape((num_level, num_level, 1, 1))
        results = np.apply_over_axes(np.sum, (P * weights), axes=(0, 1))[0, 0]

    return results


def bit_rotate_right(value, length):
    """Cyclic bit shift to the right.

    Parameters
    ----------
    value : int
        integer value to shift
    length : int
        number of bits of integer

    """
    return (value >> 1) | ((value & 1) << (length - 1))


def local_binary_pattern(image, P, R, method='default'):
    """Texture classification using gray scale and rotation invariant LBP
    (Local Binary Patterns).

    Parameters
    ----------
    image : NxM array
        graylevel image
    P : int
        number of circularly symmetric neighbor set points (quantization of the
        angular space)
    R : float
        radius of circle (spatial resolution of the operator)
    method : {'default', 'ror', 'uniform', 'var'}
        method to determine the pattern::
        * 'default': original local binary pattern which is gray scale but not
            rotation invariant.
        * 'ror': extension of default implementation which is gray scale and
            rotation invariant.
        * 'uniform': improved rotation invariance with uniform patterns and
            finer quantization of the angular space which is gray scale and
            rotation invariant.
        * 'var': rotation invariant variance measures of the contrast of local
            image texture which is rotation but not gray scale invariant.

    Returns
    -------
    output : NxM array
        LBP image

    References
    ----------
    Timo Ojala, Matti Pietikainen, Topi Maenpaa. Multiresolution Gray-Scale and
        Rotation Invariant Texture Classification with Local Binary Patterns.
        http://www.rafbis.it/biplab15/images/stories/docenti/Danielriccio/\
        Articoliriferimento/LBP.pdf, 2002.
    """
    method = method.lower()
    # texture weights
    weights = 2 ** np.arange(P)
    # local position of texture elements
    rp = - R * np.sin(2 * math.pi * np.arange(P) / P)
    cp = R * np.cos(2 * math.pi * np.arange(P) / P)
    coords = np.vstack([rp, cp]) + math.ceil(R)
    # maximum size of neighbourhood for filtering
    max_size = 2 * math.ceil(R) + 1
    # center index of flattened neightbourhood
    center_index = (max_size ** 2 - 1) / 2

    if method == 'ror':
        # allocate array for rotation invariance
        rotation_chain = np.zeros(P, dtype='int')

    def compute_lbp(texture):
        # subtract value of center pixel
        texture -= texture[center_index]
        #: get texture elements using bilinear interpolation
        texture = texture.reshape(max_size, max_size)
        texture = ndimage.map_coordinates(texture, coords, order=1)

        #: signed / thresholded texture
        signed = texture.copy()
        signed[signed >= 0] = 1
        signed[signed < 0] = 0

        if method in ('uniform', 'var'):
            #: determine number of 0 - 1 changes
            changes = np.sum(np.abs(np.diff(signed)))

            if changes <= 2:
                lbp = np.sum(signed)
            else:
                lbp = P + 1

            if method == 'var':
                lbp /= np.var(texture)
        else:

            # method == 'default'
            lbp = np.sum(signed * weights)

            if method == 'ror':
                #: shift LBP P times to the right and get minimum value
                rotation_chain[0] = lbp
                for i in xrange(1, P):
                    rotation_chain[i] = \
                        bit_rotate_right(rotation_chain[i - 1], P)
                lbp = np.min(rotation_chain)

        return lbp

    dtype = 'int'
    if method == 'var':
        dtype = 'float'
    output = np.zeros(image.shape, dtype)

    ndimage.generic_filter(image, compute_lbp, size=(max_size, max_size),
                           mode='constant', cval=0, output=output)

    return output
