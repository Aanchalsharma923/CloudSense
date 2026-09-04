import os
import struct
import numpy as np
import argparse

def inspect_grd_file(filepath: str, inferred_x: int, inferred_y: int, year: int, inferred_missing: float):
    print(f"\n{'='*50}")
    print(f"Inspecting File: {filepath}")
    print(f"{'='*50}")
    
    # Check if file exists
    if not os.path.exists(filepath):
        print(f"[!] Error: File {filepath} does not exist.")
        return

    # 1. FILE SIZE AND DIMENSION VALIDATION
    file_size = os.path.getsize(filepath)
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days = 366 if is_leap else 365
    
    expected_values = days * inferred_x * inferred_y
    expected_bytes_direct = expected_values * 4
    
    # A single contiguous array for all days
    # Fortran sequential unformatted might wrap EACH array (day) or the entire chunk.
    # Typically, RECL=X*Y*4 means each record is 1 day.
    # For a day record: 4 byte marker + (X*Y*4) bytes + 4 byte marker = (X*Y*4 + 8) bytes.
    # Total for sequential = days * (X*Y*4 + 8)
    expected_bytes_sequential_daily = days * ((inferred_x * inferred_y * 4) + 8)
    
    print("--- 1. BYTE SIZE AND RECORD STRUCTURE ---")
    print(f"Actual File Size      : {file_size} bytes")
    print(f"Expected Direct Access: {expected_bytes_direct} bytes")
    print(f"Expected Seq (Daily)  : {expected_bytes_sequential_daily} bytes")
    
    structure = "UNKNOWN"
    if file_size == expected_bytes_direct:
        structure = "DIRECT ACCESS (Contiguous Float32)"
        print("[+] Match: File size matches contiguous Direct Access structure.")
    elif file_size == expected_bytes_sequential_daily:
        structure = "SEQUENTIAL ACCESS (Daily Record Markers)"
        print("[+] Match: File size matches Sequential Access with daily Fortran record markers.")
    else:
        print(f"[-] Mismatch: File size does not match inferred dimensions for {days} days ({inferred_x}x{inferred_y}).")
        
    # Read first and last 8 bytes to see if record markers exist
    with open(filepath, 'rb') as f:
        head = f.read(8)
        f.seek(-8, os.SEEK_END)
        tail = f.read(8)
    print(f"First 8 bytes (hex): {head.hex()}")
    print(f"Last 8 bytes (hex) : {tail.hex()}")

    # 2. ENDIANNESS TEST
    print("\n--- 2. ENDIANNESS & DISTRIBUTION TEST ---")
    if structure == "SEQUENTIAL ACCESS (Daily Record Markers)":
        print("[!] Sequential decoding not implemented in this inspector script yet. Assuming direct or reading raw bytes.")
    
    # Read raw as float32
    raw_bytes = np.fromfile(filepath, dtype=np.uint8)
    
    # Little-endian float32
    le_arr = np.frombuffer(raw_bytes, dtype='<f4')
    # Big-endian float32
    be_arr = np.frombuffer(raw_bytes, dtype='>f4')
    
    print(f"Total values read: {len(le_arr)}")
    
    def analyze_array(arr, name):
        # Exclude exact candidates for sentinels from min/max/mean to see real data distribution
        candidate_mask = np.isclose(arr, inferred_missing, rtol=1e-5, atol=1e-5)
        sentinel_count = np.sum(candidate_mask)
        valid_data = arr[~candidate_mask]
        
        # Also let's check for NaNs or Inf
        nan_count = np.sum(np.isnan(arr))
        inf_count = np.sum(np.isinf(arr))
        
        print(f"  [{name} Endian]")
        print(f"    - Sentinel candidates ({inferred_missing}) count: {sentinel_count}")
        print(f"    - NaN / Inf count: {nan_count} / {inf_count}")
        
        if len(valid_data) > 0:
            print(f"    - Valid Data Range: [{np.nanmin(valid_data):.2f}, {np.nanmax(valid_data):.2f}]")
            print(f"    - Valid Data Mean : {np.nanmean(valid_data):.2f}")
        else:
            print("    - Valid Data: NONE (all values are sentinel, NaN, or Inf)")
            
    analyze_array(le_arr, "Little")
    analyze_array(be_arr, "Big")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect Gridded Binary Files")
    parser.add_argument("--file", type=str, required=True, help="Path to GRD file")
    parser.add_argument("--x", type=int, required=True, help="Inferred X dimension")
    parser.add_argument("--y", type=int, required=True, help="Inferred Y dimension")
    parser.add_argument("--year", type=int, required=True, help="Year of data")
    parser.add_argument("--missing", type=float, required=True, help="Inferred missing value")
    args = parser.parse_args()
    
    inspect_grd_file(args.file, args.x, args.y, args.year, args.missing)
