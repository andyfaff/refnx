import numba
import numpy as np
import cmath


def numba_parratt(
    q,
    slabs,
    scale=1.0,
    bkg=0.0,
    threads=numba.config.NUMBA_DEFAULT_NUM_THREADS,
):
    current_threads = numba.get_num_threads()
    if threads == -1:
        threads = numba.config.NUMBA_DEFAULT_NUM_THREADS

    numba.set_num_threads(threads)

    qvals = np.asarray(q).astype(float, copy=False)
    flatq = np.ravel(qvals)
    sld = slabs[:, 2] * 1j
    sld += slabs[:, 1]
    reflectivity = _numba_kernel(
        flatq, slabs[:, 0], sld, slabs[:, -1], scale, bkg
    )

    numba.set_num_threads(current_threads)

    return np.reshape(reflectivity, qvals.shape)


@numba.jit(
    numba.float64[:](
        numba.float64[:],
        numba.float64[:],
        numba.complex128[:],
        numba.float64[:],
        numba.float64,
        numba.float64,
    ),
    nopython=True,
    parallel=True,
    cache=True,
)
def _numba_kernel(q, d, sld, sigma, scale, bkg):
    nlayers = d.shape[0] - 2
    points = q.shape[0]

    R = np.empty_like(q)

    sld = np.pi * 4e-6 * (sld - sld[0])
    for qi in numba.prange(points):
        q2 = 0.25 * q[qi] ** 2
        kn = cmath.sqrt(q2 - sld[-2])
        kn_next = cmath.sqrt(q2 - sld[-1])
        # Fresnel reflectivity for the interfaces
        RRJ = RRJ_1 = (
            (kn - kn_next)
            / (kn + kn_next)
            * cmath.exp(-2.0 * kn * kn_next * sigma[-1] ** 2)
        )

        kn_next = kn
        for lj in range(nlayers - 1, -1, -1):
            kn = cmath.sqrt(q2 - sld[lj])
            # Fresnel reflectivity for the interfaces
            rj = (
                (kn - kn_next)
                / (kn + kn_next)
                * cmath.exp(-2.0 * kn * kn_next * sigma[lj + 1] ** 2)
            )
            beta = cmath.exp(-2.0j * kn_next * d[lj + 1])

            RRJ = (rj + RRJ_1 * beta) / (1.0 + RRJ_1 * beta * rj)
            RRJ_1 = RRJ
            kn_next = kn

        R[qi] = bkg + scale * np.abs(RRJ) ** 2
    return R
