import os
import sys
import glob
import shutil

def flush_pipeline(case_name):
    if not os.path.exists(case_name):
        print(f"❌ Folder '{case_name}' does not exist.")
        return

    print(f"⚠️  This will delete all contents in '{case_name}' except files ending in 'original.laz'")
    confirm = input("Proceed? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("Aborted.")
        return

    for root, dirs, files in os.walk(case_name):
        for file in files:
            if not file.endswith("original.laz"):
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            shutil.rmtree(dir_path)
            print(f"Deleted folder: {dir_path}")

    print("✅ Flush complete.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python flush_pipeline.py <case_folder>")
    else:
        flush_pipeline(sys.argv[1])
