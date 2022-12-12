import numpy as np
import cv2 as cv
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import os
from multiprocessing import Pool
import sys



def apply_shifts_online_cust(fname, cnmf_fname):
    """
    apply the shifts from a given cnmf object to 
    the corresponding raw video file
    save the results to an F order memmap
    """
    
    import caiman as cm
    from caiman.source_extraction.cnmf import cnmf as cnmf
    cap = cv.VideoCapture(fname)
    fn = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    ht = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    wd = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    npix = int(ht * wd)
    shape = (npix, fn)
    if len(cnmf_fname) == 0:
        cnmf_fname = (Path(fname).parent/'cnmf.hdf5').as_posix()
    cnm = cnmf.load_CNMF(cnmf_fname)
    assert fn == cnm.estimates.C.shape[1], "cnmf shape does not match the number of frames in the provided video"
    shifts = cnm.estimates.shifts[-fn:]
    fname_new =(Path(fname).parent/f"{Path(fname).stem}_d1_{ht}_d2_{wd}_d3_1_order_F_frames_{fn}_.mmap").as_posix()
    f = np.memmap(fname_new, 
                  mode = 'w+',
                  shape = shape,
                  dtype = np.float32,
                  order = 'F')
    del f
    for i in tqdm(range(fn)):
        ret, fr = cap.read()
        _f = np.memmap(fname_new, dtype = "float32",
                       mode = 'r+', shape = (1, npix),
                       offset = int(i*npix*32/8),
                       order = 'F')
        _f[:] = cm.motion_correction.apply_shift_iteration(fr[:,:,0], shifts[i]).flatten(order = "F")
        del _f
    return fname_new

def print_fr(fpath):
    """
    function to print the frame rate to stdout
    for use in the bash script to get the frame
    rate of the provided video
    """
    cap = cv.VideoCapture(fpath)
    print(cap.get(cv.CAP_PROP_FPS))

def run_pipeline_online(fpath):
    """
    run the entire pipeline
    """
    
    import caiman as cm
    from caiman.source_extraction.cnmf import params as params
    from caiman.source_extraction.cnmf.online_cnmf import OnACID
    import logging
    import glob
    
    logging.basicConfig(format= "%(relativeCreated)12d [%(filename)s:%(funcName)20s():%(lineno)s]"\
                                "[%(process)d] %(message)s",
                        level=logging.INFO)
    
    if os.environ.get("SLURM_SUBMIT_DIR") is not None:
        sdir = os.environ.get("SLURM_SUBMIT_DIR")
        os.environ["SLURM_SUBMIT_DIR"] = Path(fpath).parent.as_posix()
    
    print(f"{str(datetime.now())}: loading parameters", flush = True)
    opts_dict = np.load("opts.npy", allow_pickle = True).item()
    opts_dict = {j: k for i in opts_dict.values() for j, k in i.items()}
    opts = params.CNMFParams(params_dict = opts_dict)
    cap = cv.VideoCapture(fpath)
    fr = int(cap.get(cv.CAP_PROP_FPS))
    opts = opts.change_params({'fnames': [fpath], 'fr': fr})    
    print(f"{str(datetime.now())}: setting up the cluster", flush = True)  
    c, dview, n_processes = cm.cluster.setup_cluster(backend='local', n_processes=None, single_thread=False)
    print(f"{str(datetime.now())}: instantiating the CNMF object")
    cnm = OnACID(params=opts, dview=dview)
    print(f"{str(datetime.now())}: running the pipeline", flush = True)
    cnm.fit_online()
    print(f"{str(datetime.now())}: saving CNMF-E results", flush = True)
    try:
        cnm.save((Path(fpath).parent/'cnmf.hdf5').as_posix())
    except ValueError:
        pass
    cm.stop_server(dview=dview)
    if 'sdir' in locals():
        os.environ["SLURM_SUBMIT_DIR"] = sdir
    log_files = glob.glob('Yr*_LOG_*')
    for log_file in log_files:
        os.remove(log_file)
    np.save((Path(fpath).parent/"opts.npy").as_posix(), opts.to_dict())

    
if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("method")
    parser.add_argument("-f", "--fpath", required = True)
    parser.add_argument("-t", "--t_hr_per_chunk", default = 2)
    parser.add_argument("-s", "--fname_stem", default = "chunk")
    parser.add_argument("-n", "--n_frames_skip", default = 4)
    parser.add_argument("-c", "--cnmf_path", default = "")
    args = parser.parse_args()
    if args.method == 'downsample':
        downsample(args.fpath, int(args.n_frames_skip))
    elif args.method == 'run_pipeline_online':
        run_pipeline_online(args.fpath)
    elif args.method == 'apply_shifts_online_cust':
        apply_shifts_online_cust(args.fpath, args.cnmf_path)
    elif args.method == 'print_fr':
        print_fr(args.fpath)
    else:
        raise ValueError("Unrecognized method")
        
    
    
    
