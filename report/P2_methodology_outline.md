# P2 methodology outline

## step 1: get the pointcloud of area

- which pointcloud? AHN4/AHN5
- which area?


## step 2: filter pointcloud

- remove non vegetation  
    - remove last returns
        - mostly for grass/ground stuff
    - remove single returns
        - some points would be vegetation but its a small price

- use classification? (not always available so rather not imo)    

- use NDVI?


## step 3: segment trees

### step 3A: voxelize
- use voxelized return numbers method to get to LAI per voxel

### step 3B: Machine learning
- use machine learning with vegetation features to separate tree species


## step 4: reconstruct trees

- watershed algorithm?

- alpha wrap?

## step 5: assign porosities to trees

- find appropriate porosities
    - use LAI and/or other values




## step 6: mesh the trees

- to confirm if its usable in cfd