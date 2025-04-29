#include <iostream>
#include <vector>
#include <sstream> // For stringstream
#include "FoxTree.h"

// Function to convert string to double
double to_double(const std::string& str) {
    std::stringstream ss(str);
    double value;
    ss >> value;
    return value;
}

// Function to convert string to int
int to_int(const std::string& str) {
    std::stringstream ss(str);
    int value;
    ss >> value;
    return value;
}

int main(int argc, char** argv) {
    if (argc < 6) {
        std::cerr << "Usage: ./segmentation <input_file> <output_file> <radius> <verticalResolution> <minPointsPerCluster>\n";
        return 1;
    }

    std::string input_file = argv[1];
    std::string output_file = argv[2];
    double radius = to_double(argv[3]);
    double verticalResolution = to_double(argv[4]);
    int minPointsPerCluster = to_int(argv[5]);

    std::vector<Point3D> points;
    Point3D tempPt;

    FILE* inFile = fopen(input_file.c_str(), "r");
    if (inFile) {
        while (!feof(inFile)) {
            fscanf(inFile, "%lf %lf %lf\n", &tempPt.x, &tempPt.y, &tempPt.z);
            points.push_back(tempPt);
        }
        fclose(inFile);
    } else {
        std::cerr << "Error: Could not open input file: " << input_file << std::endl;
        return 1;
    }

    std::cout << "Number of points loaded: " << points.size() << std::endl;

    std::cout << "Parameters: Radius=" << radius
              << ", VerticalResolution=" << verticalResolution
              << ", MinPointsPerCluster=" << minPointsPerCluster << std::endl;

    FoxTree* foxTree = new FoxTree(points, radius, verticalResolution, minPointsPerCluster);

    foxTree->separateTrees(1, 1);

    foxTree->outputTrees(output_file.c_str(), foxTree->m_nTrees);
    std::cout << "Finished" << std::endl;

    if (foxTree) delete foxTree; foxTree = nullptr;

    return 0;
}
