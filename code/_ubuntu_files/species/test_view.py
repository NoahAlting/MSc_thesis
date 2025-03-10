import rerun as rr

rr.init("tree_visualization", spawn=False)  # Do NOT spawn a new viewer
rr.connect()  # Explicitly connect to the running Rerun viewer

# Log something basic to test:
rr.log("debug_test", rr.TextDocument("Hello, Rerun!"))

# Log your point cloud here
rr.log("tree_5", rr.Points3D(positions=[[0, 0, 0], [1, 1, 1], [2, 2, 2]]))  # Example data

print("Logged data to Rerun. Check the viewer.")
