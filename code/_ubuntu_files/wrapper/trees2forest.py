import os

def merge_obj_files_in_folder(input_folder, output_file):
    # Collect all OBJ file paths from the folder and sort them
    obj_files = sorted(
        [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(".obj")]
    )
    
    global_vertices = []  # All vertices from all files
    groups = []           # List of (group_name, face_lines)
    vertex_offset = 0

    for i, filepath in enumerate(obj_files):
        group_name = f"tree_{i}"  # or use os.path.splitext(os.path.basename(filepath))[0]
        file_vertices = []
        file_faces = []

        with open(filepath, "r") as f:
            for line in f:
                if line.startswith("v "):
                    file_vertices.append(line)
                elif line.startswith("f "):
                    # Adjust each face's vertex indices by the current vertex_offset.
                    parts = line.strip().split()
                    new_face = ["f"]
                    for token in parts[1:]:
                        subparts = token.split("/")
                        try:
                            idx = int(subparts[0])
                        except ValueError:
                            continue
                        new_idx = idx + vertex_offset
                        # Rebuild token, preserving texture/normal if present.
                        new_token = str(new_idx)
                        if len(subparts) > 1:
                            new_token += "/" + "/".join(subparts[1:])
                        new_face.append(new_token)
                    file_faces.append(" ".join(new_face) + "\n")
        
        global_vertices.extend(file_vertices)
        groups.append((group_name, file_faces))
        vertex_offset += len(file_vertices)

    # Write the final merged file.
    with open(output_file, "w") as out:
        # Write all vertices first.
        for v in global_vertices:
            out.write(v)
        # Write each group's faces preceded by a group label.
        for group_name, faces in groups:
            out.write(f"g {group_name}\n")
            for face in faces:
                out.write(face)

    print(f"Merged {len(obj_files)} OBJ files into {output_file}")

if __name__ == "__main__":
    input_folder = "meshes"      # Folder containing individual tree OBJ files.
    output_file = "merged_trees.obj"  # Final merged OBJ file.
    merge_obj_files_in_folder(input_folder, output_file)
