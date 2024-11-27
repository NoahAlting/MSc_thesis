#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Point_set_3.h>
#include <CGAL/IO/read_points.h>
#include <CGAL/IO/read_las_points.h>

#include <CGAL/Surface_mesh.h>
#include <CGAL/alpha_wrap_3.h>

#include <CGAL/Real_timer.h>

#include <CGAL/cluster_point_set.h>
#include <CGAL/Polygon_mesh_processing/polygon_soup_to_polygon_mesh.h>
#include <CGAL/Polygon_mesh_processing/repair_polygon_soup.h>
#include <CGAL/Polygon_mesh_processing/triangulate_faces.h>

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>


typedef CGAL::Exact_predicates_inexact_constructions_kernel K;
typedef K::Point_3 Point;
typedef std::vector<Point> Point_range;

typedef CGAL::Point_set_3<Point>                         Point_set;
namespace PMP = CGAL::Polygon_mesh_processing;

typedef std::vector<std::size_t>  CGAL_Polygon;

using Mesh = CGAL::Surface_mesh<Point>;

///////////////////////////////////////////////////////////////////
//! [Analysis]

int main(int argc, char** argv)
{
    const std::string filename = (argc > 1) ? argv[1] : "tudcampus_sim.laz";

    std::cerr << "Reading input" << std::endl;
    Point_set points;
//    if (!(CGAL::IO::read_point_set(filename, points)))
    if (!(CGAL::IO::read_LAS(filename, points.point_back_inserter())))
    {
        std::cerr << "Error: cannot read " << filename << std::endl;
        return EXIT_FAILURE;
    }

    // Stream for STL
    std::stringstream stl;

    // compute clusters
    Point_set::Property_map<int> cluster_map = points.add_property_map<int>("cluster", 0).first;
    const double spacing = 0.5;
    int nb_clusters = 1;
//    std::size_t nb_clusters
//            = CGAL::cluster_point_set(points, cluster_map,
//                                      CGAL::parameters::neighbor_radius(spacing));
    std::cerr << "Clustering done, number of clusters: " << nb_clusters << std::endl;

    std::vector<Point> points_arr;
    std::vector<CGAL_Polygon> polygons;
    // Compute the alpha and offset values
    const double relative_alpha = (argc > 2) ? std::stod(argv[2]) : 1500.;
    const double relative_offset = (argc > 3) ? std::stod(argv[3]) : 2000.;
    for (std::size_t i = 0; i < nb_clusters; ++i) {
        std::vector<Point> pts;
        for (std::size_t j = 0; j < points.size(); ++j)
            if (cluster_map[i] == static_cast<int>(i))
                pts.push_back(points.point(j));
        if (pts.size() < 10) {
            std::cout << "Found less than 10 pts in cluster, skipping!" << std::endl;
            continue;
        }
        CGAL::Bbox_3 bbox = CGAL::bbox_3(std::cbegin(pts), std::cend(pts));
        const double diag_length = std::sqrt(CGAL::square(bbox.xmax() - bbox.xmin()) +
                                             CGAL::square(bbox.ymax() - bbox.ymin()) +
                                             CGAL::square(bbox.zmax() - bbox.zmin()));
        const double alpha = diag_length / relative_alpha;
        const double offset = diag_length / relative_offset;
        std::cout << "absolute alpha = " << alpha << " absolute offset = " << offset << std::endl;
        // Construct the wrap
        CGAL::Real_timer t;
        t.start();
        Mesh wrap;
        CGAL::alpha_wrap_3(pts, alpha, offset, wrap);

        t.stop();
        std::cout << "Result: " << num_vertices(wrap) << " vertices, " << num_faces(wrap) << " faces" << std::endl;
        std::cout << "Took " << t.time() << " s." << std::endl;

        //add wrap to mesh
        for (auto face: wrap.faces()) {
            CGAL_Polygon p;
            auto vertices = wrap.vertices_around_face(wrap.halfedge(face));
            for (auto vertex = vertices.begin(); vertex != vertices.end(); ++vertex) {
                points_arr.push_back(wrap.point(*vertex));
                p.push_back(points_arr.size() - 1);
            }
            polygons.push_back(p);
        }
    }
    //todo instead of clusters, use connected components at the end

    // soup to mesh
    Mesh newMesh;
    PMP::repair_polygon_soup(points_arr, polygons);
    PMP::orient_polygon_soup(points_arr, polygons);
    PMP::polygon_soup_to_polygon_mesh(points_arr, polygons, newMesh);
    PMP::triangulate_faces(newMesh);

    // Save the result
    std::string input_name = std::string(filename);
    input_name = input_name.substr(input_name.find_last_of("/") + 1, input_name.length() - 1);
    input_name = input_name.substr(0, input_name.find_last_of("."));
    std::string output_name = input_name + "_" + std::to_string(static_cast<int>(relative_alpha))
                              + "_" + std::to_string(static_cast<int>(relative_offset)) + ".obj";
    std::cout << "Writing to " << output_name << std::endl;


    CGAL::IO::write_polygon_mesh(output_name, newMesh, CGAL::parameters::stream_precision(17));
    return EXIT_SUCCESS;
}
