# Reduction steps performed by *refnx*

Here we give an overview of the reduction steps performed by *refnx* for **Platypus** and **Spatz** reflectometry data. The process for both instruments is generally the same, albeit with a gravity correction for **Platypus**.

## Obtaining an intensity/wavelength spectrum

The datasets are saved in an HDF file that requires the `h5py` package to load them. The datasets are loaded when a `refnx.reduce.PlatypusNexus` (or `SpatzNexus`) object is created. After this one uses the `PlatypusNexus.process` method to calculate the intensity wavelength spectrum. 

### Error propagation

All array manipulations within the refnx reduction code propagate uncertainties using the functionality from the `refnx.util.ErrorProp` module.

### Options for processing

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

### Determination of specular ridge location

