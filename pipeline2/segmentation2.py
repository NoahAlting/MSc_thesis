# segmentation.py  –  unified single + tuning runner
# ---------------------------------------------------
import os
import subprocess
import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------- small helpers ------------------------------------------------
def next_index(csv_path: str) -> int:
    """Return how many rows already exist in CSV (0 if file missing)."""
    if os.path.exists(csv_path):
        return len(pd.read_csv(csv_path))
    return 0

# ---------- call the C++ binary ------------------------------------------
def run_segment_trees(exe: str, params, input_xyz: str, out_file: str):
    radius, vres, min_pts = params
    cmd = [exe, input_xyz, out_file, str(radius), str(vres), str(min_pts)]
    logger.info("Running: %s", " ".join(cmd))

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        logger.info("C++ stdout:\n%s", res.stdout or "<no stdout>")
        if res.stderr:
            logger.warning("C++ stderr:\n%s", res.stderr)

    except subprocess.CalledProcessError as e:
        logger.error("C++ failed (code %d)", e.returncode)
        logger.error("stdout:\n%s", e.stdout or "<no stdout>")
        logger.error("stderr:\n%s", e.stderr or "<no stderr>")
        return None

    return out_file



# ---------- CSV maintenance ----------------------------------------------
def create_or_update_csv(csv_path: str, out_dir: str, new_rows: list[dict]):
    """
    new_rows: [{'file':..., 'radius':..., 'vres':..., 'min_pts':...}, ...]
    """
    cols = ["File Name", "Radius", "Vertical Res",
            "Min Points", "Num Points", "tree_count"]
    df = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame(columns=cols)

    for row in new_rows:
        xyz_path = os.path.join(out_dir, row["file"])
        xyz_df   = pd.read_csv(xyz_path, sep=r"\s+", header=None,
                               names=["tree_id", "x", "y", "z"])
        num_pts  = len(xyz_df)
        tree_cnt = xyz_df["tree_id"].nunique()

        df.loc[len(df)] = [row["file"], row["radius"], row["vres"],
                           row["min_pts"], num_pts, tree_cnt]

    df.to_csv(csv_path, index=False)
    logger.info("CSV updated → %s  (rows=%d)", csv_path, len(df))

# ---------- single‑param run ---------------------------------------------
def run_single(data_dir, exe, input_xyz, out_dir, r, v, m, csv_path):
    os.makedirs(out_dir, exist_ok=True)

    idx     = next_index(csv_path)
    out_f   = os.path.join(out_dir, f"{data_dir}_{idx:04d}.xyz")
    success = run_segment_trees(exe, (r, v, m), input_xyz, out_f)

    if success:
        create_or_update_csv(csv_path, out_dir, [{
            "file":   os.path.basename(out_f),
            "radius": r, "vres": v, "min_pts": m
        }])

# ---------- parameter sweep ----------------------------------------------
def run_parallel(data_dir, exe, input_xyz, out_dir, cores,
                 r_vals, v_vals, m_vals, csv_path):
    os.makedirs(out_dir, exist_ok=True)

    combos    = list(product(r_vals, v_vals, m_vals))
    start_idx = next_index(csv_path)
    tasks     = []

    # pre‑assign filenames so every worker knows its final file
    for i, params in enumerate(combos):
        idx   = start_idx + i
        out_f = os.path.join(out_dir, f"{data_dir}_{idx:04d}.xyz")
        tasks.append((params, out_f))

    new_rows = []

    with ThreadPoolExecutor(max_workers=cores) as pool:
        for (params, out_f), result in tqdm(
                zip(tasks, pool.map(lambda t: run_segment_trees(
                    exe, t[0], input_xyz, t[1]), tasks)),
                total=len(tasks), desc="segmenting"):
            if result:
                r, v, m = params
                new_rows.append({
                    "file": os.path.basename(out_f),
                    "radius": r, "vres": v, "min_pts": m
                })

    if new_rows:
        create_or_update_csv(csv_path, out_dir, new_rows)

# ---------- main guard ----------------------------------------------------
if __name__ == "__main__":
    from shared_logging import setup_logging

    data_dir = "whm_100"                         # <‑ your dataset folder
    setup_logging(os.path.join(data_dir, "segmentation.log"), append=True)

    # windows exe: "segmentation_code\build_release\Release\segmentation.exe"
    # windows exe: .
    # exe = "./segmentation_code/build_release/Release/segmentation.exe"                    # C++ binary
    exe = "./segmentation_code/build/Debug/segmentation.exe"  

    xyz   = os.path.abspath(os.path.join(data_dir, "forest.xyz"))
    out_d = os.path.join(data_dir, "segmentation_results")
    csv   = os.path.join(data_dir, "segmentation_stats.csv")

    # parameter selection
    r_vals = [1000]
    v_vals = [500]
    m_vals = [3]
    cores  = 1

    if len(r_vals) == len(v_vals) == len(m_vals) == 1:
        run_single(data_dir, exe, xyz, out_d,
                   r_vals[0], v_vals[0], m_vals[0], csv)
    else:
        run_parallel(data_dir, exe, xyz, out_d, cores,
                     r_vals, v_vals, m_vals, csv)

    logger.info("Segmentation finished.")
    
    # Beep sound for Windows
    import platform

    if platform.system() == "Windows":
        import winsound
        for _ in range(3):  # three short beeps
            winsound.Beep(1000, 200)  # frequency (Hz), duration (ms)


