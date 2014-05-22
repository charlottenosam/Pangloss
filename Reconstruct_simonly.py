#!/usr/bin/env python
# ======================================================================

import pangloss

import sys,getopt,cPickle,numpy
import matplotlib.pyplot as plt


# ======================================================================

def Reconstruct(argv):
    """
    NAME
        Reconstruct.py

    PURPOSE
        Read in a simulation lightcone (or list of lightcones) and compute all 
        quantities needed to estimate kappah, the convergence due to
        halos, at the centre of the lightcone. Output is a list of sample
        kappah values drawn from Pr(kappah|D), where D refers to either 
        observed data, or simulated data from a calibration line of
        sight.

    COMMENTS
        The config file contains the list of lightcones to be
        reconstructed, in the form of either a directory or a single
        instance. If a directory is specified, one also gives a number
        ("batchsize") of lightcones to be reconstructed at a time. 
        The number of kappah samples desired must also be given in the
        config file.

    FLAGS
        -h            Print this message [0]

    INPUTS
        configfile    Plain text file containing Pangloss configuration

    OUTPUTS
        stdout        Useful information
        samples       Catalog(s) of samples from Pr(kappah|D)

    EXAMPLE
        Reconstruct.py example.config

    BUGS
        - Code is incomplete.

    AUTHORS
      This file is part of the Pangloss project, distributed under the
      GPL v2, by Tom Collett (IoA) and  Phil Marshall (Oxford). 
      Please cite: Collett et al 2013, http://arxiv.org/abs/1303.6564

    HISTORY
      2013-03-21 started Collett & Marshall (Oxford)
    """

    # --------------------------------------------------------------------

    try:
       opts, args = getopt.getopt(argv,"h",["help"])
    except getopt.GetoptError, err:
       print str(err) # will print something like "option -a not recognized"
       print Reconstruct.__doc__  # will print the big comment above.
       return

    for o,a in opts:
       if o in ("-h", "--help"):
          print Reconstruct.__doc__
          return
       else:
          assert False, "unhandled option"

    # Check for setup file in array args:
    if len(args) == 1:
        configfile = args[0]
        print pangloss.doubledashedline
        print pangloss.hello
        print pangloss.doubledashedline
        print "Reconstruct: assigning halo mass to various lightcones"
        print "Reconstruct: taking instructions from",configfile
    else:
        print Reconstruct.__doc__
        return

    # --------------------------------------------------------------------
    # Read in configuration, and extract the ones we need:
    
    experiment = pangloss.Configuration(configfile)

    # Get the experiment name from the configfile name instead?
    EXP_NAME = experiment.parameters['ExperimentName']
    CALIB_DIR = experiment.parameters['CalibrationFolder'][0]
    
    Rc = experiment.parameters['LightconeRadius'] # in arcmin

    zd = experiment.parameters['StrongLensRedshift']
    zs = experiment.parameters['SourceRedshift']

    calpickles = []
    Nc = experiment.parameters['NCalibrationLightcones']
    for i in range(Nc):
        calpickles.append(experiment.getLightconePickleName('simulated',pointing=i))
       
    # Ray tracing:
    RTscheme = experiment.parameters['RayTracingScheme']
    
    # Sampling Pr(kappah|D):
    Ns = experiment.parameters['NRealisations']
    
    # Reconstruct calibration lines of sight?
    DoCal = experiment.parameters['ReconstructCalibrations']

    # --------------------------------------------------------------------
    # Make redshift grid:
    
    grid = pangloss.Grid(zd,zs,nplanes=100)
    
    # --------------------------------------------------------------------
    # Read in lightcones from pickles:

    calcones = []
    for i in range(Nc):
        calcones.append(pangloss.readPickle(calpickles[i]))

    if DoCal=="False": #must be string type
        calcones=[]
        calpickles=[]

    allcones = calcones
    allconefiles = calpickles 
    
    # --------------------------------------------------------------------
    # Set up kappa_smooth
    #kappa_smooth = 0.188247882068  # BORG
    kappa_smooth = 0.0716519068853 # Zach
    density = 1.2
    drange = 0.1
    
    # --------------------------------------------------------------------
    # Select only lightcones within certain number density limits
    subcones = []
    lc_num = []
    for i in range(len(allcones)):

        #print pangloss.dashedline
        #print "Reconstruct:   given data in "+allconefiles[i]

        # Get lightcone, and start PDF for its kappa_halo:
        lc = allcones[i] 
        
        lc_density = lc.countGalaxies()
        #print 'This lightcone is',lc_density,'times denser than the average...'
        
        if density - drange <= lc_density <= density + drange:
            subcones.append(allcones[i])
            lc_num.append(i)
    
    # --------------------------------------------------------------------
    # Make realisations using each lighcone of given number density, and store sample kappah vals:
    pk = pangloss.PDF('kappa_cone')
    pmu = pangloss.PDF('mu_cone')
    
    Nsub = len(subcones)
    
    print pangloss.dashedline
    print "Reconstruct: sampling %i LoS with number density ~ %.1f the average" % (Nsub, density)   
    print pangloss.dashedline
    
    for j in range(Nsub):        
         
        lc = subcones[j]
        
        # Redshift scaffolding:
        lc.defineSystem(zd,zs)
        lc.loadGrid(grid)

        # Figure out data quality etc:
        lc.configureForSurvey(experiment)

        if j % 50 == 0 and j !=0:
            print ("Reconstruct: ...on sample %i out of %i..." % (j,Nsub))

        lc.snapToGrid(grid)
            
        # Draw c from Mhalo:
        lc.drawConcentrations(errors=True)
            
        # Compute each halo's contribution to the convergence:
        lc.makeKappas(truncationscale=5)
            
        k_add=lc.combineKappas()
        mu_add=lc.combineMus()
    
            
        pmu.append([lc.mu_add_total])
        pk.append([lc.kappa_add_total])

            
        # Make a nice visualisation of one of the realisations, in
        # two example cases:
        if j ==0 and (lc.flavor == 'real' or i == 0):
            lc.plot('kappa', output=CALIB_DIR+"example_snapshot_kappa_uncalib.png")
            lc.plot('mu', output=CALIB_DIR+"example_snapshot_mu_uncalib.png")

          #  print "Reconstruct: saved visualisation of uncalibrated lightcone..."
            
 
        x = allconefiles[lc_num[j]]


    # --------------------------------------------------------------------
        
        # Pickle this lightcone's PDF:

        pfile = x.split('.')[0].split("_lightcone")[0]+"_"+EXP_NAME+"_PofKappah.pickle"
        pangloss.writePickle(pk,pfile)

     #   print "Reconstruct: Pr(kappah|D) saved to "+pfile
        
    # --------------------------------------------------------------------
    
    outputfile = "figs/"+EXP_NAME+"_n"+str(density)+"_PofKappa" 
               
    #pmu.plot('mu_cone', mean=(1.+2*kappa_smooth), density=num_density, output=x.split('.')[0].split("_lightcone")[0]+"_"+EXP_NAME+"_PofMu.png")
    pk.plot('kappa_cone', smooth=0, density=density, output=outputfile+"_uncalib.png", title=r'All LoS with $\xi \sim$'+str(density)+r', no $\kappa_{smooth}$ correction')    
    pk.plot('kappa_cone', smooth=kappa_smooth, density=density, output=outputfile+"_kappasmooth.png", title=r'All LoS with $\xi \sim$'+str(density)+r', with $\kappa_{smooth}$ correction')
    
    print pangloss.doubledashedline
    print "Reconstruct: saved P(kappa) to",outputfile

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -   
    
    print pangloss.doubledashedline
    return

# ======================================================================

if __name__ == '__main__': 
    Reconstruct(sys.argv[1:])

# ======================================================================
