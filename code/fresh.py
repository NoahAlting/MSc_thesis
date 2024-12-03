import numpy as np
import rerun as rr
import laspy
import os


def get_ndvi(red, nir):
    red = np.array(red, dtype=np.float64)
    nir = np.array(nir, dtype=np.float64)

    red = red / 65535
    nir = nir / 255

    return (nir - red) / (nir + 1e-8)


def main():
    input_file = os.path.join('data', 'bws_500.LAZ')

    with laspy.open(input_file) as f:
        las = f.read()

        red = las.red
        nir = las.nir

    ndvi = get_ndvi(red, nir)

    # Copy pointcloud and do calculations on the copy
    out_las = las
    out_las.add_extra_dim(laspy.ExtraBytesParams(name='ndvi', type=np.float32))
    out_las.ndvi = ndvi

    # Filter 1: Filter out points with NDVI value under threshold
    ndvi_threshold = -0.1
    out_las = out_las[out_las.ndvi > ndvi_threshold]

    # Filter 2: Remove points with single return
    out_las = out_las[out_las.number_of_returns > 1]

    # Filter 3: Remove last return of all remaining points
    out_las = out_las[out_las.return_number != out_las.number_of_returns]

    # Convert LAS data to numpy array for visualization
    xyz = np.vstack((out_las.x, out_las.y, out_las.z)).transpose()
    colors = np.vstack((out_las.red, out_las.green, out_las.blue)).transpose() / 65535.0  # Normalize colors

    # Initialize Rerun for visualization
    rr.init("PointCloud Visualization", spawn=True)

    # Log point cloud with positions and colors
    rr.log("point_cloud", rr.Points3D(positions=xyz, colors=colors))

    print("Point cloud logged to Rerun Viewer!")

if __name__ == "__main__":
    main()
