# Reduction steps performed by *refnx*

Here we give an overview of the reduction steps performed by *refnx* for **Platypus** and **Spatz** reflectometry data. The process for both instruments is generally the same, albeit with a gravity correction for **Platypus**.

## Obtaining an intensity/wavelength spectrum

The datasets are saved in an HDF file that requires the `h5py` package to load them. The datasets are loaded when a `refnx.reduce.PlatypusNexus` (or `SpatzNexus`) object is created. After this one uses the `PlatypusNexus.process` method to calculate the intensity wavelength spectrum. The steps below are listed in the order that they occur. At the end of all these steps there are several arrays of interest:

 - `m_topandtail`, a rebinned, background subtracted, detector image. Shape (N, T, Y). N is the number of detector images, T is the number of wavelength bins, and Y is the number of detector pixels
 - `m_spec`, intensity vs wavelength spectra.  Shape (N, T).
 - `m_lambda`, wavelengths. Shape (1, T).
 - `m_lambda_fwhm`, wavelength uncertainty. Shape (N, T).
 - `m_beampos`, beam centre, in pixels. Shape (N,). 

#### Error propagation

All array manipulations (background subtraction/rebinning/integration/etc) within the refnx reduction code propagate uncertainties using the functionality from the `refnx.util.ErrorProp` module.

#### Options for processing

There are detailed options for controlling how each dataset is processed. These are thoroughly outlined in the documentation for the `refnx.reduce.ReductionOptions` class. You supply a `ReductionOptions` object when the `PlatypusNexus.process` method is called.

### Loading the files and cataloguing what's in them

After loading the contents of the HDF5 file go through a cataloguing process that extracts all the relevant instrument parameters that will be needed to calculate the spectrum, such as: detector image, beam monitor counts, slit openings, distances between all components, chopper settings, spin flipper states, etc.
The detector image has shape (N, T, Y, X), where N is the number of images in the data, T is the number of time-of-flight (TOF) channels, Y is the number of y-pixels, X is the number of x-pixels. In general most of the arrays containing instrument settings have shape (N,).

### Average over unwanted direction

PLP doesn't need the horizontal direction on the detector for calculating a specular spectrum, and SPZ doesn't need the vertical direction. If the detector image has multiple pixels in those directions they are collapsed down into a single pixel, rendering the detector image as
(N, T, Y) for PLP and (N, T, X) for SPZ.

### Pixel efficiency normalisation by a flood field

A flood field measurement can be done with an H2O filled cuvette. H2O scatters fairly isotropically ('flat scatterer'). The flood field measurement is done with full x and y detector pixelisation. The normalisation array is calculated by summing over the same set of x pixels (PLP) or y pixels (SPZ) used in the actual measurement (those axes being the directions with little information unless one is doing GISANS).

Thus on PLP the normalisation array has shape (Y,), on SPZ the shape is (X,). The mean value of the normalisation array is 1. This assumes that the detector pixel efficiency is wavelength independent.

The detector image is then divided through by this normalisation array, which compensates for some pixels being more efficient than others.

### Calculate chopper-detector distance

The total flight length (CHOD) is measured from the mid-point of the chopper pair being used, to where the specular beam hits the detector. On SPZ this is independent of 2theta because the detector arm moves on an arc. On PLP CHOD the detector moves in a straight line up-and-down. While we know the horizontal sample-detector distance (adjacent), the beam travels along a hypotenuse, so larger 2theta have a longer CHOD for a given sample-detector distance. 
CHOD is calculated using the nominal omega, 2theta values.
The calculation is slightly different between the FOC/SB/DB operational modes on PLP.

### Calculate time-offsets

Each of the time bins in the detector image has a nominal TOF. In 24 Hz operation on PLP each time bin is usually 40 us wide, with 1000 time bins. The bin edges in the TOF array are therefore 0, 40 us, 80 us, 120 us, etc. These TOF values need to be corrected by an offset, to obtain the true flight time. The flight time is always defined as being when the neutrons pass the mid-point of the chopper pair being used.

There are a few contributions to this time offset:

`master_phase_offset` - this value corrects for an angular offset of where the T0 pulse is actually emitted by the master chopper compared to where it's nominally supposed to come from. The magnitude of this offset depends on chopper frequency.

`phase_angle_offset` - Normally a pair of choppers operates in an optically blind fashion, the leading edge of the 'following' chopper is lined up with the trailing edge of the master chopper. The T0 of all neutron wavelengths occurs at exactly the same time, at the mid-point between the master and following choppers. At zero phase angle this term is nominally 0.
If the phase angle is opened up then significantly more neutrons can be transmitted. Here, the neutrons pass the chopper-chopper mid-point at earlier times, and `phase_angle_offset` is no longer negligible.
On PLP the `phase_angle_offset` is wavelength dependent because neutrons travel parabolically due to gravity. This parabolic trajectory can lead to an apparent phase opening/closing, which is more significant for longer wavelengths.

Instrument calibrations are routinely done to determine the `master_phase_offset`, and the exact operating conditions under which the following chopper has zero phase angle. This information is stored in the HDF5 datafile, allowing the phase angle to be calculated.

### Conversion of TOF to lambda

The corrected TOF, CHOD, and de-Broglie's equation is used to calculate the wavelengths corresponding to each time bin.

### Gravity unwarping of detector image (PLP direct beams only)

Gravity causes neutrons to travel parabolically. In a PLP direct beam the long wavelength neutrons hit the detector significantly lower than short wavelength neutrons. Here we estimate this gravitational drop and 'unwarp' the detector image by shifting the long wavelength neutrons upwards (i.e. along the y detector direction). This means the vertical beam centre for each wavelength is at exactly the same place. 
This unwarping is not done for a PLP reflected beam because the gravitational droop causes long wavelength neutrons to have a higher angle of incidence than short wavelengths. Thus the vertical beam centres are approximately the same for short and long wavelengths.
This is not done for SPZ because of the horizontal scattering plane.

### Determination of specular ridge (beam centre) location

This identifies the detector pixels that are considered to come from the specular region, and which pixels are treated as coming from the background region. The specular ridge is also called the 'foreground' region. The beam centre will lie in the foreground region.
There are a few ways that these regions are found. In all cases the search is done with a detector image that has not been rebinned ((T, Y) for PLP and (T, X) for SPZ).

#### Automatic beam finder

The last 50 wavelength bins of a detector image are summed along the wavelength axis to render an array with full Y (PLP) or X (SPZ) pixelation. This array is modelled with a Gaussian to obtain a peak centre and width.
The same process then occurs with the last 100 wavelength bins, and then the last 150 wavelength bins, etc. 
If the peak centre and width are considered to have converged (aren't changing) between successive calls, then the last centre and width to be calculated are used as the beam location. 
This approach is designed to find the beam location using longer wavelengths. At shorter wavelengths (high Q) the specular ridge can be difficult to identify because of incoherent background, which makes the beam appear much wider than it actually is. We don't want to include those regions of incoherent scattering in the foreground region.
The width of the foreground region is four times the standard deviation of the gaussian peak. i.e. from two standard deviations above the beam centre (hipx) to two standard deviations below the beam centre (lopx). lopx and hipx are rounded to the nearest whole number. The beam centre is kept at full precision.
The background region starts from four pixels outside the foreground region and extends for two standard deviations of the peak width. There is a background region on either side of the foreground region.
If the automatic beam finder doesn't work, it can fall back to manual beam finding.

#### Manual beam finder

A GUI window displays two graphs. On the left hand side is the full detector image, on the right hand side is a 1-D graph where the detector image has been integrated along the wavelength axis for the last L wavelength bins. The user should choose L such that the 1-D graph does not include wavelength bins that have a significant amount of incoherent scattering. The extent of the foreground region is controlled by the user moving two blue lines that delimit the region (these lines are lopx and hipx). The user can also move two black lines that denote the outer extent of the background region. The beam centre and width are recalculated each time the foreground region lines are moved.

#### User specified peak centre and width

A user specified peak centre and width (`peak_pos`) are used to calculate the foreground (lopx, hipx) and background regions, similar to how the automatic beam finder uses those numbers.

#### User specified lopx, hipx

The user can specify the range of pixels in the foreground region (`lopx_hipx`). The beam centre is determined from one of the above methods. The beam centre must lie in-between lopx and hipx.

#### User specified background region

The user provides a boolean mask (`background_mask`) that specifies which Y/X pixels are considered to lie within a background region.

### Wavelength rebinning

The data acquisition occurs with narrow time bins. The narrowness of the time bins ensures that sufficient accuracy is retained, but can lead to noisiness in the wavelength spectrum. 
In this rebinning process adjacent wavelength bins are added together. Whilst this coarsens time/wavelength resolution, the noisiness in the spectrum is reduced because there are a much greater number of counts in each bin.
The rebinning process is done along the wavelength axis of the N-dimensional detector image.

The user can provide the `wavelength_bins` in an array. Alternatively, the wavelength bins are calculated from `lo_wavelength` to `hi_wavelength` using a `rebin_percent` parameter that controls how the bins are combined together.
The width of a bin centred at `lo_wavelength` is roughly `lo_wavelength * rebin_percent / 100`, with the widths of following bins being calculated as a geometric series (i.e. `1 + rebin_percent / 100` times the previous width). The rebin_percent is slightly adjusted such that the centres of the first and last bins are exactly `lo_wavelength` and `hi_wavelength`.

The neutrons are redistributed from their original bins into the new wavelength bins. If an original bin spans two new wavelength bins then the counts are divided between the two bins; such that the total number of counts in the spectrum remains the same.

### Spectrum normalisation by wavelength bin width

The intensity in each wavelength bin is divided by the width of the bin. This allows spectra processed with different `rebin_percent` to be directly compared.
We are still working with an N-D detector image at this point.

### Background subtraction

We attempt to subtract background signal from the specular signal. This is done after the detector image has been rebinned.
For a given wavelength bin the intensities of the pixels in the background regions are extracted. A straight line is fitted to intensity vs pixel number. This allows us to estimate the background contribution to the foreground region, as a function of foreground pixel number. This background contribution is subtracted. The uncertainty of the background contribution is determined from the confidence interval of the linear regression.

### Integration over the foreground region (i.e. integrate over specular beam)

Up until this point the array manipulations have been dealing with a detector image that has 3 dimensions, (N, T, Y). Here N is the number of detector images, T is the number of wavelength/time bins, Y is the number of detector pixels (or X on SPZ). We may have multiple detector images if we've been doing a scan, or been dealing with event mode acquisition.

In this step we sum the number of counts in the foreground region, between lopx and hipx, for a given wavelength bin. This is known as 'constant wavelength summation'.

This step gives an array of shape (N, T), i.e. there are N spectra, each of which has length T. This array will be denoted by `m_spec`

### Normalisation by beam monitor

We divide the detector image (N, T, Y) and `m_spec` by the beam monitor counts (shape=(N,)). This compensates for reactor power fluctuation.

### Calculation of wavelength resolution

The wavelength resolution has three main components:

 - burst time due to spacing between choppers. This gets larger as the distance between the choppers increases. It's also affected by phase opening.
 - crossing time, how quickly does a chopper cross a beam of finite height/width.
 - rebinning percentage, as this increases the wavelength resolution degrades.
