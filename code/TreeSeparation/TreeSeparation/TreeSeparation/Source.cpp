/*
*	Copyright (C) 2016 by
*       Jinhu Wang (jinhu.wang@tudelft.nl)
*       Roderik Lindenbergh (r.c.lindenbergh@tudelft.nl) [http://doris.tudelft.nl/~rlindenbergh/]
*       Laser and Optical Remote Sensing
*	Dept. of Geoscience and Remote Sensing
*	TU Delft, https://tudelft.nl
*
*	This is free software; you can redistribute it and/or modify
*	it under the terms of the GNU General Public License Version 3
*	as published by the Free Software Foundation.
*
*	TreeSeparation is distributed in the hope that it will be useful,
*	but WITHOUT ANY WARRANTY; without even the implied warranty of
*	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
*	GNU General Public License for more details.
*
*	You should have received a copy of the GNU General Public License
*	along with this program. If not, see <http://www.gnu.org/licenses/>.
*/


#include<iostream>

#include"FoxTree.h"


void main()
{
	std::vector<Point3D> points;
	Point3D tempPt;

	//Reading points from ASCII formated file;
	FILE* inFile = fopen("../TestDatasets/whm_002_filtered.xyz", "r");
	if (inFile)
	{
		while (!feof(inFile))
		{
			fscanf(inFile, "%lf %lf %lf\n",
				&tempPt.x, &tempPt.y, &tempPt.z);
			points.push_back(tempPt);
		}
		fclose(inFile);
	}
	else
	{
		std::cout << "There was an error in data loading..." << std::endl;
		return; 
	} 

	std::cout << "Number of points loaded: " << points.size() << std::endl;

	//Parameters
	const double radius = 2000.0; // 1.0
	const double verticalResolution = 100.0; // 0.7
	const int miniPtsPerCluster = 3; // 3

	// print used parameters
    std::cout << "Parameters: Radius=" 	<< radius 
			  << ", VerticalResolution=" << verticalResolution
              << ", MinPointsPerCluster=" << miniPtsPerCluster 
			  << std::endl;


	//Initialization
	FoxTree* foxTree = new FoxTree(points, radius, verticalResolution, miniPtsPerCluster);

	//Topdown direction
	foxTree->separateTrees(1, 1);

	//Output separation results
	foxTree->outputTrees("../TestDatasets/whm_002_segmented.xyz", foxTree->m_nTrees); 
	std::cout << "Finished" << std::endl;

	if (foxTree) delete foxTree; foxTree = nullptr;
}
