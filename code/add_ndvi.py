import matplotlib.pyplot as plt
import numpy as np
import laspy
import os

def calculate_ndvi(red, nir):
    red = np.array(red, dtype=np.float64)
    nir = np.array(nir, dtype=np.float64)
    
    return (nir - red) / (nir + red + 1e-8) # add small eps to avoid division by 0 


def main():
    
    #get pointcloud to look at
    input_file = os.path.join('data', 'bws_sq100.LAZ')
    output_file = os.path.join('data', 'test_small.LAZ')
    
    #open LAS
    with laspy.open(input_file) as f:
        las = f.read()
        #available data contains:
        #['X', 'Y', 'Z', 'intensity', 'return_number', 'number_of_returns', 'synthetic', 'key_point', 'withheld', 'overlap', 'scanner_channel', 'scan_direction_flag', 'edge_of_flight_line', 'classification', 'user_data', 'scan_angle', 'point_source_id', 'gps_time', 'red', 'green', 'blue', 'nir']

        red = las.red
        nir = las.nir

    ndvi = calculate_ndvi(red, nir)

    out_las = las
    out_las.add_extra_dim(laspy.ExtraBytesParams(name="ndvi", type=np.float32))
    out_las.ndvi = ndvi



if __name__ == "__main__":
    main()
    print(f'Successfully ran {os.path.basename(__file__)}!')
